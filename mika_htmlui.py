
import attr

from js import jQuery as jq
import js
from pyodide import create_proxy

from mika import Vector2D, GameScreen, ScreenCell

@attr.s
class HTMLUI:
    
    scr = attr.ib(factory=GameScreen)

    registered_onclick = attr.ib(factory=list)
    def onclick_handler_global(self, e):
        for f in self.registered_onclick:
            pos = Vector2D(int(jq(e.target).attr("data-x")), int(jq(e.target).attr("data-y")))
            f(pos)
        return False

    registered_onkeypress = attr.ib(factory=list)
    def onkeypress_handler_global(self, e):
        for f in self.registered_onkeypress:
            f(e.code, e.ctrlKey, e.shiftKey, e.altKey)
        return False

    def screen_output(self):
        onclick_proxy = create_proxy(lambda e: self.onclick_handler_global(e))
        onkeypress_proxy = create_proxy(lambda e: self.onkeypress_handler_global(e))
        jq_cont = jq("<div class='game-screen-container' tabindex='-1'>")
        jq_cont.on("keydown", onkeypress_proxy)
        for y in range(self.scr.map.dim.y):
            for x in range(self.scr.map.dim.x):
                jq_cell = jq("<div>")
                jq_cell.attr("data-x", x)
                jq_cell.attr("data-y", y)
                jq_cell.on("click", onclick_proxy)
                jq_cont.append(jq_cell)
        return jq_cont

    def screen_update(self, jq_cont):
        children = jq_cont.children()
        for i, cell in enumerate(self.scr.map):
            cell = cell or ScreenCell()
            jq_cell = jq(children[i])
            jq_cell.text(cell.ch or "")
            jq_cell.attr("style", "")
            jq_cell.css("color", cell.fg if not cell.hlit else cell.bg)
            jq_cell.css("background-color", cell.bg if not cell.hlit else cell.fg)
            if cell.bold:
                jq_cell.css("font-weight", "bold")
            if cell.emph:
                jq_cell.css("font-style", "italic")
            lines = []
            if cell.undl:
                lines.append("underline")
            if cell.midl:
                lines.append("line-through")
            if cell.topl:
                lines.append("overline")
            jq_cell.css("text-decoration", " ".join(lines))
