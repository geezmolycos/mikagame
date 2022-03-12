from itertools import count
import re
import asyncio

import attr

from styleml.core import CharacterToken
from utilities import Vector2D, Cardinal, List2D, grouper

@attr.s(frozen=True)
class ScreenCell:
    ch = attr.ib(default=None)
    fg = attr.ib(default="white")
    bg = attr.ib(default="black")
    hlit = attr.ib(default=False)
    bold = attr.ib(default=False)
    emph = attr.ib(default=False)
    undl = attr.ib(default=False)
    midl = attr.ib(default=False)
    topl = attr.ib(default=False)
@attr.s
class GameScreen:
    map = attr.ib(init=False)
    dim = attr.ib(default=Vector2D(40, 25))
    
    def __attrs_post_init__(self):
        self.clear_screen()

    def get_display_cell(self, pos):
        c = self.map[pos]
        c = c or ScreenCell()
        return c

    def print_cell(self, pos, cell):
        self.map[pos] = cell
    
    def print_token(self, t, origin, mati=Vector2D(1, 0), matj=Vector2D(0, 1)):
        if isinstance(t, CharacterToken):
            style = t.meta.get("style") or {}
            pos = t.meta.get("pos").affine_transform(mati, matj, origin)
            self.print_cell(pos, ScreenCell(t.value, **style))
    
    def print_tokens(self, tokens, origin, mati=Vector2D(1, 0), matj=Vector2D(0, 1)):
        for t in tokens:
            self.print_token(t, origin, mati, matj)
    
    def paint_cell(self, pos, style):
        c = attr.evolve(self.map[pos] or ScreenCell(), **style)
        self.map[pos] = c

    def paint_rectangle(self, pos0, pos1, style):
        for y in range(pos0.y, pos1.y):
            for x in range(pos0.x, pos1.x):
                self.paint_cell(Vector2D(x, y), style)
    
    async def async_print_tokens(self, tokens, origin, mati=Vector2D(1, 0), matj=Vector2D(0, 1), waiter=None, start_from=0):
        tokens = tokens[start_from:]
        for i, t in enumerate(tokens):
            post_delay = t.meta.get("post_delay", 0)
            self.print_token(t, origin, mati, matj)
            if post_delay != 0 and waiter is not None:
                should_continue = await waiter(post_delay, t)
                if not should_continue:
                    return i
        return None
    
    def clear_screen(self):
        self.map = List2D(self.dim)

    def clear_rectangle(self, pos0, pos1):
        for y in range(pos0.y, pos1.y):
            for x in range(pos0.x, pos1.x):
                self.print_cell(Vector2D(x, y), None)

def str_to_cells(s, template=None):
    if template is None:
        template = ScreenCell()
    cells = []
    if isinstance(template, ScreenCell):
        for ch in s:
            cells.append(attr.evolve(template, ch=ch))
    else:
        for ch in s:
            ch_t = template.get(ch)
            if ch_t is None:
                ch_t = ScreenCell(ch)
            cells.append(ch_t)
    return cells

def str_to_mlcells(s, template=None):
    "若template是单个ScreenCell，则将该template作为模板。若template是ch->ScreenCell的映射表，则采用该表"
    template = template or ScreenCell()
    mlcells = []
    for ss in s.split("\n"):
        mlcells.append(str_to_cells(ss, template))
    return mlcells
    

# TODO: 编写自定义字符和插入自定义字符的命令
# TODO: 进行游戏本体设计，因为基础已经打好了
# 游戏本体应该由几个类组成，比如一个类负责地图，一个类负责人物对话，但是这些类由一个大的状态机类管理

if __name__ == "__main__":
    pass

