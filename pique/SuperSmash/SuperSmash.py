'''
Based on the SmashOff gamemode by Dr.Morphman. Knock ur opponents into waters to kill them. 
This new version has smoother knockback animation, Items and Ultimate Powers for each weapon class!

This is the SuperSmashOff base script. for the full package download following scripts:
	NadeLauncher.py (https://github.com/VierEck/aos-stuff/blob/main/pique/NadeLauncher.py)
	SmashPowers.py (https://github.com/VierEck/aos-stuff/blob/main/pique/SuperSmash/SmashPowers.py)
	SmashItems.py
to set the actual gamemode logic install ONE of the following gamemode scripts:
	SuperSmashTimedKills.py
	SuperSmashTimedRatio.py
	SuperSmashTimedEllimination.py

original SmashOff Gamemode script by Dr.Morphman:
	https://aloha.pk/t/smashoff/13723/3
smoother knockback animation is achieved thanks to Jipok's charge.py script. 
	https://github.com/piqueserver/piqueserver-extras/blob/master/scripts/charge.py
damage percentage is achieved thanks to Jipok's max_hp.py script.
	https://github.com/piqueserver/piqueserver-extras/blob/master/scripts/max_hp.py

Authors: 
	VierEck.
	Dr.Morphman
	Jipok
'''


import asyncio
from time import monotonic as time
from typing import Any, Optional, Sequence, Tuple, Union
from pyspades.constants import CTF_MODE, WEAPON_KILL
from piqueserver.config import config
from pyspades.contained import SetHP
from pyspades import world


smash_cfg = config.section("SuperSmashOff")

FPS = smash_cfg.option("FPS", 120).get() #clientside position update rate. for smooth overall gameplay u need higher ups.

CHARGE_LIMIT = smash_cfg.option("charge_amount"   , 3).get()
CHARGE_POWER = smash_cfg.option("airjump_power"   , 1).get()
DMG_POWER    = smash_cfg.option("knockback_power" , 1).get()

DMG_SPADE = smash_cfg.option("dmg_spade", 20).get()
DMG_NADE  = smash_cfg.option("dmg_nade" , 30).get() #ranged splash dmg

DMG_VALS = {
	0 : { #rifle
		0: smash_cfg.option("dmg_rifle_head", 15).get(), #head
		1: smash_cfg.option("dmg_rifle_body", 10).get(), #body
		2: smash_cfg.option("dmg_rifle_limb",  5).get(), #limb
	},
	1 : { #smg
		0: smash_cfg.option("dmg_smg_head", 3).get(),
		1: smash_cfg.option("dmg_smg_body", 2).get(),
		2: smash_cfg.option("dmg_smg_limb", 1).get(),
	},
	2 : { #pump. dmg for each pellet
		0: smash_cfg.option("dmg_pump_head", 5).get(),
		1: smash_cfg.option("dmg_pump_body", 3).get(),
		2: smash_cfg.option("dmg_pump_limb", 2).get(),
	},
}

MAX_DAMAGE = DMG_SPADE if DMG_SPADE > DMG_NADE else DMG_NADE
for i in range(3):
	for j in range(3):
		if MAX_DAMAGE < DMG_VALS[i][j]:
			MAX_DAMAGE = DMG_VALS[i][j]

body_amount_indicators = [49, 29, 27]
limb_amount_indicators = [33, 18, 16]


