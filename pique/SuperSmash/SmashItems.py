'''
Items in SuperSmashOff.
supplementory script for SuperSmashOff Gamemode

this is the base items script. to actually add items u need to install following supplementory scripts:
	SmashItemBuffs.py
	SmashItemAbilities.py
	SmashItemCompanions.py

Inspired by the Christmas Present Item Blocks from Sauerkraut Survival Server (by 1AmYF)

Authors: 
	VierEck.
'''


from asyncio import sleep, ensure_future
from random import randint, choice
from piqueserver.config import config
from pyspades.constants import BUILD_BLOCK, DESTROY_BLOCK
from pyspades.common import make_color
from pyspades.contained import SetColor, BlockAction


smash_cfg = config.section("SuperSmashOff")

MAX_ITEMS       = smash_cfg.option("max_items"      , 32).get() #max amount of items at a given time
ITEM_SPAWN_RATE = smash_cfg.option("item_spawn_rate", 15).get() #in secs
ITEMS_WEAKER    = smash_cfg.option("items_weaker"   , []).get() #empty list -> all items in dict
ITEMS_DECENT    = smash_cfg.option("items_decent"   , []).get()
ITEMS_LEGENDARY = smash_cfg.option("items_legendary", []).get()

ITEM_COLOR_WEAKER    = (0, 255, 0)
ITEM_COLOR_DECENT    = (255, 0, 0)
ITEM_COLOR_LEGENDARY = (255, 0, 255)


class BlockItem():
	def __init__(self, p, col, pos, method):
		self.pos    = pos
		self.method = staticmethod(method)
		x, y, z = pos
		
		color_pkt = SetColor()
		color_pkt.player_id = 35
		r, g, b = col
		color_pkt.value = make_color(r, g, b)
		p.broadcast_contained(color_pkt, save=True)
		
		block_action = BlockAction()
		block_action.x = x
		block_action.y = y
		block_action.z = z
		block_action.value = BUILD_BLOCK
		block_action.player_id = 35
		p.broadcast_contained(block_action, save=True)
		
		p.map.set_point(x, y, z, col)
		p.user_blocks.add((x, y, z))

#
def apply_script(pro, con, cfg):

	class SmashItems_C(con):
	
		def on_block_removed(c, x, y, z):
			c.smash_break_item_block((x, y, z))
			return con.on_block_removed(c, x, y, z)
		
		def smash_break_item_block(c, pos):
			p = c.protocol
			for block in p.smash_item_block_list:
				if block.pos == pos:
					block.method(c, pos)
					p.smash_item_block_list.remove(block)
	
	class SmashItems_P(pro):
	
		SMASH_ITEM_DICT = { #other scripts extend this dict with more items
			0: {}, #weaker items
			1: {}, #decent items
			2: {}, #legendary items
		}
		
		def smash_add_item_to_dict(p, item_type: int, method: staticmethod, name = None): #use this to add items to dict
			if item_type < 0 or item_type > 2:
				return
			if name is None:
				name = method.__name__
			for key in p.SMASH_ITEM_DICT:
				if key == name:
					return
			p.SMASH_ITEM_DICT[item_type][name] = method

		smash_item_block_list = []
		def smash_spawn_item_random(p):
			if p.smash_item_block_list is not None:
				item_list = []
				item_type = 0
				method    = None
				col       = None
				rInt = randint(1, 16)
				if rInt == 1: #legendary (1/16 chance)
					item_list = ITEMS_LEGENDARY
					item_type = 2
					col = ITEM_COLOR_LEGENDARY
				elif rInt < 7: #decent (5 / 16 chance)
					item_list = ITEMS_DECENT
					item_type = 1
					col = ITEM_COLOR_DECENT
				else: #weaker (10 / 16 chance)
					item_list = ITEMS_WEAKER
					col = ITEM_COLOR_WEAKER
				
				if len(p.SMASH_ITEM_DICT[item_type]) > 0:
					if len(item_list) <= 0:
						method = p.SMASH_ITEM_DICT[item_type][choice(list(p.SMASH_ITEM_DICT[item_type].keys()))]
					else:
						itemName = choice(item_list)
						if itemName in list(p.SMASH_ITEM_DICT[item_type].keys()):
							method = p.SMASH_ITEM_DICT[item_type][choice(item_list)]
				
				if method is not None:
					x, y, z = p.get_random_location(True)
					z -= 1
					pos = x, y, z
					if p.map.is_valid_position(x, y, z):
						if len(p.smash_item_block_list) >= MAX_ITEMS and len(p.smash_item_block_list) > 0: #fifo
							first_block = p.smash_item_block_list[0]
							x2, y2, z2 = first_block.pos
							
							block_action = BlockAction()
							block_action.x = x2
							block_action.y = y2
							block_action.z = z2
							block_action.value = DESTROY_BLOCK
							block_action.player_id = 35
							p.broadcast_contained(block_action, save=True)
							
							p.smash_item_block_list.remove(first_block)
							p.user_blocks.discard((x2, y2, z2))
							p.map.remove_point(x2, y2, z2)
						p.smash_item_block_list.append(BlockItem(p, col, pos, method))
					
		
		smash_item_spawn_loop_task = None
		async def smash_item_spawn_loop(p):
			while True:
				await sleep(ITEM_SPAWN_RATE)
				p.smash_spawn_item_random()
	
		def on_map_change(p, map_):
			ext = p.map_info.extensions
			ITEM_COLOR_WEAKER    = (0, 255, 0)
			ITEM_COLOR_DECENT    = (255, 0, 0)
			ITEM_COLOR_LEGENDARY = (255, 0, 255)
			if "item_color_weaker" in ext:
				ITEM_COLOR_WEAKER = ext["item_color_weaker"]
			if "item_color_decent" in ext:
				ITEM_COLOR_DECENT = ext["item_color_decent"]
			if "item_color_legendary" in ext:
				ITEM_COLOR_LEGENDARY = ext["item_color_legendary"]
			
			#adjust item amount according to map size
			if "max_items" in ext:
				MAX_ITEMS = ext["max_items"]
			if "item_spawn_rate" in ext:
				ITEM_SPAWN_RATE = ext["item_spawn_rate"]
				
			if p.smash_item_spawn_loop_task is None:
				p.smash_item_spawn_loop_task = ensure_future(p.smash_item_spawn_loop())
			return pro.on_map_change(p, map_)
		
		def on_map_leave(p):
			if p.smash_item_spawn_loop_task is not None:
				p.smash_item_spawn_loop_task.cancel()
				p.smash_item_spawn_loop_task = None
			return pro.on_map_leave(p)
	
	
	return SmashItems_P, SmashItems_C
