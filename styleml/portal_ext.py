
import attr

from .convenient_argument import parse_convenient_obj_repr, parse_convenient_dict
from .core import StyleMLExtParser
from .core import CharacterToken, BracketToken, CommandToken
from .core import AnchorToken, AnchorRemoveToken, ChainToken, NewLineToken, RelReposToken, AbsReposToken

from utilities import Vector2D


@attr.s
class PortalExtParser(StyleMLExtParser):
    r"""
    \n代表换行，\r代表回到行首（是命令，与转义字符区分开）
    \anchor[名字]代表一个锚点
    \anchorrm[名字]删除一个锚点
    而\chain[名字]会寻找对应的锚点，将字符输出的位置重定位到锚点上
    \repos[col#...,row#...]则会重定位字符输出到指定的行数和列数
    \offset[col#...,row#...]会给输出位置增加偏移量
    """
    
    def transformer(self, tokens):
        transformed_tokens = []
        for t in tokens:
            if isinstance(t, CommandToken) and t.value in ("n", "r"):
                amount = parse_convenient_obj_repr(t.meta.get("argument", ""), macros=t.meta.get("macros") or {}) or {"n": 1, "r": 0}[t.value]
                transformed_tokens.append(NewLineToken(amount))
            elif isinstance(t, CommandToken) and t.value in ("anchor", "anchorrm", "chain"):
                argument = t.meta.get("argument")
                transformed_tokens.append({
                    "anchor": AnchorToken,
                    "anchorrm": AnchorRemoveToken,
                    "chain": ChainToken
                    }[t.value](argument))
            elif isinstance(t, CommandToken) and t.value in ("repos", "offset"):
                arguments = parse_convenient_dict(t.meta.get("argument", ""), macros=t.meta.get("macros") or {})
                pos = Vector2D(arguments.get("col"), arguments.get("row"))
                transformed_tokens.append({"repos": AbsReposToken, "offset": RelReposToken}[t.value](pos))
            else:
                transformed_tokens.append(t)
        return transformed_tokens
