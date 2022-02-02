from itertools import count
import re
import asyncio

import attr

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
        if c is None:
            c = ScreenCell()
        return c

    def print_cell(self, pos, cell):
        self.map[pos] = cell
    
    def print_footprints(self, footprints):
        for pos, cell in footprints:
            self.print_cell(pos, cell)
    
    def paint_cell(self, pos, styles):
        c = attr.evolve(self.map[pos] or ScreenCell(), **styles)
        self.map[pos] = c

    def paint_rectangle(self, pos0, pos1, styles):
        for y in range(pos0.y, pos1.y):
            for x in range(pos0.x, pos1.x):
                self.paint_cell(Vector2D(x, y), styles)
    
    async def async_print_footprints(self, footprints, pre_delays, interruption_event=None, start_from=0):
        footprints = footprints[start_from:]
        pre_delays = pre_delays[start_from:]
        for i, (pos, cell), pre_delay in zip(count(0), footprints, pre_delays):
            if pre_delay != 0:
                done, pending = await asyncio.wait([
                    asyncio.sleep(pre_delay),
                    (interruption_event or asyncio.Event()).wait(),
                    ], return_when=asyncio.FIRST_COMPLETED)
                if interruption_event.is_set():
                    return i
                list(pending)[0].cancel() # 一定是interruption_event
            self.print_cell(pos, cell)
        return i
    
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
    from pprint import pprint
    _ = styleml_str_to_tokens(r"\def[green||#=s##=l#fg=green#=r#]Oh I have an \anchor[=ap]apple, \exp[green|]I have a pen. \chain[=ap]APPLE")
    _ = styleml_tokens_expand_macros(_, recursive=True)
    print(_)
    mlcells = styleml_tokens_to_mlcells(_)
    pprint(mlcells_to_footprints_line_wrap_portal(
        Vector2D(0, 0), mlcells, initial_offset=(0, 2), area=(4, 8),
        portals=styleml_tokens_to_portals(_)
        ))

