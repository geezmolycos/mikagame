
import re

from .core import StyleMLExtParser
from .core import CharacterToken, CommandToken, BracketToken
from .convenient_argument import parse_convenient_pair, parse_convenient_dict

import attr

@attr.s
class MacroExtParser(StyleMLExtParser):
    r"""
    定义宏的命令如：\def[宏名=宏内容]
    宏内容中有可能出现的特殊字符，包括"\", "[", "]"，已经在解析成token的时候解析好了
    参数用#名字#表示
    而"#"本身用##表示
    消除宏的命令：\undef[宏名]
    调用宏的命令如：\!宏名[参数]
    """
    initial_macros = attr.ib(factory=dict)
    
    def expand_and_get_defined_macros(self, tokens, initial_macros=None):
        if initial_macros is None:
            initial_macros = self.initial_macros
        current_macros = initial_macros.copy()
        transformed_tokens = []
        for t in tokens:
            if isinstance(t, CommandToken) and t.value == "def":
                name, expand_to = parse_convenient_pair(t.meta.get("argument"))
                current_macros[name] = expand_to
            elif isinstance(t, CommandToken) and t.value == "undef":
                name = t.meta.get("argument")
                current_macros.pop(name)
            elif isinstance(t, CommandToken) and len(t.value) != 0 and t.value[0] == "!": # 由!开头的命令，是宏调用
                macro_name = t.value[1:]
                macro_arguments = parse_convenient_dict(t.meta.get("argument", ""))
                macro_template = current_macros[macro_name]
                macro_arguments.update({"": "#"})
                expanded_text = re.sub(r"#(.*?)#", lambda match: macro_arguments.get(match[1], ""), macro_template)
                expanded_tokens = self.core.tokenize(expanded_text)
                # recursive expansion
                recursive_expanded_tokens, inner_macros = self.expand_and_get_defined_macros(expanded_tokens, initial_macros=current_macros)
                transformed_tokens.extend(recursive_expanded_tokens)
                current_macros.update(inner_macros)
            else:
                transformed_tokens.append(t)
        return transformed_tokens, current_macros
    
    def transformer(self, tokens):
        return self.expand_and_get_defined_macros(tokens, initial_macros=None)[0]
    
