
import attr

from utilities import Vector2D, List2D, Cardinal

from mika_screen import ScreenCell
from mika_htmlui import HTMLGameScreen

from styleml.core import StyleMLCoreParser, ReturnCharExtParser
from styleml.portal_ext import PortalExtParser
from styleml.macro_ext import MacroExtParser
from styleml_mika_exts import StyleExtParser, AnimationExtParser, LineWrapExtParser

import mika_dialogue as dialogue

from pyodide import create_proxy
from js import jQuery as jq

import asyncio

scr = HTMLGameScreen()

styleml_parser = StyleMLCoreParser(
    ext_parser=[
        PortalExtParser(),
        AnimationExtParser(initial_tick=0.05),
        StyleExtParser(initial_style=dict(bg="white", fg="black")),
        ReturnCharExtParser(),
        LineWrapExtParser(cr_area=Vector2D(20, 0))
        ]
    )

macro_parser = MacroExtParser(core=styleml_parser)

jq("body").append(scr.jq_cont)

dialogue_frame_pos = Vector2D(10, 11)
dialogue_frame_area = (25, 5)
dialogue_frame_dr = Vector2D(dialogue_frame_pos.x + dialogue_frame_area[0], dialogue_frame_pos.y + dialogue_frame_area[1])

map_frame_pos = Vector2D(10, 0)
map_frame_area = (25, 10)
map_frame_dr = Vector2D(map_frame_pos.x + map_frame_area[0], map_frame_pos.y + map_frame_area[1])

current_choice = None
total_choice = 0

in_character_dialogue = None

next_blocked = False
ongoing_animation = False

@attr.s
class Waiter:
    interrupted = attr.ib(default=False)
    instant = attr.ib(default=False)
    update_event = attr.ib(factory=asyncio.Event)
    
    async def __call__(self, time):
        if self.interrupted:
            return False
        if self.instant:
            return True
        done, pending = await asyncio.wait([
            asyncio.create_task(asyncio.sleep(time)),
            asyncio.create_task(self.update_event.wait()),
        ], return_when=asyncio.FIRST_COMPLETED) # 保证中断事件触发时立刻中断
        for t in pending: # 清楚多余任务
            t.cancel()
        if self.interrupted:
            return False
        return True

waiter = Waiter()

def clear_map():
    for y in range(map_frame_pos.y, map_frame_dr.y):
        for x in range(map_frame_pos.x, map_frame_dr.x):
            scr.print_cell(Vector2D(x, y), ScreenCell(fg="black", bg="white"))

def print_map():
    global total_choice
    waiter.interrupted = True
    waiter.update_event.set()
    interrupt_ongoing_map = asyncio.Event()
    clear_map()
    tokens = map_dialogue.eval_sentence(current_choice, in_character_dialogue=in_character_dialogue)
    total_choice = map_dialogue.current_st_args.get("n", 0)
    async def t():
        global next_blocked
        if map_dialogue.current_st_args.get("blk"): # block next
            next_blocked = True
        global waiter
        waiter = Waiter()
        global ongoing_animation
        ongoing_animation = True
        try:
            await scr.async_print_tokens(tokens, map_frame_pos, waiter=waiter)
        except Exception as e:
            import traceback
            traceback.print_exc()
        ongoing_animation = False
        if map_dialogue.current_ts_args.get("imm"): # immediate
            next()
        next_blocked = False
    task = t()
    asyncio.create_task(task)

def init_map_dialogue(map_text, character_texts):
    global map_dialogue
    map_dialogue = dialogue.MapDialogue(
        sentences=dialogue.tokens_to_sentences(styleml_parser.tokenize(map_text)),
        styleml_parser=styleml_parser,
        macro_parser=macro_parser,
        characters={
            k: dialogue.CharacterDialogue(
                sentences=dialogue.tokens_to_sentences(styleml_parser.tokenize(t)),
                styleml_parser=styleml_parser,
                macro_parser=macro_parser
                ) for k, t in character_texts.items()
            }
        )
    clear_map()
    clear_dialogue()
    print_map()

def clear_dialogue():
    for y in range(dialogue_frame_pos.y, dialogue_frame_dr.y):
        for x in range(dialogue_frame_pos.x, dialogue_frame_dr.x):
            scr.print_cell(Vector2D(x, y), ScreenCell(fg="black", bg="white"))

def print_dialogue():
    global total_choice
    waiter.interrupted = True
    waiter.update_event.set()
    interrupt_ongoing_map = asyncio.Event()
    clear_dialogue()
    tokens = character_dialogue.eval_sentence(current_choice)
    total_choice = character_dialogue.current_st_args.get("n", 0)
    async def t():
        global next_blocked
        if character_dialogue.current_st_args.get("blk"): # block next
            next_blocked = True
        global waiter
        waiter = Waiter()
        global ongoing_animation
        ongoing_animation = True
        await scr.async_print_tokens(tokens, dialogue_frame_pos, waiter=waiter)
        ongoing_animation = False
        if character_dialogue.current_ts_args.get("imm"): # immediate
            next()
        next_blocked = False
    task = t()
    asyncio.create_task(task)

def next():
    global in_character_dialogue, character_dialogue
    global current_choice
    if next_blocked:
        return False
    if ongoing_animation:
        waiter.instant = True
        waiter.update_event.set()
        return False
    current_choice = None
    if in_character_dialogue is None:
        should, character_name = map_dialogue.should_change_to_character()
        if should:
            in_character_dialogue = character_name
            character_dialogue = map_dialogue.characters[character_name]
            print_map()
            print_dialogue()
        else:
            map_dialogue.next_sentence()
            print_map()
    else:
        try:
            character_dialogue.next_sentence()
        except IndexError:
            in_character_dialogue = None
            character_dialogue.reset_dialogue()
            clear_dialogue()
            print_map()
        else:
            print_dialogue()
    return True
        
#jq("#next").on("click", create_proxy(lambda e: next()))

def choose_next():
    global current_choice
    current_choice = ((-1 if current_choice is None else current_choice) + 1) % total_choice
    if in_character_dialogue is None:
        clear_map()
        print_map()
    else:
        clear_dialogue()
        print_dialogue()
#jq("#choose-next").on("click", create_proxy(_))

def choose_prev():
    global current_choice
    current_choice = ((0 if current_choice is None else current_choice) - 1) % total_choice
    if in_character_dialogue is None:
        clear_map()
        print_map()
    else:
        clear_dialogue()
        print_dialogue()
#jq("#choose-prev").on("click", create_proxy(_))

def keypress(code, ctrl, shift, alt):
    if code == "Space":
        next()
    elif code in ("ArrowLeft", "ArrowUp"):
        choose_prev()
    elif code in ("ArrowRight", "ArrowDown"):
        choose_next()
scr.registered_onkeypress.append(keypress)

# load characters

import mika_modules
import mika_yaml_scene
import os

all_modules = mika_modules.walk_modules("./demo_root")
# 读取人物
all_characters = {}
map_texts = [mika_yaml_scene.scene_styleml_header]
for m, file_name in all_modules.items():
    ext = os.path.splitext(file_name)[1]
    if ext == ".mika_character":
        with open(os.path.join("demo_root", file_name), encoding="utf-8") as f:
            all_characters[m] = f.read()
    elif ext == ".mika_scene":
        with open(os.path.join("demo_root", file_name), encoding="utf-8") as f:
            scene_text = mika_yaml_scene.MikaScene.from_yaml(f.read()).to_styleml_text(m)
        map_texts.append(scene_text)

init_map_dialogue(
    map_text="".join(map_texts),
    character_texts=all_characters
)