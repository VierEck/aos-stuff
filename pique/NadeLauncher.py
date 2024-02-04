'''
explosion on impact with block

this is a barebones supplementory script which doesnt work on its own. modify or create a script extending on it.
to give player the nadelauncher append them to protocol.NadeLauncher_list

a recreation of the nadelauncher from Teaboy's pysnip server.
	https://github.com/TeaBoyy/AoS_TeaBoy_Server/blob/main/scripts/grenade_launchers.py
some parts of this code r from nadelauncher_ohnoez.py (maintainer: Wizardian):
	https://github.com/aloha-pk/spades-public/blob/master/legacy/scripts/nadelauncher_ohnoez.py
some parts of this code r from airstrike2.py by hompy:
	https://github.com/aloha-pk/piqueserver/blob/master/piqueserver/scripts/airstrike2.py

Authors: 
	VierEck.
	TeaBoy
	hompy
	Wizardian
'''


import asyncio
from time import monotonic as time
from pyspades.packet import register_packet_handler
from pyspades.contained import GrenadePacket, WeaponInput
from pyspades.constants import UPDATE_FREQUENCY, WEAPON_TOOL
from pyspades.world import Grenade


#
def apply_script(pro, con, cfg):

	class NadeLauncher_C(con):
		NadeLauncher_last_time = 0.0
		NadeLauncher_speed     = 1.0
		
		def on_spawn(c, pos):
			c.protocol.NadeLauncher_list.append(c)
			return con.on_spawn(c, pos)
		
		def NadeLauncher_on_nade_exploded(c, nade):
			c.grenade_exploded(nade)
		
		def NadeLauncher_shoot(c):
			p = c.protocol
			c.NadeLauncher_last_time = time()
			
			pos  = c.world_object.position
			vel  = c.world_object.orientation
			vel *= c.NadeLauncher_speed
			
			nade = p.world.create_object(Grenade, 0.0, pos, None, vel, c.NadeLauncher_on_nade_exploded)
			nade.team = c.team
			
			collision = nade.get_next_collision(UPDATE_FREQUENCY)
			if not collision:
				return
			eta, x, y, z = collision
			nade.fuse = eta
				
			nade_pkt = GrenadePacket()
			nade_pkt.player_id = c.player_id
			nade_pkt.value     = nade.fuse
			nade_pkt.position  = pos.get()
			nade_pkt.velocity  = vel.get()
			p.broadcast_contained(nade_pkt)
	
	
	class NadeLauncher_P(pro):
		
		NadeLauncher_list = []
		NadeLauncher_bullet_loop_task = None
		async def NadeLauncher_bullet_loop(p):
			while True:
				await asyncio.sleep(0.05) #20 ups
				for pl in p.NadeLauncher_list:
					if pl.world_object and not pl.world_object.dead and pl.tool == WEAPON_TOOL:
						if pl.world_object.primary_fire and time() > pl.NadeLauncher_last_time + pl.weapon_object.delay:
							pl.NadeLauncher_shoot()
		
		def on_map_change(p, map_):
			if p.NadeLauncher_bullet_loop_task is None:
				p.NadeLauncher_bullet_loop_task = asyncio.ensure_future(p.NadeLauncher_bullet_loop())
			return pro.on_map_change(p, map_)
		
		def on_map_leave(p):
			if p.NadeLauncher_bullet_loop_task is not None:
				p.NadeLauncher_bullet_loop_task.cancel()
				p.NadeLauncher_bullet_loop_task = None
			return pro.on_map_leave(p)
	
	
	return NadeLauncher_P, NadeLauncher_C
