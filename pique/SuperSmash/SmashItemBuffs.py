'''
supplementory script for SmashItems.py (and by extension SuperSmash.py)

Items to buff Player Stats

Authors:
	VierEck.
'''


from pyspades.contained import Restock
from pyspades.constants import WEAPON_TOOL, WEAPON_KILL, HEADSHOT_KILL, HEAD, TORSO, ARMS


isInit = True


#weak items
def MedKit(c, pos = None):
	c.set_hp(c.hp - c.protocol.smash_get_MAX_DAMAGE())
	c.send_chat("You were healed")

def Ammo(c, pos = None):
	c.grenades = 3
	c.blocks = 50
	c.weapon_object.reset()
	restock = Restock()
	c.send_contained(restock)
	c.set_hp(c.hp)
	c.send_chat("You ammo has beend restocked")
	if c.smash_item_lethalmag:
		c.smash_item_lethalmag = False
		c.send_chat("You have no more lethal Bullets")

def Weight(c, pos = None):
	c.smash_item_weight = True
	c.send_chat("Your weight increased! You experience less knockback but ur jumps r weaker")

def Feather(c, pos = None):
	c.smash_item_feather = True
	c.send_chat("Your light as a feather. You can jump higher but experience more knockback")


#decent items
def FullHeal(c, pos = None):
	c.set_hp(1)
	c.send_chat("You were fully healed")

def Shield(c, pos = None):
	c.smash_item_shield = 255
	c.send_chat("You received a shield. You wont receive damage for some time")

def Sponge(c, pos = None):
	c.smash_item_sponge = True
	c.send_chat("You have become a sponge! You experience less knockback")

def BoostDMG(c, pos = None):
	c.smash_item_dmg_boost += .5
	c.send_chat("Your damage output got boosted")


#legendary items
def IronSkin(c, pos = None):
	c.smash_item_ironskin = 255
	c.send_chat("Your skin has become iron! Bullets and shrapnel ricochet off u and hit the nearest enemy")

def Vampire(c, pos = None):
	c.smash_item_vampire = True
	c.send_chat("You have become a vampire! The damage you deal simultaneously heals you")

def LethalMag(c, pos = None):
	Ammo(c, pos)
	c.smash_item_lethalmag = True
	c.send_chat("your current mag is filled with lethal bullets. Make every Bullet count!")


#
def apply_script(pro, con, cfg):

	class SmashItemBuffs_C(con):
		smash_item_dmg_boost = 1
		smash_item_shield    = 0
		smash_item_weight    = False
		smash_item_sponge    = False
		smash_item_ironskin  = 0
		smash_item_vampire   = False
		smash_item_lethalmag = False
		smash_item_feather   = False
	
		def on_spawn(c, pos):
			
			if c.smash_item_feather:
				c.smash_item_feather = False
				c.send_chat("You r not as light as a feather anymore!")
		
			if c.smash_item_lethalmag:
				smash_item_lethalmag = False
				c.send_chat("You have no more lethal Bullets!")
		
			if c.smash_item_vampire:
				c.smash_item_vampire = False
				c.send_chat("You are not a vampire anymore!")
			
			if c.smash_item_ironskin > 0:
				c.smash_item_ironskin = 0
				c.send_chat("Your Skin isn't iron anymore!")
				
			if c.smash_item_sponge:
				c.smash_item_sponge = False
				c.send_chat("You are not a sponge anymore!")
				
			if c.smash_item_weight:
				c.smash_item_weight = False
				c.send_chat("You lost weight!")
			
			c.smash_item_dmg_boost = 1
			
			if c.smash_item_shield > 0:
				c.smash_item_shield = 0
				c.send_chat("You lost your shield!")
				
			return con.on_spawn(c, pos)
		
		def smash_apply_dmg(c, dmg):
			p = c.protocol
			
			if c.smash_killer is not None:
				if c.smash_killer.smash_item_vampire and c.smash_killer is not c:
					c.smash_killer.set_hp(c.smash_killer.hp - dmg)
				
				if c.smash_killer.smash_item_lethalmag and c.smash_killer.tool == WEAPON_TOOL:
					weap      = c.smash_killer.weapon_object.id
					hit_type  = HEADSHOT_KILL
					body_part = HEAD
					if dmg == p.smash_get_DMG_VALS()[weap][1]:
						hit_type  = WEAPON_KILL
						body_part = TORSO
					elif dmg == p.smash_get_DMG_VALS()[weap][2]:
						hit_type  = WEAPON_KILL
						body_part = ARMS
					dmg  = c.smash_killer.weapon_object.get_damage(body_part, c.world_object.position, c.smash_killer.world_object.position)
					dmg *= 2.55
					dmg *= c.smash_killer.smash_item_dmg_boost
					c.set_hp(c.hp + dmg)
					if c.hp >= 255:
						c.kill(c.smash_killer, hit_type, None)
					return
				
				dmg *= c.smash_killer.smash_item_dmg_boost
		
			if c.smash_item_ironskin > 0:
				c.smash_item_ironskin -= dmg
				if c.smash_item_ironskin <= 0:
					c.send_chat("Your iron skin got destroyed!")
				dist = 1024
				victim = None
				for pl in p.players.values():
					if pl.world_object and not pl.world_object.dead and pl is not c:
						pl_dist = (pl.world_object.position - c.world_object.position).length()
						if pl_dist < dist:
							dist = pl_dist
							victim = pl
				if victim is not None:
					aim  = victim.world_object.position - c.world_object.position
					aim /= aim.length()
					k    = p.smash_get_DMG_POWER()
					k   *= 1.0 + (victim.hp + dmg) / (255.0 + p.smash_get_MAX_DAMAGE())
					victim.smash_apply_dmg(dmg)
					victim.smash_apply_knockback(aim*k)
				dmg = 0
				
			if c.smash_item_shield > 0:
				c.smash_item_shield -= dmg
				if c.smash_item_shield <= 0:
					c.send_chat("Your shield broke!")
				dmg = 0
				
			con.smash_apply_dmg(c, dmg)
		
		def smash_apply_knockback(c, vel):
		
			if c.smash_item_weight or c.smash_item_sponge:
				vel *= 0.5
			
			if c.smash_item_feather:
				vel *= 1.25
				
			con.smash_apply_knockback(c, vel)
		
		def smash_apply_charge(c, vel):
		
			if c.smash_item_weight:
				vel *= 0.75
			
			if c.smash_item_feather:
				vel *= 1.5
				
			con.smash_apply_charge(c, vel)
		
		def _on_reload(c):
			if c.smash_item_lethalmag:
				c.smash_item_lethalmag = False
				c.send_chat("You have no more lethal Bullets")
			con._on_reload(c)
	
	
	class SmashItemBuffs_P(pro):
		
		def on_map_change(p, map_):
			global isInit
			if isInit:
				isInit = False
				
				p.smash_add_item_to_dict(0, MedKit)
				p.smash_add_item_to_dict(0, Ammo)
				p.smash_add_item_to_dict(0, Weight)
				p.smash_add_item_to_dict(0, Feather)
				
				p.smash_add_item_to_dict(1, FullHeal)
				p.smash_add_item_to_dict(1, Shield)
				p.smash_add_item_to_dict(1, Sponge)
				p.smash_add_item_to_dict(1, BoostDMG)
				
				p.smash_add_item_to_dict(2, IronSkin)
				p.smash_add_item_to_dict(2, Vampire)
				p.smash_add_item_to_dict(2, LethalMag)
			return pro.on_map_change(p, map_)
	
	
	return SmashItemBuffs_P, SmashItemBuffs_C'''
supplementory script for SmashItems.py (and by extension SuperSmash.py)

Items to buff Player Stats

Authors:
	VierEck.
'''


