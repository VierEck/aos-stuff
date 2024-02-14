'''
SuperSmashOff FreeForAll DeathMatch. Gamemode script.

Players r all in the same team so they see each other on the map.
Your companions r spawned on the opposite team to visually distinguish them from enemies.

recommended setting:
	default_time_limit = "10min"
	respawn_time       = "6sec" 

pls include disco.py for disco effect at round end


based on FreeForAll by Yourself:
	https://github.com/aloha-pk/piqueserver/blob/master/piqueserver/game_modes/freeforall.py

Authors: 
	VierEck.
	Yourself
'''


from random import randint
from twisted.internet.reactor import callLater
from pyspades.constants import CTF_MODE
from piqueserver.config import config
from piqueserver.commands import command, target_player
from piqueserver.server import scripts_option
from pyspades.contained import CreatePlayer, IntelCapture, PositionData, GrenadePacket
from pyspades.world import Grenade
from pyspades.common import Vertex3


DM_MODE_TIME, DM_MODE_COUNT = range(2)


smash_cfg = config.section("SuperSmashOff")
PLAYER_TEAM     = smash_cfg.option("SSFFADM_player_team"    , None).get() #0 == team1/blue; 1 == team2/green
DM_MODE         = smash_cfg.option("SSFFADM_mode"           , "time").get() 
COUNT_MAX_KILLS = smash_cfg.option("SSFFADM_count_max_kills", 100).get()
if "count" in DM_MODE:
	#game end on first player to achieve max kills. 
	#if time limit is reached then game ends like in time mode.
	DM_MODE = DM_MODE_COUNT 
else:
	#time = default mode
	#game end only on map time limit reached
	DM_MODE = DM_MODE_TIME


def broadcast_chat_status(p, msg):
	for pl in p.players.values():
		pl.send_chat("C% " + msg)


def print_scores(c):
	msg  = ": score = "
	msg += "+kills(" + str(c.smash_kills) + ") "
	msg += "-deaths(" + str(c.smash_deaths) + ") "
	msg += "-suicides(" + str(c.smash_suicides) + ") = "
	msg += str(c.smash_get_score())
	return msg


@command("smash_score")
@target_player
def smash_get_scores(c, pl):
	pl.send_chat(pl.name + print_scores(pl))


