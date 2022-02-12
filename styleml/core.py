
from string import ascii_letters, digits

import attr

from utilities import Vector2D, list_split, list_join

"""
接口化styleml语言：
styleml语言的各解析阶段和各概念名称
原文(text) -tokenize->
tokens -transform->
tokens -render->
tokens(pos, style) -做其他的事情，例如将其转化为footprints->
...

tokens是若干个Token实例组成的列表，每个Token实例有(类型(type)，)值(value)和元数据(meta)
mlcellstr代表多行的ScreenCell，每个Cell都有元数据，同时有游标cursor，可以多个串起来
footprints是包括坐标元数据的mlcellstr

tokenize过程是固定的，将文本转化成CharacterToken, BracketToken, CommandToken
transform过程由styleml的各扩展完成，负责解析对应的CommandToken，并为文本添加元数据
render过程由某个Renderer完成，扩展可以在render过程中添加元数据

"""
@attr.s(frozen=True)
class Token:
    value = attr.ib(default=None)
    meta = attr.ib(factory=dict)
    printable = False
    require_macros = False

@attr.s(frozen=True)
class CharacterToken(Token):
    printable = True

@attr.s(frozen=True)
class BracketToken(Token):
    
    def is_left(self):
        return self.value == "{"
    
    def is_right(self):
        return self.value == "}"
    
@attr.s(frozen=True)
class CommandToken(Token):
    require_macros = True

@attr.s(frozen=True)
class AnchorToken(Token):
    pass

@attr.s(frozen=True)
class AnchorRemoveToken(Token):
    pass

@attr.s(frozen=True)
class ChainToken(Token):
    pass

@attr.s(frozen=True)
class ReposToken(Token):
    pass
    
    def repos_target(self, original_pos):
        raise NotImplementedError()

@attr.s(frozen=True)
class RelReposToken(ReposToken):
    
    def repos_target(self, original_pos):
        col, row = self.value
        v = Vector2D(col or 0, row or 0) # None代表不移动
        return original_pos + v

@attr.s(frozen=True)
class AbsReposToken(ReposToken):
    
    def repos_target(self, original_pos):
        col, row = self.value
        v = Vector2D(original_pos.x if col is None else col, original_pos.y if row is None else row) # None代表不移动
        return v

@attr.s(frozen=True)
class NewLineToken(ReposToken):
    
    def repos_target(self, original_pos):
        x, y = original_pos
        return Vector2D(0, y+self.value)

