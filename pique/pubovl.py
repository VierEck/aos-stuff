'''
latest version: https://github.com/VierEck/aos-scripts/blob/main/pique/pubovl.py
LICENSE: GPL-3.0
codeauthors: VierEck., DryByte (https://github.com/DryByte)

tricks your client into joining you as a spectator. noone else can see 
that you r one. now u can spectate cheaters without alerting them of the 
fact that u r spectating them. have fun. 

scoreboard statistics may get out of sync. Ammo and blocks get out of 
sync since leaving ovl refills you only client-side. this is not much of 
a problem though since the server still keeps track of ur correct amount 
of ammo and blocks. 

/ovl 
	to become a "hidden spectator". use command again to leave that mode. 
/ovl <player> 
	to make someone else become a "hidden spectator". use again to make 
	the player leave that mode. 
/exovl <ip address> 
	use from console or somewhere else. to fake-join as a spectator on ur 
	side. 
'''

from piqueserver.commands import command, target_player
from pyspades.common import Vertex3, make_color
from pyspades.constants import WEAPON_TOOL, WEAPON_KILL
from pyspades import contained as loaders
from pyspades import world
from piqueserver.scheduler import Scheduler
from ipaddress import ip_address


@command('pubovl', 'ovl', admin_only=True)
@target_player
def pubovl(connection, player):
	protocol = connection.protocol
	player.hidden = not player.hidden

	x, y, z = player.world_object.position.get()

	# full compatibility
	create_player = loaders.CreatePlayer()
	create_player.player_id = player.player_id
	create_player.name = player.name
	create_player.x = x
	create_player.y = y
	create_player.z = z + 2
	create_player.weapon = player.weapon

	if player.hidden:
		create_player.team = -1

		player.send_contained(create_player)
		
		client = player.client_string.lower()
		if not "voxlap" in client: #fake deuce does not work in voxlap ;-;
			player.spawn_deuce()
			
		player.send_chat("you are now using pubovl")
		protocol.irc_say('* %s is using pubovl' % player.name) #let the rest of the staff team know u r using this
	else:
		create_player.team = player.team.id

		set_color = loaders.SetColor()
		set_color.player_id = player.player_id
		set_color.value = make_color(*player.color)
		
		player.send_contained(create_player, player)
		
		if player.deuce_spawned:
			player.delete_deuce()
		
		if player.world_object.dead:                              #without this u could run around even though u r supposed to be
			schedule = Scheduler(player.protocol)                 #dead. this could be abused for cheats so we dont allow this. 
			schedule.call_later(0.1, player.spawn_dead_after_ovl) #need call_later cause otherwise u die as spectator which means u
		else:                                                     #dont die at all. 
			player.fix_ori = player.protocol.world_time + 0.5
			
		player.send_chat('you are no longer using pubovl')
		protocol.irc_say('* %s is no longer using pubovl' % player.name)
		

@command('externalovl', 'exovl', admin_only=True) #external~outside: "outside the game". player is connected but not joined to the game
def exovl(connection, ip):                        #                  yet. in this state, since he neither appears on scoreboard nor yet
	protocol = connection.protocol                #                  spawned, he is completely invisible to everyone like he didnt exist. 
	ip_command = ip_address(str(ip))
	for player in protocol.connections.values():
		ip_player = ip_address(player.address[0])
		if player.name is None and ip_player == ip_command:
			x = 256 # spawn them in the middle of the map instead of the left upper corner. 
			y = 256
			z = 0
			create_player = loaders.CreatePlayer()
			create_player.player_id = player.player_id
			create_player.name = "external Deuce" #server doesnt know ur name yet, dont worry, when u rly join u get ur actual name back. 
			create_player.x = x
			create_player.y = y
			create_player.z = z
			create_player.weapon = 0
			create_player.team = -1
			player.send_contained(create_player)
			player.send_chat("you are now using externalovl")
			protocol.irc_say('*%s is using externalovl' % ip)

