
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
        AnimationExtParser(initial_tick=0.1),
        StyleExtParser(initial_style=dict(bg="white", fg="black")),
        ReturnCharExtParser(),
        LineWrapExtParser(cr_area=Vector2D(20, 0))
        ]
    )

macro_parser = MacroExtParser(core=styleml_parser)

jq("body").append(scr.jq_cont)

dialogue_frame_pos = Vector2D(10, 0)
dialogue_frame_area = (25, 5)
dialogue_frame_dr = Vector2D(dialogue_frame_pos.x + dialogue_frame_area[0], dialogue_frame_pos.y + dialogue_frame_area[1])

def clear_dialogue():
    for y in range(dialogue_frame_pos.y, dialogue_frame_dr.y):
        for x in range(dialogue_frame_pos.x, dialogue_frame_dr.x):
            scr.print_cell(Vector2D(x, y), ScreenCell(fg="black", bg="white"))

def print_dialogue(choice=None, interruption_event=None):
    tokens = character_dialogue.eval_sentence(choice)
    asyncio.create_task(scr.async_print_tokens(tokens, dialogue_frame_pos, interruption_event=interruption_event))

def _(e):
    global character_dialogue
    dialogue_text = jq("#dialogue-text").val()
    character_dialogue = dialogue.CharacterDialogue(
        sentences=dialogue.tokens_to_sentences(styleml_parser.tokenize(dialogue_text)),
        styleml_parser=styleml_parser,
        macro_parser=macro_parser
        )
    clear_dialogue()
    print_dialogue()
jq("#reload").on("click", create_proxy(_))

def _(e):
    character_dialogue.next_sentence()
    clear_dialogue()
    print_dialogue()
jq("#next").on("click", create_proxy(_))

def _(e):
    s = int(jq("#sty-text").val())
    clear_dialogue()
    print_dialogue(s, None)
jq("#choose").on("click", create_proxy(_))
