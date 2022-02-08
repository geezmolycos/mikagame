class MyPoorLittleSite():
    """一个描述地点的类"""

    def __init__(self, sites):
        self.name = sites[0]
        sites.pop(0)
        self.reachable_sites = sites

    def show_reachable_sites(self):
        print("你现在在" + self.name +'!')
        print("你可以去的地方有：")
        No = 1
        for site in self.reachable_sites:
            print('\t' + str(No) + '-' + site)
            No += 1
        print("输入对应的序号来前往对应的地方")