#
def apply_script(pro, con, cfg):

	class SuperSmashFFADM_C(con):
		smash_kills     = 0
		smash_deaths    = 0
		smash_suicides  = 0
		smash_spawn_pos = None
		
		def smash_get_score(c):
			return c.smash_kills - c.smash_deaths - c.smash_suicides
	
		def on_team_join(c, team):
			if not team.spectator:
				return PLAYER_TEAM
			return con.on_team_join(c, team)
		
		def on_spawn(c, pos):
			if c.local:
				b = c
				try:
					bot_team = b.smash_bot_friend.team.other
					
					create_pkt = CreatePlayer()
					create_pkt.x, create_pkt.y, create_pkt.z = pos
					create_pkt.weapon    = b.weapon
					create_pkt.player_id = b.player_id
					create_pkt.name      = b.name
					create_pkt.team      = bot_team.id
					
					b.smash_bot_friend.send_contained(create_pkt)
				except AttributeError:
					pass
			return con.on_spawn(c, pos)
		
		def on_spawn_location(c, pos):
			p = c.protocol
			if c.smash_spawn_pos is None:
				x, y, z = p.get_random_location(True)
				z -= 2
				return (x, y, z)
			else:
				_pos = c.smash_spawn_pos
				c.smash_spawn_pos = None
				return _pos
		
		def respawn(c):
			p = c.protocol
			x, y, z = p.get_random_location(True)
			z -= 2
			c.smash_spawn_pos = x, y, z
			t = c.get_respawn_time() - 3
			def foresee_spawn(c):
				pos_pkt = PositionData()
				pos_pkt.x, pos_pkt.y, pos_pkt.z = c.smash_spawn_pos
				c.send_contained(pos_pkt)
			if t > 0.5:
				callLater(t, foresee_spawn, c)
			else:
				foresee_spawn(c)
			con.respawn(c)
		
		def on_kill(c, killer, kill_type, nade):
			p = c.protocol
			if killer and c != killer:
				killer.smash_kills += 1
				c.smash_deaths     += 1
				
				killer.streak += 1
				killer.best_streak = max(killer.streak, killer.best_streak)
			else:
				c.smash_suicides += 1
			if DM_MODE == DM_MODE_COUNT:
				if killer.smash_kills >= COUNT_MAX_KILLS:
					p._time_up()
			return con.on_kill(c, killer, kill_type, nade)
	
	
	class SuperSmashFFADM_P(pro):
		game_mode       = CTF_MODE
		smash_round_end = False
		
		def on_game_end(p):
			p.smash_round_end = True
			score_player_list = []
			x, y, z = 256, 256, 0
			for pl in p.players.values():
				score = pl.smash_get_score()
				
				did_insert = False
				for i in range(len(score_player_list)):
					other = score_player_list[i]
					other_score = other.smash_get_score()
					if score > other_score:
						score_player_list.insert(i, pl)
						did_insert = True
						break
				if not did_insert:
					score_player_list.append(pl)
						
				if not pl.team.spectator:
					#gather everyone at map center
					pl.smash_spawn_pos = x + randint(-5, 5), y + randint(-5, 5), z
					pl.spawn()
			
			if len(score_player_list) > 0:
				winner = score_player_list[0]
				
				placement_list = []
				placement      = 0
				last_score     = -1234567
				for i in range(0, len(score_player_list)):
					pl = score_player_list[i]
					score = pl.smash_get_score()
					if last_score != score:
						last_score = score
						placement += 1
					placement_list.append(placement)
				
				#anounce podium
				for i in range(min(5, len(score_player_list))):
					if placement_list[i] > 3:
						break
					pl = score_player_list[i]
					msg  = str(placement_list[i]) + ". " + str(pl.name) 
					msg += print_scores(pl)
					p.broadcast_chat(msg)
				
				#inform about ur own stats
				for i in range(len(score_player_list)):
					pl = score_player_list[i]
					msg  = str(placement_list[i]) + ". " + str(pl.name)
					msg += print_scores(pl)
					pl.send_chat(msg)
				
				#play the winning fanfare
				intel_pkt = IntelCapture()
				intel_pkt.player_id = winner.player_id
				intel_pkt.winning = True
				p.broadcast_contained(intel_pkt)
				
				broadcast_chat_status(p, winner.name + " has won")
				broadcast_chat_status(p, "with " + str(winner.smash_get_score()) + " points!")
				
				#one last bang. fling everyone in random directions
				vPos = Vertex3(x, y, z + 5)
				vel  = Vertex3()
				nade = p.world.create_object(Grenade, 0.0, vPos, None, vel, winner.grenade_exploded)
				nade_pkt = GrenadePacket()
				nade_pkt.player_id = winner.player_id
				nade_pkt.value     = nade.fuse
				nade_pkt.position  = vPos.get()
				nade_pkt.velocity  = vel.get()
				p.broadcast_contained(nade_pkt)
			script_names = scripts_option.get()
			if "disco" in script_names or "piqueserver.scripts.disco" in script_names:
				if not p.disco:
					p.toggle_disco(False)
		
		def _time_up(p):
			p.on_game_end()
			pro._time_up(p)
		
		def on_map_change(p, map_):
			p.max_score       = 1
			p.smash_round_end = False
			p.friendly_fire   = True
			p.respawn_waves   = False
			ext = p.map_info.extensions
			global PLAYER_TEAM
			if PLAYER_TEAM is None:
				if "SSFFADMPlayerTeam" in ext and ext["SSFFADMPlayerTeam"] == 0:
					PLAYER_TEAM = p.team_1
				else:
					PLAYER_TEAM = p.team_2
			elif PLAYER_TEAM == 0:
				PLAYER_TEAM = p.team_1
			else:
				#by default 2, since team_2 on aloha is red and red is cooler than blue
				PLAYER_TEAM = p.team_2
			
			script_names = scripts_option.get()
			if "disco" in script_names or "piqueserver.scripts.disco" in script_names:
				if p.disco:
					p.toggle_disco(False)
			return pro.on_map_change(p, map_)
		
		def get_mode_name(p): #server list
			return "SSFFADM"
	
	
	return SuperSmashFFADM_P, SuperSmashFFADM_C
