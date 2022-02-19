
import yaml

import attr

from mika_modules import resolve_module_ref

scene_styleml_header = r"""
\st\
\def[choice_ind=\\ifelse\[a!choice,b;%i%,then=>,else= \]]\
    \def[to_or_dial=\\ifelse\[a!choice,b;%i%,then=\\\\def\\\[to=%to%\\\]\\\\def\\\[dialog%dial%\\\]\]]\
    \def[noflash=\
            \\ifelse\[\
            a!choice,b?,\
            else=\\\\tick\\\[:0\\\]\
        \]\
        \\ifelse\[\
            a!cdm,b?,\
            else=\\\\tick\\\[:0\\\]\
        \]\
    ]\
    \def[nochoosestay=\
        \\ifelse\[a!choice,b?,then=\\\\def\\\[to=%to%\\\]\\\\def\\\[dialog%dial%\\\]\]
    ]\
\ts[imm+]
"""

@attr.s
class MikaScene:
    description = attr.ib(default="")
    connected_to = attr.ib(factory=dict)
    characters = attr.ib(factory=dict)
    
    @classmethod
    def from_yaml(cls, yaml_text):
        return cls(**yaml.safe_load(yaml_text))

    def to_styleml_text(self, this_label):
        choice_amount = len(self.connected_to) + len(self.characters)
        head = fr"\stchoice[label={this_label},n;{choice_amount},m=choice,character_dialogue_m=cdm]\!noflash \!nochoosestay[to={this_label},dial=?]"
        gotos = []
        i = 0
        for connection_label, connection_desc in self.connected_to.items():
            connection_label = resolve_module_ref(this_label, connection_label)
            gotos.append(fr"{{\!choice_ind[i={i}]-{connection_desc}}}\!to_or_dial[i={i},to={connection_label},dial=?]")
            i += 1
        for character_id, character_desc in self.characters.items():
            character_id = resolve_module_ref(this_label, character_id)
            gotos.append(fr"{{\!choice_ind[i={i}]-{character_desc}}}\!to_or_dial[i={i},to={this_label},dial=={character_id}]")
            i += 1
        tail = fr"\ts[to!to,dialogue!dialog]"
        return head + self.description + "\n" + "\n".join(gotos) + tail
    
if __name__ == "__main__":
    print(MikaScene(connected_to=dict(ap="A地",bp="b地"), description="这里是没有地", characters={"..jm":"金毛"}).to_styleml_text("nop"))
