
import attr

from utilities import Vector2D
import mika_modules
import styleml.convenient_argument as conv
from styleml.core import StyleMLCoreParser
from styleml_mika_exts import LineWrapExtParser, AffineTransformExtParser

@attr.s
class ScreenRegion:
    size = attr.ib(default=Vector2D(0, 0))
    origin = attr.ib(default=Vector2D(0, 0))
    row_grow = attr.ib(default=Vector2D(1, 0))
    col_grow = attr.ib(default=Vector2D(0, 1))

@attr.s
class Sentence:
    
    content_tokens = attr.ib(default=None)
    region_conv = attr.ib(default=None)
    next_conv = attr.ib(default=None)
    choice_amount = attr.ib(default=None)
    uninterruptable = attr.ib(default=False)
    pause_after = attr.ib(default=True)
    call_conv = attr.ib(default=None)
    return_conv = attr.ib(default=None)
    clear_region_conv = attr.ib(default=None)
    meta = attr.ib(factory=dict)
    
    def __attrs_post_init__(self):
        if isinstance(self.content_tokens, str):
            self.content_tokens = StyleMLCoreParser.tokenize(self.content_tokens)
    
    @property
    def has_choices(self):
        return self.choice_amount is not None

@attr.s
class ModularMacroProxy:
    global_macros = attr.ib(factory=dict)
    stage = attr.ib(factory=dict)
    base_module = attr.ib(default="")
    
    def __getitem__(self, macro_name):
        absolute = mika_modules.resolve_module_ref(self.base_module, macro_name)
        if absolute not in self.stage:
            return self.global_macros[absolute]
        return self.stage[absolute]
    
    def __setitem__(self, macro_name, value):
        absolute = mika_modules.resolve_module_ref(self.base_module, macro_name)
        self.stage[absolute] = value
    
    def __contains__(self, macro_name):
        absolute = mika_modules.resolve_module_ref(self.base_module, macro_name)
        return absolute in self.stage or absolute in self.global_macros
    
    def merge(self):
        self.global_macros.update(self.stage)
    
    def copy(self):
        return attr.evolve(self, stage=self.stage.copy())

    def update(self, value):
        if isinstance(value, dict):
            self.stage.update(value)
        elif isinstance(value, ModularMacroProxy):
            if self.global_macros is not value.global_macros:
                raise ValueError("other is incompatible with this proxy")
            self.stage.update(value.stage)
    
    def get(self, macro_name, default=None):
        try:
            return self[macro_name]
        except KeyError:
            return default

@attr.s
class RegionalDialogueManager:

    sentences = attr.ib(factory=dict)
    screen_regions = attr.ib(factory=dict)
    macros = attr.ib(factory=dict)
    macro_parser = attr.ib(default=None)
    postmacro_parser = attr.ib(default=None)
    current_sentence_name = attr.ib(default=None)
    next_sentence_name = attr.ib(default=None)
    is_next_sentence_call = attr.ib(default=False)
    is_next_sentence_return = attr.ib(default=False)
    call_stack = attr.ib(factory=list)
    
    @property
    def current_sentence(self):
        return self.sentences[self.current_sentence_name]
    
    def eval_sentence(self, choice=None):
        s = self.current_sentence
        name = self.current_sentence_name
        proxy = ModularMacroProxy(global_macros=self.macros, base_module=name)
        if s.has_choices:
            proxy[".choice"] = choice
        expanded, macros = self.macro_parser.expand_and_get_defined_macros(s.content_tokens, proxy)
        self.next_sentence_name = mika_modules.resolve_module_ref(
            name,
            conv.parse_convenient_obj_repr(s.next_conv, macros=macros)
        )
        self.is_next_sentence_call = conv.parse_convenient_obj_repr(s.call_conv, macros=macros)
        self.is_next_sentence_return = conv.parse_convenient_obj_repr(s.return_conv, macros=macros)
        rendered = self.postmacro_parser.render(self.postmacro_parser.transform(expanded))
        region = self.screen_regions[conv.parse_convenient_obj_repr(s.region_conv, macros=macros)]
        line_wrapped = LineWrapExtParser(region.size, only_printable=False).post_renderer(rendered)
        transformed = AffineTransformExtParser(origin=region.origin, col_grow=region.col_grow, row_grow=region.row_grow).post_renderer(line_wrapped)
        macros.merge()
        return transformed
    
    def next_sentence(self):
        if self.is_next_sentence_call:
            self.call_stack.append(self.current_sentence_name)
        if self.is_next_sentence_return:
            self.current_sentence_name = self.call_stack.pop()
        else:
            self.current_sentence_name = self.next_sentence_name

    