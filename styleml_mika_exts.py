
import attr

from styleml.core import StyleMLExtParser
from styleml.core import CharacterToken, BracketToken, CommandToken
from styleml.convenient_argument import parse_convenient_dict

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
            elif isinstance(t, CommandToken) and t.value == "":
                argument = t.meta.get("argument")
                if argument is not None:
                    parsed_argument = parse_convenient_dict(argument)
                    step_style[-1] |= parsed_argument
            else:
                transformed_tokens.append(t)
        return transformed_tokens