@attr.s
class StyleMLCoreParser:
    """
    StyleML的核心解析器
    """
    command_identifier = ascii_letters + digits + "_" + "!"
    
    ext_parser = attr.ib(factory=list)
    
    def __attrs_post_init__(self):
        for parser in self.ext_parser:
            parser.set_core_parser(self)
    
    @classmethod
    def tokenize(cls, text, inline_mode=False): # inline_mode不使用多行处理，不截行首行尾，也不除行首空格
        # 处理转义符
        text_as_rlist = list(reversed(text))
        escaped_text_as_list = []
        while len(text_as_rlist) != 0:
            ch = text_as_rlist.pop()
            try:
                escape = text_as_rlist[-1]
            except IndexError:
                escape = ""
            if ch == "\\" and escape in tuple("\\[]{}@#"): # 处理转义字符
                text_as_rlist.pop()
                escaped_text_as_list.append(ch + escape)
            else:
                escaped_text_as_list.append(ch)
        
        if not inline_mode:
            # 处理行首开始符(@)和注释符(#)
            trimmed_text_as_rlist = []
            for line in list_split(escaped_text_as_list, "\n"):
                leading, *rest = list_split(line, "@")
                if not rest: # 没行首开始符
                    leading.reverse()
                    try:
                        while (ch := leading.pop()) == " ": # 去除前导空格
                            pass
                        leading.append(ch) # 把去多的加回来
                    except IndexError:
                        pass # 整行都是空格，pop完了
                    leading.reverse()
                    line = leading
                else:
                    rest = list_join(rest, "@")
                    line = rest
                # 注释符
                leading, *rest = list_split(line, "#")
                trimmed_text_as_rlist.append(leading)
            trimmed_text_as_rlist = list_join(trimmed_text_as_rlist, "\n")
            trimmed_text_as_rlist.reverse()
            
            # 处理换行符转义
            flattened_text_as_rlist = []
            while len(trimmed_text_as_rlist) != 0:
                ch = trimmed_text_as_rlist.pop()
                try:
                    escape = trimmed_text_as_rlist[-1]
                except IndexError:
                    escape = ""
                if ch == "\\" and escape == "\n":
                    trimmed_text_as_rlist.pop()
                else:
                    flattened_text_as_rlist.append(ch)
            flattened_text_as_rlist.reverse()
        else:
            escaped_text_as_list.reverse()
            flattened_text_as_rlist = escaped_text_as_list
            
        
        # 解析tokens
        tokens = []
        while len(flattened_text_as_rlist) != 0:
            ch = flattened_text_as_rlist.pop()
            if ch == "\\": # command
                command = []
                try:
                    while flattened_text_as_rlist[-1] in cls.command_identifier:
                        command.append(flattened_text_as_rlist.pop())
                except IndexError: # 防止文本最后出现命令的情况
                    pass
                command = "".join(command)
                meta = {}
                try:
                    if flattened_text_as_rlist[-1] == "[":
                        flattened_text_as_rlist.pop()
                        argument = []
                        while flattened_text_as_rlist[-1] != "]":
                            argument.append(flattened_text_as_rlist.pop()[-1]) # 可能有转义序列
                        flattened_text_as_rlist.pop()
                        argument = "".join(argument)
                        meta["argument"] = argument
                except IndexError: # 防止文本最后出现无参数的命令
                    pass
                if len(flattened_text_as_rlist) != 0 and flattened_text_as_rlist[-1] == " ": # command后可以有一个空格
                    flattened_text_as_rlist.pop()
                tokens.append(CommandToken(command, meta))
            elif ch in tuple("{}"):
                tokens.append(BracketToken(ch))
            else:
                tokens.append(CharacterToken(ch[-1])) # 可能有转义序列
        
        return tokens

    def transform(self, tokens):
        for parser in self.ext_parser:
            tokens = parser.transformer(tokens)
        return tokens

    def renderer(self, tokens):
        """
        支持的Token类型：printable的，Anchor, Chain, Repos
        """
        rendered_tokens = []
        current_pos = Vector2D(0, 0)
        current_anchors = {}
        for t in tokens:
            rendered_t = attr.evolve(t, meta=(t.meta | {"pos": current_pos}))
            rendered_tokens.append(rendered_t)
            if isinstance(rendered_t, ReposToken):
                current_pos = rendered_t.repos_target(current_pos)
            elif isinstance(rendered_t, AnchorToken):
                current_anchors[rendered_t.value] = rendered_t
            elif isinstance(rendered_t, AnchorRemoveToken):
                current_anchors.pop(rendered_t.value)
            elif isinstance(rendered_t, ChainToken):
                current_pos = current_anchors.get(rendered_t.value).meta["pos"] or Vector2D(0, 0)
            if t.printable:
                current_pos += Vector2D(1, 0)
        return rendered_tokens
        

    def render(self, tokens):
        tokens = self.renderer(tokens)
        for parser in self.ext_parser:
            tokens = parser.post_renderer(tokens)
        return tokens

@attr.s
class StyleMLExtParser:
    
    core = attr.ib(default=None)
    
    def set_core_parser(self, core):
        self.core = core
    
    def transformer(self, tokens):
        return tokens
    
    def post_renderer(self, tokens):
        return tokens

@attr.s
class ReturnCharExtParser(StyleMLExtParser):
    
    def transformer(self, tokens):
        transformed_tokens = []
        for t in tokens:
            if isinstance(t, CharacterToken) and t.value == "\n":
                transformed_tokens.append(NewLineToken(1))
            elif isinstance(t, CharacterToken) and t.value == "\r":
                transformed_tokens.append(NewLineToken(0))
            else:
                transformed_tokens.append(t)
        return transformed_tokens

if __name__ == "__main__":
    import sys
    s = StyleMLCoreParser(ext_parser=[ReturnCharExtParser()])
    print(s.render(s.transform(s.tokenize("1234567"))))
