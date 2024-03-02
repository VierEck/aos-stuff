'''
packet-less extension for higher client position update rate. 


Authors: 
	VierEck.
'''


from time import monotonic as time
from twisted.internet.reactor import callLater
from piqueserver.commands import command
from pyspades.packet import register_packet_handler
from pyspades.contained import PositionData
from pyspades.constants import MAX_POSITION_RATE
from pyspades.player import check_nan


MIN_POS_RATE = 1/29
CHAT_INDICATOR_SUPPORT = "This server supports the PosUpgrade extension"
CHAT_INDICATOR_FAIL    = "PosUpgrade extension could not be detected"


def notification(c, msg):
	p = c.protocol
	p.irc_say(msg)
	print(msg)


def PosUpgrade_check(c):
	c.PosUpgrade_detect = 60
	def evaluate_detection():
		if c.PosUpgrade_detect < 1:
			c.PosUpgrade_supports = True
			notification(c, c.name + " supports PosUpgrade")
		else:
			if c.team.spectator:
				#player somehow ends up in spectator before detection ended.
				#so try to detect him again when he changes team.
				c.PosUpgrade_detect = None
			else:
				c.PosUpgrade_detect = False
				#if detection fails but client actually does support it, send indication
				#so that client stops sending pos at higher rate for their own good
				c.send_chat(CHAT_INDICATOR_FAIL)
	callLater(3, evaluate_detection)


@command("posupgrade")
def PosUpgrade_manual_check(c):
	print("test")
	if not c.PosUpgrade_supports:
		notification(c, c.name + " performs manual PosUpgrade check...")
		c.send_chat(CHAT_INDICATOR_SUPPORT)
		PosUpgrade_check(c)


def apply_script(pro, con, cfg):


	class PosUpgrade_C(con):
		PosUpgrade_supports          = False
		PosUpgrade_detect            = None
		PosUpgrade_last_pos_time     = 0
		PosUpgrade_last_src_pos_time = 0
		
		def on_join(c):
			#indicate gameproperty to client via chat
			c.send_chat(CHAT_INDICATOR_SUPPORT)
			return con.on_join(c)
		
		def on_spawn(c, pos):
			if not c.local and not c.PosUpgrade_supports and c.PosUpgrade_detect is None:
				PosUpgrade_check(c)
			return con.on_spawn(c, pos)
		
		def posupgrade_on_position_update(c):
			#source interface only fires every second and most scripts account for that.
			#to not disturb the existing relationship, this additional interface is introduced.
			pass 
		
		def posupgrade_on_position_unvalidated(c, pos):
			pass
		
		def posupgrade_check_speedhack(c, x, y, z):
			if not c.speedhack_detect:
				return True
			return c.check_speedhack(x, y, z) #i cant come up with anything else, better than nothing tho
		
		@register_packet_handler(PositionData)
		def on_position_update_recieved(c, pkt):
			if not c.PosUpgrade_supports:
				if c.PosUpgrade_detect:
					if c.PosUpgrade_last_pos_time + MAX_POSITION_RATE > time():
						if time() - c.PosUpgrade_last_pos_time < MIN_POS_RATE: 
							c.PosUpgrade_detect -= 1
					c.PosUpgrade_last_pos_time = time()
				return con.on_position_update_recieved(c, pkt)
			#hijack
			if c.PosUpgrade_last_src_pos_time + MAX_POSITION_RATE < time():
				c.PosUpgrade_last_src_pos_time = time()
				return con.on_position_update_recieved(c, pkt)
			if not c.hp or c.team.spectator or not c.world_object:
				return
			x, y, z = pkt.x, pkt.y, pkt.z
			if check_nan(x, y, z):
				c.on_hack_attempt('Invalid position data received')
				return
			if c.posupgrade_on_position_unvalidated((x, y, z)) is False:
				return
			if not c.posupgrade_check_speedhack(x, y, z):
				c.set_location()
				return
			if not c.freeze_animation:
				c.world_object.set_position(x, y, z)
				c.posupgrade_on_position_update()
			c.PosUpgrade_last_pos_time = time()
	
	
	return pro, PosUpgrade_C
