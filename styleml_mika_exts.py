
import attr

from styleml.core import StyleMLExtParser
from styleml.core import Token, CharacterToken, BracketToken, CommandToken
from styleml.convenient_argument import parse_convenient_dict, parse_convenient_obj_repr

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


if __name__ == "__main__":
    from styleml.core import StyleMLCoreParser, ReturnCharExtParser
    from styleml.portal_ext import PortalExtParser
    from pprint import pprint
    p = StyleMLCoreParser(ext_parser=[PortalExtParser(), AnimationExtParser(), StyleExtParser(), ReturnCharExtParser()])
    pprint(p.render(p.transform(p.tokenize(r"""\tick[$0.1]Behold\delay[$0.5], here I am!\delay[$1.0]
The {\s[bg=gray]Most {\s[fg=gold]\tick[$0.4]ALMIGHTY} and {\s[fg=red]\tick[$0.4]POWERFUL}}
{\s[bg=red]Dragon} in this Kingdom!"""))))