from pyspades.contained import Restock
from pyspades.constants import WEAPON_TOOL, WEAPON_KILL, HEADSHOT_KILL, HEAD, TORSO, ARMS


isInit = True


#weak items
def MedKit(c, pos = None):
	c.set_hp(c.hp - c.protocol.smash_get_MAX_DAMAGE())
	c.send_chat("You were healed")

def Ammo(c, pos = None):
	c.grenades = 3
	c.blocks = 50
	c.weapon_object.reset()
	restock = Restock()
	c.send_contained(restock)
	c.set_hp(c.hp)
	c.send_chat("You ammo has beend restocked")
	if c.smash_item_lethalmag:
		c.smash_item_lethalmag = False
		c.send_chat("You have no more lethal Bullets")

def Weight(c, pos = None):
	c.smash_item_weight = True
	c.send_chat("Your weight increased! You experience less knockback but ur jumps r weaker")

def Feather(c, pos = None):
	c.smash_item_feather = True
	c.send_chat("Your light as a feather. You can jump higher but experience more knockback")


#decent items
def FullHeal(c, pos = None):
	c.set_hp(1)
	c.send_chat("You were fully healed")

def Shield(c, pos = None):
	c.smash_item_shield = 255
	c.send_chat("You received a shield. You wont receive damage for some time")

def Sponge(c, pos = None):
	c.smash_item_sponge = True
	c.send_chat("You have become a sponge! You experience less knockback")

def BoostDMG(c, pos = None):
	c.smash_item_dmg_boost += .5
	c.send_chat("Your damage output got boosted")


#legendary items
def IronSkin(c, pos = None):
	c.smash_item_ironskin = 255
	c.send_chat("Your skin has become iron! Bullets and shrapnel ricochet off u and hit the nearest enemy")

def Vampire(c, pos = None):
	c.smash_item_vampire = True
	c.send_chat("You have become a vampire! The damage you deal simultaneously heals you")

def LethalMag(c, pos = None):
	Ammo(c, pos)
	c.smash_item_lethalmag = True
	c.send_chat("your current mag is filled with lethal bullets. Make every Bullet count!")


