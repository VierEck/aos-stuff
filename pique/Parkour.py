'''
Parkour gamemode with checkpoint/waterbug fix and more.

No highscores. Highscore lists open to public master get undermined by cheaters. 
Even if u do implement a list for trusted players or players with an account, 
imo a Highscore simply needs to be verified via video evidence. 
At that point might aswell just host a list somewhere else like on a forum or on ur
website, not here. 


based on parkour.py by 1AmYF:
	https://github.com/1AmYF/aos-server-mods/blob/master/scripts/piqueserver/parkour.py

I just realized (10 min after uploading this script) that DryBytes parkour server code is open to public:
	https://github.com/FL-AoS/Parkour-Server

Authors:
	VierEck.
	1AmYF    (https://twitter.com/1AmYF)(https://github.com/1AmYF)
	DryByte  (https://github.com/DryByte)
'''


from os.path import join, exists
from math import floor
from time import strftime, monotonic as time
from piqueserver.config import config
from piqueserver.commands import command
from pyspades.constants import CTF_MODE, BLUE_BASE, SPADE_TOOL, BLOCK_TOOL, WEAPON_TOOL, GRENADE_TOOL
from pyspades.collision import vector_collision


HIDE_COORD  = (0, 0, 63)

parkour_cfg = config.section("parkour")
GOAL_CHECK_ON_UPS = parkour_cfg.option("goal_check_on_ups", default=True, cast=bool).get()


def tell_time(c, t, dc, msg):
	p = c.protocol
	mins = str(int(floor(t / 60)))
	if len(mins) == 1:
		mins = "0" + mins
	secs = str(int(t % 60))
	if len(secs) == 1:
		secs = "0" + secs
	mili = str(int((t - int(t)) / 0.001))
	display_time = mins + ":" + secs + ":" + mili
	msg = msg % (c.name, display_time, dc)
	p.broadcast_chat(msg)
	p.irc_say(msg)
	return display_time


@command("reset", "r")
def cmd_reset(c, gesture=None):
	if gesture is None:
		c.parkour_on_reset()
	else:
		if "spade" in gesture:
			c.parkour_reset_gesture = SPADE_TOOL
		elif "block" in gesture:
			c.parkour_reset_gesture = BLOCK_TOOL
		elif "weap" in gesture:
			c.parkour_reset_gesture = WEAPON_TOOL
		elif "nade" in gesture:
			c.parkour_reset_gesture = GRENADE_TOOL
		else:
			return "Invalid gesture name. Pls try one of these: spade, block, weapon, grenade"
		return "Set gesture to " + gesture


def apply_script(pro, con, cfg):
	
	
	class parkour_C(con):
		parkour_current_cp     = -1, -1, -1
		parkour_start_time     = None
		parkour_cp_time        = None
		parkour_death_count    = 0
		parkour_cp_death_count = 0
		parkour_reset_gesture  = None
		
		def parkour_check_pos(c):
			if c.parkour_current_cp[0] < -1.1:
				return
			if not c.world_object or c.world_object.dead:
				return
			if c.world_object.airborne or c.world_object.position.z > 59.5:
				return
			p = c.protocol
			for cp in p.parkour_checkpoints:
				if c.parkour_current_cp[0] >= cp[0]:
					break
				if c.world_object.position.x >= cp[0]:
					c.parkour_on_cp_reached(cp)
					break
			if GOAL_CHECK_ON_UPS:
				if vector_collision(c.world_object.position, c.team.base):
					c.parkour_on_complete()
		
		def parkour_on_cp_reached(c, cp):
			c.parkour_current_cp = cp
			old_cp_time          = c.parkour_cp_time
			c.parkour_cp_time    = time()
			tell_time(c, c.parkour_cp_time - old_cp_time, c.parkour_cp_death_count,  
				"%s, checkpoint split: %s mins, %s deaths")
		
		def parkour_on_complete(c):
			if c.parkour_start_time is not None:
				complete_time = time() - c.parkour_start_time #calc first above all else
				tell_time(c, complete_time, c.parkour_death_count, 
					"Congratulations, %s completed the parkour! Stats: %s mins, %s deaths")
			c.parkour_current_cp = -2, -2, -2
		
		def parkour_on_reset(c, spawn=True):
			c.parkour_current_cp  = -1, -1, -1
			c.parkour_start_time  = time()
			c.parkour_cp_time     = time()
			c.parkour_death_count = 0
			if spawn:
				c.spawn()
		
		def on_tool_set_attempt(c, tool):
			if c.parkour_reset_gesture is tool:
				c.parkour_on_reset()
				return False
			return con.on_tool_set_attempt(c, tool)
		
		def on_spawn_location(c, pos):
			p = c.protocol
			if c.parkour_current_cp[0] < -0.1:
				c.parkour_on_reset(False)
				return p.parkour_start
			return c.parkour_current_cp
		
		def on_kill(c, killer, type_, nade):
			p = c.protocol
			if c.team is p.team_1:
				c.parkour_death_count += 1
			return con.on_kill(c, killer, type_, nade)
		
		def on_refill(c):
			if not GOAL_CHECK_ON_UPS:
				c.parkour_on_complete()
			return con.on_refill(c)
		
		def on_disconnect(c):
			p = c.protocol
			if c.team is p.team_1 and c.parkour_current_cp[0] > -1.9:
				if c.parkour_start_time is not None:
					tell_time(c, time() - c.parkour_start_time, c.parkour_death_count, 
						"%s ragequit after %s mins, %s deaths")
			con.on_disconnect(c)
		
		def on_flag_take(c):
			return False
	
	
	class parkour_P(pro):
		game_mode = CTF_MODE
		parkour_checkpoints = []
		parkour_start       = None
		parkour_end         = None
		
		def on_world_update(p):
			for pl in p.team_1.get_players():
				pl.parkour_check_pos()
			return pro.on_world_update(p)
		
		def on_map_change(p, map):
			ext = p.map_info.extensions
			for must_have in ("parkour_start", "parkour_end"):
				if must_have not in ext:
					raise Exception("Missing parkour map metadata: %s" % must_have)
			p.parkour_start = ext["parkour_start"]
			p.parkour_end = ext["parkour_end"]
			if "parkour_checkpoints" in ext:
				p.parkour_checkpoints = ext["parkour_checkpoints"][::-1]
			p.green_team.locked = True
			p.balanced_teams    = 0
			p.building          = False
			p.fall_damage       = False
			return pro.on_map_change(p, map)
		
		def on_base_spawn(p, x, y, z, base, ent_id):
			if ent_id == BLUE_BASE:
				return p.parkour_end
			return HIDE_COORD

		def on_flag_spawn(p, x, y, z, flag, ent_id):
			return HIDE_COORD
	
	
	return parkour_P, parkour_C
