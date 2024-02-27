'''
Extension packet for higher client position update rate. 


Authors: 
	VierEck.
'''


from math import isnan, isinf
from time import monotonic as time
from piqueserver.config import config
from pyspades.packet import register_packet_handler
from pyspades.contained import ProtocolExtensionInfo, VersionResponse, PositionData
from pyspades.constants import MAX_POSITION_RATE


POSUPGRADE_EXT_ID  = 102 #hopefully this one isnt already taken
POSUPGRADE_EXT_VER = 1
POSUPGRADE_EXT = POSUPGRADE_EXT_ID, POSUPGRADE_EXT_VER


posext_cfg = config.section("PositionUpgrade")
#lets say u host a private server with friends. 
#u trust everyone so u dont need speedhack detection
TRUST = posext_cfg.option("trust", False).get()


def notification(c, msg):
	p = c.protocol
	p.irc_say(msg)


def check_nan(*vals) -> bool: 
	#copy paste from aloha source
	#suggestion: check_nan needs an interface. how about putting it in protocol?
    for val in vals:
        if isnan(val) or isinf(val):
            return True
    return False


def apply_script(pro, con, cfg):


	class PosUpgrade_C(con):
		PosUpgrade_supports             = False
		PosUpgrade_last_pos_update_old  = 0
		
		def posupgrade_on_position_update(c):
			#source interface only fires every second and most scripts account for that.
			#to not disturb the existing relationship, this additional interface is needed.
			pass 
		
		def posupgrade_check_speedhack(c, x, y, z):
			if TRUST:
				return True
			#TODO: check speedhack
			return True
		
		@register_packet_handler(PositionData)
		def on_position_update_recieved(c, pkt):
			if not c.PosUpgrade_supports:
				return con.on_position_update_recieved(c, pkt)
			#hijack
			if c.PosUpgrade_last_pos_update_old + MAX_POSITION_RATE < time():
				c.PosUpgrade_last_pos_update_old = time()
				#handles intel/tent stuff and on_position_update()
				con.on_position_update_recieved(c, pkt)
			else:
				x, y, z = pkt.x, pkt.y, pkt.z
				if check_nan(x, y, z):
					c.on_hack_attempt('Invalid position data received')
					return
				if not c.posupgrade_check_speedhack(x, y, z):
					return
				if not c.freeze_animation: #when is freeze animation ever used?
					c.world_object.set_position(x, y, z)
					c.posupgrade_on_position_update()
		
		@register_packet_handler(VersionResponse)
		def on_version_info_recieved(c, pkt):
			if not (pkt.client == 'o' and pkt.version <= (0, 1, 3)):
				ext_pkt = ProtocolExtensionInfo()
				ext_pkt.extensions = [ POSUPGRADE_EXT ]
				c.send_contained(ext_pkt)
			return con.on_version_info_recieved(c, pkt)
		
		@register_packet_handler(ProtocolExtensionInfo)
		def on_ext_info_received(c, pkt):
			if POSUPGRADE_EXT in pkt.extensions:
				c.PosUpgrade_supports = True
				notification(c, c.name + " supports Position Upgrade Extension")
			return con.on_ext_info_received(c, pkt)
	
	
	return pro, PosUpgrade_C