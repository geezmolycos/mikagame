import mika_svgui
import styleml.core, styleml.macro_ext, styleml.portal_ext
import styleml_mika_exts, styleml_glyph_exts
import mika_yaml_dialogue

import mika_regional_dialogue

from utilities import Vector2D

from js import jQuery as jq

scr = mika_svgui.SVGGameScreen()

jq("body").append(scr.jq_svg)

styleml_parser = styleml.core.StyleMLCoreParser(
    ext_parser=[
        styleml.portal_ext.PortalExtParser(),
        styleml_glyph_exts.GlyphsetExtParser(),
        styleml_mika_exts.AnimationExtParser(initial_tick=0.07),
        styleml_mika_exts.StyleExtParser(),
        styleml.core.ReturnCharExtParser()
    ]
)

speech_region = mika_regional_dialogue.ScreenRegion(
    size=Vector2D(25, 5),
    origin=Vector2D(0, 5)
)

map_region = mika_regional_dialogue.ScreenRegion(
    size=Vector2D(25, 5),
    origin=Vector2D(0, 0)
)

manager = mika_regional_dialogue.RegionalDialogueManager(
    sentences=mika_yaml_dialogue.parse_mikad_module("a.c", """
.char:
    default:
        region_conv: "=speech"
    st:
        - 今天是个好日子
        - 心想的事儿都能成
.mmm:
    default:
        region_conv: "=map"
    st:
        -
            _template: choice
            desc: 描述
            choices:
                - j,.<c.char.0,走
                - j,.,此
"""
    ),
    screen_regions={
        "speech": speech_region,
        "map": map_region
    },
    macro_parser=styleml.macro_ext.MacroExtParser(),
    postmacro_parser=styleml_parser,
    current_sentence_name="a.c.mmm.0"
)

print(manager.sentences)

def _(code, ctrl, shift, alt):
    manager.next_sentence()
    scr.print_tokens(manager.eval_sentence(), origin=Vector2D(0, 0))

scr.registered_onkeypress.append(_)
scr.print_tokens(manager.eval_sentence(), origin=Vector2D(0, 0))
manager.eval_sentence(choice=0)
manager.next_sentence()
scr.print_tokens(manager.eval_sentence(), origin=Vector2D(0, 0))
