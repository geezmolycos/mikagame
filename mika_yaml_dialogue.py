import yaml
import mika_regional_dialogue
import mika_modules

class TemplateClassProxy:
    def __init__(self, target):
        self.target = target
        
    def __getitem__(self, key):
        return getattr(self.target, key)

class Templates:
    
    def alias(self, content):
        pass

    
    def seq(self, content):
        content = content.copy()
        try:
            default = content.pop("default")
        except KeyError:
            default = {}
        s = content.pop("s") 
        for i, l in enumerate(s):
            if isinstance(l, str):
                l = {"content_tokens": l}
            # make sure content is dict
            l = default | dict(next_conv="=" + ".." + str(i + 1)) | l | {"_is_paragraph": True}
            content[str(i)] = l
        content[str(len(s))] = default | dict(next_conv=content["next_conv"], uninterruptable_conv="+", pause_after_conv="-")
        content.update(dict(next_conv="=.0", uninterruptable_conv="+", pause_after_conv="-"))
    
    def choice(self, content):
        pass

def make_sentence_ignore_extra_args(kwargs):
    kwargs["content_tokens"] = kwargs.get("content_tokens", kwargs.get("contents", kwargs.get("c", [])))
    typ = mika_regional_dialogue.Sentence
    filtered = {
        attribute.name: kwargs[attribute.name]
        for attribute in typ.__attrs_attrs__
        if attribute.name in kwargs
    }
    return typ(**filtered)

def paragraph_constructor(loader, node):
    value = loader.construct_mapping(node)
    value["_is_paragraph"] = True
    return value

def apply_template(
    paragraph_content,
    templates=TemplateClassProxy(Templates())
    ):
    paragraph_content = paragraph_content.copy()
    templates_to_apply = paragraph_content.pop("_t")
    result = paragraph_content
    for t in templates_to_apply:
        result = templates[templates_to_apply](result)
    return result

def expand_paragraph(
    module_name,
    paragraph_content
    ):
    expanded = {}
    if isinstance(paragraph_content, dict):
        new_paragraph_content = {}
        for k, v in paragraph_content.items():
            if isinstance(v, dict) and v["_is_paragraph"]:
                submodule_name = mika_modules.resolve_module_ref(module_name, "." + k)
                expanded.update(expand_paragraph(submodule_name, v))
            else:
                new_paragraph_content[k] = v
    elif isinstance(paragraph_content, str):
        new_paragraph_content = {"content_tokens": paragraph_content}
    expanded[module_name] = new_paragraph_content
    return expanded

def to_sentence_pool(expanded_paragraphs):
    return {k: make_sentence_ignore_extra_args(v) for k, v in expanded_paragraphs.items()}



