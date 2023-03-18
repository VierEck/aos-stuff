"""
lastest version: https://github.com/VierEck/aos-scripts/blob/main/pique/gamemodes/supersmashoff.py
LICENSE: GPL-3.0
codeauthor: VierEck.
codeauthor of original charge script: Jipok (https://github.com/piqueserver/piqueserver-extras/blob/master/scripts/charge.py)
codeauthor of original smashoff gamemode: Dr.Morphman (https://aloha.pk/t/smashoff/13723/3)

I just realized u will need python 3.10

based on Morphman's gamemode "Smashoff". Super SmashOff uses Jipok's 
charge script for inflicting knockback which looks a lot smoother. 

furthermore players can use aimed charges. they charge into the direction 
they are looking at, giving them a lot more control over their movement. 

mapblocks r (or rather should be) undestructable in this gamemode, since 
digging down makes u virtually invincible as ur enemies are incapable of 
launching u anywhere and some smashoff maps are going to be prone to 
griefing. 

this may or may not be a complete lagshow. i recommend playing on low ping


config.toml exemplary copypaste template: 

[supersmashoff] #these configs are also commands and can be changed ingame. 
				#ingame command template: /smashad <config> <value>
damagelimit = 300 #set to 0 if u want unlimited "health"
baseknockback = 1 #multiplies knockback globaly
basedamage = 1 #keep in mind that damage scales up knockback aswell

chargecooldown = 0.2
chargepower = 1.5
chargelimit = 3

riflehead = 20 #damage values for each body part depending on weapon
riflebody = 15
riflelimb = 10

smghead = 8
smgbody = 6
smglimb = 4

shotgunhead = 4 #damage for each shotgun pellet. keep in mind one shot has 8 pellets
shotgunbody = 3
shotgunlimb = 2

spadedamage = 30 #strongest weapon. reward dynamic high risk close combat
nadedamage = 20 #maybe surprisingy weak to some, but splash damage 
				#makes more than up for it imo
"""

import time
import asyncio
from piqueserver.commands import command, get_player
from piqueserver.config import config
from pyspades.world import Grenade
from pyspades.constants import CTF_MODE
from pyspades import contained as loaders

smash_config = config.section('supersmashoff')

@command('smash') #i think this "/command <command> <value>" format is good so that commands from other scripts wont overlap
def smashplayercommands(connection, command, player_=None):
	protocol = connection.protocol
	player = None
	if player_ is not None:
		player = get_player(protocol, player_)
	match command:
		case 'help':
			connection.send_chat('/smash help, /smash hp <player>')
			connection.send_chat('commands:')
		case 'hp':
			if player is None:
				connection.send_chat('Your Damage: %.0f' % connection.dmgpercent)
			else:
				connection.send_chat('%s Damage: %.0f' % (player.name, player.dmgpercent))
		case _:
			connection.send_chat('command doesnt exist. for more info, please type /smash help')
		
