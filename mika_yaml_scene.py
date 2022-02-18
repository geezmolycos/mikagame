
import yaml

import attr

scene_styleml_header = r"""
\st\
\def[choice_ind=\\ifelse\[a!choice,b;%i%,then=*,else= \]]\
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
\ts[imm+]
"""

@attr.s
class MikaScene:
    description = attr.ib(default="")
    connected_to = attr.ib(factory=dict)
    characters = attr.ib(factory=dict)
    
    @classmethod
    def from_yaml(cls, yaml_text):
        return cls(**yaml.load(yaml_text, Loader=yaml.Loader))

    def to_styleml_text(self, this_label):
        choice_amount = len(self.connected_to) + len(self.characters)
        head = fr"\stchoice[label={this_label},n;{choice_amount},m=choice,character_dialogue_m=cdm]\!noflash "
        gotos = []
        i = 0
        for connection_label, connection_desc in self.connected_to.items():
            gotos.append(fr"\!choice_ind[i={i}]{connection_desc}\!to_or_dial[i={i},to={connection_label},dial=?]")
            i += 1
        for character_id, character_desc in self.characters.items():
            gotos.append(fr"\!choice_ind[i={i}]{character_desc}\!to_or_dial[i={i},to={this_label},dial=={character_id}]")
            i += 1
        tail = fr"\ts[to!to,dialogue!dialog]"
        return head + self.description + "\n" + "\n".join(gotos) + tail
    
if __name__ == "__main__":
    print(MikaScene(connected_to=dict(ap="A地",bp="b地"), description="这里是没有地", characters=dict(jm="金毛")).to_styleml_text("nop"))
