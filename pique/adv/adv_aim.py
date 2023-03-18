'''
Copyrights for portions of this file are held by one or more contributors from the Ace of Spades community and aloha.pk.
LICENSE: GPL-3.0
author: VierEck.

latest version: https://github.com/VierEck/aos-scripts/blob/main/pique/adv/adv_aim.py

prerequisite for gamemodes or other scripts. 
make sure to load prerequisites first in script order. 
this script is intended to be used in the adventure gamemode. 
since i dont see much use for it other than in a "single-player" experience. 

it can stand on its own however. use following commands and config settings 
to extend the experience and fun to ur liking on ur server. 

manipulate the player's aim and field of view. exclusively only works for openspades clients. 


config.toml copypaste template:
[adv_aim]
aimbot = false #enable aimbot. aimbot loop (re-)starting on map start and ending on map end. 
aimbot_individual_config = true #wether to change config values for individual players instead of globally. 
aimbot_key = "scope" #which action triggers aimbot. "scope", "sneak". 
aimbot_friendlyfire = false #wether aimbot should target teammates aswell. 
target_priority = "sight" #how aimbot prioritises targets. "sight"->nearest to sight | "pos"->nearest to ur position
aimbot_type = "soft" #"hard" -> hard_aimbot | "soft" -> soft_aimbot.
soft_aimbot_speed = 1 #how fast soft_aimbot turns towards target.
soft_aimbot_stable_speed = false #wether soft aimbot gets slower towards target or has consistent speed. 
aimbot_loop_ups = 60 #aimbot update per second. best effect with 60.
'''

from piqueserver.commands import command
from piqueserver.config import config
from pyspades import world
from pyspades.common import Vertex3
from pyspades.collision import distance_3d_vector
from pyspades import contained as loaders
import asyncio

adv_aim_config = config.section('adv_aim')

@command('advaim')
def advaim(connection, value, subvalue=None):
	'''
	option for each player to individually configurate their aimbot settings. 
	'''
	c = connection
	p = c.protocol
	value = value.lower()
	if not p.adv_aim_aimbot_individual_config:
		return 'no permission'
	
	elif value == 'aimbot':
		c.adv_aim_ab = not c.adv_aim_ab
		msg = 'aimbot turned %s' % ('on' if c.adv_aim_ab else 'off')
			
	elif value == 'type':
		c.adv_aim_ab_type = subvalue.lower()
		msg = 'aimbot_type set to %s' % c.adv_aim_ab_type
		
	elif value == 'key':
		c.adv_aim_aimbot_key = subvalue.lower()
		msg = 'aimbot_key set to %s' % c.adv_aim_aimbot_key
		
	elif value == 'friendlyfire':
		c.adv_aim_friendlyfire = not c.adv_aim_friendlyfire
		msg = 'friendlyfire turned %s' % ('on' if c.adv_aim_friendlyfire else 'off')
		
	elif value == 'priority':
		c.adv_aim_target_priority = subvalue.lower()
		msg = 'priority set to target nearest to %s' % (c.adv_aim_target_priority)
		
	elif value == 'speed':
		c.adv_aim_soft_speed = int(subvalue)/100
		msg = 'soft aimbot speed set to %.4f' % c.adv_aim_soft_speed
	
	elif value == 'stable':
		c.adv_aim_soft_stable = not c.adv_aim_soft_stable
		msg = 'soft aimbot speed now set to %s' % ('consistent' if c.adv_aim_soft_stable else 'dynamic')
	
	else:
		return 'invalid value'
		
	return msg

@command('advaimstaff', admin_only=True)
def advaim(connection, value, subvalue=None):
	'''
	staff command. configurate the global/protocol adv_aim settings. 
	'''
	c = connection
	p = c.protocol
	value = value.lower()
	if value == 'individual':
		p.adv_aim_aimbot_individual_config = not p.adv_aim_aimbot_individual_config
		for player in p.players.values():
			player.adv_aim_set_individual_config()
		msg = 'WARNING!! individual configs turned %s' % ('on' if p.adv_aim_aimbot_individual_config else 'off')
			   #this command will always reset everyones individual settings. so be careful.
	elif value == 'aimbot':
		p.adv_aim_ab = not p.adv_aim_ab
		p.adv_aim_manage_loop(start_end=True) if p.adv_aim_ab else p.adv_aim_manage_loop(start_end=False)
		msg = 'WARNING!! global aimbot turned %s' % ('on' if p.adv_aim_ab else 'off')
			   #u dont want to accidentally turn this on in a legit match lol. so be careful. 
	elif value == 'type':
		p.adv_aim_ab_type = subvalue.lower()
		msg = 'global aimbot_type set to %s' % p.adv_aim_ab_type
		
	elif value == 'key':
		p.adv_aim_aimbot_key = subvalue.lower()
		msg = 'global aimbot_key set to %s' % p.adv_aim_aimbot_key
		
	elif value == 'friendlyfire':
		p.adv_aim_friendlyfire = not p.adv_aim_friendlyfire
		msg = 'global friendlyfire turned %s' % ('on' if p.adv_aim_friendlyfire else 'off')
		
	elif value == 'priority':
		p.adv_aim_target_priority = subvalue.lower()
		msg = 'global priority set to target nearest to %s' % (p.adv_aim_target_priority)
		
	elif value == 'speed':
		p.adv_aim_soft_speed = int(subvalue)/100
		msg = 'global soft aimbot speed set to %.4f' % p.adv_aim_soft_speed
	
	elif value == 'stable':
		p.adv_aim_soft_stable = not p.adv_aim_soft_stable
		msg = 'global soft aimbot speed now set to %s' % ('consistent' if p.adv_aim_soft_stable else 'dynamic')
	
	else:
		return 'invalid value'
		
	p.irc_say('* %s' % msg)
	return msg

