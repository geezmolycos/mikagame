
from mika import Vector2D, List2D, Cardinal, ScreenCell, parse_styleml_to_tokens, styleml_parse_style, styleml_tokens_to_cells_list, cells_list_to_footprints
from mika_htmlui import HTMLUI
from pyodide import create_proxy
from js import jQuery as jq

htmlui = HTMLUI()

jq_cont = htmlui.screen_output()
htmlui.screen_update(jq_cont)
jq("body").append(jq_cont)

caret_pos = Vector2D(0, 0)
highlight_pos = Vector2D(0, 0)
def cat(key, ctrl, shift, alt):
    global caret_pos, highlight_pos
    if key[:3] == "Key":
        ch = key[3] if shift else key[3].lower()
        htmlui.scr.print_cell(caret_pos, ScreenCell(ch))
        caret_pos += Cardinal.RIGHT
    elif key[:5] == "Arrow":
        caret_pos += dict(Up=Cardinal.UP, Down=Cardinal.DOWN, Left=Cardinal.LEFT, Right=Cardinal.RIGHT)[key[5:]]
    elif key == "Backspace":
        caret_pos += Cardinal.LEFT
        htmlui.scr.print_cell(caret_pos, ScreenCell())
    elif key == "Enter":
        caret_pos = Vector2D(0, caret_pos.y + 1)
    elif key == "Space":
        caret_pos += Cardinal.RIGHT
    elif key == "Delete":
        htmlui.scr.print_cell(caret_pos, ScreenCell())
    htmlui.scr.paint_cell(highlight_pos, dict(hlit=False))
    highlight_pos = caret_pos
    htmlui.scr.paint_cell(highlight_pos, dict(hlit=True))
    htmlui.screen_update(jq_cont)

htmlui.registered_onkeypress.append(cat)

def _(e):
    s = jq("#sty-text").val()
    tokens = parse_styleml_to_tokens(s)
    tokens = styleml_parse_style(tokens)
    cells_list = styleml_tokens_to_cells_list(tokens)
    footprints = cells_list_to_footprints(Vector2D(0, 0), cells_list)
    htmlui.scr.print_footprints(footprints)
    htmlui.screen_update(jq_cont)

jq("#show-sty").on("click", create_proxy(_))

