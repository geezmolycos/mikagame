import attr

from styleml.core import CommandToken

from styleml.convenient_argument import parse_convenient_dict

@attr.s
class Sentence:
    content = attr.ib(default=None)
    st_arg = attr.ib(default=None)
    ts_arg = attr.ib(default=None)
    label = attr.ib(default=None)

@attr.s
class ChoiceSentence(Sentence):
    pass

def tokens_to_sentences(tokens):
    it = iter(tokens)
    sentences = []
    while True:
        try:
            t = next(it)
        except StopIteration:
            break
        if isinstance(t, CommandToken) and t.value in ("st", "stchoice"):
            st_arg = t.meta.get("argument", "")
            content = []
            while (content_t := next(it)).value not in ("ts"):
                content.append(content_t)
            ts_arg = content_t.meta.get("argument", "")
            st = {"st": Sentence, "stchoice": ChoiceSentence}[t.value](content=content, st_arg=st_arg, ts_arg=ts_arg, label=parse_convenient_dict(st_arg).get("label"))
            sentences.append(st)
    return sentences

@attr.s
class CharacterDialogue:
    
    sentences = attr.ib(factory=list)
    labeled_sentences = attr.ib(init=False)
    current_sentence_index = attr.ib(init=False)
    current_macros = attr.ib(init=False)
    current_st_args = attr.ib(init=False)
    current_ts_args = attr.ib(init=False)
    next_macros = attr.ib(init=False)
    macro_parser = attr.ib(default=None)
    styleml_parser = attr.ib(default=None)
    
    def __attrs_post_init__(self):
        self.labeled_sentences = {}
        for i, st in enumerate(self.sentences):
            if st.label is not None:
                self.labeled_sentences[st.label] = i # 记录每个label对应的sentence index
        self.reset_dialogue(clear_macro=True)
    
    @property
    def current_sentence(self):
        return self.sentences[self.current_sentence_index]
    
    def eval_sentence(self, choice=None):
        self.current_st_args = parse_convenient_dict(self.current_sentence.st_arg, macros=self.current_macros)
        if isinstance(self.current_sentence, ChoiceSentence):
            choice_macro_name = self.current_st_args.get("m")
            if choice_macro_name is not None:
                self.current_macros[choice_macro_name] = choice
        expanded, macros = self.macro_parser.expand_and_get_defined_macros(
            self.current_sentence.content,
            initial_macros=self.current_macros
            )
        rendered = self.styleml_parser.render(self.styleml_parser.transform(expanded))
        self.next_macros = macros
        self.current_ts_args = parse_convenient_dict(self.current_sentence.ts_arg, macros=self.next_macros)
        return rendered
    
    def next_sentence(self):
        if "to" in self.current_ts_args:
            to = self.current_ts_args.get("to")
            next_index = self.labeled_sentences[to]
        else:
            next_index = self.current_sentence_index + 1
        if len(self.sentences) <= next_index:
            raise IndexError("no more sentences!")
        self.current_macros = self.next_macros
        self.current_sentence_index = next_index
    
    def reset_dialogue(self, clear_macro=False):
        self.current_sentence_index = 0
        self.current_st_args = None
        self.current_ts_args = None
        if clear_macro:
            self.current_macros = {}
            self.next_macros = {}

@attr.s
class MapDialogue(CharacterDialogue):
    
    characters = attr.ib(factory=dict)
    
    def should_change_to_character(self):
        if "dialogue" in self.current_ts_args and self.current_ts_args["dialogue"] is not None:
            return True, self.current_ts_args["dialogue"]
        else:
            return False, None
    
    def eval_sentence(self, choice=None, in_character_dialogue=False):
        if in_character_dialogue:
            if "character_dialogue_m" in self.current_st_args:
                character_dialogue_macro_name = self.current_st_args["character_dialogue_m"]
                self.current_macros[character_dialogue_macro_name] = in_character_dialogue
        else:
            if self.current_st_args is not None and "character_dialogue_m" in self.current_st_args:
                character_dialogue_macro_name = self.current_st_args["character_dialogue_m"]
                if character_dialogue_macro_name in self.current_macros:
                    self.current_macros.pop(character_dialogue_macro_name)
        return super().eval_sentence(choice)
    
        

# 描述有选项的长对话的语言：
# 使用\st表示一个句子，可选的label参数作为句子名字
# \ts表示句子结束，参数的imm表示给用户停止的机会与否，参数的to表示要跳转到的label（默认是下一句）
# 使用\stchoice[n=数量, m=choice]来表示让玩家作出选择，选择时会改变当前句子的macro，即choice会变成0, 1, 2, ...，并且会重新渲染该句子
# 当前句子可以通过该macro来改变自己的样貌
# 解析流程：tokenize->外部分析器，将长对话分成「若干个句子」->将每个句子做成一个实例，编号id，有label的贴上label
# 句子实例中包括tokenize出的token，句子结束方式

# 更下一步设计：
# 先使用按钮选项完成游戏的主程序，使用tab在各区域间切换，使用字母按键选择选项。


if __name__ == "__main__":
    
    from utilities import Vector2D, List2D, Cardinal

    from mika_screen import ScreenCell

    from styleml.core import StyleMLCoreParser, ReturnCharExtParser
    from styleml.portal_ext import PortalExtParser
    from styleml.macro_ext import MacroExtParser
    from styleml_mika_exts import StyleExtParser, AnimationExtParser, LineWrapExtParser
    
    dialogue_text = r"""
\st 今天是个好日子\ts
\st 心想的事儿都能成\ts
\stchoice[label=ch,n;2,m=choice]\
    \def[selected=\\s\[hlit+\]]\
    \ifelse[\
        a!choice,b?,\
        else=\\tick\[:0\]\
    ]\
    今天你想什么事呀？
    \repos[row;3,col;5]\
    {\ifelse[\
        a!choice,b;0,\
        then!selected\
    ]没想什么}\
    \offset[col;8]\
    {\ifelse[\
        a!choice,b;1,\
        then!selected\
    ]想吃饭}\
    \ifelse[\
        a!choice,b;0,\
        then=\\def\[to=a\],\
        else=\\def\[to=b\]\
    ]\
\ts[to!to]\
\st[label=a]\
那就等明天来罢。
\ts[to=ch]\
\st[label=b]\
给你吃大嘴巴子。
\ts\
\st啪\ts
    """
    
    styleml_parser = StyleMLCoreParser(
        ext_parser=[
            PortalExtParser(),
            AnimationExtParser(initial_tick=0.1),
            StyleExtParser(initial_style=dict(bg="white", fg="black")),
            ReturnCharExtParser(),
            LineWrapExtParser(cr_area=Vector2D(20, 0))
            ]
        )

    macro_parser = MacroExtParser()
    
    character_dialogue = CharacterDialogue(
        sentences=tokens_to_sentences(styleml_parser.tokenize(dialogue_text)),
        styleml_parser=styleml_parser,
        macro_parser=macro_parser
        )
    
    from pprint import pprint
    pprint(character_dialogue.sentences)
    character_dialogue.eval_sentence()
    globals().update(locals())