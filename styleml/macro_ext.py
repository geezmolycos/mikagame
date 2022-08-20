
import re

from .core import StyleMLExtParser, StyleMLCoreParser
from .core import CharacterToken, CommandToken, BracketToken
from .convenient_argument import parse_convenient_pair, parse_convenient_dict

import attr

@attr.s
class MacroExtParser(StyleMLExtParser):
    r"""
    定义宏的命令如：\def[宏名=宏内容]
    宏内容中有可能出现的特殊字符，包括"\", "[", "]"，已经在解析成token的时候解析好了
    参数用%名字%表示
    而"%"本身用%%表示
    定义宏还有命令\defexp，采取先展开再定义，即eager evaluation的形式
    消除宏的命令：\undef[宏名]
    调用宏的命令如：\!宏名[参数]
    命令参数和命令不能嵌套，因此，if/else以基于宏的方式实现
    \ifelse[a=a,b=b,then=c,else=d] -> c if a == b else d
    """
    initial_macros = attr.ib(factory=dict)
    tokenize = attr.ib(default=StyleMLCoreParser.tokenize)
    
    def expand_and_get_defined_macros(self, tokens, initial_macros=None):
        if initial_macros is None:
            initial_macros = self.initial_macros
        current_macros = initial_macros.copy()
        transformed_tokens = []
        for t in tokens:
            if isinstance(t, CommandToken) and t.value == "def":
                name, expand_to = parse_convenient_pair(t.meta.get("argument"), macros=current_macros)
                current_macros[name] = expand_to
            elif isinstance(t, CommandToken) and t.value == "defexp":
                name, to_expand = parse_convenient_pair(t.meta.get("argument"), macros=current_macros)
                expanded, inner_macros = self.expand_and_get_defined_macros(to_expand, initial_macros=current_macros)
                current_macros[name] = expanded # 里面定义的宏不放出来，只用展开的结果
            elif isinstance(t, CommandToken) and t.value == "undef":
                name = t.meta.get("argument")
                current_macros.pop(name)
            elif isinstance(t, CommandToken) and len(t.value) != 0 and t.value[0] == "!": # 由!开头的命令，是宏调用
                macro_name = t.value[1:]
                macro_arguments = parse_convenient_dict(t.meta.get("argument", ""), macros=current_macros)
                macro_template = current_macros[macro_name]
                macro_arguments.update({"": "%"})
                expanded_text = re.sub(r"%(.*?)%", lambda match: macro_arguments.get(match[1], ""), macro_template)
                expanded_tokens = self.tokenize(expanded_text, inline_mode=True)
                # recursive expansion
                recursive_expanded_tokens, inner_macros = self.expand_and_get_defined_macros(expanded_tokens, initial_macros=current_macros)
                transformed_tokens.extend(recursive_expanded_tokens)
                current_macros.update(inner_macros)
            elif isinstance(t, CommandToken) and t.value == "ifelse":
                arguments = parse_convenient_dict(t.meta.get("argument", ""), macros=current_macros)
                a, b = arguments.get("a"), arguments.get("b")
                exp_then, exp_else = arguments.get("then"), arguments.get("else")
                exp = None
                if a == b: # 已经将引用宏的能力写到了convenient obj expr中
                    exp = exp_then
                else:
                    exp = exp_else
                if exp: # 有可能then或else没有指定内容
                    expanded_tokens = self.tokenize(exp, inline_mode=True)
                    recursive_expanded_tokens, inner_macros = self.expand_and_get_defined_macros(expanded_tokens, initial_macros=current_macros)
                    transformed_tokens.extend(recursive_expanded_tokens)
                    current_macros.update(inner_macros)
            elif isinstance(t, CommandToken) and t.value == "debug_print_macros":
                print(f"printing macros from {t}: \n", current_macros)
            elif t.require_macros:
                t = attr.evolve(t, meta=(t.meta | {"macros": current_macros.copy()}))
                transformed_tokens.append(t)
            else:
                transformed_tokens.append(t)
        return transformed_tokens, current_macros
    
    def transformer(self, tokens):
        return self.expand_and_get_defined_macros(tokens, initial_macros=None)[0]
