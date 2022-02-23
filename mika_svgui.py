
import re
import attr

from js import jQuery as jq
import js
from pyodide import create_proxy

from mika_screen import Vector2D, GameScreen, ScreenCell
from styleml_glyph_exts import CustomGlyph

def create_svg_elem(name):
    return js.document.createElementNS("http://www.w3.org/2000/svg", name)

@attr.s
class SVGGameScreen(GameScreen):
    
    cell_height = 24
    cell_width = 24
    
    def __attrs_post_init__(self):
        super().__attrs_post_init__()
        self.jq_svg, self.cell_slots = self.create_svg_base()
        self.render_refresh_all()
        
    def print_cell(self, pos, cell):
        super().print_cell(pos, cell)
        self.render_refresh_pos(pos)
    
    def paint_cell(self, pos, styles):
        super().paint_cell(pos, styles)
        self.render_refresh_pos(pos)
    
    def clear_screen(self):
        super().clear_screen()
        if hasattr(self, "jq_svg"): # 刚开始的时候jq_svg还没有初始化
            self.render_refresh_all()

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
    
    def create_svg_base(self):
        jq_svg = jq(create_svg_elem("svg"))
        cell_height, cell_width = self.cell_height, self.cell_width
        cell_slots = {}
        jq_svg.addClass("game-screen")
        jq_svg.attr("width", cell_width * self.dim.x).attr("height", cell_height * self.dim.y)
        for y in range(self.dim.y):
            for x in range(self.dim.x):
                cell_g = jq(create_svg_elem("g")).attr("data-x", x).attr("data-y", y)
                cell_g.attr("transform", f"translate({x*cell_width}, {y*cell_height})")
                bg = jq(create_svg_elem("rect")).attr("x", 0).attr("y", 0).attr("width", self.cell_width).attr("height", self.cell_height)
                bg.addClass("cell-bg")
                cell_g.append(bg)
                text = jq(create_svg_elem("text")).attr("x", self.cell_width / 2).attr("y", self.cell_height / 2)
                text.addClass("cell-text")
                text.css("text-anchor", "middle")
                text.css("dominant-baseline", "central")
                text.css("font-size", f"{self.cell_width}px")
                cell_g.append(text)
                custom = jq(create_svg_elem("g")).attr("x", 0).attr("y", 0)
                cell_g.append(custom)
                cell_slots[Vector2D(x, y)] = dict(g=cell_g, bg=bg, text=text, custom=custom)
                jq_svg.append(cell_g)
        return jq_svg, cell_slots
    
    def render_refresh_all(self):
        for y in range(self.dim.y):
            for x in range(self.dim.x):
                self.render_refresh_pos(Vector2D(x, y))
    
    def render_refresh_pos(self, pos):
        self.render_refresh_cell(self.get_display_cell(pos), self.cell_slots[pos])
    
    @classmethod
    def render_refresh_cell(cls, cell, slots):
        if isinstance(cell.ch, CustomGlyph):
            getattr(cls.CustomGlyphRenderers, cell.ch.type)(cls, cell, slots)
        else:
            slots["custom"].empty()
            slots["bg"].css("fill", cell.bg)
            slots["text"].css("fill", cell.fg).text(cell.ch or "")
            if cell.bold:
                slots["text"].css("font-weight", "bold")
            if cell.emph:
                slots["text"].css("font-style", "italic")
            lines = []
            if cell.undl:
                lines.append("underline")
            if cell.midl:
                lines.append("line-through")
            if cell.topl:
                lines.append("overline")
            slots["text"].css("text-decoration", " ".join(lines))
    
    class CustomGlyphRenderers:
        
        @classmethod
        def _c_hz_lr(cls, width, height, children):
            each_width = width / len(children)
            combined = jq(create_svg_elem("g"))
            for i, child in enumerate(children):
                r = jq(create_svg_elem("g")).attr(
                    "transform",
                    f"translate({i * each_width}, 0) scale({1 / len(children)}, 1.0)"
                    ).append(child)
                combined.append(r)
            return combined
        @classmethod
        def _c_hz_ud(cls, width, height, children):
            each_height = height / len(children)
            combined = jq(create_svg_elem("g"))
            for i, child in enumerate(children):
                r = jq(create_svg_elem("g")).attr(
                    "transform",
                    f"translate(0, {i * each_height}) scale(1.0, {1 / len(children)})"
                    ).append(child)
                combined.append(r)
            return combined
        @classmethod
        def _c_hz_io(cls, width, height, children):
            shrink = 0.8
            size = 1
            combined = jq(create_svg_elem("g"))
            for child in children:
                x = width * (1 - size) / 2
                y = height * (1 - size) / 2
                r = jq(create_svg_elem("g")).attr(
                    "transform",
                    f"translate({x}, {y}) scale({size}, {size})"
                    ).append(child)
                size *= shrink
                combined.append(r)
            return combined

        @classmethod
        def _c_hz_wrap_text(cls, width, height, text, cell):
            jq_text = jq(create_svg_elem("text")).attr("x", width / 2).attr("y", height / 2)
            jq_text.text(text).css("fill", cell.fg)
            if cell.bold:
                jq_text.css("font-weight", "bold")
            if cell.emph:
                jq_text.css("font-style", "italic")
            jq_text.addClass("cell-text")
            jq_text.css("text-anchor", "middle")
            jq_text.css("dominant-baseline", "central")
            jq_text.css("font-size", f"{width}px")
            return jq_text
        
        @classmethod
        def c_hz(cls, scr, cell, slots):
            c = slots["custom"]
            c.empty()
            working_stack = []
            for op in reversed(cell.value):
                if op == "-":
                    working_stack.append(
                        cls._c_hz_lr(
                            scr.cell_width, scr.cell_height,
                            [working_stack.pop(), working_stack.pop()]
                        )
                    )
                elif op == "=":
                    l = []
                    while working_stack[-1] != ".":
                        l.append(working_stack.pop())
                    working_stack.append(
                        cls._c_hz_lr(
                            scr.cell_width, scr.cell_height,
                            l
                        )
                    )
                elif op == "|":
                    working_stack.append(
                        cls._c_hz_ud(
                            scr.cell_width, scr.cell_height,
                            [working_stack.pop(), working_stack.pop()]
                        )
                    )
                elif op == ":":
                    l = []
                    while working_stack[-1] != ".":
                        l.append(working_stack.pop())
                    working_stack.append(
                        cls._c_hz_ud(
                            scr.cell_width, scr.cell_height,
                            l
                        )
                    )
                elif op == ".":
                    working_stack.append(
                        cls._c_hz_ud(
                            scr.cell_width, scr.cell_height,
                            [working_stack.pop(), working_stack.pop()]
                        )
                    )
                elif op == ",":
                    l = []
                    while working_stack[-1] != ".":
                        l.append(working_stack.pop())
                    working_stack.append(
                        cls._c_hz_ud(
                            scr.cell_width, scr.cell_height,
                            l
                        )
                    )
                else: # character
                    working_stack.append(cls._c_hz_wrap_text(scr.cell_width, scr.cell_height, op, cell))
            return working_stack[-1]


