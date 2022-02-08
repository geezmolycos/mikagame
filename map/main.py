from game_function import get_site
from my_poor_little_site import MyPoorLittleSite

filename_maps = 'map\地图数据.txt'

with open(filename_maps, encoding='utf-8') as file_object:
    mapdates_lines = file_object.readlines()

sites = []
for line in mapdates_lines:
    sites.append(MyPoorLittleSite(get_site(line)))


sitename_2_siteid = {}
for i in range(len(sites)):
    sitename_2_siteid[sites[i].name] = i

current_site = sites[0]

while True:
    current_site.show_reachable_sites()
    next_site_id=input()
    next_site_id=int(next_site_id)
    next_site_name=current_site.reachable_sites[next_site_id-1]
    next_site_id=sitename_2_siteid[next_site_name]
    current_site=sites[next_site_id]    
