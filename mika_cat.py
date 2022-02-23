
from mika_screen import Vector2D, List2D, Cardinal, ScreenCell
from mika_htmlui import HTMLGameScreen

from styleml.core import StyleMLCoreParser, ReturnCharExtParser
from styleml.portal_ext import PortalExtParser
from styleml.macro_ext import MacroExtParser
from styleml_mika_exts import StyleExtParser, AnimationExtParser, LineWrapExtParser
from styleml_glyph_exts import GlyphsetExtParser

from pyodide import create_proxy
from js import jQuery as jq

import asyncio

htmlui = HTMLGameScreen()

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

jq("body").append(htmlui.jq_cont)

caret_pos = Vector2D(0, 0)
highlight_pos = Vector2D(0, 0)
def cat(key, ctrl, shift, alt):
    global caret_pos, highlight_pos
    if key[:3] == "Key":
        ch = key[3] if shift else key[3].lower()
        htmlui.print_cell(caret_pos, ScreenCell(ch))
        caret_pos += Cardinal.RIGHT
    elif key[:5] == "Arrow":
        caret_pos += dict(Up=Cardinal.UP, Down=Cardinal.DOWN, Left=Cardinal.LEFT, Right=Cardinal.RIGHT)[key[5:]]
    elif key == "Backspace":
        caret_pos += Cardinal.LEFT
        htmlui.print_cell(caret_pos, ScreenCell())
    elif key == "Enter":
        caret_pos = Vector2D(0, caret_pos.y + 1)
    elif key == "Space":
        caret_pos += Cardinal.RIGHT
    elif key == "Delete":
        htmlui.print_cell(caret_pos, ScreenCell())
    htmlui.paint_cell(highlight_pos, dict(hlit=False))
    highlight_pos = caret_pos
    htmlui.paint_cell(highlight_pos, dict(hlit=True))

htmlui.registered_onkeypress.append(cat)

interrupt_events = {}
next_animation_id = 0

def _(e):
    s = jq("#sty-text").val()
    tokens = styleml_parser.render(styleml_parser.transform(styleml_parser.tokenize(
        s
    )))
    #htmlui.scr.print_footprints(footprints)
    
    global next_animation_id
    interrupt_event = asyncio.Event()
    current_animation_id = next_animation_id
    interrupt_events[current_animation_id] = interrupt_event
    next_animation_id += 1
    async def _():
        try:
            await htmlui.async_print_tokens(tokens, origin=Vector2D(0, 0))
            interrupt_events.pop(current_animation_id)
        except Exception as e:
            import traceback
            traceback.print_exc()
    asyncio.create_task(_())
    # htmlui.screen_update(jq_cont)

jq("#show-sty").on("click", create_proxy(_))

def _(e):
    htmlui.clear_screen()
    
jq("#clear-sty").on("click", create_proxy(_))


def _(e):
    for anim_id, interrupt_event in interrupt_events.items():
        interrupt_event.set()
    
jq("#interrupt-sty-animation").on("click", create_proxy(_))
