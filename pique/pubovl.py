'''
PubOVL. Secret Spectating.


Authors: 
	VierEck.
	DryByte (https://github.com/DryByte)
'''


from piqueserver.scheduler import Scheduler
from piqueserver.commands import command, target_player
from pyspades.contained import CreatePlayer, KillAction, PlayerLeft, WorldUpdate, OrientationData


def notification(c, msg):
	p = c.protocol
	if c in p.players.values():
		c.send_chat(msg)
		if "you are" == msg[:7].lower():
			msg = c.name + " is " + msg[7:]
	p.irc_say("* " + msg)


@command("pubovl", "ovl", admin_only=True)
@target_player
def pubovl(c, pl):
	p = c.protocol
	if pl.pubovl_is_active:
		pl.pubovl_end()
	else:
		pl.pubovl_start()
	if c in p.players.values() and c != pl:
		notification(c, c.name + " has given PubOVL to " + pl.name)


def apply_script(pro, con, cfg):


	class pubovl_C(con):
		pubovl_is_active     = False
		pubovl_dummy_spawned = False
		pubovl_fix_ori       = 0
		
		def send_contained(c, pkt, sequence = False):
			p = c.protocol
			if c.pubovl_is_active:
				if pkt.id in (CreatePlayer.id, KillAction.id) and pkt.player_id == c.player_id:
					if c.pubovl_dummy_spawned:
						pkt.player_id = p.pubovl_dummy_id
					else:
						return #hijack
			elif pkt.id == CreatePlayer.id:
				if c.player_id == p.pubovl_dummy_id or p.pubovl_dummy_id > 31:
					p.pubovl_update_dummy()
			return con.send_contained(c, pkt, sequence)
		
		def on_orientation_update(c, x, y, z):
			p = c.protocol
			if c.pubovl_fix_ori > p.world_time:
				ori_pkt = OrientationData()
				ori_pkt.x, ori_pkt.y, ori_pkt.z = c.world_object.orientation.get()
				c.send_contained(ori_pkt)
				return False
			return con.on_orientation_update(c, x, y, z)
		
		def pubovl_start(c):
			p = c.protocol
			c.pubovl_spawn_dummy()
			
			create_pkt = CreatePlayer()
			create_pkt.player_id = c.player_id
			create_pkt.name      = c.name
			create_pkt.team      = -1
			create_pkt.weapon    = c.weapon
			create_pkt.x, create_pkt.y, create_pkt.z = c.world_object.position.get()
			create_pkt.z += 2
			c.send_contained(create_pkt)
			
			c.pubovl_is_active = True
			notification(c, "you are now using PubOVL")
		
		def pubovl_end(c):
			p = c.protocol
			
			c.pubovl_remove_dummy()
			c.pubovl_is_active = False
			notification(c, "you are no longer using PubOVL")
			
			create_pkt = CreatePlayer()
			create_pkt.player_id = c.player_id
			create_pkt.name      = c.name
			create_pkt.team      = c.team.id
			create_pkt.weapon    = c.weapon
			create_pkt.x, create_pkt.y, create_pkt.z = c.world_object.position.get()
			create_pkt.z += 2
			c.send_contained(create_pkt)
			
			if c.world_object.dead:
				def send_dead():
					if c and not c.disconnected:
						kill_pkt = KillAction()
						kill_pkt.killer_id = kill_pkt.player_id = c.player_id
						kill_pkt.kill_type    = 2
						kill_pkt.respawn_time = c.get_respawn_time() #fixme: incorrect respawn time
						c.send_contained(kill_pkt)
				sched = Scheduler(p)
				sched.call_later(0.1, send_dead)
			else:
				c.pubovl_fix_ori = p.world_time + 0.5
		
		def pubovl_spawn_dummy(c):
			if c.pubovl_dummy_spawned:
				return
			clin_str = c.client_string.lower()
			if "voxlap" in clin_str:
				return #dummy doesnt work in voxlap
			p = c.protocol
			p.pubovl_update_dummy()
			if p.pubovl_dummy_id > 31:
				if "betterspades" not in clin_str or "iv of spades" not in clin_str:
					return #only betterspades and iv of spades are (>32) compatible as of now :/
			
			create_pkt = CreatePlayer()
			create_pkt.player_id = p.pubovl_dummy_id
			create_pkt.name      = c.name
			create_pkt.team      = c.team.id
			create_pkt.weapon    = c.weapon
			create_pkt.x, create_pkt.y, create_pkt.z = c.world_object.position.get()
			c.send_contained(create_pkt)
			
			c.pubovl_dummy_spawned = True
			
			def send_dummy_dead():
				if c and not c.disconnected:
					kill_pkt = KillAction()
					kill_pkt.killer_id = kill_pkt.player_id = p.pubovl_dummy_id
					kill_pkt.kill_type    = 2
					kill_pkt.respawn_time = c.get_respawn_time() #fixme: incorrect respawn time
					c.send_contained(kill_pkt)
			
			def send_dummy_ori():
				if c and not c.disconnected:
					p.players[p.pubovl_dummy_id] = c
					items = []
					highest_player_id = max(p.players)
					for i in range(highest_player_id + 1):
						pos = ori = None
						try:
							pl = p.players[i]
							if (not pl.filter_visibility_data and not pl.team.spectator):
								pos = pl.world_object.position.get()
								ori = pl.world_object.orientation.get()
						except (KeyError, TypeError, AttributeError):
							pass
						if pos is None:
							pos = (0.0, 0.0, 0.0)
							ori = (0.0, 0.0, 0.0)
						items.append((pos, ori))
					ups_pkt = WorldUpdate()
					ups_pkt.items = items[:highest_player_id+1]
					del p.players[p.pubovl_dummy_id]
					c.send_contained(ups_pkt)
			
			sched = Scheduler(p)
			if c.world_object.dead:
				sched.call_later(0.1, send_dummy_dead)
			else:
				sched.call_later(0.1, send_dummy_ori)
		
		def pubovl_remove_dummy(c):
			if not c.pubovl_dummy_spawned:
				return
			p = c.protocol
			c.pubovl_dummy_spawned = False
			
			left_pkt = PlayerLeft()
			left_pkt.player_id = p.pubovl_dummy_id
			c.send_contained(left_pkt)
		
		def on_team_changed(c, old_team): #take forced team switch into account
			if c.pubovl_is_active:
				p = c.protocol
				c.pubovl_remove_dummy()
				c.pubovl_is_active = False
				notification(c, "you are no longer using PubOVL")
			return con.on_team_changed(c, old_team)
	
	
	class pubovl_P(pro):
		pubovl_dummy_id  = 0
		
		def broadcast_contained(p, pkt, unsequenced=False, sender=None, team=None, save=False, rule=None):
			if pkt.id in (CreatePlayer.id, KillAction.id):
				pl = p.players[pkt.player_id]
				if pl.pubovl_is_active:
					pkt.player_id = p.pubovl_dummy_id
					pl.send_contained(pkt)
					sender = pl
				elif pkt.id == CreatePlayer.id:
					if pl.player_id == p.pubovl_dummy_id or p.pubovl_dummy_id > 31:
						p.pubovl_update_dummy()
			return pro.broadcast_contained(p, pkt, unsequenced, sender, team, save, rule)
		
		def pubovl_update_dummy(p):
			new_id = 0
			for pl in p.connections.values():
				if pl.player_id is not None and new_id == pl.player_id:
					new_id += 1
			if new_id != p.pubovl_dummy_id:
				for pl in p.connections.values():
					if pl.pubovl_is_active:
						pl.pubovl_remove_dummy()
				p.pubovl_dummy_id = new_id
				for pl in p.connections.values():
					if pl.pubovl_is_active:
						pl.pubovl_spawn_dummy()
		
		def on_map_leave(p):
			for pl in p.connections.values():
				pl.pubovl_is_active = pl.pubovl_dummy_spawned = False
			return pro.on_map_leave(p)
	
	
	return pubovl_P, pubovl_C
