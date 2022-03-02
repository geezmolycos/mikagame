import mika_svgui
import styleml.core, styleml.macro_ext, styleml.portal_ext
import styleml_mika_exts, styleml_glyph_exts

import mika_regional_dialogue

scr = mika_svgui.SVGGameScreen()

styleml_parser = styleml.core.StyleMLCoreParser(
    ext_parser=[
        styleml.portal_ext.PortalExtParser(),
        styleml_glyph_exts.GlyphsetExtParser(),
        styleml_mika_exts.AnimationExtParser(initial_tick=0.07),
        styleml_mika_exts.StyleExtParser(initial_style=dict(bg="white", fg="black")),
        styleml.core.ReturnCharExtParser()
    ]
)

mika_regional_dialogue.RegionalDialogueManager(
    sentences={
        "a": mika_regional_dialogue.Sentence()
    }
)

