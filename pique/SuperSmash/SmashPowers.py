'''
Ultimate Powers for each weapon class in SuperSmashOff.
supplementory script for the SuperSmashOff Gamemode

NadeLauncher.py needs to be installed for shotgun ultimate power.
SmashPowers.py needs to access NadeLauncher.py. Adjust script hirarchy accordingly

Rifle ult: lethal Weapons
SMG   ult: dmg boost
Pump  ult: nadelauncher	

Authors: 
	VierEck.
'''


import asyncio
from random import randint
from time import monotonic as time
from piqueserver.config import config
from pyspades.contained import Restock, FogColor
from pyspades.constants import WEAPON_TOOL, GRENADE_KILL
from pyspades.common import make_color

smash_cfg = config.section('SuperSmashOff')

HOLD_INTEL_TIME = smash_cfg.option("hold_intel_time", 15).get() #in sec
POWER_TIME      = smash_cfg.option("power_time"     , 30).get()
INTEL_TIME      = smash_cfg.option("intel_appear_time"     , 90).get()
INTEL_APPEAR_TIME_LOWER = smash_cfg.option("intel_appear_time_min", 60).get() #min, max random time
INTEL_APPEAR_TIME_UPPER = smash_cfg.option("intel_appear_time_max", 60 * 2).get()

def refill_ammo(c):
	c.grenades = 3
	c.blocks = 50
	c.weapon_object.reset()
	restock = Restock()
	c.send_contained(restock)
	c.set_hp(c.hp)

def set_intel(flag, pos):
	if flag is not None:
		flag.set(*pos)
		flag.update()

def broadcast_warning(p, msg): #broadcast chat funcs from source didnt work for me. idk why
	for pl in p.players.values():
		pl.send_chat_warning(msg)

def broadcast_error(p, msg):
	for pl in p.players.values():
		pl.send_chat_error(msg)


