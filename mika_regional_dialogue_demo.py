
import asyncio
import attr

import mika_svgui
import styleml.core, styleml.macro_ext, styleml.portal_ext, styleml.convenient_argument
import styleml_mika_exts, styleml_glyph_exts
import mika_yaml_dialogue

import mika_regional_dialogue

import mika_modules

from utilities import Vector2D

from js import jQuery as jq

scr = mika_svgui.SVGGameScreen()

jq("body").append(scr.jq_svg)

styleml_parser = styleml.core.StyleMLCoreParser(
    ext_parser=[
        mika_regional_dialogue.InterSentenceCallExtParser(),
        styleml.portal_ext.PortalExtParser(),
        styleml_glyph_exts.GlyphsetExtParser(),
        styleml_mika_exts.AnimationExtParser(initial_tick=0.07),
        styleml_mika_exts.StyleExtParser(),
        styleml.core.ReturnCharExtParser()
    ]
)

speech_region = mika_regional_dialogue.ScreenRegion(
    size=Vector2D(25, 5),
    origin=Vector2D(0, 5)
)

map_region = mika_regional_dialogue.ScreenRegion(
    size=Vector2D(25, 5),
    origin=Vector2D(0, 0)
)

manager = mika_regional_dialogue.RegionalDialogueManager(
    sentences=mika_yaml_dialogue.parse_mikad_module("a.c", r"""
.char:
    default:
        region_conv: "=speech"
    st:
        - 
            content_tokens: 今天是个好日子
            pause_after_conv: "-"
            uninterruptable_conv: "+"
        - '心想的事儿都能成，\stcallsync[=a.c.call.0]心想的事儿都能成'
.call:
    default:
        region_conv: "=map"
    st:
        - 你好我好大家好
        - 他好我也好
.mmm:
    default:
        region_conv: "=map"
    st:
        -
            _template: choice
            desc: 描述
            choices:
                - j,.<c.char.0,走
                - j,.,此
"""
    ),
    screen_regions={
        "speech": speech_region,
        "map": map_region
    },
    macro_parser=styleml.macro_ext.MacroExtParser(),
    postmacro_parser=styleml_parser,
    current_sentence_name="a.c.char.0"
)

def clear_region(region_name):
    region = manager.screen_regions[region_name]
    for y in range(region.size.y):
        for x in range(region.size.x):
            pos = region.origin + Vector2D(x, y)
            scr.print_cell(pos, None)

@attr.s
class AnimationWrapper:
    task = attr.ib(default=None)
    ongoing = attr.ib(default=False)
    finished = attr.ib(default=False)
    finished_event = attr.ib(default=asyncio.Event())
    meta = attr.ib(factory=dict)

    async def wrapper_task(self):
        try:
            self.ongoing = True
            await asyncio.create_task(self.task)
            self.finished = True
            self.finished_event.set()
        except Exception:
            import traceback
            traceback.print_exc()
    
    def start(self):
        return asyncio.create_task(self.wrapper_task())

@attr.s
class AnimationManager:
    pool = attr.ib(factory=dict)
    next_id = attr.ib(default=0)
    
    def add_animation(self, anim):
        this_id = self.next_id
        self.pool[this_id] = anim
        self.next_id += 1
        return this_id
    
    async def pool_wrapper(self, anim_id):
        await self.pool[anim_id].start()
        self.pool.pop(anim_id)
    
    def start_animation(self, anim_id):
        return asyncio.create_task(self.pool_wrapper(anim_id))

@attr.s
class InterSentenceWaiter:
    interrupted = attr.ib(default=False)
    instant = attr.ib(default=False)
    update_event = attr.ib(factory=asyncio.Event)
    async_inter_sentence_caller = attr.ib(default=None)
    base_sentence_name = attr.ib(default=None)
    
    async def __call__(self, time, t=None):
        if self.interrupted:
            return False
        if isinstance(t, mika_regional_dialogue.InterSentenceCallToken):
            is_sync, target = t.value["is_sync"], t.value["target"]
            task = asyncio.create_task(self.async_inter_sentence_caller(
                mika_modules.resolve_module_ref(self.base_sentence_name, target),
                instant=self.instant,
                macros=t.meta["macros"]
            ))
            if is_sync:
                await task
        if self.instant:
            return True
        done, pending = await asyncio.wait([
            asyncio.create_task(asyncio.sleep(time)),
            asyncio.create_task(self.update_event.wait()),
        ], return_when=asyncio.FIRST_COMPLETED) # 保证中断事件触发时立刻中断
        for t in pending: # 清除多余任务
            t.cancel()
        if self.interrupted:
            return False
        return True

animation_pool = AnimationManager()

def add_print_tokens_animation(tokens, base_sentence_name, meta, instant=False):
    waiter = InterSentenceWaiter(
        async_inter_sentence_caller=async_inter_sentence_caller,
        base_sentence_name=base_sentence_name,
        instant=instant
    )
    meta["waiter"] = waiter
    return animation_pool.add_animation(
        AnimationWrapper(
            scr.async_print_tokens(
                tokens, origin=Vector2D(0, 0), waiter=waiter
            ),
            meta=meta
        )
    )

async def async_inter_sentence_caller(sentence_name, instant=False, macros=None):
    fork_manager = manager.fork_from_inter_sentence_call(sentence_name=sentence_name, macros=macros)
    await consequent_next_sentence(fork_manager, first=True, skip_pause=True, instant=instant)

async def render_current_sentence(manager, instant=False):
    try:
        if manager.current_conv("clear_region_conv"):
            clear_region(manager.current_conv("region_conv"))
        i = add_print_tokens_animation(
            manager.eval_sentence(),
            manager.current_sentence_name,
            meta={"sentence_name": manager.current_sentence_name},
            instant=instant
        )
        await animation_pool.start_animation(i)
    except Exception:
        import traceback
        traceback.print_exc()

async def consequent_next_sentence(manager, first=False, skip_pause=False, instant=False):
    if not first:
        try:
            manager.next_sentence()
        except IndexError:
            return
    while True:
        await render_current_sentence(manager, instant=instant)
        if manager.current_conv("pause_after_conv") and not skip_pause:
            break
        try:
            manager.next_sentence()
        except IndexError:
            return

def main_start_next_sentence(first=False):
    asyncio.create_task(consequent_next_sentence(manager, first=first))

def try_skip_animation():
    for anim_id, wrapper in animation_pool.pool.items():
        if not manager.eval_conv(wrapper.meta["sentence_name"], "uninterruptable_conv"):
            wrapper.meta["waiter"].instant = True
            wrapper.meta["waiter"].update_event.set()
        
main_start_next_sentence(True)

def _():
    if len(animation_pool.pool) > 0:
        try_skip_animation()
    else:
        main_start_next_sentence()

scr.registered_onkeypress.append(lambda key, ctrl, shift, alt: _())
