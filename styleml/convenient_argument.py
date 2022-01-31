
import re

def parse_convenient_obj_repr(s):
    "使用一个标点符号和字符串表示一个简单对象，比如是数字/字符串/真假"
    m = re.match(r"([=#$\+\-?])(.*)", s)
    if not m:
        return None
    type, value = m[1], m[2]
    obj = None
    if type == "=":
        obj = value
    elif type == "#":
        obj = int(value)
    elif type == "$":
        obj = float(value)
    elif type == "+":
        obj = True
    elif type == "-":
        obj = False
    elif type == "?":
        obj = None
    return obj

def parse_convenient_pair(s):
    "使用一个key和convenient obj repr相连，代表一个键-值对"
    m = re.match(r"([0-9A-Za-z_]*)(.*)", s)
    key, repr = m[1], m[2]
    obj = parse_convenient_obj_repr(repr)
    return key, obj

def parse_convenient_dict(s, delimiter=",", lower=parse_convenient_pair):
    "解析convenient pair组成的dict"
    styles = {}
    for piece in s.split(delimiter):
        key, obj = lower(piece)
        styles[key] = obj
    return styles

def parse_convenient_list(s, delimiter="|", lower=lambda x: x):
    "使用'|'分隔开的参数中的若干个部分"
    arguments = []
    for piece in s.split(delimiter):
        obj = lower(piece)
        arguments.append(obj)
    return arguments