def apply_script(protocol, connection, config):
	class pubovlProtocol(protocol):
		deuce_id = 0
		
	class pubovlConnection(connection):
		hidden = False
		deuce_spawned = False
		fix_ori = 0
		
		def is_server_full(self):
			if len(self.protocol.players) >= 32:
				return True
			else:
				return False
				
		def delete_deuce(self):
			deuce_left = loaders.PlayerLeft()
			deuce_left.player_id = self.protocol.deuce_id
			self.send_contained(deuce_left, self)
			self.deuce_spawned = False
		
		def spawn_deuce(self):
			x, y, z = self.world_object.position.get()
			create_deuce = loaders.CreatePlayer()
			create_deuce.player_id = self.protocol.deuce_id
			create_deuce.name = self.name
			create_deuce.team = self.team.id
			create_deuce.x = x
			create_deuce.y = y
			create_deuce.z = z
			create_deuce.weapon = self.weapon
			self.send_contained(create_deuce)
			self.deuce_spawned = True
			schedule = Scheduler(self.protocol)
			schedule.call_later(0.1, self.deuce_ups)
		
		def deuce_ups(self):
			self.protocol.players[self.protocol.deuce_id] = self
			items = []
			highest_player_id = max(self.protocol.players)
			for i in range(highest_player_id+1):
				position = orientation = None
				try:
					player = self.protocol.players[i]
					if (not player.filter_visibility_data and
							not player.team.spectator):
						world_object = player.world_object
						position = world_object.position.get()
						orientation = world_object.orientation.get()
				except (KeyError, TypeError, AttributeError):
					pass
				if position is None:
					position = (0.0, 0.0, 0.0)
					orientation = (0.0, 0.0, 0.0)
				items.append((position, orientation))
			world_update = loaders.WorldUpdate()
			world_update.items = items[:highest_player_id+1]
			del self.protocol.players[self.protocol.deuce_id]
			self.send_contained(world_update)
		
		def spawn_dead_after_ovl(self):
			kill_action = loaders.KillAction()
			kill_action.killer_id = self.player_id
			kill_action.player_id = self.player_id
			kill_action.kill_type = 2
			kill_action.respawn_time = self.get_respawn_time() #not actual spawn time, maybe fix this later. 
			self.send_contained(kill_action)
			
		def on_orientation_update(self, x, y, z):
			if self.fix_ori > self.protocol.world_time:
				a, b, c = self.world_object.orientation.get()
				send_ori = loaders.OrientationData()
				send_ori.x = a
				send_ori.y = b
				send_ori.z = c
				self.send_contained(send_ori)
				return False
			return connection.on_orientation_update(self, x, y, z)
		
		def kill(self, by=None, kill_type=WEAPON_KILL, grenade=None):
			if self.hp is None:
				return
			if self.on_kill(by, kill_type, grenade) is False:
				return
			self.drop_flag()
			self.hp = None
			self.weapon_object.reset()
			kill_action = loaders.KillAction()
			kill_action.kill_type = kill_type
			if by is None:
				kill_action.killer_id = kill_action.player_id = self.player_id
			else:
				kill_action.killer_id = by.player_id
				kill_action.player_id = self.player_id
			if by is not None and by is not self:
				by.add_score(1)
			kill_action.respawn_time = self.get_respawn_time() + 1
			
			if self.hidden: 
				self.protocol.broadcast_contained(kill_action, sender=self, save=True) 
				if self.deuce_spawned:
					deuce_id = self.protocol.deuce_id
					if by is None:
						kill_action.killer_id = kill_action.player_id = deuce_id
					else:
						kill_action.killer_id = by.player_id
						kill_action.player_id = deuce_id
					self.send_contained(kill_action)
				if by is not None:
					self.send_chat('[pubovl]: you were killed by %s' % by.name)
			else:
				 self.protocol.broadcast_contained(kill_action, save=True)   
			self.world_object.dead = True
			self.respawn()

			return connection.kill(self, by, kill_type, grenade)
			
		def spawn(self, pos=None):
			self.spawn_call = None
			if self.team is None:
				return
			spectator = self.team.spectator
			create_player = loaders.CreatePlayer()
			if not spectator:
				if pos is None:
					x, y, z = self.get_spawn_location()
					x += 0.5
					y += 0.5
					z -= 2.4
				else:
					x, y, z = pos
				returned = self.on_spawn_location((x, y, z))
				if returned is not None:
					x, y, z = returned
				if self.world_object is not None:
					self.world_object.set_position(x, y, z, True)
				else:
					position = Vertex3(x, y, z)
					self.world_object = self.protocol.world.create_object(
						world.Character, position, None, self._on_fall)
				self.world_object.dead = False
				self.tool = WEAPON_TOOL
				self.refill(True)
				create_player.x = x
				create_player.y = y
				create_player.z = z
				create_player.weapon = self.weapon
			create_player.player_id = self.player_id
			create_player.name = self.name
			create_player.team = self.team.id
			if self.filter_visibility_data and not spectator:
				self.send_contained(create_player)
			else:
				if self.hidden: 
					self.protocol.broadcast_contained(create_player, sender=self,save=True)
					if self.deuce_spawned:
						create_player.player_id = self.protocol.deuce_id
						self.send_contained(create_player)
				else:
					self.protocol.broadcast_contained(create_player, save=True)
			if not spectator:
				self.on_spawn((x, y, z))

			if not self.client_info:
				handshake_init = loaders.HandShakeInit()
				self.send_contained(handshake_init)
				
			if self.player_id == self.protocol.deuce_id:
				if self.deuce_spawned:
					for players in self.protocol.players.values():
						if players.hidden:
							players.delete_deuce()
						
				self.protocol.deuce_id = self.protocol.player_ids.pop()
				self.protocol.player_ids.put_back(self.protocol.deuce_id)
				
				if self.deuce_spawned:
					for players in self.protocol.players.values():
						if players.hidden:
							players.spawn_deuce()

			if not self.hidden:
				return connection.spawn(self, pos)

		def on_team_changed(self, old_team):                    #normally server rejects ur teamchange when ur in ovl cause
			if self.hidden:	                                    #teamid dont align. however if an admin force switches u the
				self.send_chat('you are no longer using pubovl')#script looses track of wether u r using ovl or not. 
				self.hidden = False	                            #idk why i cant irc relay this. 
				if self.deuce_spawned:
					self.delete_deuce()

			return connection.on_team_changed(self, old_team)
			
	return pubovlProtocol, pubovlConnection