@command('smashad', admin_only=True)
def smashadmincommands(connection, command, value=None): #on the fly ingame configuration and admin commands.
	protocol = connection.protocol
	match command: 
		case 'help':
			connection.send_chat('other command template: /smashad <command> <value/player>')
			connection.send_chat('config command template: /smashad <config> <value>')
			connection.send_chat('all smash configs can be changed via command.')
		case 'damagelimit':
			protocol.smash_dmg_limit = int(value)
			protocol.irc_say('%s set to %.0f' % (command, int(value)))
			protocol.broadcast_chat('%s set to %.0f' % (command, int(value)))
		case 'baseknockback':
			protocol.smash_base_knock = int(value)
			protocol.irc_say('%s set to %.0f' % (command, int(value)))
			protocol.broadcast_chat('%s set to %.0f' % (command, int(value)))
		case 'basedamage':
			protocol.smash_base_dmg = int(value)
			protocol.irc_say('%s set to %.0f' % (command, int(value)))
			protocol.broadcast_chat('%s set to %.0f' % (command, int(value)))
			
		case 'chargecooldown':
			protocol.charge_cooldown = int(value)
			protocol.irc_say('%s set to %.0f' % (command, int(value)))
			protocol.broadcast_chat('%s set to %.0f' % (command, int(value)))
		case 'chargepower':
			protocol.charge_power = int(value)
			protocol.irc_say('%s set to %.0f' % (command, int(value)))
			protocol.broadcast_chat('%s set to %.0f' % (command, int(value)))
		case 'chargelimit':
			protocol.charge_limit = int(value)
			protocol.irc_say('%s set to %.0f' % (command, int(value)))
			protocol.broadcast_chat('%s set to %.0f' % (command, int(value)))
			
		case 'riflehead':
			protocol.smash_rifle_head = int(value)
			protocol.irc_say('%s set to %.0f' % (command, int(value)))
			protocol.broadcast_chat('%s set to %.0f' % (command, int(value)))
		case 'riflebody':
			protocol.smash_rifle_body = int(value)
			protocol.irc_say('%s set to %.0f' % (command, int(value)))
			protocol.broadcast_chat('%s set to %.0f' % (command, int(value)))
		case 'riflelimb':
			protocol.smash_rifle_limb = int(value)
			protocol.irc_say('%s set to %.0f' % (command, int(value)))
			protocol.broadcast_chat('%s set to %.0f' % (command, int(value)))
			
		case 'smghead':
			protocol.smash_smg_head = int(value)
			protocol.irc_say('%s set to %.0f' % (command, int(value)))
			protocol.broadcast_chat('%s set to %.0f' % (command, int(value)))
		case 'smgbody':
			protocol.smash_smg_body = int(value)
			protocol.irc_say('%s set to %.0f' % (command, int(value)))
			protocol.broadcast_chat('%s set to %.0f' % (command, int(value)))
		case 'smglimb':
			protocol.smash_smg_limb = int(value)
			protocol.irc_say('%s set to %.0f' % (command, int(value)))
			protocol.broadcast_chat('%s set to %.0f' % (command, int(value)))
			
		case 'shotgunhead':
			protocol.smash_shotty_head = int(value)
			protocol.irc_say('%s set to %.0f' % (command, int(value)))
			protocol.broadcast_chat('%s set to %.0f' % (command, int(value)))
		case 'shotgunbody':
			protocol.smash_shotty_body = int(value)
			protocol.irc_say('%s set to %.0f' % (command, int(value)))
			protocol.broadcast_chat('%s set to %.0f' % (command, int(value)))
		case 'shotgunlimb':
			protocol.smash_shotty_limb = int(value)
			protocol.irc_say('%s set to %.0f' % (command, int(value)))
			protocol.broadcast_chat('%s set to %.0f' % (command, int(value)))
			
		case 'spadedamage':
			protocol.smash_spade = int(value)
			protocol.irc_say('%s set to %.0f' % (command, int(value)))
			protocol.broadcast_chat('%s set to %.0f' % (command, int(value)))
		case 'nadedamage':
			protocol.smash_nade = int(value)
			protocol.irc_say('%s set to %.0f' % (command, int(value)))
			protocol.broadcast_chat('%s set to %.0f' % (command, int(value)))
			
		case _: 
			connection.send_chat('command doesnt exist. for more info, type /smashad help')
		
