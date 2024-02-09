'''
supplementory script for SmashItems.py (and by extension SuperSmash.py)

Items to give players special abilities
(i gotta admit that the difference to SmashItemBuffs can be kinda blurry)

Authors:
	VierEck.
'''


import asyncio
from math import cos, sin
from twisted.internet.reactor import callLater
from pyspades.packet import register_packet_handler
from pyspades.contained import BlockAction, OrientationData, GrenadePacket
from pyspades.constants import BUILD_BLOCK, WEAPON_TOOL, DESTROY_BLOCK
from pyspades.common import Vertex3


isInit = True


def build_block(c, x, y, z):
	p = c.protocol
	
	block_action = BlockAction()
	block_action.x = x
	block_action.y = y
	block_action.z = z
	block_action.value = BUILD_BLOCK
	block_action.player_id = c.player_id
	p.broadcast_contained(block_action, save=True)
	
	p.map.set_point(x, y, z, c.color)
	p.user_blocks.add((x, y, z))

def build_wall(c, x, y, z):
	p = c.protocol
	
	aim = c.world_object.orientation
	if abs(aim.y) > abs(aim.x):
		x2 = x - 1
		for i in range(3):
			for j in range(3):
				if not p.map.get_solid(x2 + i, y, z - j):
					build_block(c, x2 + i, y, z - j)
	else:
		y2 = y - 1
		for i in range(3):
			for j in range(3):
				if not p.map.get_solid(x, y2 + i, z - j):
					build_block(c, x, y2 + i, z - j)

def set_ori(c, x, y, z):
	c.world_object.set_orientation(x, y, z)
	send_ori = OrientationData()
	send_ori.x = x
	send_ori.y = y
	send_ori.z = z
	c.send_contained(send_ori)

def get_aimbot_target(c):
	target = None
	nougat = 1024
	for pl in c.protocol.players.values():
		if not pl.world_object or pl.world_object.dead or c is pl:
			continue
		'''
		pos_check = pl.world_object.position
		if not c.can_see(pos_check.x, pos_check.y, pos_check.z): #why does this not work?
			continue
		'''
		aim = c.world_object.orientation
		origin = c.world_object.position
		arrow = pl.world_object.position
		dist = Vertex3()
		dist.set_vector(arrow)
		dist -= origin
		dist /= dist.length()
		diff = aim - dist
		diff = diff.length()
		if diff < nougat:
			nougat = diff
			target = pl
	return target

def do_aimbot(c, target):
	aim = c.world_object.orientation
	origin = c.world_object.position
	arrow = target.world_object.position
	aim_goal = Vertex3()
	aim_goal.set_vector(arrow)
	aim_goal -= origin
	if aim == aim_goal:
		return
	diff = aim_goal - aim
	if diff.length() > 0.8:
		diff /= diff.length()
		aim += diff * 0.75
	else:
		aim.set_vector(aim_goal)
	aim /= aim.length()
	set_ori(c, *aim.get())

def do_confusion(c):
	aim = c.world_object.orientation
	aim.z = 0
	aim.x = cos(0.1) * aim.x - sin(0.1) * aim.y
	aim.y = sin(0.1) * aim.x + cos(0.1) * aim.y
	aim *= 1.5 + sin(c.smash_item_confused_len)
	set_ori(c, *aim.get())


#weak items
def Wall(c, pos = None):
	c.smash_item_wall = True
	c.send_chat("You gained the ability to build walls")


#decent items
def Poison(c, pos = None): #not that strong but annoying if it appears too often
	c.smash_item_poisons = True
	c.send_chat("You received Poison. Enemies get poisoned if u damage them")
	#i also wanted to add a regeneration item, but didnt cuz u get damage sounds 
	#and that would make it annoying, despite being the opposite of poison  :(

def AnEyeForAnEye(c, pos = None):
	c.smash_item_eyeforeye = True
	c.send_chat("You received the AnEyeForAnEye ability. The damage you take is applied to ur enemy aswell")

def Earthquake(c, pos = None):
	p = c.protocol
	for pl in p.players.values():
		if pl.world_object and not pl.world_object.dead and pl is not c:
			pl.smash_apply_dmg(20)
			pl.smash_apply_knockback(Vertex3(0, 0, -2))
	p.broadcast_chat("Earthquake!")


#legendary items
def Aimbot_end(c):
	p = c.protocol
	if c in p.smash_aimbot_list:
		p.smash_aimbot_list.remove(c)
	c.send_chat("You dont have aimbot anymore!")
def Aimbot(c, pos = None):
	p = c.protocol
	p.smash_aimbot_list.append(c)
	c.send_chat("You received aimbot")
	callLater(30, Aimbot_end)
	

def PortalGun_end(c):
	c.smash_item_portalgun = False
	c.send_chat("You lost the portal gun!")
def PortalGun(c, pos = None):
	c.smash_item_portalgun = True
	c.send_chat("You received the portal gun. Teleport to a block by shooting at it")
	def end():
		c.smash_item_portalgun = False
	callLater(30, end)
	#this could "break" some maps. players may get to places they shouldnt, but lets just keep it in for now

def Psychic_end(c):
	c.smash_item_psychic = False
	c.send_chat("You r not a psychic anymore!")
def Psychic(c, pos = None):
	c.smash_item_psychic = True
	c.send_chat("You have become a Psychic. Confuse your opponents by shooting at them")
	callLater(30, Psychic_end(c))

def Stomp_end(c):
	c.smash_item_stomp = False
	c.send_chat("You lost the stomp ability!")
def Stomp(c, pos = None):
	c.smash_item_stomp = True
	c.send_chat("You received the stomp ability. When you land u make the ground shake")
	callLater(30, Stomp_end(c))

