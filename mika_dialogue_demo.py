
import attr

from mika_screen import Vector2D, List2D, Cardinal, ScreenCell
from mika_screen import str_to_mlcells
from mika_htmlui import HTMLGameScreen

from styleml.core import StyleMLCoreParser, ReturnCharExtParser
from styleml.portal_ext import PortalExtParser
from styleml.macro_ext import MacroExtParser
from styleml_mika_exts import StyleExtParser, AnimationExtParser, LineWrapExtParser

from styleml.core import CommandToken

from styleml.convenient_argument import parse_convenient_dict

from pyodide import create_proxy
from js import jQuery as jq

import asyncio

@attr.s
class Sentence:
    content = attr.ib(default=None)
    label = attr.ib(default=None)
    to = attr.ib(default=None)
    imm = attr.ib(default=False)
    is_tsm = attr.ib(default=False)

@attr.s
class ChoiceSentence(Sentence):
    choice_amount = attr.ib(default=None)
    state_macro = attr.ib(default=None)

def tokens_to_sentences(tokens):
    it = iter(tokens)
    sentences = []
    while True:
        try:
            t = next(it)
        except StopIteration:
            break
        if isinstance(t, CommandToken) and t.value in ("st", "stchoice"):
            a = {}
            arguments = parse_convenient_dict(t.meta.get("argument", ""))
            a["label"] = arguments.get("label")
            if t.value == "stchoice":
                a["choice_amount"] = arguments.get("n")
                a["state_macro"] = arguments.get("m")
            content = []
            while (content_t := next(it)).value not in ("ts", "tsm"):
                content.append(content_t)
            a["content"] = content
            end_arguments = parse_convenient_dict(content_t.meta.get("argument", ""))
            a["to"] = end_arguments.get("to")
            a["imm"] = end_arguments.get("imm")
            a["is_tsm"] = content_t.value == "tsm"
            st = {"st": Sentence, "stchoice": ChoiceSentence}[t.value](**a)
            sentences.append(st)
    return sentences

@attr.s
class CharacterDialogue:
    
    sentences = attr.ib(factory=list)
    labeled_sentences = attr.ib(init=False)
    current_sentence_index = attr.ib(default=0)
    current_macros = attr.ib(factory=dict)
    next_macros = attr.ib(factory=dict)
    macro_parser = attr.ib(default=None)
    styleml_parser = attr.ib(default=None)
    
    def __attrs_post_init__(self):
        for i, st in enumerate(self.sentences):
            if st.label is not None:
                self.labeled_sentences[st.label] = i # 记录每个label对应的sentence index
    
    @property
    def current_sentence(self):
        return self.sentences[self.current_sentence_index]
    
    def eval_sentence(self, choice=None):
        if isinstance(self.current_sentence, ChoiceSentence):
            self.current_macros[self.current_sentence.state_macro] = choice
        expanded, macros = self.macro_parser.expand_and_get_defined_macros(
            self.current_sentence.content,
            initial_macros=self.current_macros
            )
        rendered = self.styleml_parser.render(self.styleml_parser.transform(expanded))
        self.next_macros = macros
        return rendered
    
    def next_sentence(self):
        self.current_macros = self.next_macros
        if self.current_sentence.to is not None:
            if self.current_sentence.is_tsm: # 是引用自宏的引用值
                next_index = self.labeled_sentences[self.current_macros[self.current_sentence.to]]
            else:
                next_index = self.labeled_sentences[self.current_sentence.to]
        else:
            next_index = self.current_sentence_index + 1
        if len(self.sentences) <= next_index:
            raise IndexError("no more sentences!")
        self.current_sentence_index = next_index

# 描述有选项的长对话的语言：
# 使用\st表示一个句子，可选的label参数作为句子名字
# \ts表示句子结束，参数的imm表示给用户停止的机会与否，参数的to表示要跳转到的label（默认是下一句）
# \tsm表示参数不是字面量，而是宏名字
# 使用\stchoice[n=数量, m=choice]来表示让玩家作出选择，选择时会改变当前句子的macro，即choice会变成0, 1, 2, ...，并且会重新渲染该句子
# 当前句子可以通过该macro来改变自己的样貌
# 而\stchoicem是上述命令的宏版本
# 解析流程：tokenize->外部分析器，将长对话分成「若干个句子」->将每个句子做成一个实例，编号id，有label的贴上label
# 句子实例中包括tokenize出的token，句子结束方式

# 更下一步设计：
# 先使用按钮选项完成游戏的主程序，使用tab在各区域间切换，使用字母按键选择选项。

scr = HTMLGameScreen()

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

jq("body").append(scr.jq_cont)

dialogue_frame_pos = Vector2D(10, 19)
dialogue_frame_area = (25, 5)
dialogue_frame_dr = Vector2D(dialogue_frame_pos.x + dialogue_frame_area[0], dialogue_frame_pos.y + dialogue_frame_area[1])

dialogue_text = r"""
\st this \ts
\st that \ts
\st fine \ts
\st okay \ts
"""

character_dialogue = CharacterDialogue(
    sentences=tokens_to_sentences(styleml_parser.tokenize(dialogue_text)),
    styleml_parser=styleml_parser,
    macro_parser=macro_parser
    )

def clear_dialogue():
    for y in range(dialogue_frame_pos.y, dialogue_frame_dr.y):
        for x in range(dialogue_frame_pos.x, dialogue_frame_dr.x):
            scr.print_cell(Vector2D(x, y), ScreenCell(fg="black", bg="white"))

def print_dialogue(interruption_event):
    tokens = character_dialogue.eval_sentence()
    print(tokens)
    asyncio.create_task(scr.async_print_tokens(tokens, dialogue_frame_pos, interruption_event=interruption_event))

clear_dialogue()
def _(e):
    s = jq("#sty-text").val()
    clear_dialogue()
    print_dialogue(None)
    character_dialogue.next_sentence()
jq("#show-sty").on("click", create_proxy(_))