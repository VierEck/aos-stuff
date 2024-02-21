'''
supplementory script for SmashItems.py (and by extension SuperSmash.py)

Items that spawn companions who aid u. only works if max_players is set below 32.
its recommended to have at max 24 players, leaving at least 8 more slots for bots.


the companions r based on the zombie bots from the survive gamemode by 1AmYF:
	https://github.com/1AmYF/aos-server-mods/blob/master/scripts/piqueserver/survive.py#L155
	
Special Thanks to Rakete for providing a test server during development!

Authors:
	VierEck.
	1AmYF
'''


from asyncio import sleep, ensure_future
from enet import Address
from time import monotonic as time
from twisted.internet.reactor import callLater
from random import randint, choice
from piqueserver.config import config
from pyspades.contained import SetTool, WeaponInput, ChatMessage, InputData
from pyspades.constants import (RIFLE_WEAPON, SMG_WEAPON, SHOTGUN_WEAPON, SPADE_TOOL, MELEE_KILL, 
                                WEAPON_KILL, HEADSHOT_KILL, MELEE_DISTANCE, CHAT_ALL, TOOL_INTERVAL)


isInit = True
POPULATION_COMPATIBLE = False


smash_cfg = config.section("SuperSmashOff")
FPS = smash_cfg.option("companion_fps", 10).get()


GREETINGS = [ "aloha", "hola", "hi", "servus", "salut", "welcome", "bienvenido", "willkomen", "bonjour", ]
ZOMBIE_NOISE = [ "ughhhgh", "rargghh", "blarrarrhh", "must eat brains", "braiinsns...", "grruaarrglrr", ]


def broadcast_bot_chat(b, msg):
	p = b.protocol
	chat_pkt = ChatMessage()
	chat_pkt.chat_type = CHAT_ALL
	chat_pkt.player_id = b.player_id
	chat_pkt.value     = msg
	p.broadcast_contained(chat_pkt)

def broadcast_bot_shoot(b, is_shoot):
	p = b.protocol
	weap_pkt = WeaponInput()
	weap_pkt.player_id = b.player_id
	weap_pkt.primary   = is_shoot
	weap_pkt.secondary = False
	p.broadcast_contained(weap_pkt)

def broadcast_bot_inp(b):
	p = b.protocol
	inp_pkt = InputData()
	inp_pkt.player_id = b.player_id
	inp_pkt.up        = b.world_object.up
	inp_pkt.down      = b.world_object.down
	inp_pkt.left      = b.world_object.left
	inp_pkt.right     = b.world_object.right
	inp_pkt.jump      = b.world_object.jump
	inp_pkt.crouch    = b.world_object.crouch
	inp_pkt.sneak     = b.world_object.sneak
	inp_pkt.sprint    = b.world_object.sprint
	p.broadcast_contained(inp_pkt, save=True)


class LocalPeer:
	address = Address(str.encode("localhost"), 0)
	roundTripTime = 0.0

	def send(self, *arg, **kw):
		pass

	def reset(self):
		pass


