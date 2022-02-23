
import re
import attr

from js import jQuery as jq
import js
from pyodide import create_proxy

from mika_screen import Vector2D, GameScreen, ScreenCell
from styleml_glyph_exts import CustomGlyph

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
    def jq_combine_characters(cls, combining_sequence):
        working_stack = []
        for op in reversed(combining_sequence):
            if op == "-":
                div = jq("<div>")
                div.append(working_stack.pop())
                div.append(working_stack.pop())
                div.css("transform", "scale(0.5, 1.0) translate(-0.3rem, 0.2rem)")
                div.css("letter-spacing", "-4px")
                working_stack.append(div)
            elif op == "|":
                div = jq("<div>")
                div.append(working_stack.pop())
                div.append(jq("<br>"))
                div.append(working_stack.pop())
                div.css("transform", "scale(1.0, 0.5) translate(0rem, -0.3rem)")
                div.css("line-height", "90%")
                working_stack.append(div)
            elif op == "0":
                div = jq("<div>")
                divo = jq("<div>")
                divi = jq("<div>")
                divo.append(working_stack.pop())
                divi.append(working_stack.pop())
                divo.css("position", "absolute")
                divo.css("transform", "scale(1.2, 1.2) translate(0rem, 0.3rem)")
                divi.css("transform", "scale(0.6, 0.6) translate(0rem, -0.3rem)")
                div.append(divo)
                div.append(divi)
                working_stack.append(div)
            else: # character
                working_stack.append(op)
        return working_stack[-1]

    @classmethod
    def screen_refresh_jq_cell(cls, cell, jq_cell):
        jq_cell.attr("style", "")
        if isinstance(cell.ch, CustomGlyph):
            jq_cell.text("")
            ch = cell.ch
            if ch.type == "c_hz":
                jq_cell.append(cls.jq_combine_characters(ch.value))
            elif ch.type == "c_zy":
                s = ch.value
                mus = []
                diao = None
                while len(s) > 0:
                    g = re.match(
                        r"(er|ang|eng|an|en|au|eu|ai|ei|a|o|e|y|i|u|w|b|p|m|f|d|t|n|l|g|k|h|j|q|x|zh|ch|sh|r|z|c|s|1|2|3|4|5) *(.*)",
                        s)
                    if g is None:
                        break
                    mu, s = g[1], g[2]
                    if mu in tuple("12345"):
                        diao = mu
                    else:
                        mus.append(mu)
                if diao:
                    diao = {"1":" ", "2": "ˊ", "3": "ˇ", "4": "ˋ", "5": "˙"}[diao]
                mu_fr = "b,p,m,f,d,t,n,l,g,k,h,j,q,x,zh,ch,sh,r,z,c,s,i,u,w,a,o,e,y,ai,ei,au,eu,an,en,ang,eng,er".split(",")
                mu_to = "ㄅㄆㄇㄈㄉㄊㄋㄌㄍㄎㄏㄐㄑㄒㄓㄔㄕㄖㄗㄘㄙㄧㄨㄩㄚㄛㄜㄝㄞㄟㄠㄡㄢㄣㄤㄥㄦ"
                lut = dict(zip(mu_fr, mu_to))
                mus = [lut[m] for m in mus]
                if len(mus) == 1:
                    rendered = jq("<div>").append(mus[0])
                elif len(mus) == 2:
                    if mus[0] in ("ㄧ", "ㄨ", "ㄩ"):
                        rendered = cls.jq_combine_characters("|" + mus[0] + mus[1])
                    else:
                        rendered = cls.jq_combine_characters("-" + mus[0] + mus[1])
                elif len(mus) == 3:
                    rendered = cls.jq_combine_characters("-" + mus[0] + "|" + mus[1] + mus[2])
                rendered = jq("<div>").append(rendered)
                if diao:
                    rendered.append(jq("<div>").css("transform", "translate(-1rem,1rem)").append(diao))
                jq_cell.append(rendered)
        else:
            jq_cell.text(cell.ch or "")
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
        jq_cell = jq(self.jq_cont.children()[pos.y*self.dim.x + pos.x])
        self.screen_refresh_jq_cell(self.map[pos], jq_cell)
