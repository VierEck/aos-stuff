'''
Easily define Team names and colors per map in the map.txt extension section.

example:

	extensions = {
		"TeamName1"  : "Pink",
		"TeamColor1" : (255, 0, 255),
		"TeamName2"  : "Yellow",
		"TeamColor2" : (255, 255, 0),
	}

if one of these extension item is missing it will default to its contemporary value from config.toml

Author: VierEck.
Credit: Rakete (for the idea)
'''

from piqueserver.config import config

def apply_script(pro, con, cfg):

	class MapTeam_P(pro):
		
		def on_map_change(p, map_):
			ext = p.map_info.extensions
			
			#Team 1 ("blue")
			if "TeamColor1" in ext:
				p.team_1.color = tuple(ext["TeamColor1"])
			else:
				p.team_1.color = tuple(config.section('team1').option('color', default=(0, 0, 196)).get())
			if "TeamName1" in ext:
				p.team_1.name = str(ext["TeamName1"])
			else:
				p.team_1.name = str(config.section('team1').option('name', default="Blue").get())
			
			#Team 2 ("green")
			if "TeamColor2" in ext:
				p.team_2.color = tuple(ext["TeamColor2"])
			else:
				p.team_2.color = tuple(config.section('team2').option('color', default=(0, 0, 196)).get())
			if "TeamName2" in ext:
				p.team_2.name = str(ext["TeamName2"])
			else:
				p.team_2.name = str(config.section('team2').option('name', default="Green").get())
			
			return pro.on_map_change(p, map_)
	
	return MapTeam_P, con
