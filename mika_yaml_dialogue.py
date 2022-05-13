import yaml
import attr

import mika_regional_dialogue
import mika_modules

class TemplateClassProxy:
    def __init__(self, target):
        self.target = target
        
    def __getitem__(self, key):
        return getattr(self.target, key)
    

def extend_flow(carrier, insertion):
    if "next_conv" not in insertion and "next_conv" in carrier:
        insertion["next_conv"] = carrier["next_conv"]
    if "return_conv" not in insertion and "return_conv" in carrier:
        insertion["return_conv"] = carrier["next_conv"]

class Templates:
    
    def _default(self, name, content):
        return self.expand_abbr(name, content)
    
    def expand_abbr(self, name, content):
        content["content_tokens"] = content.get("content_tokens", content.get("contents", content.get("c", [])))
        return content
    
    def alias(self, name, content):
        alias_name = content["alias"]
        content[alias_name] = dict(next_conv="="+name, uninterruptable_conv="+", pause_after_conv="-") | {"_is_paragraph": True, "_use_absolute_name": True}
        return content
    
    def seq(self, name, content):
        try:
            default = content.copy()
            if "s" in default:
                default.pop("s")
            if "_t" in default:
                default.pop("_t")
        except KeyError:
            default = {}
        s = content.pop("s") 
        for i, l in enumerate(s):
            if isinstance(l, str):
                l = {"content_tokens": l, "_is_paragraph": True}
            # make sure content is dict
            l = default | dict(next_conv="=" + ".." + str(i + 1), return_conv="-") | l
            content[str(i)] = l
        final = default | {"_t": ["imm"]}
        final["mock_location"] = content.get("mock_location", name)
        extend_flow(content, final)
        content[str(len(s))] = final
        content.update(dict(next_conv="=.0", return_conv="-", uninterruptable_conv="+", pause_after_conv="-") | {"_is_paragraph": True})
        return content
    
    def choice(self, name, content):
        """
        choice有自己的描述，还有各子选项的对话内容
        """
        text = r"\!choiceanim " + content["content_tokens"] + "\n"
        for i, choice_d in enumerate(content["ch"]):
            key, choice_paragraph = choice_d["key"], choice_d["p"]
            criteria = choice_d.get("criteria")
            text += "{"
            if criteria is not None:
                text += fr"\def[.checkcriteria=\\ifelse\[a!{criteria},b-,then=\\\\def\\\[.target=.\\\]\\\\def\\\[.iscall-\\\]\\\\!disabledchosen ,else=\\\\!chosen \]]"
            else:
                text += fr"\def[.checkcriteria=\\!chosen ]"
            text += fr"\ifelse[a!.choice,b;{i},then=\\def\[.target=.{i}\]\\!.checkcriteria ,else=\\!unchosen ]"
            text += key
            text += "}\n"
            choice_paragraph["mock_location"] = content.get("mock_location", name)
            extend_flow(content, choice_paragraph)
            content[str(i)] = choice_paragraph | {"_is_paragraph": True}
        text += fr"\ifelse[a!.choice,b?,then=\\def\[.target=.\]]"
        return content | {
            "content_tokens": text,
            "next_conv": "!.target",
            "choice_amount_conv": f";{len(content['ch'])}",
            "call_conv": "-",
            "return_conv": "-",
        }
            
    
    def branch(self, name, content):
        criteria = content["criteria"]
        content["t"].update({"_is_paragraph": True})
        content["f"].update({"_is_paragraph": True})
        content["content_tokens"] = fr"\ifelse[a!{criteria},b+,then=\\def\[.target=.t\],else=\\def\[.target=.f\]]"
        content["t"]["mock_location"] = content.get("mock_location", name)
        content["f"]["mock_location"] = content.get("mock_location", name)
        extend_flow(content, content["t"])
        extend_flow(content, content["f"])
        return content | {
            "next_conv": "!.target",
            "uninterruptable_conv": "+",
            "pause_after_conv": "-"
        }
    
    def imm(self, name, content):
        content["pause_after_conv"] = "-"
        content["uninterruptable_conv"] = "+"
        return content

    def call(self, name, content):
        if "next_conv" in content:
            content["call_return_conv"] = content["next_conv"]
        content["next_conv"] = content["call_target"]
        content["call_conv"] = "+"
        return content

def make_sentence_ignore_extra_args(kwargs):
    typ = mika_regional_dialogue.Sentence
    filtered = {
        attribute.name: kwargs[attribute.name]
        for attribute in typ.__attrs_attrs__
        if attribute.name in kwargs
    }
    return typ(**filtered)

def paragraph_constructor(loader, node):
    try:
        value = loader.construct_mapping(node)
    except yaml.constructor.ConstructorError:
        value = loader.construct_scalar(node)
        value = {"content_tokens": value}
    value["_is_paragraph"] = True
    return value

def apply_template(
    paragraph_name,
    paragraph_content,
    templates=TemplateClassProxy(Templates())
    ):
    templates_to_apply = ["_default"] + paragraph_content.pop("_t", [])
    result = paragraph_content
    for t in templates_to_apply:
        result = templates[t](paragraph_name, result)
    return result

def expand_paragraph(
    paragraph_name,
    paragraph_content
    ):
    expanded = {}
    if isinstance(paragraph_content, dict):
        new_paragraph_content = {}
        for k, v in paragraph_content.items():
            if isinstance(v, dict) and v.get("_is_paragraph", False):
                if not v.get("_use_absolute_name", False):
                    rel_name = "." + k
                else:
                    rel_name = k
                subparagraph_name = mika_modules.resolve_module_ref(paragraph_name, rel_name)
                v = apply_template(subparagraph_name, v)
                try:
                    expanded.update(expand_paragraph(subparagraph_name, v))
                except Exception as e:
                    raise ValueError(f"error expanding paragraph {subparagraph_name}") from e
            else:
                new_paragraph_content[k] = v
    elif isinstance(paragraph_content, str):
        new_paragraph_content = {"content_tokens": paragraph_content}
    expanded[paragraph_name] = new_paragraph_content
    return expanded

def to_sentence_pool(expanded_paragraphs):
    return {k: make_sentence_ignore_extra_args(v) for k, v in expanded_paragraphs.items()}

def parse_mikad_module(module_name, s):
    yaml.add_constructor(u'!para', paragraph_constructor)
    so = yaml.full_load(s)
    ex = expand_paragraph(module_name, so)
    pl = to_sentence_pool(ex)
    return pl

if __name__ == "__main__":
    s = """
a:
    !para
    c: good
    dd:
        !para
        _t: [alias]
        alias: ..cc
        c: better
b:
    !para
    _t: [seq]
    s:
        - ca
        - 
            !para
            _t: [seq]
            s:
                - ia
                - ib
                - ic
        - cc
d:
    !para
    _t: [choice]
    c: choose one
    ch:
        -
            key: hello
            p: !para 1234abc
        -
            key: bye
            p: !para 987byebye
    """
    yaml.add_constructor(u'!para', paragraph_constructor)
    so = yaml.full_load(s)
    ex = expand_paragraph("s", so)
    pl = to_sentence_pool(ex)
    from pprint import pprint
    pprint(pl)
    
