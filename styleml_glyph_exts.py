
import attr

from styleml.core import StyleMLExtParser
from styleml.core import BracketToken, CommandToken, CharacterToken
from styleml.convenient_argument import parse_convenient_obj_repr

@attr.s
class CustomGlyph:
    
    type = attr.ib(default=None)
    value = attr.ib(default=None)
    meta = attr.ib(factory=dict)

@attr.s
class GlyphsetExtParser(StyleMLExtParser):
    
    initial_glyphset = attr.ib(default=None)
    
    def transformer(self, tokens):
        step_glyphset = [self.initial_glyphset]
        transformed_tokens = []
        for t in tokens:
            if isinstance(t, BracketToken) and t.is_left():
                step_glyphset.append(step_glyphset[-1])
                transformed_tokens.append(t)
            elif isinstance(t, BracketToken) and t.is_right():
                step_glyphset.pop()
                transformed_tokens.append(t)
            elif isinstance(t, CommandToken) and t.value == "g":
                transformed_tokens.append(
                    CharacterToken(value=CustomGlyph(type=step_glyphset[-1], value=t.meta.get("argument")))
                    )
            elif isinstance(t, CommandToken) and t.value == "glyphset":
                step_glyphset[-1] = t.meta.get("argument")
            else:
                transformed_tokens.append(t)
        return transformed_tokens