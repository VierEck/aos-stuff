'''
Shows player where exactly they respawn, which gives them 
a better chance to prepare and defend against spawncamping. 

config:
	[respawn_preview]
	preview_time     = 3.0  #at which countdowned time to preview spawn location. 
	                        #set to 100 or any high number to preview spawn location
	                        #throughout entire respawn time.  
	min_respawn_time = 0.5  #stop preview when respawn time is smaller than this. 


Authors:
	VierEck. 
'''


from piqueserver.config import config as cfg
from twisted.internet.reactor import callLater
from pyspades.contained import PositionData


respawn_preview_cfg = cfg.section("respawn_preview")
PREVIEW_TIME        = respawn_preview_cfg.option("preview_time", default=3.0, cast=float).get()
MIN_RESPAWN_TIME    = respawn_preview_cfg.option("min_respawn_time", default=0.5, cast=float).get()


def apply_script(pro, con, config_):
	
	class RespawnPreview_C(con):
		
		def RespawnPreview_send_preview(c, pos) -> None:
			if not c.team.spectator: #spectator dont need respawn preview
				pos_pkt = PositionData()
				pos_pkt.x, pos_pkt.y, pos_pkt.z = pos
				c.send_contained(pos_pkt)
		
		def respawn(c) -> None:
			if c.spawn_call is None:
				x, y, z = c.get_spawn_location()
				#from spawn(c). spawn location on center and above of block
				x += 0.5
				y += 0.5
				z -= 2.4
				pos = x, y, z
				r_time = c.get_respawn_time()
				p_time = r_time - PREVIEW_TIME
				if r_time >= MIN_RESPAWN_TIME:
					if p_time <= 0: 
						c.RespawnPreview_send_preview(pos)
					else:
						callLater(p_time, c.RespawnPreview_send_preview, pos)
				c.spawn_call = callLater(r_time, c.spawn, pos)
			return con.respawn(c)
	
	return pro, RespawnPreview_C