#
def apply_script(pro, con, cfg):

	class SmashPowers_C(con):
		smash_has_ult         = False
		smash_pickup_time     = 0
		smash_drop_intel_hits = 0
		
		def on_flag_take(c):
			c.smash_drop_intel_hits = 3
			c.smash_pickup_time = time()
			c.protocol.smash_flag_player = c
			set_intel(c.team.flag, (0, 0, 0))
			return con.on_flag_take(c);
		
		def drop_flag(c):
			p = c.protocol
			if c.smash_has_ult:
				c.smash_ult_end()
			elif p.smash_flag_player is not None and c == p.smash_flag_player:
				p.smash_flag_player = None
				pos = c.world_object.position
				x, y, z = p.map.get_safe_coords(pos.x, pos.y, pos.z)
				z = p.map.get_z(x, y, z)
				set_intel(c.team.flag, (x, y, z))
			con.drop_flag(c)
			
		def smash_cap_intel(c): #not actually caps intel, unleashes ult
			p = c.protocol
			c.smash_has_ult = True
			c.set_hp(1)
			refill_ammo(c)
			fog_pkt = FogColor()
			fog_pkt.color = make_color(128, 0, 0)
			p.broadcast_contained(fog_pkt)
			if c.weapon_object.id == 2: #pump
				c.has_NadeLauncher = True
				c.NadeLauncher_velocity = 2.0
			broadcast_error(p, c.name + " has unleashed his Ultimate Power")
		
		def smash_ult_end(c):
			p = c.protocol
			c.smash_has_ult = False
			p.smash_flag_player = None
			fog_pkt = FogColor()
			r, g, b = p.fog_color
			fog_pkt.color = make_color(r, g, b)
			p.broadcast_contained(fog_pkt)
			if c.weapon_object.id == 2:
				c.has_NadeLauncher = False
			c.drop_flag()
			set_intel(c.team.other.flag, (0, 0, 0))
			broadcast_warning(p, c.name + " ran out of Ultimate Power")
		
		def smash_on_hit(c, hit_amount, pl, hit_type, nade):
			p = c.protocol
			if not c.smash_has_ult:
				return None
			if p.smash_flag_player is None or p.smash_flag_player != c:
				if pl == p.smash_flag_player:
					pl.smash_drop_intel_hits -= 1
					if pl.smash_drop_intel_hits <= 0:
						pl.drop_flag()
				return None
			
			if c.weapon_object.id == 0: #rifle
				#lethal bullets in the hands of a good player is overpowered
				if   hit_type == 0: #body or limb
					if hit_amount == 49:
						pl.set_hp(pl.hp + 127)
					elif hit_amount == 33:
						pl.set_hp(pl.hp + 84)
				elif hit_type == 1: #head
					pl.kill(c, hit_type, None)
					return False
				elif hit_type == 2: #spade
					pl.set_hp(pl.hp + 208)
				else:               #nade
					pl.set_hp(pl.hp + int(hit_amount * 2.55))
				if pl.hp >= 255:
					pl.kill(c, hit_type, None)
				return False
				
			elif c.weapon_object.id == 1: #smg
				#couldnt think of anything better, but tbh smgay deserves a boring ult
				return c.smash_get_dmg(c.weapon_object.id, hit_type, hit_amount) * 3
				
			else: #pump
				#give some love to the shotgun. it needs it.
				if nade is None and hit_type == GRENADE_KILL:
					return False
				
			return con.smash_on_hit(c, hit_amount, pl, hit_type, nade)
		
		def smash_apply_dmg(c, dmg):
			if c.smash_killer is not None and c.smash_killer.has_NadeLauncher:
				if c != c.smash_killer:
					c.set_hp(c.hp + dmg * 2) #boost dmg for pump ult
				return #dont do dmg on urself during pump ult
			con.smash_apply_dmg(c, dmg)
		
		def on_kill(c, killer, kill_type, nade):
			p = c.protocol
			if c.smash_has_ult:
				c.smash_ult_end()
			return con.on_kill(c, killer, kill_type, nade)
	
	
	class SmashPowers_P(pro):
	
		smash_flag_spawns = None
		def smash_spawn_intel(p, info=True):
			ext = p.map_info.extensions
			pos = None
			if "Smash_Intel_Spawns" in ext:
				p.smash_flag_spawns = tuple(ext["Smash_Intel_Spawns"])
				pos = p.smash_flag_spawns[randint(0, len(p.smash_flag_spawns) - 1)]
			else:
				pos = p.get_random_location(True)
			for flag in (p.team_1.flag, p.team_2.flag):
				set_intel(flag, pos)
			if info:
				broadcast_warning(p, "The intel has appeared!")
		
		def smash_despawn_intel(p):
			for flag in (p.team_1.flag, p.team_2.flag):
				set_intel(flag, (0, 0, 0))
			broadcast_warning(p, "The intel disappeared...")
		
		smash_flag_player = None
		smash_powers_loop_task = None
		async def smash_powers_loop(p):
			while True:
				#wait some time. 
				await asyncio.sleep(randint(INTEL_APPEAR_TIME_LOWER, INTEL_APPEAR_TIME_UPPER))
				
				#now spawn the intel. start the frenzy
				p.smash_spawn_intel()
				intel_appear_finish_time = time() + INTEL_TIME
				intel_is_capped = False
				while intel_appear_finish_time > time():
					if p.smash_flag_player is not None and p.smash_flag_player.smash_pickup_time + HOLD_INTEL_TIME < time():
						#player has hold onto intel long enough, now unleash his ult
						intel_is_capped = True
						break
					for flag in (p.team_1.flag, p.team_2.flag):
						if flag is not None:
							if flag.z > 61.5:
								p.smash_spawn_intel(info=False)
					await asyncio.sleep(1)
				
				if intel_is_capped or p.smash_flag_player is not None:
					p.smash_flag_player.smash_cap_intel()
					await asyncio.sleep(POWER_TIME)
					if p.smash_flag_player is not None:
						p.smash_flag_player.smash_ult_end()
				else:
					p.smash_despawn_intel() #noone managed to get the intel, so remove it...
		
		def on_flag_spawn(c, x, y, z, flag, entity_id):
			return (0, 0, 0)
		
		def on_base_spawn(self, x, y, z, base, entity_id):
			return (0, 0, 0)
		
		def on_map_change(p, map_):
			if p.smash_powers_loop_task is None:
				p.smash_powers_loop_task = asyncio.ensure_future(p.smash_powers_loop())
			return pro.on_map_change(p, map_)
		
		def on_map_leave(p):
			if p.smash_powers_loop_task is not None:
				p.smash_powers_loop_task.cancel()
				p.smash_powers_loop_task = None
			return pro.on_map_leave(p)
	
	
	return SmashPowers_P, SmashPowers_C
