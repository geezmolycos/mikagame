
from mika_screen import Vector2D, List2D, Cardinal, ScreenCell
# from mika_htmlui import HTMLGameScreen
from mika_svgui import SVGGameScreen

from styleml.core import StyleMLCoreParser, ReturnCharExtParser
from styleml.portal_ext import PortalExtParser
from styleml.macro_ext import MacroExtParser
from styleml_mika_exts import StyleExtParser, AnimationExtParser, LineWrapExtParser
from styleml_glyph_exts import GlyphsetExtParser

from pyodide import create_proxy
from js import jQuery as jq

import asyncio

import attr

@attr.s
class Waiter:
    interrupted = attr.ib(default=False)
    instant = attr.ib(default=False)
    update_event = attr.ib(factory=asyncio.Event)
    
    async def __call__(self, time, t=None):
        if self.interrupted:
            return False
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

ui = SVGGameScreen()

styleml_parser = StyleMLCoreParser(
    ext_parser=[
        MacroExtParser(),
        PortalExtParser(),
        GlyphsetExtParser(),
        AnimationExtParser(),
        StyleExtParser(),
        ReturnCharExtParser(),
        LineWrapExtParser(cr_area=Vector2D(20, 0))
        ]
    )

jq("body").append(ui.jq_svg)

caret_pos = Vector2D(0, 0)
highlight_pos = Vector2D(0, 0)
def cat(key, ctrl, shift, alt):
    global caret_pos, highlight_pos
    if key[:3] == "Key":
        ch = key[3] if shift else key[3].lower()
        ui.print_cell(caret_pos, ScreenCell(ch))
        caret_pos += Cardinal.RIGHT
    elif key[:5] == "Arrow":
        caret_pos += dict(Up=Cardinal.UP, Down=Cardinal.DOWN, Left=Cardinal.LEFT, Right=Cardinal.RIGHT)[key[5:]]
    elif key == "Backspace":
        caret_pos += Cardinal.LEFT
        ui.print_cell(caret_pos, ScreenCell())
    elif key == "Enter":
        caret_pos = Vector2D(0, caret_pos.y + 1)
    elif key == "Space":
        caret_pos += Cardinal.RIGHT
    elif key == "Delete":
        ui.print_cell(caret_pos, ScreenCell())
    caret_pos = Vector2D(caret_pos.x % ui.dim.x, caret_pos.y % ui.dim.y)
    ui.paint_cell(highlight_pos, dict(hlit=False))
    highlight_pos = caret_pos
    ui.paint_cell(highlight_pos, dict(hlit=True))

ui.registered_onkeypress.append(cat)

waiters = {}
next_animation_id = 0

def _(e):
    s = jq("#sty-text").val()
    tokens = styleml_parser.render(styleml_parser.transform(styleml_parser.tokenize(
        s
    )))
    #ui.scr.print_footprints(footprints)
    
    global next_animation_id
    waiter = Waiter()
    current_animation_id = next_animation_id
    waiters[current_animation_id] = waiter
    next_animation_id += 1
    async def _():
        try:
            await ui.async_print_tokens(tokens, origin=Vector2D(0, 0), waiter=waiter)
            waiters.pop(current_animation_id)
        except Exception as e:
            import traceback
            traceback.print_exc()
            import sys
            sys.exit(1)
    asyncio.create_task(_())
    # ui.screen_update(jq_cont)

jq("#show-sty").on("click", create_proxy(_))

def _(e):
    #import cProfile
    #cProfile.run("ui.clear_screen()")
    ui.clear_screen()
    
jq("#clear-sty").on("click", create_proxy(_))


def _(e):
    for anim_id, waiter in waiters.items():
        waiter.interrupted = True
        waiter.update_event.set()
    
jq("#interrupt-sty-animation").on("click", create_proxy(_))