#
def apply_script(pro, con, cfg):

	class SmashItemAbilities_C(con):
		smash_item_wall         = False
		smash_item_poisons      = False
		smash_item_poisoned     = False
		smash_item_portalgun    = False
		smash_item_eyeforeye    = False
		smash_item_psychic      = False
		smash_item_confused_len = 0
		smash_item_stomp        = False
	
		def on_spawn(c, pos):
			p = c.protocol
			
			if c.smash_item_stomp:
				Stomp_end(c)
			
			if c in p.smash_confused_list:
				p.smash_confused_list.remove(c)
				c.smash_item_confused_len = 0
			
			if c.smash_item_psychic:
				Psychic_end(c)
			
			if c.smash_item_eyeforeye:
				c.smash_item_eyeforeye = False
				c.send_chat("You lost the AnEyeForAnEye ability!")
			
			if c.smash_item_portalgun:
				PortalGun_end(c)
			
			if c.smash_item_poisons:
				c.smash_item_poisons = False
				c.send_chat("You lost the Poison Ability!")
			if c.smash_item_poisoned:
				c.smash_item_poisoned = False
		
			if c in p.smash_aimbot_list:
				Aimbot_end(c)
			
			if c.smash_item_wall:
				c.smash_item_wall = False
				c.send_chat("You lost the ability to build Walls!")
			
			return con.on_spawn(c, pos)
			
		def smash_apply_dmg(c, dmg):
			p = c.protocol
		
			if c.smash_killer is not None:
				if c.smash_killer.smash_item_poisons and c != c.smash_killer:
					c.smash_item_poisoned = True
					c.send_chat("You have been poisoned by " + c.smash_killer.name)
				
				if c.smash_item_eyeforeye and c != c.smash_killer:
					c.smash_killer.set_hp(c.smash_killer.hp + dmg)
					
				if c.smash_killer.smash_item_psychic and c.smash_killer is not c and c not in p.smash_confused_list:
					c.smash_item_confused_len = 1
					p.smash_confused_list.append(c)
					c.send_chat("You have been confused by " + c.smash_killer.name)
			
			con.smash_apply_dmg(c, dmg)
		
		def on_block_build(c, x, y, z):
			p = c.protocol
		
			if c.smash_item_wall:
				build_wall(c, x, y, z)
				
			return con.on_block_build(c, x, y, z)
		
		@register_packet_handler(BlockAction)
		def on_block_action_recieved(c, pkt):
			
			if c.smash_item_portalgun and c.tool == WEAPON_TOOL and pkt.value == DESTROY_BLOCK:
				c.set_location_safe((pkt.x, pkt.y, pkt.z), True)
			
			con.on_block_action_recieved(c, pkt)
		
		def on_position_update(c):
		
			if c.smash_item_poisoned:
				c.set_hp(c.hp + 1)
				
			return con.on_position_update(c)
		
		def smash_on_fall_always(c):
			p = c.protocol
			
			if c.smash_item_stomp:
				for pl in p.players.values():
					if pl.world_object and not pl.world_object.dead and pl is not c:
						aim = pl.world_object.position - c.world_object.position
						if aim.length() < 28: #nade distance
							aim.z -= aim.length() / 2
							aim /= aim.length()
							pl.smash_apply_dmg(10)
							pl.smash_apply_knockback(aim)
				pos = c.world_object.position
				pos.z += 1
				nade_pkt = GrenadePacket()
				nade_pkt.player_id = c.player_id
				nade_pkt.value     = 0
				nade_pkt.position  = pos.get()
				nade_pkt.velocity  = Vertex3().get()
				p.broadcast_contained(nade_pkt)
			
			con.smash_on_fall_always(c)
	
	
	class SmashItemAbilities_P(pro):
	
		smash_aimbot_list = []
		smash_confused_list = []
		smash_aimbot_loop_task = None
		async def smash_aimbot_loop(p):
			fps = 1/60
			while True:
				await asyncio.sleep(fps)
				if len(p.smash_aimbot_list) > 0:
					for pl in p.smash_aimbot_list:
						if pl.tool == WEAPON_TOOL and pl.world_object.secondary_fire:
							target = get_aimbot_target(pl)
							if target is not None:
								do_aimbot(pl, target)
				
				if len(p.smash_confused_list) > 0:
					for pl in p.smash_confused_list:
						if pl.world_object and not pl.world_object.dead and pl.smash_item_confused_len < 10:
							pl.smash_item_confused_len += fps
							do_confusion(pl)
						else:
							p.smash_confused_list.remove(pl)
						
		
		def on_map_change(p, map_):
			global isInit
			if isInit:
				isInit = False
				
				p.smash_add_item_to_dict(0, Wall)
				
				p.smash_add_item_to_dict(1, Poison)
				p.smash_add_item_to_dict(1, Earthquake)
				p.smash_add_item_to_dict(1, AnEyeForAnEye)
				
				p.smash_add_item_to_dict(2, Aimbot)
				p.smash_add_item_to_dict(2, PortalGun)
				p.smash_add_item_to_dict(2, Psychic)
				p.smash_add_item_to_dict(2, Stomp)
			
			if p.smash_aimbot_loop_task is None:
				p.smash_aimbot_loop_task = asyncio.ensure_future(p.smash_aimbot_loop())
			return pro.on_map_change(p, map_)
		
		def on_map_leave(p):
			if p.smash_aimbot_loop_task is not None:
				p.smash_aimbot_loop_task.cancel()
				p.smash_aimbot_loop_task = None
			return pro.on_map_leave(p)
	
	return SmashItemAbilities_P, SmashItemAbilities_C
