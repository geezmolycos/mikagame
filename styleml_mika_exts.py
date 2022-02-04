
import attr

from styleml.core import StyleMLExtParser
from styleml.core import Token, CharacterToken, BracketToken, CommandToken
from styleml.convenient_argument import parse_convenient_dict, parse_convenient_obj_repr
from utilities import Vector2D, Cardinal

from mika_screen import ScreenCell

@attr.s
class StyleExtParser(StyleMLExtParser):
    
    initial_style = attr.ib(default=None)
    
    def transformer(self, tokens):
        step_style = [self.initial_style or {}] # 解析嵌套格式标记的时候，使用栈来实现每一步的模板记录
        transformed_tokens = []
        for t in tokens:
            if isinstance(t, CharacterToken):
                t = attr.evolve(t, meta=(t.meta | {"style": step_style[-1]}))
                transformed_tokens.append(t)
            elif isinstance(t, BracketToken) and t.is_left():
                step_style.append(step_style[-1])
                transformed_tokens.append(t)
            elif isinstance(t, BracketToken) and t.is_right():
                step_style.pop()
                transformed_tokens.append(t)
            elif isinstance(t, CommandToken) and t.value == "s":
                argument = t.meta.get("argument")
                if argument is not None:
                    parsed_argument = parse_convenient_dict(argument)
                    step_style[-1] = step_style[-1] | parsed_argument
            else:
                transformed_tokens.append(t)
        return transformed_tokens

@attr.s
class AnimationExtParser(StyleMLExtParser):
    r"""
    \delay[...]: 立即延时 ...(s)
    \delaym[...]: 立即延时若干个tick
    \delayc[...]: 立即延时若干个字符
    \tick[...]: 设置每个字符延时 ...(s)
    \tickm[...]: 设置延时倍率
    """
    
    initial_tick = attr.ib(default=0)
    
    def transformer(self, tokens):
        step_tick = [self.initial_tick]
        step_tick_multiplier = [1]
        transformed_tokens = []
        for t in tokens:
            if isinstance(t, CharacterToken):
                t = attr.evolve(t, meta=(t.meta | {"post_delay": step_tick[-1] * step_tick_multiplier[-1]}))
                transformed_tokens.append(t)
            elif isinstance(t, CommandToken) and t.value == "tick":
                argument = t.meta.get("argument")
                step_tick[-1] = parse_convenient_obj_repr(argument)
            elif isinstance(t, CommandToken) and t.value == "tickm":
                argument = t.meta.get("argument")
                step_tick_multiplier[-1] = parse_convenient_obj_repr(argument)
            elif isinstance(t, CommandToken) and t.value == "delay":
                delay = parse_convenient_obj_repr(t.meta.get("argument"))
                transformed_tokens.append(Token(meta={"post_delay": delay}))
            elif isinstance(t, CommandToken) and t.value == "delaym":
                delay = parse_convenient_obj_repr(t.meta.get("argument"))
                transformed_tokens.append(Token(meta={"post_delay": step_tick[-1] * delay}))
            elif isinstance(t, CommandToken) and t.value == "delayc":
                delay = parse_convenient_obj_repr(t.meta.get("argument"))
                transformed_tokens.append(Token(meta={"post_delay": step_tick[-1] * step_tick_multiplier[-1] * delay}))
            elif isinstance(t, BracketToken) and t.is_left():
                step_tick.append(step_tick[-1])
                step_tick_multiplier.append(step_tick_multiplier[-1])
                transformed_tokens.append(t)
            elif isinstance(t, BracketToken) and t.is_right():
                step_tick.pop()
                step_tick_multiplier.pop()
                transformed_tokens.append(t)
            else:
                transformed_tokens.append(t)
        return transformed_tokens

@attr.s
class LineWrapExtParser(StyleMLExtParser):
    
    cr_area = attr.ib(default=Vector2D(0, 0)) # 0 代表无限制
    only_printable = attr.ib(default=True)
    
    @property
    def columns(self):
        return self.cr_area.x
    
    @property
    def rows(self):
        return self.cr_area.y
    
    def post_renderer(self, tokens):
        columns_for_row = {} # 先确定每行的长度
        total_row_amount = 0 # 和一共多少行
        for t in tokens:
            if self.only_printable and not t.printable:
                continue
            x, y = t.meta["pos"]
            columns_for_row[y] = max(columns_for_row.get(y, 0), x)
            total_row_amount = max(total_row_amount, y)
        total_row_amount += 1
        wrapped_row = {} # 再算出wrap前对应wrap后的行号
        accumulated_rows = 0
        for i in range(total_row_amount):
            wrapped_row[i] = accumulated_rows
            length = columns_for_row.get(i, 0)
            split_into = (length // self.columns if self.columns else 0) + 1
            accumulated_rows += split_into
        transformed_tokens = []
        for t in tokens:
            x, y = t.meta["pos"]
            row = wrapped_row[y] + (x // self.columns if self.columns else 0)
            col = x % self.columns if self.columns else x
            if self.rows != 0 and row >= self.rows:
                continue # 超出界限了
            t = attr.evolve(t, meta=(t.meta | {"pos": Vector2D(col, row)}))
            transformed_tokens.append(t)
        return transformed_tokens

@attr.s
class AffineTransformExtParser:
    origin = attr.ib(default=Vector2D(0, 0))
    row_grow = attr.ib(default=Vector2D(1, 0))
    col_grow = attr.ib(default=Vector2D(0, 1))
    
    def post_renderer(self, tokens):
        transformed_tokens = []
        for t in tokens:
            if pos := t.meta.get("pos"):
                t = attr.evolve(
                    t, meta=(
                        t.meta | {"pos": pos.affine_transform(self.row_grow, self.col_grow, self.origin)}
                        )
                    )
            transformed_tokens.append(t)
        return transformed_tokens

if __name__ == "__main__":
    from styleml.core import StyleMLCoreParser, ReturnCharExtParser
    from styleml.portal_ext import PortalExtParser
    from styleml.macro_ext import MacroExtParser
    from pprint import pprint
    p = StyleMLCoreParser(ext_parser=[MacroExtParser(), PortalExtParser(), AnimationExtParser(), StyleExtParser(), ReturnCharExtParser(), LineWrapExtParser(cr_area=Vector2D(5, 0))])
    #pprint(p.render(p.transform(p.tokenize(r"""\tick[$0.1]Behold\delay[$0.5], here I am!\delay[$1.0]\n The {\s[bg=gray]Most {\s[fg=gold]\tick[$0.4]ALMIGHTY} and {\s[fg=red]\tick[$0.4]POWERFUL}}\n {\s[bg=red]Dragon} in this Kingdom!"""))))
    # pprint(p.render(p.transform(p.tokenize(
    #     r"\tick[$0.05]\def[green=\\s\[fg=green\]]Oh I have an \anchor[=ap]apple, I have {\!green a pen}. {\chain[=ap]\s[fg=red,bg=orange]APPLE}"
    # ))))
    pprint(p.render(p.transform(p.tokenize(
        r"""
\def[set=\\def\[a=%a%\]]\
\!set[a=1]\
this is \!a
\!a  is 1
\!set[a=2]\
\!a  is 2
        """
    ))))
