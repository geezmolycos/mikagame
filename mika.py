from itertools import count, zip_longest
import re
import asyncio

import attr

def grouper(iterable, n, fillvalue=None):
    "Collect data into non-overlapping fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)

@attr.s(order=False, frozen=True)
class Vector2D:

    x = attr.ib()
    y = attr.ib()

    @property
    def length(self):
        return (self.x**2 + self.y**2) ** 0.5

    @property
    def manhattan(self):
        return abs(self.x) + abs(self.y)

    @property
    def tuple(self):
        return (self.x, self.y)

    def __neg__(self):
        return type(self)(-self.x, -self.y)

    def __add__(self, other):
        return type(self)(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return self + (-other)

    def __mul__(self, other):
        return type(self)(self.x * other, self.y * other)

    __rmul__ = __mul__

    def dot_product(self, other):
        return self.x * other.x + self.y * other.y

    def is_perpendicular_to(self, other):
        return self.dot_product(other) == 0

    def cross_product(self, other):
        return self.x * other.y - self.y * other.x

    def is_parallel_to(self, other):
        return self.cross_product(other) == 0

    def __iter__(self):
        yield from self.tuple

    def apply_matrix(self, mati, matj):
        return self.x * mati + self.y * matj

    def affine_transform(self, mati, matj, translation):
        return self.apply_matrix(mati, matj) + translation

    def affine_transform_with_origin(self, origin, *args, **kwargs):
        return (self - origin).affine_transform(*args, **kwargs) + origin

class Cardinal:
    NORTH = UP = FORWARD = Vector2D(0, -1)
    EAST = RIGHT = Vector2D(1, 0)
    SOUTH = DOWN = BACKWARD = Vector2D(0, 1)
    WEST = LEFT = Vector2D(-1, 0)

def list_transpose(l):
    return list(map(list, zip(*l)))

@attr.s
class List2D:
    dim = attr.ib()

    def __attrs_post_init__(self):
        self.l = [None] * self.dim.x * self.dim.y

    def flatten(self, index):
        if index.x >= self.dim.x or index.y >= self.dim.y:
            raise IndexError(f"index {index} is out of bound")
        return index.y * self.dim.x + index.x

    def __getitem__(self, key):
        if isinstance(key, Vector2D):
            return self.l[self.flatten(key)]
        elif isinstance(key, slice):
            q = []
            x_range = range(key.start.x, key.stop.x, key.step.x)
            y_range = range(key.start.y, key.stop.y, key.step.y)
            for i in x_range:
                q.extend(self.l[
                    self.flatten(Vector2D(i, key.start.y))
                    :self.flatten(Vector2D(i, key.stop.y))
                    :key.step.y
                ])
            n = List2D(Vector2D(len(x_range), len(y_range)))
            n.l = q
            return n
        else:
            raise KeyError()

    def __setitem__(self, key, value):
        if isinstance(key, Vector2D):
            self.l[self.flatten(key)] = value
        elif isinstance(key, slice):
            x_range = range(key.start.x, key.stop.x, key.step.x)
            y_range = range(key.start.y, key.stop.y, key.step.y)
            for i, j in zip(x_range, count(0)):
                self.l[
                    self.flatten(Vector2D(i, key.start.y))
                    :self.flatten(Vector2D(i, key.stop.y))
                    :key.step.y
                ] = value[Vector2D(j, 0):Vector2D(j, len(y_range))]
                # ".l" is not necessary since __iter__ is implemented
        else:
            raise KeyError()

    def __iter__(self):
        yield from self.l
    
    def copy(self):
        new = type(self)(self.dim)
        new.l = self.l.copy()
        return new

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

@attr.s(frozen=True)
class DynamicScreenCell(ScreenCell):

    def __call__(self, tick):
        return ScreenCell()

@attr.s(frozen=True)
class TransitionScreenCell(DynamicScreenCell):
    transition_tick = attr.ib(default=0)
    before = attr.ib(default=ScreenCell())
    after = attr.ib(default=ScreenCell())

    def __call__(self, tick):
        if tick <= self.transition_tick:
            return self.before
        else:
            return self.after

@attr.s
class GameScreen:
    map = attr.ib(factory=lambda: List2D(Vector2D(40, 25)))
    tick = attr.ib(default=0)

    def get_cell(self, pos):
        c = self.map[pos]
        if c is None:
            c = ScreenCell()
        elif isinstance(c, DynamicScreenCell):
            c = c(self.tick)
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
    
    async def async_print_footprints(self, footprints, delays):
        for (pos, cell), pre_delay in zip(footprints, delays):
            await asyncio.sleep(pre_delay)
            self.print_cell(pos, cell)
    
def cells_to_footprints(pos, cells, dir=Cardinal.RIGHT):
    footprints = []
    for c in cells:
        footprints.append((pos, c))
        pos += dir
    return footprints
    
def mlcells_to_footprints(pos, mlcells, dir0=Cardinal.RIGHT, dir1=Cardinal.DOWN):
    footprints = []
    for cells in mlcells:
        footprints.extend(cells_to_footprints(pos, cells, dir=dir0))
        pos += dir1
    return footprints
    
def mlcells_to_footprints_line_wrap(pos, mlcells, dir0=Cardinal.RIGHT, dir1=Cardinal.DOWN, max_length=None, max_lines=None):
    if max_length is None:
        return mlcells_to_footprints(pos, mlcells, dir0=dir0, dir1=dir1)
    footprints = []
    line_number = 0
    for cells in mlcells:
        for line in grouper(cells, max_length): # 将每一行按最大字符数分成若干行
            footprints.extend(cells_to_footprints(pos, line, dir=dir0))
            line_number += 1
            pos += dir1
            if max_lines is not None and line_number >= max_lines: # 达到最大行数限制
                break
        else:
            continue
        break
    return footprints

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

def parse_convenient_obj_repr(s):
    "使用一个标点符号和字符串表示一个简单对象，比如是数字/字符串/真假"
    m = re.match(r"([=#$\+\-?])(.*)", s)
    type, value = m[1], m[2]
    obj = None
    if type == "=":
        obj = value
    elif type == "#":
        obj = int(value)
    elif type == "$":
        obj = float(value)
    elif type == "+":
        obj = True
    elif type == "-":
        obj = False
    elif type == "?":
        obj = None
    return obj

def parse_convenient_pair(s):
    "使用一个key和convenient obj repr相连，代表一个键-值对"
    m = re.match(r"([0-9A-Za-z_]+)(.*)", s)
    key, repr = m[1], m[2]
    obj = parse_convenient_obj_repr(repr)
    return key, obj

def parse_attr_style_argument(s):
    "解析格式标记方括号中的文本"
    styles = {}
    for piece in s.split(","):
        key, obj = parse_convenient_pair(piece)
        styles[key] = obj
    return styles

def styleml_str_to_tokens(s):
    tokens = []
    rest = s
    while True:
        m = re.match(r"([^\\\{\}]*)(.*)", rest, re.S) # 遇到特殊字符"\{}"停止解析
        plain_str, rest = m[1], m[2]
        if len(rest) > 1 and rest[0] == "\\" and rest[1] in ("\\", "{", "}"):# 转义符
            plain_str += rest[1]
            rest = rest[2:]
        tokens.append(("string", plain_str, {}))
        if not rest:
            break
        if rest[0] == "\\": # 标签标记的开始
            m = re.match(r"\\([0-9A-Za-z_]*)\[(.*?)\](.*)", rest, re.S)
            if m:
                command, argument, rest = m[1], m[2], m[3]
                tokens.append(("command", command, {"argument": argument}))
            else:
                m = re.match(r"\\([0-9A-Za-z_]*) (.*)", rest, re.S)
                command, rest = m[1], m[2]
                tokens.append(("command", command, {}))
        elif rest[0] == "{":
            rest = rest[1:]
            tokens.append(("left_bracket",))
        elif rest[0] == "}":
            rest = rest[1:]
            tokens.append(("right_bracket",))
    return tokens

def styleml_tokens_parse_style(tokens, initial_template=None): # 会将其他命令顺延
    step_template = [initial_template or ScreenCell()] # 解析嵌套格式标记的时候，使用栈来实现每一步的模板记录
    parsed_tokens = []
    for item in tokens:
        if item[0] == "string":
            parsed_tokens.append(("string", item[1], item[2] | {"template": step_template[-1]}))
        elif item[0] == "left_bracket":
            step_template.append(step_template[-1])
            parsed_tokens.append(item)
        elif item[0] == "right_bracket":
            step_template.pop()
            parsed_tokens.append(item)
        elif item[0] == "command" and item[1] == "":
            argument = item[2].get("argument")
            if argument:
                parsed_argument = parse_attr_style_argument(argument)
                step_template[-1] = attr.evolve(step_template[-1], **parsed_argument)
        else:
            parsed_tokens.append(item)
    return parsed_tokens

def styleml_tokens_parse_animation(tokens, default_delay=None):
    r"""
    \delay[...]: 立即延时 ...(s)
    \tick[...]: 设置每个字符延时 ...(s)
    """
    step_tick = [default_delay]
    parsed_tokens = []
    for item in tokens:
        if item[0] == "string":
            if step_tick[-1] == None:
                parsed_tokens.append(item)
            else:
                parsed_tokens.append(("string", item[1], item[2] | {"tick": step_tick[-1]}))
        elif item[0] == "command" and item[1] == "tick":
            if (argument := item[2].get("argument")) is not None:
                step_tick[-1] = parse_convenient_obj_repr(argument)
        elif item[0] == "command" and item[1] == "delay":
            if (argument := item[2].get("argument")) is not None:
                parsed_tokens.append(("delay", parse_convenient_obj_repr(argument)))
        elif item[0] == "left_bracket":
            step_tick.append(step_tick[-1])
            parsed_tokens.append(item)
        elif item[0] == "right_bracket":
            step_tick.pop()
            parsed_tokens.append(item)
        else:
            parsed_tokens.append(item)
    return parsed_tokens


def styleml_tokens_to_mlcells(tokens):
    mlcells = [[]]
    for typ, *values in tokens:
        if typ == "string":
            plain_str = values[0]
            template = values[1].get("template") or ScreenCell()
            piece_mlcells = str_to_mlcells(plain_str, template)
            mlcells[-1].extend(piece_mlcells[0])
            mlcells.extend(piece_mlcells[1:]) # 如果长度是1的话，该行为空操作
    return mlcells

def styleml_tokens_to_footprint_delays(tokens):
    delays = []
    immediate_delay = 0
    for typ, *values in tokens:
        if typ == "string":
            plain_str = values[0]
            tick = values[1].get("tick") or 0
            len_no_newline = len(plain_str) - plain_str.count("\n")
            if len_no_newline != 0:
                delays.extend((tick + immediate_delay,) + (tick,) * (len_no_newline - 1))
                immediate_delay = 0
        elif typ == "delay":
            immediate_delay += values[0]
    return delays


# TODO: 使用asyncio写出文本动画，而且可以由其他事件中断
# TODO: 进行游戏本体设计，因为基础已经打好了
# 游戏本体应该由几个类组成，比如一个类负责地图，一个类负责人物对话，但是这些类由一个大的状态机类管理

if __name__ == "__main__":
    _ = styleml_str_to_tokens(r"\delay[$3]Oh\delay[$1] I have an \tick[$0.1]apple")
    print(styleml_tokens_parse_animation(_))

