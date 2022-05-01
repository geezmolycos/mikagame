import yaml
import mika_regional_dialogue
import mika_modules

class TemplateClassProxy:
    def __init__(self, target):
        self.target = target
        
    def __getitem__(self, key):
        return getattr(self.target, key)
class Templates:
    
    def choice(self, para_full_name, i, desc):
        """
        一个choice需要一个描述，一个list存储其中的选项
        这些选项包括跳转(jump)或调用(call)模式。
        """
        this_name = mika_modules.resolve_module_ref(para_full_name, "." + str(i))
        content = r"\!choiceanim " + desc["desc"] + "\n"
        choices = desc["choices"]
        for choice_i, ch in enumerate(choices):
            if isinstance(ch, str):
                ch_mode, ch_target, *ch_desc = ch.split(",")
                ch_desc = ",".join(ch_desc)
                ch_criteria = None
            elif isinstance(ch, dict):
                ch_mode, ch_target, ch_desc = ch["mode"], ch["target"], ch["desc"]
                ch_criteria = ch.get("criteria")
            iscall_conv = "+" if ch_mode == "c" else "-"
            content += "{"
            if ch_criteria is not None:
                content += fr"\def[.checkcriteria=\\ifelse\[a!{ch_criteria},b-,then=\\\\def\\\[.target=.\\\]\\\\def\\\[.iscall-\\\]\\\\!disabledchosen ,else=\\\\!chosen \]]"
            else:
                content += fr"\def[.checkcriteria=\\!chosen ]"
            content += fr"\ifelse[a!.choice,b;{choice_i},then=\\def\[.target={ch_target}\]\\def\[.iscall{iscall_conv}\]\\!.checkcriteria ,else=\\!unchosen ]"
            content += ch_desc
            content += "}\n"
        content += fr"\ifelse[a!.choice,b?,then=\\def\[.target={this_name}\]\\def\[.iscall-\]]"
        return desc | {
            "content_tokens": content,
            "next_conv": "!.target",
            "choice_amount_conv": f";{len(choices)}",
            "call_conv": "!.iscall",
            "return_conv": "-",
        }

def make_sentence_ignore_extra_args(kwargs):
    kwargs["content_tokens"] = kwargs.get("content_tokens", kwargs.get("contents", kwargs.get("c", [])))
    typ = mika_regional_dialogue.Sentence
    filtered = {
        attribute.name: kwargs[attribute.name]
        for attribute in typ.__attrs_attrs__
        if attribute.name in kwargs
    }
    return typ(**filtered)

class Derivers:
    
    def _default(self, para_full_name, i, desc):
        derived = {}
        if i == 0:
            derived.update(self.paragraph_level_jumper(para_full_name, i, desc))
        
        return derived
    
    def paragraph_level_jumper(self, para_full_name, i, desc):
        para_level_ref_sentence = make_sentence_ignore_extra_args(dict(
            content_tokens=[],
            next_conv="="+mika_modules.resolve_module_ref(para_full_name, "." + str(i)),
            uninterruptable_conv="+",
            pause_after_conv="-",
        ))
        return {para_full_name: para_level_ref_sentence}

    
    def alias(self, para_full_name, i, desc):
        para_level_ref_sentence = make_sentence_ignore_extra_args(dict(
            content_tokens=[],
            next_conv="="+mika_modules.resolve_module_ref(para_full_name, "." + str(i)),
            uninterruptable_conv="+",
            pause_after_conv="-",
        ))
        return {mika_modules.resolve_module_ref(para_full_name, desc["alias"]): para_level_ref_sentence}

def parse_mikad_module(
    module_name,
    content,
    template_transformers=TemplateClassProxy(Templates()),
    derivers=TemplateClassProxy(Derivers()),
    ):
    if template_transformers is None:
        template_transformers = {}
    content = yaml.safe_load(content)
    sentence_pool = {}
    for para_name, para_content in content.items():
        para_full_name = mika_modules.resolve_module_ref(module_name, para_name)
        default = para_content.get("default", {})
        sentences = para_content["st"]
        for i, s in enumerate(sentences):
            if isinstance(s, str):
                s = {
                    "content_tokens": s
                }
            # 应用template
            template_to_apply_names = s.get("_template") or default.get("_template", [])
            if not isinstance(template_to_apply_names, list):
                template_to_apply_names = [template_to_apply_names]
            s = default | dict(
                next_conv="=" + ".." + str(i + 1),
                return_conv="+" if i == len(sentences) - 1 else "-"
            ) | s
            for t in template_to_apply_names:
                s = template_transformers[t](para_full_name, i, s)
            # 应用deriver
            deriver_to_apply_names = s.get("_deriver") or default.get("_deriver", [])
            if not isinstance(deriver_to_apply_names, list):
                deriver_to_apply_names = [deriver_to_apply_names]
            for d in deriver_to_apply_names:
                sentence_pool.update(derivers[d](para_full_name, i, s))
            # 构建句子
            s = make_sentence_ignore_extra_args(default | s)
            sentence_pool[mika_modules.resolve_module_ref(para_full_name, "." + str(i))] = s
    return sentence_pool

if __name__ == "__main__":
    print(parse_mikad_module("a.c", """
char:
    default:
        region_conv: "=char"
    st:
        - 今天是个好日子
        - 心想的事儿都能成
mmm:
    st:
        -
            _template: choice
            desc: 描述
            choices:
                - j,...char.0,此
"""))
