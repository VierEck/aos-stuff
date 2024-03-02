'''
Based on the SmashOff gamemode by Dr.Morphman. Knock ur opponents into waters to kill them. 
This new version has air jumps, smoother knockback animation, Items and Ultimate Powers for each weapon class!

60 ups is highly recommended! Playing on voxlap is not recommended.

This is the SuperSmashOff base script. for the full package download following scripts and setup this hirarchy:
	SuperSmash.py
	NadeLauncher.py        (https://github.com/VierEck/aos-stuff/blob/main/pique/NadeLauncher.py)
	SmashPowers.py         (https://github.com/VierEck/aos-stuff/blob/main/pique/SuperSmash/SmashPowers.py)
	SmashItems.py          (https://github.com/VierEck/aos-stuff/blob/main/pique/SuperSmash/SmashItems.py)
	SmashItemBuffs.py      (https://github.com/VierEck/aos-stuff/blob/main/pique/SuperSmash/SmashItemBuffs.py)
	SmashItemAbilities.py  (https://github.com/VierEck/aos-stuff/blob/main/pique/SuperSmash/SmashItemAbilities.py)
	SmashItemCompanions.py (https://github.com/VierEck/aos-stuff/blob/main/pique/SuperSmash/SmashItemCompanions.py)

to set the actual gamemode logic install ONE of the following gamemode scripts:
	FreeForAll DeathMatch:
		SuperSmashFFADM.py (https://github.com/VierEck/aos-stuff/blob/main/pique/SuperSmash/SuperSmashFFADM.py)
	Team DeathMatch:
		SuperSmashTDM.py   (wip)


original SmashOff Gamemode script by Dr.Morphman:
	https://aloha.pk/t/smashoff/13723/3
smoother knockback animation is achieved thanks to Jipok's charge.py script. 
	https://github.com/piqueserver/piqueserver-extras/blob/master/scripts/charge.py
damage percentage is achieved thanks to Jipok's max_hp.py script.
	https://github.com/piqueserver/piqueserver-extras/blob/master/scripts/max_hp.py

Special Thanks to Rakete for providing a test server during development!

Authors: 
	VierEck.
	Dr.Morphman
	Jipok
'''


from math import floor
from itertools import product
from asyncio import sleep, ensure_future
from time import monotonic as time
from typing import Any, Optional, Sequence, Tuple, Union
from pyspades.contained import BlockAction
from pyspades.constants import (WEAPON_KILL, HEADSHOT_KILL, MELEE_KILL, GRENADE_KILL, 
                                RIFLE_WEAPON, SMG_WEAPON, SHOTGUN_WEAPON, DESTROY_BLOCK)
from piqueserver.config import config
from pyspades.contained import SetHP
from pyspades import world


smash_cfg = config.section("SuperSmashOff")

FPS = smash_cfg.option("FPS", 120).get() #position update rate. for smooth overall gameplay u need higher ups.

CHARGE_LIMIT = smash_cfg.option("airjump_amount"  , 2).get()
CHARGE_POWER = smash_cfg.option("airjump_power"   , 1).get()
DMG_POWER    = smash_cfg.option("knockback_power" , 1.5).get()

DMG_SPADE = smash_cfg.option("dmg_spade", 20).get()
DMG_NADE  = smash_cfg.option("dmg_nade" , 30).get() #ranged splash dmg

