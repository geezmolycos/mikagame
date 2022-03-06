import yaml
import mika_regional_dialogue
import mika_modules


def parse_mikad_module(module_name, content, template_transformers=None):
    if template_transformers is None:
        template_transformers = {}
    content = yaml.safe_load(content)
    sentence_pool = {}
    for para_name, para_content in content.items():
        para_full_name = mika_modules.resolve_module_ref(module_name, "." + para_name)
        default = para_content["default"]
        sentences = para_content["st"]
        for i, s in enumerate(sentences):
            if isinstance(s, str):
                s = mika_regional_dialogue.Sentence(**default | dict(
                    content_tokens=s,
                    next_conv="=" + mika_modules.resolve_module_ref(para_full_name, "." + str(i + 1)),
                    return_conv="+" if i == len(sentences) - 1 else "-", # 最后一个句子要返回
                ))
            elif isinstance(s, dict):
                template = s.get("_template", [])
                if not isinstance(template, list):
                    template = [template]
                for t in template:
                    s = template_transformers[t](s)
                s = mika_regional_dialogue.Sentence(**default | s)
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
"""))