def apply_script(protocol, connection, config):
	class SmashConnection(connection):
		sneak = False
		charging = False
		charge_allowed = False
		anim_state = 0
		last_charge_time = 0
		last_shotty_time = 0
		dmgpercent = 0 #the higher this value the more knockback u experience like in smashbros
		killer = None
		killer_id = 0
		type_id = 0

		def on_spawn(self, pos):
			self.last_charge_time = 0
			self.last_shotty_time = 0
			self.charge_again = self.protocol.charge_limit
			return connection.on_spawn(self, pos)

		def on_login(self, name):
			connection.on_login(self, name)
			self.protocol.smasher_list.append(self)
			self.last_charge_time = 0
			self.send_chat("Knock your opponents into water to kill him!")
			self.send_chat("There is a limit of %.0f charges per jump" % self.protocol.charge_limit)
			self.send_chat("You got the aimcharge ability. Jump and press V (sneak) while in the air!")
			self.send_chat("Gamemode: Super SmashOff by VierEck.")
			
		def kill_player(self):
			if (self.killer == None): 
				self.killer_id = self.player_id
				self.type_id = 2
			
			self.drop_flag()
			self.hp = None
			self.weapon_object.reset()
			kill_action = loaders.KillAction()
			kill_action.killer_id = self.killer_id
			kill_action.player_id = self.player_id
			kill_action.kill_type = self.type_id
			kill_action.respawn_time = self.get_respawn_time()
			if self.killer is not None and self.killer is not self:
				self.killer.add_score(1)
			self.protocol.broadcast_contained(kill_action, save=True)
			self.world_object.dead = True
			self.respawn()
			self.killer = None
			self.dmgpercent = 0
		
		def on_walk_update(self, up: bool, down: bool, left: bool, right: bool) -> None:
			if not up and not left and not right and not down:
				self.anim_state = 0 #standing
			return connection.on_walk_update(self, up, down, left, right)

		def on_animation_update(self, jump, crouch, sneak, sprint):
			if sprint:
				self.anim_state = 2
			elif crouch:
				self.anim_state = 3
			elif sneak:
				self.anim_state = 4
			elif jump:
				self.anim_state = 0
			else: #walking
				self.anim_state = 1 
			if sneak and not self.sneak and self in self.protocol.smasher_list:
				if (time.monotonic() >= self.last_charge_time + self.protocol.charge_cooldown) and self.charge_allowed:
					vel = self.world_object.velocity
					aim = self.world_object.orientation
					k = self.protocol.charge_power / aim.length()
					vel.set(*(aim*k).get())
					self.charging = True
					self.last_charge_time = time.monotonic()
					self.charge_again = self.charge_again - 1
					self.send_chat_warning("charges left: %.0f" % self.charge_again)
			self.sneak = sneak
			return connection.on_animation_update(self, jump, crouch, sneak, sprint)
			
		def get_damage(self, weapon, bodyorspade, amount):
			weapon_body_val = {
				0 : {
					'head': self.protocol.smash_rifle_head,
					'body': self.protocol.smash_rifle_body,
					'limb': self.protocol.smash_rifle_limb,
				},
				1 : {
					'head': self.protocol.smash_smg_head,
					'body': self.protocol.smash_smg_body,
					'limb': self.protocol.smash_smg_limb,
				},
				2 : {
					'head': self.protocol.smash_shotty_head,
					'body': self.protocol.smash_shotty_body,
					'limb': self.protocol.smash_shotty_limb,
				}
			}
			body_damage_values = [49, 29, 27]
			limb_damage_values = [33, 18, 16]
			typedamage = 0
			match bodyorspade:
				case 0:
					if amount in body_damage_values:
						typedamage = weapon_body_val[weapon]['body']
					elif amount in limb_damage_values:
						typedamage = weapon_body_val[weapon]['limb']
				case 1:
					typedamage = weapon_body_val[weapon]['head']
				case 2:
					typedamage = self.protocol.smash_spade
				case _: #grenade
					amount /= 10
					if amount > 100:
						amount = 100
					typedamage = (amount / 100) * self.protocol.smash_nade
			totaldamage = typedamage * self.protocol.smash_base_dmg
			return totaldamage
			
		def get_knockback(self, damage, player, grenade, weapon):
			totalknockback = self.protocol.smash_base_knock * (damage/10 + player.dmgpercent/100)
			if not grenade:
				p_vel = player.world_object.velocity
				aim = self.world_object.orientation
				k = totalknockback / aim.length()
				if weapon == 2 and time.monotonic() < self.last_shotty_time + 0.1:
					k += p_vel.length() #each pellet in a shot add to one big knockback
				p_vel.set(*(aim*k).get())
				player.charging = True
				if self.weapon_object.id == 2:			
					self.last_shotty_time = time.monotonic()
			else:
				p_vel = player.world_object.velocity
				aim = player.world_object.position - grenade.position
				k = totalknockback / aim.length()
				p_vel.set(*(aim*k).get())
				player.charging = True
				
		def update_player_dmg(self, player, totaldamage):
			player.dmgpercent += totaldamage
			if player.dmgpercent >= self.protocol.smash_dmg_limit and self.protocol.smash_dmg_limit != 0:
				player.dmgpercent = self.protocol.smash_dmg_limit
			if player.player_id != self.player_id:
				self.send_chat_status("[%s]" % player.name)
				self.send_chat_status("%.f percent" % player.dmgpercent)
			player.send_chat_status("Your Damage:")
			player.send_chat_status("%.f percent" % player.dmgpercent)
			
		def on_hit(self, hit_amount: float, player: 'FeatureConnection', _type: int, grenade: Grenade) -> bool:
			player.killer = self
			player.killer_id = self.player_id
			player.type_id = _type
			
			totaldamage = self.get_damage(self.weapon_object.id, _type, hit_amount)
			self.get_knockback(totaldamage, player, grenade, self.weapon_object.id)
			self.update_player_dmg(player, totaldamage)
			return False

	class SmashProtocol(protocol):
		game_mode = CTF_MODE
		
		#on the fly ingame configuration
		smash_dmg_limit = smash_config.option('damagelimit', 300).get()
		smash_base_knock = smash_config.option('baseknockback', 1).get()
		smash_base_dmg = smash_config.option('basedamage', 1).get()
													   
		charge_cooldown = smash_config.option('chargecooldown', 0.2).get()
		charge_power = smash_config.option('chargepower', 1.5).get()
		charge_limit = smash_config.option('chargelimit', 3).get()
	
		smash_rifle_head = smash_config.option('riflehead', 20).get()
		smash_rifle_body = smash_config.option('riflebody', 15).get()
		smash_rifle_limb = smash_config.option('riflelimb', 10).get()
	
		smash_smg_head = smash_config.option('smghead', 8).get()
		smash_smg_body = smash_config.option('smgbody', 6).get()
		smash_smg_limb = smash_config.option('smglimb', 4).get()
	
		smash_shotty_head = smash_config.option('shotgunhead', 4).get()
		smash_shotty_body = smash_config.option('shotgunbody', 3).get()
		smash_shotty_limb = smash_config.option('shotgunlimb', 2).get()
	
		smash_spade = smash_config.option('spadedamage', 30).get()
		smash_nade = smash_config.option('nadedamage', 20).get()
		
		smasher_list = []
		smash_loop_task = None
		last_kill_update = time.monotonic()
		last_condition_update = time.monotonic()
		last_charge_update = time.monotonic()
		
		async def smash_loop(self):
			while True:
				for player in self.smasher_list:
					if player.world_object is None:
						continue
					#charge condition update 20 times a sec
					if time.monotonic() - self.last_condition_update >= 1/20: 
						self.last_condition_update = self.world_time
						if player.world_object.velocity.z == 0.0:
							player.charge_allowed = False
							player.charge_again = player.protocol.charge_limit
							match player.anim_state:
								case 0:#standing
									if player.world_object.velocity.length() <= 0.0:
										player.charging = False
										player.killer = None
								case 1:#walking
									if player.world_object.velocity.length() <= 0.25:
										player.charging = False
										player.killer = None
								case 2:#sprint
									if player.world_object.velocity.length() <= 0.3250:
										player.charging = False
										player.killer = None
								case 3:#crouch
									if player.world_object.velocity.length() <= 0.075:
										player.charging = False
										player.killer = None
								case 4:#sneak
									if player.world_object.velocity.length() <= 0.125:
										player.charging = False
										player.killer = None
								case _:#idk lmao
									if player.world_object.velocity.length() <= 0.0:
										player.charging = False
										player.killer = None
						else: 
							player.charge_allowed = True
						if player.charge_again == 0:
							player.charge_allowed = False
					#waterdamage update 5 times a sec
					if time.monotonic() - self.last_kill_update >= 1/5:
						self.last_kill_update = self.world_time
						if player.world_object.position.z > 60 and not player.world_object.dead:
							player.kill_player()
					#charge position update 120 times a sec
					if player.charging:
						player.set_location()
				await asyncio.sleep(1/120)

		def on_map_change(self, map_):
			if self.smash_loop_task is None:
				self.smash_loop_task = asyncio.ensure_future(self.smash_loop())
			self.user_blocks = set()
			self.fall_damage = False
			return protocol.on_map_change(self, map_)

		def on_map_leave(self):
			self.smash_loop_task.cancel()
			self.smash_loop_task = None
			protocol.on_map_leave(self)
			
	return SmashProtocol, SmashConnection,
