
# 为了解决pyodide不能访问本地文件，直接把所有模块的列表缓存到一起

import mika_modules
import json

root = "demo_root"

modules = mika_modules.walk_modules(root)

for k in modules:
    modules[k] = modules[k].replace("\\", "/")

with open("walk_modules.json", "w") as f:
    json.dump(modules, f)
