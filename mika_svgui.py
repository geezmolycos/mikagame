
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
    
    cell_height = 96
    cell_width = 96
    
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
        def _c_hz_lr(cls, width, height, children): # 左右结构
            combined = jq(create_svg_elem("g"))
            total_weight = sum(weight for weight, child in children)
            ratio = 0
            for weight, render in children:
                r = jq(create_svg_elem("g")).attr(
                    "transform",
                    f"translate({ratio * width}, 0) scale({weight / total_weight}, 1.0)"
                    ).append(render)
                combined.append(r)
                ratio += weight / total_weight
            return combined
        @classmethod
        def _c_hz_ud(cls, width, height, children): # 上下结构
            combined = jq(create_svg_elem("g"))
            total_weight = sum(weight for weight, child in children)
            ratio = 0
            for weight, render in children:
                r = jq(create_svg_elem("g")).attr(
                    "transform",
                    f"translate(0, {ratio * height}) scale(1.0, {weight / total_weight})"
                    ).append(render)
                combined.append(r)
                ratio += weight / total_weight
            return combined
        @classmethod
        def _c_hz_io(cls, width, height, children, shrink=0.5, x_shift=0, y_shift=0): # 包围结构（全、边半、角半）
            size = 1
            combined = jq(create_svg_elem("g"))
            for weight, render in children:
                size *= weight # weight表示相对于正常缩放，进一步缩放的程度（会影响之后的字）
                x = width * (1 - size) / 2 * (x_shift + 1)
                y = height * (1 - size) / 2 * (y_shift + 1)
                r = jq(create_svg_elem("g")).attr(
                    "transform",
                    f"translate({x}, {y}) scale({size}, {size})"
                    ).append(render)
                combined.append(r)
                size *= shrink
            return combined
        @classmethod
        def _c_hz_rt(cls, width, height, child, rotation=0, flip_x=False, flip_y=False): # 旋转和镜像结构
            # 先旋转再镜像
            weight, render = child
            rotation *= weight
            combined = jq(create_svg_elem("g"))
            r = jq(create_svg_elem("g")).attr(
                "transform",
                f"rotate({rotation}, {width / 2}, {height / 2}) translate({width if flip_x else 0}, {height if flip_y else 0}) scale({-1 if flip_x else 1}, {-1 if flip_y else 1})"
                ).append(render)
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
        
        _c_hz_direction = {
            "1": (-1, 1),
            "2": (0, 1),
            "3": (1, 1),
            "4": (-1, 0),
            "5": (0, 0),
            "6": (1, 0),
            "7": (-1, -1),
            "8": (0, -1),
            "9": (1, -1),
        }
        
        _c_hz_shrink = {
            "0": 10/10,
            "1": 9/10,
            "2": 8/10,
            "3": 7/10,
            "4": 6/10,
            "5": 5/10,
            "6": 4/10,
            "7": 3/10,
            "8": 2/10,
            "9": 1/10,
        }
        
        _c_hz_weight = {
            "0": 0,
            "1": 1/8,
            "2": 1/4,
            "3": 1/3,
            "4": 1/2,
            "5": 1,
            "6": 2,
            "7": 3,
            "8": 4,
            "9": 8,
            "a": 1/8,
            "b": 2/8,
            "c": 3/8,
            "d": 4/8,
            "e": 5/8,
            "f": 6/8,
            "g": 7/8,
            "h": 8/8,
            "A": 1+1/8,
            "B": 1+2/8,
            "C": 1+3/8,
            "D": 1+4/8,
            "E": 1+5/8,
            "F": 1+6/8,
            "G": 1+7/8,
            "H": 1+8/8,
        }

        @classmethod
        def _c_hz_parse_combine(cls, width, height, text, cell):
            working_stack = []
            def get_render(it):
                return it.get("render") or cls._c_hz_wrap_text(width, height, it.get("ch"), cell)
            text = list(text)
            while len(text) > 0:
                op = text.pop()
                if op in tuple("%&"): # 需要额外方位信息
                    dir = working_stack.pop().get("ch")
                    x_shift, y_shift = cls._c_hz_direction[dir]
                    if op == "&":
                        shrink_char = working_stack.pop().get("ch")
                        shrink = cls._c_hz_shrink[shrink_char]
                elif op == "$": # 设置weight
                    weight_char = working_stack.pop().get("ch")
                    weight = cls._c_hz_weight[weight_char]
                    working_stack[-1]["weight"] = weight
                if op in tuple("-|*%&"): # 多参数指令
                    if working_stack[-1].get("ch") not in tuple("<,"): # 两种定界符，以便于使用
                        children = [working_stack.pop(), working_stack.pop()]
                    else:
                        working_stack.pop()
                        children = []
                        while (it := working_stack.pop()).get("ch") not in tuple(">."):
                            children.append(it)
                    weighted_render_children = [
                        (it.get("weight", 1), get_render(it))
                        for it in children
                    ]
                    working_stack.append(dict(render=
                        {
                            "-": cls._c_hz_lr,
                            "|": cls._c_hz_ud,
                            "*": cls._c_hz_io,
                            "%": lambda *args, **kwargs: cls._c_hz_io(*args, **dict(x_shift=x_shift, y_shift=y_shift) | kwargs),
                            "&": lambda *args, **kwargs: cls._c_hz_io(*args, **dict(x_shift=x_shift, y_shift=y_shift, shrink=shrink) | kwargs),
                        }[op](width, height, weighted_render_children) # 根据指示符的不同，选择不同的结构
                    ))
                elif op == "/": # flip
                    axis = working_stack.pop().get("ch")
                    it = working_stack.pop()
                    working_stack.append(dict(render=cls._c_hz_rt(width, height, (it.get("weight", 1), get_render(it)), flip_x=axis=="x", flip_y=axis=="y")))
                elif op == "?": # rotate
                    it = working_stack.pop()
                    working_stack.append(dict(render=cls._c_hz_rt(width, height, (it.get("weight", 1), get_render(it)), rotation=180)))
                elif op in tuple("$"):
                    pass
                else: # character
                    working_stack.append({"ch": op})
            return get_render(working_stack.pop())
        
        @classmethod
        def c_hz(cls, scr, cell, slots):
            slots["bg"].css("fill", cell.bg)
            c = slots["custom"]
            c.empty()
            combined = cls._c_hz_parse_combine(scr.cell_width, scr.cell_height, cell.ch.value, cell)
            c.append(combined)