def apply_script(protocol, connection, config):
	class adv_aim_connection(connection):
		
		def adv_aim_set_send_ori(self, x, y, z):
			'''
			set player's server orientation value and send it. 
			'''
			self.world_object.set_orientation(x, y, z)
			send_ori = loaders.OrientationData()
			send_ori.x = x
			send_ori.y = y
			send_ori.z = z
			self.send_contained(send_ori)
		
		def adv_send_ori(self, x, y, z):
			'''
			only send new orientation data. 
			'''
			send_ori = loaders.OrientationData()
			send_ori.x = x
			send_ori.y = y
			send_ori.z = z
			self.send_contained(send_ori)
			
		def adv_aim_set_fov(self, strength=1):
			'''
			manipulate FOV. 
			do it in a loop otherwise client immediately overwrites it. 
			strength = 1 -> neutral/normal.
			strength > 0 -> zoom out
			strength < 0 -> zoom in
			'''
			ori = self.world_object.orientation
			ori /= ori.length()
			ori *= strength
			self.adv_aim_set_send_ori(*ori.get())
			
		def adv_aim_snap_pos(self, x, y, z):
			'''
			instantly lock player's aim on to the given map position coordinates x y z. 
			'''
			target = Vertex3(x, y, z)
			origin = self.world_object.position
			arrow = target
			aim = Vertex3()
			aim.set_vector(arrow)
			aim -= origin
			aim /= aim.length()
			self.adv_aim_set_send_ori(*aim.get())
		
		def adv_aim_towards_pos(self, x, y, z, speed=1, stable=False):
			'''
			gradually move player's aim towards the given map position coordinates x y z. 
			'''
			target = Vertex3(x, y, z)
			aim = self.world_object.orientation
			origin = self.world_object.position
			arrow = target
			aim_goal = Vertex3()
			aim_goal.set_vector(arrow)
			aim_goal -= origin
			if aim == aim_goal:
				return
			diff = aim_goal - aim
			if diff.length() > 0.01:
				if stable:
					diff /= diff.length()
				aim += diff / (100*(1/speed))
				aim /= aim.length()
			else:
				aim.set_vector(aim_goal)
			aim /= aim.length()
			self.adv_aim_set_send_ori(*aim.get())
		
		def adv_aim_hard_aimbot(self, friendlyfire=False, sight=True):
			'''
			instantly lock aim on target. better effect in a short loop
			sight (True) -> get enemy nearest to sight. this looks cooler
			not sight (False) -> get enemy nearest on map. 
			'''
			target = None
			if sight:
				target = self.adv_aim_get_sight_target(friendlyfire)
			else:
				target = self.adv_aim_get_nearest_target(friendlyfire)
			if target and target.world_object:
				origin = self.world_object.position
				arrow = target.world_object.position
				aim = Vertex3()
				aim.set_vector(arrow)
				aim -= origin
				aim /= aim.length()
				self.adv_aim_set_send_ori(*aim.get())
			
		def adv_aim_soft_aimbot(self, speed=1, friendlyfire=False, sight=True, stable=False):
			'''
			lock aim on target but cooler. 
			this will only move player's sight towards target in small "steps" so u have to use this in a loop that lasts long enough. 
			stable (True) -> consistent speed. 
			not stable (False)-> aimbot gets slower as approaching target. looks less robotic, less abrupt and just better. 
			'''
			target = None
			if sight:
				target = self.adv_aim_get_sight_target(friendlyfire)
			else:
				target = self.adv_aim_get_nearest_target(friendlyfire)
			if target and target.world_object:
				aim = self.world_object.orientation
				origin = self.world_object.position
				arrow = target.world_object.position
				aim_goal = Vertex3()
				aim_goal.set_vector(arrow)
				aim_goal -= origin
				if aim == aim_goal:
					return
				diff = aim_goal - aim
				if diff.length() > 0.01:
					if stable:
						diff /= diff.length()
						aim += diff / (2/speed)
					else:
						aim += diff / (100/speed)
					aim /= aim.length()
				else:
					aim.set_vector(aim_goal)
				aim /= aim.length()
				self.adv_aim_set_send_ori(*aim.get())
		
		def adv_aim_get_nearest_target(self, friendlyfire=False):
			'''
			get target nearest to player on map. 
			'''
			target = None
			nougat = 512
			if friendlyfire:
				player_list = self.protocol.players.values() 
			else:
				player_list = self.team.other.get_players()
			for player in player_list:
				if not player.world_object or player.world_object.dead:
					continue
				dist = distance_3d_vector(self.world_object.position, player.world_object.position)
				if dist < nougat:
					nougat = dist
					target = player
			return target
		
		def adv_aim_get_sight_target(self, friendlyfire=False):
			'''
			get targest nearest to the player's sight/crosshair. 
			'''
			target = None
			nougat = 512
			if friendlyfire:
				player_list = self.protocol.players.values() 
			else:
				player_list = self.team.other.get_players()
			for player in player_list:
				if not player.world_object or player.world_object.dead or self is player:
					continue
				aim = self.world_object.orientation
				origin = self.world_object.position
				arrow = player.world_object.position
				dist = Vertex3()
				dist.set_vector(arrow)
				dist -= origin
				dist /= dist.length()
				diff = aim - dist
				diff = diff.length()
				if diff < nougat:
					nougat = diff
					target = player
			return target
		
		def adv_aim_set_individual_config(self):
			p = self.protocol
			self.adv_aim_ab = p.adv_aim_ab
			self.adv_aim_ab_type = p.adv_aim_ab_type
			self.adv_aim_aimbot_key = p.adv_aim_aimbot_key
			self.adv_aim_friendlyfire = p.adv_aim_friendlyfire
			self.adv_aim_target_priority = p.adv_aim_target_priority
			self.adv_aim_soft_speed = p.adv_aim_soft_speed
			self.adv_aim_soft_stable = p.adv_aim_soft_stable
		
		def on_login(self, name):
			if self.protocol.adv_aim_aimbot_individual_config:
				self.adv_aim_set_individual_config()
			return connection.on_login(self, name)
		
	class adv_aim_protocol(protocol):
		adv_aim_ab = adv_aim_config.option('aimbot', False).get()
		adv_aim_aimbot_individual_config = adv_aim_config.option('aimbot_individual_config', False).get()
		adv_aim_ab_type = adv_aim_config.option('aimbot_type', default='soft').get()
		adv_aim_aimbot_key = adv_aim_config.option('aimbot_key', default='scope').get()
		adv_aim_friendlyfire = adv_aim_config.option('aimbot_friendlyfire', False).get()
		adv_aim_target_priority = adv_aim_config.option('target_priority', 'sight').get()
		adv_aim_soft_speed = adv_aim_config.option('soft_aimbot_speed', 1).get()
		adv_aim_soft_stable = adv_aim_config.option('soft_aimbot_stable_speed', False).get()
		adv_aim_aimbot_loop_ups = adv_aim_config.option('aimbot_loop_ups', 60).get()
		
		def on_map_change(self, map_):
			if self.adv_aim_ab:
				self.adv_aim_manage_loop(start_end=True, ups=self.adv_aim_aimbot_loop_ups)
			return protocol.on_map_change(self, map_)
		
		def on_map_leave(self):
			if self.adv_aim_ab:
				self.adv_aim_manage_loop(start_end=False)
			return protocol.on_map_leave(self)
	
		async def adv_aim_loop(self, ups=60):
			'''
			best effect with 60 ups. the smoothest possible experience. 
			since world doesnt update faster than that. the effect also actually gets worse above 60 ups. 
			'''
			while True:
				for player in self.players.values():
					if player.world_object:
						if self.adv_aim_aimbot_individual_config:
							aimbot = player.adv_aim_ab
							ab_type = player.adv_aim_ab_type
							key = player.adv_aim_aimbot_key
							friendlyfire = player.adv_aim_friendlyfire
							priority = player.adv_aim_target_priority
							speed = player.adv_aim_soft_speed
							stable = player.adv_aim_soft_stable
						else:
							aimbot = self.adv_aim_ab
							ab_type = self.adv_aim_ab_type
							key = self.adv_aim_aimbot_key
							friendlyfire = self.adv_aim_friendlyfire
							priority = self.adv_aim_target_priority
							speed = self.adv_aim_soft_speed
							stable = self.adv_aim_soft_stable
						if aimbot and player.tool == 2: #2 = WEAPON_TOOL
							if (key == 'sneak' and player.world_object.sneak) or (key == 'scope' and player.world_object.secondary_fire):
								if ab_type == 'hard':
									player.adv_aim_hard_aimbot(friendlyfire=friendlyfire, sight=priority)
								if ab_type == 'soft':
									player.adv_aim_soft_aimbot(speed=speed, friendlyfire=friendlyfire, sight=priority, stable=stable)
				await asyncio.sleep(1/ups)
		
		def adv_aim_manage_loop(self, start_end=False, ups=60):
			'''
			start_end=True  ->  start loop
			start_end=False ->  end loop
			'''
			if start_end:
				asyncio.ensure_future(self.adv_aim_loop(ups))
			else:
				asyncio.ensure_future(self.adv_aim_loop()).cancel()
	
	return adv_aim_protocol, adv_aim_connection