#
def apply_script(pro, con, cfg):

	class Shared_C(con):
		
		def smash_on_hit(c, hit_amount, pl, hit_type, nade):
			try:
				pl.smash_bot_hurt = True
				pl.smash_bot_on_hurt(hit_amount, c, hit_type, nade) 
			except AttributeError:
				pass
			return con.smash_on_hit(c, hit_amount, pl, hit_type, nade)
	
	
	#
	class Bot(Shared_C):
		smash_bot_friend           = None
		smash_bot_last_shot_time   = 0
		smash_bot_reload_time      = 0
		smash_bot_last_charge_time = 0
		smash_bot_target           = None
		smash_bot_killed           = False
		smash_bot_hurt             = False
		
		def __init__(b, c, pos, weap, name):
			p = c.protocol
			
			b.rapid_hack_detect = False
			b.speedhack_detect = False
			Shared_C.__init__(b, p, LocalPeer())
			b.player_id = p.player_ids.pop()
			b.input     = set()
			
			b.smash_bot_friend = c
			b.smash_bot_killed = False
			b.smash_bot_target = None
			b.name = name
			b.team = c.team
			b.set_weapon(weap, True)
			p.players[(b.player_id)] = b
			b.on_login(b.name)
			x, y, z = pos
			b.spawn((x + 0.5, y + 0.5, z - 2))
			if b not in p.smash_bot_list:
				p.smash_bot_list.append(b)
		
		def smash_remove_bot(b):
			if b.disconnected:
				return
			p = b.protocol
			if b in p.smash_bot_list:
				p.smash_bot_list.remove(b)
			b.disconnected = True
			b.on_disconnect()
		
		def on_spawn_location(b, pos):
			return None
		
		def on_kill(b, by, kill_type, nade):
			b.smash_bot_killed = True
			#removing bot here would cause a crash so we just mark it for removing
			return False
		
		def smash_on_fall_always(b):
			if b.smash_bot_hurt:
				b.smash_bot_hurt = False
			return Shared_C.smash_on_fall_always(b)
		
		def smash_bot_shoots(b, t):
			if not b.world_object.primary_fire:
				b.world_object.primary_fire = True
				broadcast_bot_shoot(b, True)
		
		def smash_bot_on_hurt(b, hit_amount, killer, hit_type, nade):
			if b.smash_bot_friend != killer:
				b.smash_bot_target = killer
		
		def smash_bot_find_target(b):
			b.smash_bot_target = None
			if len(p.players) <= len(p.smash_bot_list):
				return
			p = b.protocol
			dist = 1024
			for pl in p.players.values():
				if pl.world_object and not pl.world_object.dead and pl != b and pl != b.smash_bot_friend:
					if pl in p.smash_bot_list:
						if b.smash_bot_friend == pl.smash_bot_friend:
							continue
					cur_dist = (b.world_object.position - pl.world_object.position).length()
					if cur_dist < dist:
						dist = cur_dist
						b.smash_bot_target = pl
		
		def smash_update_bot(b):
			if b.smash_bot_killed or b.disconnected:
				b.smash_bot_killed = False
				b.smash_remove_bot()
				return
			t = b.smash_bot_target
			if t is None or not t.world_object or t.world_object.dead or t.disconnected:
				b.smash_bot_find_target()
			else:				
				aim  = t.world_object.position - b.world_object.position
				aim /= aim.length()
				b.world_object.set_orientation(*aim.get())

	class Zombie(Bot):
		smash_bot_last_talk_time = 0
	
		def __init__(b, c, pos):
			p    = c.protocol
			name = "Zombie"
			i    = 0
			for pl in p.players.values():
				if pl.name != None and pl.name == name:
					i   += 1
					name = "Zombie" + str(i)
			Bot.__init__(b, c, pos, RIFLE_WEAPON, name)
			
			b.tool = SPADE_TOOL
			tool_pkt = SetTool()
			tool_pkt.player_id = b.player_id
			tool_pkt.value     = SPADE_TOOL
			p.broadcast_contained(tool_pkt, save=True)
			
			b.world_object.set_walk(True, False, False, False) #forward
			b.world_object.set_animation(False, False, False, True) #sprint
			broadcast_bot_inp(b)
		
		def smash_on_hit(b, hit_amount, pl, hit_type, nade):
			p = b.protocol
			if b.smash_bot_last_talk_time + 5 < time():
				b.smash_bot_last_talk_time = time()
				broadcast_bot_chat(b, choice(ZOMBIE_NOISE))
			return Bot.smash_on_hit(b, hit_amount, pl, hit_type, nade)
		
		def smash_bot_shoots(b, t):
			p = b.protocol
			b.on_hit(p.smash_get_DMG_SPADE(), t, MELEE_KILL, None)
			Bot.smash_bot_shoots(b, t)
			
		def smash_update_bot(b):
			Bot.smash_update_bot(b) #first find target
			if b.disconnected:
				return
			t = b.smash_bot_target
			if t is not None:
				b_pos = b.world_object.position
				t_pos = t.world_object.position
				dist  = (t_pos - b_pos).length()
				if dist < MELEE_DISTANCE:
					if b.smash_bot_last_shot_time + TOOL_INTERVAL[SPADE_TOOL] < time():
						b.smash_bot_last_shot_time = time()
						b.smash_bot_shoots(t)
				else:
					if b.world_object.primary_fire:
						b.world_object.primary_fire = False
						broadcast_bot_shoot(b, False)
					if not b.smash_bot_hurt and b_pos.z > t_pos.z + 1:
						if b.smash_bot_last_charge_time + 0.5 < time():
							b.smash_bot_last_charge_time = time()
							aim    = b.world_object.orientation
							aim.z -= 1
							b.smash_apply_charge(aim / aim.length() * 0.5)

	class Deuce(Bot):
		smash_bot_last_talk_time = 0
		
		def __init__(b, c, pos):
			p = c.protocol
			name = "Deuce"
			i = 0
			for pl in p.players.values():
				if pl.name != None and pl.name == name:
					i   += 1
					name = "Deuce" + str(i)
			Bot.__init__(b, c, pos, choice([RIFLE_WEAPON, SMG_WEAPON, SHOTGUN_WEAPON]), name)
		
		def smash_bot_on_hurt(b, hit_amount, killer, hit_type, nade):
			if killer == b.smash_bot_friend:
				if b.smash_bot_last_talk_time + 2 < time():
					b.smash_bot_last_talk_time = time()
					broadcast_bot_chat(b, choice([";-;", "D:", "T^T"]))
			Bot.smash_bot_on_hurt(b, hit_amount, killer, hit_type, nade)
		
		def smash_bot_shoots(b, t):
			weap = b.weapon_object
			if b.smash_bot_reload_time + weap.reload_time > time():
				if b.world_object.primary_fire:
					b.world_object.primary_fire = False
					broadcast_bot_shoot(b, False)
				return
			if randint(1, 10) <= 2:
				weap.current_ammo -= 1
				if weap.ammo / 2 > weap.current_ammo:
					weap.current_ammo = weap.ammo
					b.smash_bot_reload_time = time()
					if b.world_object.primary_fire:
						b.world_object.primary_fire = False
						broadcast_bot_shoot(b, False)
					return
				hit_type = WEAPON_KILL
				hit_amount = None
				if randint(1, 4) < 2:
					hit_type = HEADSHOT_KILL
				else:
					if weap.id == RIFLE_WEAPON:
						hit_amount = choice([49, 33])
					elif weap.id == SMG_WEAPON:
						hit_amount = choice([29, 18])
					else:
						hit_amount = choice([27, 16])
				b.on_hit(b.smash_get_dmg(weap.id, hit_type, hit_amount), t, hit_type, None)
			Bot.smash_bot_shoots(b, t)
		
		def smash_update_bot(b):
			Bot.smash_update_bot(b)
			if b.disconnected:
				return
			t = b.smash_bot_target
			if t is not None:
				b_pos = b.world_object.position
				t_pos = t.world_object.position
				dist  = (t_pos - b_pos).length()
				if dist < 64:
					#FIX THIS: can_see not reliable
					if b.world_object.can_see(t_pos.x, t_pos.y, t_pos.z):
						b.world_object.set_walk(False, False, False, False)
						b.world_object.set_animation(False, True, False, False)
						broadcast_bot_inp(b)
						if b.smash_bot_last_shot_time + b.weapon_object.delay < time():
							b.smash_bot_last_shot_time = time()
							b.smash_bot_shoots(t)
					elif b.smash_bot_last_charge_time + 2 < time() or b.world_object.position.z > 61.01:
						if not b.smash_bot_hurt:
							b.world_object.set_walk(False, False, False, False)
							b.world_object.set_animation(False, False, False, False)
							broadcast_bot_inp(b)
							if b.world_object.primary_fire:
								b.world_object.primary_fire = False
								broadcast_bot_shoot(b, False)
							b.smash_bot_last_charge_time = time()
							aim = b.world_object.orientation
							a_x, a_y = aim.x, aim.y
							if randint(0, 1):
								aim.x = a_y
								aim.y = -a_x
							else:
								aim.x = -a_y
								aim.y = a_x
							aim.z -= 1
							b.smash_apply_charge(aim / aim.length())
				else:
					b.world_object.set_walk(True, False, False, False)
					b.world_object.set_animation(False, False, False, True)
					broadcast_bot_inp(b)
					if b.world_object.primary_fire:
						b.world_object.primary_fire = False
						broadcast_bot_shoot(b, False)
					if not b.smash_bot_hurt and b_pos.z > t_pos.z + 1:
						if b.smash_bot_last_charge_time + 0.75 < time():
							b.smash_bot_last_charge_time = time()
							aim    = b.world_object.orientation
							aim.z -= 1
							b.smash_apply_charge(aim / aim.length())
			else:
				if b.world_object.primary_fire:
					b.world_object.primary_fire = False
					broadcast_bot_shoot(b, False)

	class Topo(Bot):
		def __init__(b, c, pos):
			p = c.protocol
			name = "Topo"
			i = 0
			for pl in p.players.values():
				if pl.name != None and pl.name == name:
					i   += 1
					name = "Topo" + str(i)
			Bot.__init__(b, c, pos, RIFLE_WEAPON, name)
		
		def smash_bot_shoots(b, t):
			weap = b.weapon_object
			if b.smash_bot_reload_time + weap.reload_time > time():
				if b.world_object.primary_fire:
					b.world_object.primary_fire = False
					broadcast_bot_shoot(b, False)
				return
			weap.current_ammo -= 1
			if weap.current_ammo <= 0:
				weap.current_ammo = weap.ammo
				b.smash_bot_reload_time = time()
				if b.world_object.primary_fire:
					b.world_object.primary_fire = False
					broadcast_bot_shoot(b, False)
				return
			b.on_hit(b.smash_get_dmg(weap.id, HEADSHOT_KILL, None), t, HEADSHOT_KILL, None)
			Bot.smash_bot_shoots(b, t)
		
		def smash_on_hit(b, hit_amount, pl, hit_type, nade):
			p = b.protocol
			dmg = b.smash_get_dmg(b.weapon_object.id, hit_type, hit_amount)
			aim  = pl.world_object.position - b.world_object.position
			aim /= aim.length()
			k    = p.smash_get_DMG_POWER()
			k   *= 1.0 + (pl.hp + dmg) / (255.0 + p.smash_get_MAX_DAMAGE())
			pl.smash_apply_knockback(aim*k)
			pl.smash_apply_dmg(dmg)
			return False
		
		def smash_update_bot(b): #what would topo do?
			Bot.smash_update_bot(b)
			if b.disconnected:
				return
			t = b.smash_bot_target
			if t is not None:
				b_pos = b.world_object.position
				t_pos = t.world_object.position
				dist  = (t_pos - b_pos).length()
				aim   = b.world_object.orientation
				if dist < 128:
					if dist < 121: #stay in fogline
						b.world_object.set_walk(False, True, False, False)
						b.world_object.set_animation(False, False, False, False)
						broadcast_bot_inp(b)
						if b.smash_bot_last_charge_time + 1 < time() or b.world_object.position.z > 61.01:
							if not b.smash_bot_hurt:
								b.smash_bot_last_charge_time = time()
								aim.x *= -1
								aim.y *= -1
								aim.z -= 1
								b.smash_apply_charge(aim / aim.length())
					else:
						b.world_object.set_walk(False, False, False, False)
						b.world_object.set_animation(False, True, False, False)
						broadcast_bot_inp(b)
					if b.world_object.can_see(t_pos.x, t_pos.y, t_pos.z):
						if b.smash_bot_last_shot_time + b.weapon_object.delay < time():
							b.smash_bot_last_shot_time = time()
							if not b.world_object.primary_fire:
								b.world_object.primary_fire = True
								broadcast_bot_shoot(b, True)
							b.smash_bot_shoots(t)
					else:
						b.world_object.set_walk(False, False, False, False)
						b.world_object.set_animation(False, True, False, False)
						broadcast_bot_inp(b)
						if b.world_object.primary_fire:
							b.world_object.primary_fire = False
							broadcast_bot_shoot(b, False)
						if b.smash_bot_last_charge_time + 1 < time() or b.world_object.position.z > 61.01:
							if not b.smash_bot_hurt and b.smash_bot_last_charge_time + 1 < time():
								b.smash_bot_last_charge_time = time()
								a_x, a_y = aim.x, aim.y
								if randint(0, 1):
									aim.x = a_y
									aim.y = -a_x
								else:
									aim.x = -a_y
									aim.y = a_x
								aim.z -= 1
								b.smash_apply_charge(aim / aim.length())
				else:
					if b.world_object.primary_fire:
						b.world_object.primary_fire = False
						broadcast_bot_shoot(b, False)
					b.world_object.set_walk(True, False, False, False)
					b.world_object.set_animation(False, False, False, False)
					broadcast_bot_inp(b)
					if b.smash_bot_last_charge_time + 1 < time() or b.world_object.position.z > 61.01:
						if not b.smash_bot_hurt:
							b.smash_bot_last_charge_time = time()
							aim.z -= 1
							b.smash_apply_charge(aim / aim.length())


	#weak items
	def CompanionZombie(c, pos):
		p = c.protocol
		if len(p.players) < 32:
			b = Zombie(c, pos)
			def remove():
				if b is not None:
					b.smash_remove_bot()
			callLater(60, remove)
	
	
	#decent items
	def CompanionDeuce(c, pos):
		p = c.protocol
		if len(p.players) < 32:
			b = Deuce(c, pos)
			def remove():
				if b is not None:
					b.smash_remove_bot()
			callLater(60, remove)
	
	
	#legendary items
	def CompanionTopo(c, pos):
		p = c.protocol
		if len(p.players) < 32:
			b = Topo(c, pos)
			def remove():
				if b is not None:
					b.smash_remove_bot()
			callLater(30, remove)
	
	
	#
	class SmashItemCompanions_C(Shared_C):
		
		def on_login(c, name):
			p = c.protocol
			if len(p.smash_bot_list) > 0:
				b_rand = choice(p.smash_bot_list)
				msg    = choice(GREETINGS)
				if c != b_rand:
					msg += " " + name
				broadcast_bot_chat(b_rand, msg)
			return Shared_C.on_login(c, name)
		
		def on_disconnect(c):
			p = c.protocol
			if len(p.players) <= len(p.smash_bot_list):
				for b in p.smash_bot_list:
					try:
						b.smash_remove_bot()
					except AttributeError:
						pass
			return Shared_C.on_disconnect(c)
	
	
	class SmashItemCompanions_P(pro):
	
		smash_bot_list = []
		def smash_companion_update(p):
			for b in p.smash_bot_list:
				b.smash_update_bot()

		smash_companion_loop_task = None
		async def smash_companion_loop(p): 
			fps = 1/FPS
			while True:
				await sleep(fps)
				p.smash_companion_update()
		
		def on_map_change(p, map_):
			global POPULATION_COMPATIBLE
			if p.max_players < 32:
				POPULATION_COMPATIBLE = True
			
			if POPULATION_COMPATIBLE:
				global isInit
				if isInit:
					isInit = False
					
					p.smash_add_item_to_dict(0, CompanionZombie)
					
					p.smash_add_item_to_dict(1, CompanionDeuce)
					
					p.smash_add_item_to_dict(2, CompanionTopo)
			
			if p.smash_companion_loop_task is None:
				p.smash_companion_loop_task = ensure_future(p.smash_companion_loop())
			return pro.on_map_change(p, map_)
		
		def on_game_end(p):
			if p.smash_companion_loop_task is not None:
				p.smash_companion_loop_task.cancel()
				p.smash_companion_loop_task = None
			for b in p.smash_bot_list:
				b.smash_remove_bot()
			p.smash_bot_list = []
			return pro.on_game_end(p)
		
		def on_map_leave(p):
			if p.smash_companion_loop_task is not None:
				p.smash_companion_loop_task.cancel()
				p.smash_companion_loop_task = None
			for b in p.smash_bot_list:
				b.smash_remove_bot()
			p.smash_bot_list = []
			return pro.on_map_leave(p)
		
		
		def smash_get_class_bot(p):
			return Bot
		
		def smash_get_class_zombie(p):
			return Zombie
		
		def smash_get_class_deuce(p):
			return Deuce
			
		def smash_get_class_topo(p):
			return Topo
	
	
	return SmashItemCompanions_P, SmashItemCompanions_C
