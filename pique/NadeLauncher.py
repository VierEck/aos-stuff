'''
explosion on impact with block

this is a barebones supplementory script which doesnt work on its own. modify or create a script extending on it.
player.has_NadeLauncher must be set to True to if u want a player to be able to use the NadeLauncher. 

a recreation of the nadelauncher from Teaboy's server. (he didnt release his script or if he did than im not aware of it)
some parts of this code r from nadelauncher_ohnoez.py (maintainer: Wizardian):
	https://github.com/aloha-pk/spades-public/blob/master/legacy/scripts/nadelauncher_ohnoez.py
some parts of this code r from airstrike2.py by hompy:
	https://github.com/aloha-pk/piqueserver/blob/master/piqueserver/scripts/airstrike2.py

Authors: 
	VierEck.
'''


from time import monotonic as time
from pyspades.contained import GrenadePacket
from pyspades.constants import UPDATE_FREQUENCY, WEAPON_TOOL
from pyspades.world import Grenade


#
def apply_script(pro, con, cfg):

	class NadeLauncher_C(con):
		has_NadeLauncher       = False
		NadeLauncher_last_time = 0.0
		NadeLauncher_velocity  = 1.0
		
		def on_shoot_set(c, fire):
			if c.has_NadeLauncher and fire and c.tool == WEAPON_TOOL:
				if time() > c.NadeLauncher_last_time + c.weapon_object.delay:
					p = c.protocol
					c.NadeLauncher_last_time = time()
					
					pos  = c.world_object.position
					vel  = c.world_object.orientation
					vel *= c.NadeLauncher_velocity
					
					nade = p.world.create_object(Grenade, 0.0, pos, None, vel, c.grenade_exploded)
					nade.team = c.team
					
					collision = nade.get_next_collision(UPDATE_FREQUENCY)
					if not collision:
						return
					eta, x, y, z = collision
					nade.fuse = eta
						
					pkt = GrenadePacket()
					pkt.player_id = c.player_id
					pkt.value     = nade.fuse
					pkt.position  = pos.get()
					pkt.velocity  = vel.get()
					p.broadcast_contained(pkt)
					
			return con.on_shoot_set(c, fire)
	
	
	return pro, NadeLauncher_C