#
def apply_script(pro, con, cfg):

	class SuperSmash_C(con):
		smash_charges        = 0
		smash_is_charging    = False
		smash_can_charge     = False
		smash_anim_state     = 0
		smash_last_sneak     = False
		smash_last_pump_time = 0
		smash_killer         = None
		smash_killer_type    = 0
		
		def on_spawn(c, pos):
			c.set_hp(1)
			return con.on_spawn(c, pos)
		
		def on_spawn_location(c, pos):
			x, y, z = c.protocol.get_random_location(True)
			z -= 2
			return (x, y, z) 
		
		def set_hp(c, value: Union[int, float], hit_by: Optional['ServerConnection'] = None, kill_type: int = WEAPON_KILL, 
		hit_indicator: Optional[Tuple[float, float, float]] = None, grenade: Optional[world.Grenade] = None) -> None:
			value = int(value)
			c.hp = max(1, min(255, value))
			set_hp = SetHP()
			set_hp.hp = c.hp
			set_hp.not_fall = 1 #no fall dmg anyways
			if hit_indicator is None:
				if hit_by is not None and hit_by is not c:
					hit_indicator = hit_by.world_object.position.get()
				else:
					hit_indicator = (0, 0, 0)
			x, y, z = hit_indicator
			set_hp.source_x = x
			set_hp.source_y = y
			set_hp.source_z = z
			c.send_contained(set_hp)
			#hijack set_hp. this is due to default set_hp setting an upper bound at 100 hp
		
		def smash_get_dmg(c, weap, hit_type, hit_amount):
			if hit_type == 0: #body or limb 
				if hit_amount in body_amount_indicators:
					return DMG_VALS[weap][1]
				if hit_amount in limb_amount_indicators:
					return DMG_VALS[weap][2]
			if hit_type == 1: #head
				return DMG_VALS[weap][0]
			if hit_type == 2: #spade
				return DMG_SPADE
			return DMG_NADE
		
		def smash_apply_dmg(c, dmg): #interface.
			c.set_hp(c.hp + dmg)
		
		def smash_apply_knockback(c, vel): #interface
			c.smash_is_charging = True
			c.world_object.velocity.set(*(vel).get())
		
		def smash_on_hit(c, hit_amount, pl, hit_type, nade): #interface
			pass
		
		def on_hit(c, hit_amount, pl, hit_type, nade):
			dmg = 0
			ret = c.smash_on_hit(hit_amount, pl, hit_type, nade)
			if ret is not None:
				if ret is False:
					return False
				else:
					dmg = ret
			else:
				dmg = c.smash_get_dmg(c.weapon_object.id, hit_type, hit_amount)
			
			pl.smash_killer      = c
			pl.smash_killer_id   = c.player_id
			pl.smash_killer_type = hit_type
			
			aim = None
			k   = DMG_POWER
			k  *= 1.0 + (pl.hp + dmg) / (255.0 + MAX_DAMAGE)
			if not nade:
				aim = c.world_object.orientation
				if c.weapon_object.id == 2 and time() < c.smash_last_pump_time + 0.1:
					k += pl.world_object.velocity.length() #each pellet in a shot add to one big knockback
			else:
				aim = pl.world_object.position - nade.position
				distFactor = (28.0 - aim.length()) / 28.0 #max nade dmg distance roughly 28 blocks
				k   *= distFactor
				dmg *= distFactor
				aim /= aim.length()
			
			pl.smash_apply_dmg(dmg)
			pl.smash_apply_knockback(aim*k)
			
			if c.weapon_object.id == 2:			
				c.smash_last_pump_time = time()
			
			return False #hijack on_hit. we dont want to do actual player damage, but other scripts may break.
		
		def on_walk_update(c, up: bool, down: bool, left: bool, right: bool) -> None:
			if not (up or down or right or left):
				c.smash_anim_state = 0 #stand
			return con.on_walk_update(c, up, down, left, right)
		
		def on_animation_update(c, jump, crouch, sneak, sprint):
			if   sprint:
				c.smash_anim_state = 2
			elif crouch:
				c.smash_anim_state = 3
			elif sneak:
				c.smash_anim_state = 4
			elif jump:
				c.smash_anim_state = 0
				c.smash_can_charge = True
			else: #walk
				c.smash_anim_state = 1 
			if sneak and not c.smash_last_sneak and c.smash_charges > 0 and c.smash_can_charge:
				aim                 = c.world_object.orientation
				k                   = CHARGE_POWER
				c.smash_is_charging = True
				c.smash_charges    -= 1
				c.world_object.velocity.set(*(aim*k).get())
				c.send_chat_notice("AirJumps: %.0f" % c.smash_charges)
			c.smash_last_sneak = sneak
			return con.on_animation_update(c, jump, crouch, sneak, sprint)
	
	
	class SuperSmash_P(pro):
	
		def smash_update(p):
			for pl in p.players.values():
					if pl.world_object is not None:
						if not pl.world_object.dead:
							if pl.smash_is_charging:
								pl.set_location()
							if pl.world_object.position.z > 61:
								pl.kill(pl.smash_killer, pl.smash_killer_type, None)
							elif not pl.world_object.airborne: #on ground
								pl.smash_can_charge = False
								pl.smash_charges    = CHARGE_LIMIT
								if   pl.smash_anim_state == 1: #walk
									if pl.world_object.velocity.length() <= 0.25:
										pl.smash_is_charging = False
										pl.smash_killer   = None
								elif pl.smash_anim_state == 2: #sprint
									if pl.world_object.velocity.length() <= 0.325:
										pl.smash_is_charging = False
										pl.smash_killer   = None
								elif pl.smash_anim_state == 3: #crouch
									if pl.world_object.velocity.length() <= 0.075:
										pl.smash_is_charging = False
										pl.smash_killer   = None
								elif pl.smash_anim_state == 4: #sneak
									if pl.world_object.velocity.length() <= 0.125:
										pl.smash_is_charging = False
										pl.smash_killer   = None
								else:                 #stand (and jump)
									if pl.world_object.velocity.length() <= 0.001:
										pl.smash_is_charging = False
										pl.smash_killer   = None
							else:
								pl.smash_can_charge = True
		
		smash_update_loop_task = None
		async def smash_update_loop(p):
			while True:
				p.smash_update()
				await asyncio.sleep(1/FPS)
		#suggestion: tie position update to world update if config fps == 0 ?
		
		def on_map_change(p, map_):
			p.user_blocks   = set() #prevent ppl from trenching
			p.fall_damage   = False
			if FPS != 0 and p.smash_update_loop_task is None:
				p.smash_update_loop_task = asyncio.ensure_future(p.smash_update_loop())
			return pro.on_map_change(p, map_)
		
		def on_map_leave(p):
			if p.smash_update_loop_task is not None:
				p.smash_update_loop_task.cancel()
				p.smash_update_loop_task = None
			return pro.on_map_leave(p)
		
		def smash_get_MAX_DAMAGE(p):
			return MAX_DAMAGE
	
	
	return SuperSmash_P, SuperSmash_C
