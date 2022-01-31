
from mika_screen import Vector2D, List2D, Cardinal, ScreenCell
from mika_screen import styleml_str_to_tokens, styleml_tokens_parse_style, styleml_tokens_to_mlcells, mlcells_to_footprints_line_wrap_portal
from mika_screen import styleml_tokens_parse_animation, styleml_tokens_to_footprint_delays, styleml_tokens_to_portals, styleml_tokens_expand_macros
from mika_screen import str_to_mlcells
from mika_htmlui import HTMLGameScreen

from pyodide import create_proxy
from js import jQuery as jq

import asyncio

scr = HTMLGameScreen()

jq("body").append(scr.jq_cont)

dialogue_frame_pos = Vector2D(11, 19)
dialogue_frame_area = (4, 27)
dialogue_frame_dr = Vector2D(dialogue_frame_pos.x + dialogue_frame_area[1], dialogue_frame_pos.y + dialogue_frame_area[0])

dialogues = [
    "我哭！",
    "我觉得真好！",
    "今天是个好日子。",
    r"心想的事儿都能成。\n{\tick[$0.5]...}\delay[$1]\n能成吗?".replace(r"\n", "\n")
]

def clear_dialogue():
    for y in range(dialogue_frame_pos.y - 1, dialogue_frame_dr.y + 1):
        for x in range(dialogue_frame_pos.x - 1, dialogue_frame_dr.x + 1):
            scr.print_cell(Vector2D(x, y), ScreenCell(fg="black", bg="white"))

def print_dialogue(text, interruption_event):
    tokens = styleml_str_to_tokens(text)
    tokens = styleml_tokens_expand_macros(tokens, recursive=True)
    tokens = styleml_tokens_parse_style(tokens, initial_template=ScreenCell(fg="black", bg="white"))
    tokens = styleml_tokens_parse_animation(tokens, default_delay=0.05)
    delays = styleml_tokens_to_footprint_delays(tokens)
    portals = styleml_tokens_to_portals(tokens)
    cells_list = styleml_tokens_to_mlcells(tokens)
    footprints = mlcells_to_footprints_line_wrap_portal(
        dialogue_frame_pos, cells_list, area=dialogue_frame_area, portals=portals)
    
    asyncio.create_task(scr.async_print_footprints(footprints, delays, interruption_event=interruption_event))

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

from mika_screen import mlcells_to_footprints
scr.print_footprints(mlcells_to_footprints(
    Vector2D(1, 16), str_to_mlcells(
        "\n".join(l.strip().strip(".") for l in """
        . ______
        .( o  o )
        . |  U |
        . | -- |
        . ======
        """.strip().split("\n")),
    )))