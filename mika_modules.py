
import os


# 模块系统描述以下：
# ""(空字符串)表示根模块
# 最前面加"."时，是相对路径
# 以".."分隔，代表兄弟模块（即向上一级），如a.b中引用"..c"，即"a.b..c"，结果是"a.c"，点越多，上溯的层数越多
def walk_modules(root, root_package=""):
    modules = {}
    for dir, subdirs, files in os.walk(root):
        rel_dir = os.path.relpath(dir, root)
        if rel_dir == ".": # 系统表示同级目录的"."
            rel_dir = ""
        package = resolve_module_ref(root_package, "." + ".".join(rel_dir.split(os.sep))) # 某文件所在的包
        for file_name in files:
            module_name = resolve_module_ref(package, "."+os.path.splitext(file_name)[0])
            modules[module_name] = os.path.join(rel_dir, file_name)
    return modules

def resolve_module_ref(current_module_name, ref_module_name):
    ref_stack = ref_module_name.split(".")
    current_stack = current_module_name.split(".")
    if len(ref_stack[-1]) == 0: # 处理以"."结尾时多一级的问题
        ref_stack.pop()
    if len(current_stack[-1]) == 0:
        current_stack.pop()
    if ref_stack[0] == "":
        # relative
        work_stack = current_stack + ref_stack[1:]
    else:
        # absolute
        work_stack = ref_stack
    abs_stack = []
    for it in work_stack:
        if len(it) == 0:
            try:
                abs_stack.pop()
            except IndexError as e:
                raise ValueError("relative module reference beyond root module") from e
        elif it[0] == "<":
            # backtrack
            search_for = it[1:]
            if len(search_for) == 0: # to root
                abs_stack = []
            while abs_stack[-1] != search_for:
                abs_stack.pop()
        else:
            abs_stack.append(it)
    return ".".join(abs_stack)

if __name__ == "__main__":
    a = "a.b.c.d"
    r = ".<b.e"
    print(resolve_module_ref(a,r))
    #print(walk_modules("./demo_root"))