#
def apply_script(pro, con, cfg):

	class SmashItemBuffs_C(con):
		smash_item_dmg_boost = 1
		smash_item_shield    = 0
		smash_item_weight    = False
		smash_item_sponge    = False
		smash_item_ironskin  = 0
		smash_item_vampire   = False
		smash_item_lethalmag = False
		smash_item_feather   = False
	
		def on_spawn(c, pos):
			'''
			if c.smash_item_feather:
				c.smash_item_feather = False
				c.send_chat("You r not as light as a feather anymore!")
		
			if c.smash_item_lethalmag:
				smash_item_lethalmag = False
				c.send_chat("You have no more lethal Bullets!")
		
			if c.smash_item_vampire:
				c.smash_item_vampire = False
				c.send_chat("You are not a vampire anymore!")
			
			if c.smash_item_ironskin > 0:
				c.smash_item_ironskin = 0
				c.send_chat("Your Skin isn't iron anymore!")
				
			if c.smash_item_sponge:
				c.smash_item_sponge = False
				c.send_chat("You are not a sponge anymore!")
				
			if c.smash_item_weight:
				c.smash_item_weight = False
				c.send_chat("You lost weight!")
			
			c.smash_item_dmg_boost = 1
			
			if c.smash_item_shield > 0:
				c.smash_item_shield = 0
				c.send_chat("You lost your shield!")'''
				
			return con.on_spawn(c, pos)
		
		def smash_apply_dmg(c, dmg):
			p = c.protocol
			
			if c.smash_killer is not None:
				if c.smash_killer.smash_item_vampire and c.smash_killer is not c:
					c.smash_killer.set_hp(c.smash_killer.hp - dmg)
				
				if c.smash_killer.smash_item_lethalmag and c.smash_killer.tool == WEAPON_TOOL:
					weap      = c.smash_killer.weapon_object.id
					hit_type  = HEADSHOT_KILL
					body_part = HEAD
					if dmg == p.smash_get_DMG_VALS()[weap][1]:
						hit_type  = WEAPON_KILL
						body_part = TORSO
					elif dmg == p.smash_get_DMG_VALS()[weap][2]:
						hit_type  = WEAPON_KILL
						body_part = ARMS
					dmg  = c.smash_killer.weapon_object.get_damage(body_part, c.world_object.position, c.smash_killer.world_object.position)
					dmg *= 2.55
					dmg *= c.smash_killer.smash_item_dmg_boost
					c.set_hp(c.hp + dmg)
					if c.hp >= 255:
						c.kill(c.smash_killer, hit_type, None)
					return
				
				dmg *= c.smash_killer.smash_item_dmg_boost
		
			if c.smash_item_ironskin > 0:
				c.smash_item_ironskin -= dmg
				if c.smash_item_ironskin <= 0:
					c.send_chat("Your iron skin got destroyed!")
				dist = 1024
				victim = None
				for pl in p.players.values():
					if pl.world_object and not pl.world_object.dead and pl is not c:
						pl_dist = (pl.world_object.position - c.world_object.position).length()
						if pl_dist < dist:
							dist = pl_dist
							victim = pl
				if victim is not None:
					aim  = victim.world_object.position - c.world_object.position
					aim /= aim.length()
					k    = p.smash_get_DMG_POWER()
					k   *= 1.0 + (victim.hp + dmg) / (255.0 + p.smash_get_MAX_DAMAGE())
					victim.smash_apply_dmg(dmg)
					victim.smash_apply_knockback(aim*k)
				dmg = 0
				
			if c.smash_item_shield > 0:
				c.smash_item_shield -= dmg
				if c.smash_item_shield <= 0:
					c.send_chat("Your shield broke!")
				dmg = 0
				
			con.smash_apply_dmg(c, dmg)
		
		def smash_apply_knockback(c, vel):
		
			if c.smash_item_weight or c.smash_item_sponge:
				vel *= 0.5
			
			if c.smash_item_feather:
				vel *= 1.25
				
			con.smash_apply_knockback(c, vel)
		
		def smash_apply_charge(c, vel):
		
			if c.smash_item_weight:
				vel *= 0.75
			
			if c.smash_item_feather:
				vel *= 1.5
				
			con.smash_apply_charge(c, vel)
		
		def _on_reload(c):
			if c.smash_item_lethalmag:
				c.smash_item_lethalmag = False
				c.send_chat("You have no more lethal Bullets")
			con._on_reload(c)
	
	
	class SmashItemBuffs_P(pro):
		
		def on_map_change(p, map_):
			global isInit
			if isInit:
				isInit = False
				
				p.smash_add_item_to_dict(0, MedKit)
				p.smash_add_item_to_dict(0, Ammo)
				p.smash_add_item_to_dict(0, Weight)
				p.smash_add_item_to_dict(0, Feather)
				
				p.smash_add_item_to_dict(1, FullHeal)
				p.smash_add_item_to_dict(1, Shield)
				p.smash_add_item_to_dict(1, Sponge)
				p.smash_add_item_to_dict(1, BoostDMG)
				
				p.smash_add_item_to_dict(2, IronSkin)
				p.smash_add_item_to_dict(2, Vampire)
				p.smash_add_item_to_dict(2, LethalMag)
			return pro.on_map_change(p, map_)
	
	
	return SmashItemBuffs_P, SmashItemBuffs_C
