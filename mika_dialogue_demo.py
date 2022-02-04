
from mika_screen import Vector2D, List2D, Cardinal, ScreenCell
from mika_screen import str_to_mlcells
from mika_htmlui import HTMLGameScreen

from styleml.core import StyleMLCoreParser, ReturnCharExtParser
from styleml.portal_ext import PortalExtParser
from styleml.macro_ext import MacroExtParser
from styleml_mika_exts import StyleExtParser, AnimationExtParser, LineWrapExtParser

from pyodide import create_proxy
from js import jQuery as jq

import asyncio

scr = HTMLGameScreen()

styleml_parser = StyleMLCoreParser(
    ext_parser=[
        MacroExtParser(),
        PortalExtParser(),
        AnimationExtParser(initial_tick=0.1),
        StyleExtParser(initial_style=dict(bg="white", fg="black")),
        ReturnCharExtParser(),
        LineWrapExtParser(cr_area=Vector2D(20, 0))
        ]
    )

jq("body").append(scr.jq_cont)

dialogue_frame_pos = Vector2D(11, 19)
dialogue_frame_area = (4, 27)
dialogue_frame_dr = Vector2D(dialogue_frame_pos.x + dialogue_frame_area[1], dialogue_frame_pos.y + dialogue_frame_area[0])

dialogues = [
    "我哭！",
    "我觉得真好！",
    r"""\def[goto=\\anchor\[resume\]\\chain\[%c%\]]\
\def[back=\\chain\[resume\]]\
\tick[$0.05]今天是个好\anchor[typo]热字
\tickm[$2]我说错了。\!goto[c=typo]日子\!back 已经改好了""",
    r"心想的事儿都能成。\n{\tick[$0.5]...}\delay[$1]\n能成吗?".replace(r"\n", "\n")
]

def clear_dialogue():
    for y in range(dialogue_frame_pos.y - 1, dialogue_frame_dr.y + 1):
        for x in range(dialogue_frame_pos.x - 1, dialogue_frame_dr.x + 1):
            scr.print_cell(Vector2D(x, y), ScreenCell(fg="black", bg="white"))

def print_dialogue(text, interruption_event):
    tokens = styleml_parser.render(styleml_parser.transform(styleml_parser.tokenize(
        text
    )))
    asyncio.create_task(scr.async_print_tokens(tokens, dialogue_frame_pos, interruption_event=interruption_event))

dialogue_number = 0
interruption_event = asyncio.Event()
def next_dialogue():
    global dialogue_number
    global interruption_event
    interruption_event.set()
    clear_dialogue()
    interruption_event = asyncio.Event()
    print_dialogue(dialogues[dialogue_number], interruption_event)
    dialogue_number += 1

clear_dialogue()
def _(e):
    s = jq("#sty-text").val()
    next_dialogue()
jq("#show-sty").on("click", create_proxy(_))