DMG_VALS = {
	RIFLE_WEAPON : {   #rifle
		0: smash_cfg.option("dmg_rifle_head", 15).get(),
		1: smash_cfg.option("dmg_rifle_body", 10).get(),
		2: smash_cfg.option("dmg_rifle_limb",  5).get(),
	},
	SMG_WEAPON : {     #smg
		0: smash_cfg.option("dmg_smg_head", 3).get(),
		1: smash_cfg.option("dmg_smg_body", 2).get(),
		2: smash_cfg.option("dmg_smg_limb", 1).get(),
	},
	SHOTGUN_WEAPON : { #pump. dmg for each pellet
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
		smash_charges         = 0
		smash_is_charging     = False
		smash_can_charge      = False
		smash_anim_state      = 0
		smash_last_sneak      = False
		smash_last_pump_time  = 0
		smash_killer          = None
		smash_killer_type     = 0
		smash_last_fall_time  = 0 #pique physics is wonky. airborne time needs to be
		smash_start_fall_time = 0 #measured for smash_on_fall_always() to work correctly
		
		def smash_apply_charge(c, vel):
			c.smash_is_charging = True
			c.smash_charges    -= 1
			c.world_object.velocity.set(*(vel).get())
			c.send_chat_notice("AirJumps: %.0f" % c.smash_charges)
		
		def smash_apply_dmg(c, dmg):
			c.set_hp(c.hp + dmg)
		
		def smash_apply_knockback(c, vel):
			c.smash_is_charging = True
			c.world_object.velocity.set(*(vel).get())
		
		def smash_get_dmg(c, weap, hit_type, hit_amount):
			if hit_type == WEAPON_KILL: #body or limb 
				if hit_amount in body_amount_indicators:
					return DMG_VALS[weap][1]
				if hit_amount in limb_amount_indicators:
					return DMG_VALS[weap][2]
			if hit_type == HEADSHOT_KILL: #head
				return DMG_VALS[weap][0]
			if hit_type == MELEE_KILL: #spade
				return DMG_SPADE
			if hit_type == GRENADE_KILL:
				return DMG_NADE
			return 0
		
		def smash_on_fall(c, dmg): #hijack interface of on_fall. on_fall is only called when there is fall dmg
			pass
		
		def smash_on_fall_always(c): #interface for everytime player falls, even if there is no fall dmg
			pass
		
		def smash_on_hit(c, hit_amount, pl, hit_type, nade):
			pass
		
		def smash_nade_exploded(c, nade):
			pass
		
		
		def on_spawn(c, pos):
			c.set_hp(1)
			return con.on_spawn(c, pos)
		
		def on_fall(c, dmg):
			c.smash_on_fall(dmg)
			return False
		
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
			pl.smash_killer_type = hit_type
			
			aim = None
			k   = DMG_POWER
			k  *= 1.0 + (pl.hp + dmg) / (255.0 + MAX_DAMAGE)
			if not nade:
				aim = c.world_object.orientation
				if c.weapon_object.id == SHOTGUN_WEAPON and time() < c.smash_last_pump_time + 0.1:
					#each pellet in a shot add to one big knockback
					k += 1 / pl.world_object.velocity.length()
			else:
				aim = pl.world_object.position - nade.position
				distFactor = (28.0 - aim.length()) / 28.0 #max nade dmg distance roughly 28 blocks
				k   *= distFactor
				dmg *= distFactor
				aim /= aim.length()
			
			pl.smash_apply_dmg(dmg)
			pl.smash_apply_knockback(aim*k)
			
			if c.weapon_object.id == SHOTGUN_WEAPON:			
				c.smash_last_pump_time = time()
			
			return False #hijack on_hit. we dont want to do actual player damage, but other scripts may break.
		
		def grenade_exploded(c, nade): #copy paste from source, slightly modified
			p = c.protocol
			if c.name is None or c.team.spectator or (nade.team is not None and nade.team is not c.team):
				return
			iface = c.smash_nade_exploded(nade)
			if iface is False:
				return
			pos = nade.position
			if pos.x < 0 or pos.x > 512 or pos.y < 0 or pos.y > 512 or pos.z < 0 or pos.z > 63:
				return
			x = int(floor(pos.x))
			y = int(floor(pos.y))
			z = int(floor(pos.z))
			for pl in p.players.values():
				if not pl.hp or pl.world_object is None:
					continue
				dmg = nade.get_damage(pl.world_object.position)
				if dmg == 0:
					continue
				#c.on_unvalidated_hit(dmg, pl, GRENADE_KILL, nade) #this causes crashes, but why?
				c.on_hit(dmg, pl, GRENADE_KILL, nade)
			for n_x, n_y, n_z in product(range(x - 1, x + 2), range(y - 1, y + 2), range(z - 1, z + 2)):
				if p.map.is_valid_position(n_x, n_y, n_z) and not p.is_indestructable(n_x, n_y, n_z):
					count = p.map.destroy_point(n_x, n_y, n_z)
					if count:
						c.total_blocks_removed += count
						c.on_block_removed(n_x, n_y, n_z)
						block_pkt = BlockAction()
						block_pkt.player_id = c.player_id
						block_pkt.value = DESTROY_BLOCK
						block_pkt.x = n_x
						block_pkt.y = n_y
						block_pkt.z = n_z
						p.broadcast_contained(block_pkt, save=True)
			#hijack. grenade_exploded from source is undesirable
		
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
				c.smash_apply_charge(c.world_object.orientation * CHARGE_POWER)
			c.smash_last_sneak = sneak
			return con.on_animation_update(c, jump, crouch, sneak, sprint)
	
		def posupgrade_on_position_unvalidated(c, pos):
			if c.smash_is_charging:
				return False
			try:
				return con.posupgrade_on_position_unvalidated(c, pos)
			except AttributeError:
				pass
	
	
	class SuperSmash_P(pro):
	
		def smash_update(p):
			for pl in p.players.values():
					if pl.world_object is not None:
						if not pl.world_object.dead:
							if pl.smash_is_charging:
								pl.set_location()
							if pl.world_object.position.z > 61.5:
								pl.kill(pl.smash_killer, pl.smash_killer_type, None)
							elif not pl.world_object.airborne: #on ground
								if pl.smash_can_charge:
									pl.smash_can_charge = False
									pl.smash_charges    = CHARGE_LIMIT
									if time() > pl.smash_last_fall_time + 0.2 and time() - pl.smash_start_fall_time > 0.2:
										pl.smash_last_fall_time = time()
										pl.smash_on_fall_always()
								if   pl.smash_anim_state == 1: #walk
									if pl.world_object.velocity.length() <= 0.25: #measured (max vel for walking)
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
								else:                          #stand (and jump)
									if pl.world_object.velocity.length() <= 0.001:
										pl.smash_is_charging = False
										pl.smash_killer   = None
							else:
								if not pl.smash_can_charge:
									pl.smash_start_fall_time = time()
									pl.smash_can_charge = True
		
		smash_update_loop_task = None
		async def smash_update_loop(p):
			fps = 1/FPS
			while True:
				p.smash_update()
				await sleep(fps)
		#suggestion: tie position update to world update if config fps == 0 ?
		
		def on_map_change(p, map_):
			p.user_blocks   = set() #prevent ppl from trenching
			p.fall_damage   = False
			if FPS != 0 and p.smash_update_loop_task is None:
				p.smash_update_loop_task = ensure_future(p.smash_update_loop())
			return pro.on_map_change(p, map_)
		
		def on_map_leave(p):
			if p.smash_update_loop_task is not None:
				p.smash_update_loop_task.cancel()
				p.smash_update_loop_task = None
			return pro.on_map_leave(p)
		
		def smash_get_FPS(p):
			return FPS
		
		def smash_get_CHARGE_LIMIT(p):
			return CHARGE_LIMIT
		
		def smash_get_CHARGE_POWER(p):
			return CHARGE_POWER
			
		def smash_get_DMG_POWER(p):
			return DMG_POWER
		
		def smash_get_MAX_DAMAGE(p):
			return MAX_DAMAGE
		
		def smash_get_DMG_VALS(p):
			return DMG_VALS
		
		def smash_get_DMG_SPADE(p):
			return DMG_SPADE
		
		def smash_get_DMG_NADE(p):
			return DMG_NADE
	
	
	return SuperSmash_P, SuperSmash_C
