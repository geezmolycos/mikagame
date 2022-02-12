
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

dialogue_frame_pos = Vector2D(10, 6)
dialogue_frame_area = (25, 5)
dialogue_frame_dr = Vector2D(dialogue_frame_pos.x + dialogue_frame_area[0], dialogue_frame_pos.y + dialogue_frame_area[1])

map_frame_pos = Vector2D(10, 0)
map_frame_area = (25, 5)
map_frame_dr = Vector2D(map_frame_pos.x + map_frame_area[0], map_frame_pos.y + map_frame_area[1])

current_choice = None
total_choice = 0

in_character_dialogue = None

def clear_map():
    for y in range(map_frame_pos.y, map_frame_dr.y):
        for x in range(map_frame_pos.x, map_frame_dr.x):
            scr.print_cell(Vector2D(x, y), ScreenCell(fg="black", bg="white"))

def print_map(interruption_event=None):
    global total_choice
    tokens = map_dialogue.eval_sentence(current_choice, in_character_dialogue=in_character_dialogue)
    total_choice = map_dialogue.current_st_args.get("n", 0)
    asyncio.create_task(scr.async_print_tokens(tokens, map_frame_pos, interruption_event=interruption_event))

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

def print_dialogue(interruption_event=None):
    global total_choice
    tokens = character_dialogue.eval_sentence(current_choice)
    total_choice = character_dialogue.current_st_args.get("n", 0)
    asyncio.create_task(scr.async_print_tokens(tokens, dialogue_frame_pos, interruption_event=interruption_event))

def next():
    global in_character_dialogue, character_dialogue
    global current_choice
    current_choice = None
    if in_character_dialogue is None:
        should, character_name = map_dialogue.should_change_to_character()
        if should:
            in_character_dialogue = character_name
            character_dialogue = map_dialogue.characters[character_name]
            clear_map()
            print_map()
            clear_dialogue()
            print_dialogue()
        else:
            map_dialogue.next_sentence()
            clear_map()
            print_map()
    else:
        try:
            character_dialogue.next_sentence()
        except IndexError:
            in_character_dialogue = None
            character_dialogue.reset_dialogue()
            clear_dialogue()
            clear_map()
            print_map()
        else:
            clear_dialogue()
            print_dialogue()
        
jq("#next").on("click", create_proxy(lambda e: next()))

def _(e):
    global current_choice
    current_choice = ((-1 if current_choice is None else current_choice) + 1) % total_choice
    if in_character_dialogue is None:
        clear_map()
        print_map()
    else:
        clear_dialogue()
        print_dialogue()
jq("#choose-next").on("click", create_proxy(_))

def _(e):
    global current_choice
    current_choice = ((0 if current_choice is None else current_choice) - 1) % total_choice
    if in_character_dialogue is None:
        clear_map()
        print_map()
    else:
        clear_dialogue()
        print_dialogue()
jq("#choose-prev").on("click", create_proxy(_))


init_map_dialogue(
    map_text=r"""
    \stchoice[label=magua,n;3,m=choice,character_dialogue_m=cdm]\
    \def[choice_ind=\\ifelse\[a!choice,b;%i%,then=*,else= \]]\
    \def[to_or_dial=\\ifelse\[a!choice,b;%i%,then=\\\\def\\\[to=%to%\\\]\\\\def\\\[dialog%dial%\\\]\]]\
    \def[noflash=\
            \\ifelse\[\
            a!choice,b?,\
            else=\\\\tick\\\[:0\\\]\
        \]\
        \\ifelse\[\
            a!cdm,b?,\
            else=\\\\tick\\\[:0\\\]\
        \]\
    ]\
    \!noflash \
    你现在在麻瓜镇。
    \!choice_ind[i=0]1.去南瓜镇\!to_or_dial[i=0,to=nangua,dial=?]
    \!choice_ind[i=1]2.去木瓜镇\!to_or_dial[i=1,to=mugua,dial=?]
    \!choice_ind[i=2]3.与金毛对话\!to_or_dial[i=2,to=magua,dial==jin_mao]
    \ts[to!to,dialogue!dialog]
    \stchoice[label=nangua,n;3,m=choice,character_dialogue_m=cdm]\
    \!noflash \
    你现在在南瓜镇
    \!choice_ind[i=0]1.去麻瓜镇\!to_or_dial[i=0,to=magua,dial=?]
    \!choice_ind[i=1]2.去木瓜镇\!to_or_dial[i=1,to=mugua,dial=?]
    \!choice_ind[i=2]3.与银毛对话\!to_or_dial[i=2,to=nangua,dial==yin_mao]
    \ts[to!to,dialogue!dialog]
    \stchoice[label=mugua,n;4,m=choice,character_dialogue_m=cdm]\
    \!noflash \
    你现在在木瓜镇
    \!choice_ind[i=0]1.去麻瓜镇\!to_or_dial[i=0,to=magua,dial=?]
    \!choice_ind[i=1]2.去南瓜镇\!to_or_dial[i=1,to=nangua,dial=?]
    \!choice_ind[i=2]3.与铜毛对话\!to_or_dial[i=2,to=mugua,dial==tong_mao]
    \!choice_ind[i=3]4.与铁毛对话\!to_or_dial[i=3,to=mugua,dial==tie_mao]
    \ts[to!to,dialogue!dialog]
    """,
    character_texts={
        "jin_mao": r"\st 你好\ts",
        "yin_mao": r"\st 你才好\ts\st 我是银毛\ts",
        "tong_mao": r"\st 你好\ts\st 我是铜毛\ts",
        "tie_mao": r"\st 你好\ts\st 我是铁毛\ts",
    }
)