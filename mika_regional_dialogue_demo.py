import mika_svgui
import styleml.core, styleml.macro_ext, styleml.portal_ext
import styleml_mika_exts, styleml_glyph_exts

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
    sentences={
        "_init": mika_regional_dialogue.Sentence(
            content_tokens=styleml_parser.tokenize("abcde"),
            region_conv="=speech",
            next_conv="=a",
            choice_amount=None,
        ),
        "a": mika_regional_dialogue.Sentence(
            content_tokens=styleml_parser.tokenize("hhh"),
            region_conv="=map",
            next_conv="=_init",
            choice_amount=None,
        )
    },
    screen_regions={
        "speech": speech_region,
        "map": map_region
    },
    macro_parser=styleml.macro_ext.MacroExtParser(),
    postmacro_parser=styleml_parser,
    current_sentence_name="_init"
)

print(manager)
manager.eval_sentence()
manager.next_sentence()
scr.print_tokens(manager.eval_sentence(), origin=Vector2D(0, 0))

