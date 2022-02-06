
import re

nothing_sentinent = object()

def parse_convenient_obj_repr(s, macros=None):
    "使用一个标点符号和字符串表示一个简单对象，比如是数字/字符串/真假"
    m = re.match(r"([=;:\+\-?!^])(.*)", s)
    if not m:
        return nothing_sentinent
    type, value = m[1], m[2]
    obj = None
    if type == "=":
        obj = value
    elif type == ";":
        obj = int(value)
    elif type == ":":
        obj = float(value)
    elif type == "+":
        obj = True
    elif type == "-":
        obj = False
    elif type == "?":
        obj = None
    elif type == "!":
        obj = macros.get(value, nothing_sentinent) if macros is not None else nothing_sentinent
    elif type == "^":
        obj = macros is not None and value in macros
    return obj

def parse_convenient_pair(s, macros=None):
    "使用一个key和convenient obj repr相连，代表一个键-值对"
    m = re.match(r"([0-9A-Za-z_]*)(.*)", s)
    key, repr = m[1], m[2]
    obj = parse_convenient_obj_repr(repr, macros=macros)
    return key, obj

def parse_convenient_dict(s, macros=None, delimiter=","):
    "解析convenient pair组成的dict"
    styles = {}
    for piece in s.split(delimiter):
        key, obj = parse_convenient_pair(piece, macros=macros)
        if obj is nothing_sentinent: # 如果obj没有内容，则跳过该obj
            continue
        styles[key] = obj
    return styles

def parse_convenient_list(s, delimiter="|", lower=lambda x: x):
    "使用'|'分隔开的参数中的若干个部分"
    arguments = []
    for piece in s.split(delimiter):
        obj = lower(piece)
        arguments.append(obj)
    return arguments

#TODO: 写宏调用类型符
# 每一个token类型，设置一个「需要此时宏」的标记，如果需要宏，在宏解析的时候，就给它复制一份
