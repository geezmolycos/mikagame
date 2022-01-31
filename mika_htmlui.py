
import attr

from js import jQuery as jq
import js
from pyodide import create_proxy

from mika_screen import Vector2D, GameScreen, ScreenCell

@attr.s
class HTMLGameScreen(GameScreen):
    
    def __attrs_post_init__(self):
        super().__attrs_post_init__()
        self.jq_cont = self.create_jq_container()
        self.screen_refresh_all()
        
    def print_cell(self, pos, cell):
        super().print_cell(pos, cell)
        self.screen_refresh_pos(pos)
    
    def paint_cell(self, pos, styles):
        super().paint_cell(pos, styles)
        self.screen_refresh_pos(pos)
    
    def clear_screen(self):
        super().clear_screen()
        if hasattr(self, "jq_cont"): # 刚开始的时候jq_cont还没有初始化
            self.screen_refresh_all()

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

    def create_jq_container(self):
        onclick_proxy = create_proxy(lambda e: self.onclick_handler_global(e))
        onkeypress_proxy = create_proxy(lambda e: self.onkeypress_handler_global(e))
        jq_cont = jq("<div class='game-screen-container' tabindex='-1'>")
        jq_cont.on("keydown", onkeypress_proxy)
        for y in range(self.map.dim.y):
            for x in range(self.map.dim.x):
                jq_cell = jq("<div>")
                jq_cell.attr("data-x", x)
                jq_cell.attr("data-y", y)
                jq_cell.on("click", onclick_proxy)
                jq_cont.append(jq_cell)
        return jq_cont

    @classmethod
    def screen_refresh_jq_cell(cls, cell, jq_cell):
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
        

    def screen_refresh_all(self):
        children = self.jq_cont.children()
        for i, cell in enumerate(self.map):
            cell = cell or ScreenCell()
            jq_cell = jq(children[i])
            self.screen_refresh_jq_cell(cell, jq_cell)
    
    def screen_refresh_pos(self, pos):
        jq_cell = jq(self.jq_cont.children()[pos.y*40 + pos.x]) # 暂时hardcode
        self.screen_refresh_jq_cell(self.map[pos], jq_cell)
