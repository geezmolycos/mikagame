"""功能函数"""


def get_site(ori_str):
    """从一行字符串获得一个记录一个地点数据的列表"""
    site = ''
    sites = []
    for char in ori_str.rstrip():
        if char != ' ':
            site += char
        else:
            sites.append(site)
            site = ''
    sites.append(site)
    return sites
