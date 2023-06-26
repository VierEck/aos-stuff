'''
author: VierEck.

SpawnLimbo.

limbo state for TC gamemode. players can choose a tent to spawn into.
'''

from pyspades.constants import BUILD_BLOCK, DESTROY_BLOCK
from pyspades.common import Vertex3, make_color
from pyspades import contained as loaders
from pyspades import world
from pyspades.packet import register_packet_handler
from time import time
import asyncio


def rotate_dead_pos(c, dir):
	if c.current_entity_id is not None:
		c.dead_time = time()
		
		block_pkt = loaders.BlockAction()
		block_pkt.player_id = 35
		block_pkt.value = DESTROY_BLOCK
		block_pkt.x, block_pkt.y, block_pkt.z = c.dead_pos
		block_pkt.z += 3
		c.send_contained(block_pkt)
		block_pkt.y -= 1
		c.send_contained(block_pkt)
	
		p = c.protocol
		c.current_entity_id += dir
		if c.current_entity_id >= len(p.entities):
			c.current_entity_id = 0
		if c.current_entity_id < 0:
			c.current_entity_id = len(p.entities) - 1
		while p.entities[c.current_entity_id].team != c.team:
			c.current_entity_id += dir
			if c.current_entity_id >= len(p.entities):
				c.current_entity_id = 0
		current_entity = p.entities[c.current_entity_id]
		c.dead_pos = current_entity.x - 8, current_entity.y, current_entity.z - 8
		
		pos_pkt = loaders.PositionData()
		pos_pkt.x, pos_pkt.y, pos_pkt.z = c.dead_pos
		c.send_contained(pos_pkt)
		
		ori_x, ori_y, ori_z = 1.5, 0, 1.5
		ori_pkt = loaders.OrientationData()
		ori_pkt.x, ori_pkt.y, ori_pkt.z = ori_x, ori_y, ori_z
		c.send_contained(ori_pkt)
		
		block_pkt = loaders.BlockAction()
		block_pkt.player_id = 35
		block_pkt.value = BUILD_BLOCK
		block_pkt.x, block_pkt.y, block_pkt.z = c.dead_pos
		block_pkt.z += 3
		c.send_contained(block_pkt)
		block_pkt.y -= 1
		c.send_contained(block_pkt)


async def spawn_limbo(c):
	p = c.protocol
	c.dead_time_start = c.dead_time = time()
	c.current_entity_id = 0
	while p.entities[c.current_entity_id].team != c.team:
		c.current_entity_id += 1
	first_entity = p.entities[c.current_entity_id]
	c.dead_pos = first_entity.x - 8, first_entity.y, first_entity.z - 8
	
	spawn_pkt = loaders.CreatePlayer()
	spawn_pkt.player_id = c.player_id
	spawn_pkt.team = c.team.id
	spawn_pkt.x, spawn_pkt.y, spawn_pkt.z = c.dead_pos
	spawn_pkt.weapon = c.weapon
	spawn_pkt.name = c.name
	c.send_contained(spawn_pkt)
	
	block_pkt = loaders.BlockAction()
	block_pkt.player_id = 35
	block_pkt.value = BUILD_BLOCK
	block_pkt.x, block_pkt.y, block_pkt.z = c.dead_pos
	block_pkt.z += 3
	c.send_contained(block_pkt)
	block_pkt.y -= 1
	c.send_contained(block_pkt)
	
	ori_x, ori_y, ori_z = 1.5, 0, 1.5
	ori_pkt = loaders.OrientationData()
	ori_pkt.x, ori_pkt.y, ori_pkt.z = ori_x, ori_y, ori_z
	c.send_contained(ori_pkt)
	
	while True:
		if c.hp:
			break
		
		pos_pkt = loaders.PositionData()
		pos_pkt.x, pos_pkt.y, pos_pkt.z = c.dead_pos
		pos_pkt.z += 1
		c.send_contained(pos_pkt)
		
		if time() > c.dead_time + 5:
			rotate_dead_pos(c, 1)
			
		await asyncio.sleep(1/10)
	c.spawn_limbo_loop.cancel()
	
	block_pkt = loaders.BlockAction()
	block_pkt.player_id = 35
	block_pkt.value = DESTROY_BLOCK
	block_pkt.x, block_pkt.y, block_pkt.z = c.dead_pos
	block_pkt.z += 3
	c.send_contained(block_pkt)
	block_pkt.y -= 1
	c.send_contained(block_pkt)
	
	c.spawn_limbo_loop = None
	c.dead_pos = None
	c.dead_time = None
	c.dead_time_start = None
	c.current_entity_id = None


async def fog_transition(c):
	r, g, b = c.dead_fog
	while True:
		r += 10
		g -= 10
		b -= 10
		if r > 255:
			r = 255
		if g < 100:
			g = 100
		if b < 100:
			b = 100
		
		fog_pkt = loaders.FogColor()
		fog_pkt.color = make_color(r, g, b)
		c.send_contained(fog_pkt)
		
		if r >= 255 and g <= 100 and b <= 100:
			break
		
		await asyncio.sleep(1/10)
	c.spawn_limbo_loop.cancel()
	c.dead_fog = None
	c.spawn_limbo_loop = asyncio.ensure_future(spawn_limbo(c))


def apply_script(protocol, connection, config):
	
	class spawn_limbo_c(connection):
		dead_fog = None
		dead_pos = None
		dead_time = None
		dead_time_start = None
		current_entity_id = None
		allowed_to_spawn = True
		spawn_limbo_loop = None
		
		def on_kill(c, by, kill_type, grenade):
			p = c.protocol
			c.dead_fog = p.fog_color
			c.allowed_to_spawn = False
			c.send_chat_warning("you are dead. choose a territory to spawn into.")
			c.spawn_limbo_loop = asyncio.ensure_future(fog_transition(c))
			return connection.on_kill(c, by, kill_type, grenade)
		
		@register_packet_handler(loaders.InputData)
		def on_input_data_recieved(c, contained: loaders.InputData):
			if not c.hp:
				if c.dead_pos is not None:
					p = c.protocol
					if contained.left:
						rotate_dead_pos(c, -1)
					elif contained.right:
						rotate_dead_pos(c, 1)
					elif time() >= c.dead_time_start + p.respawn_time:
						if contained.jump or contained.up or contained.down:
							x, y, z = c.dead_pos
							z += 8
							pos = x, y, z
							c.spawn(pos)
			return connection.on_input_data_recieved(c, contained)
		
		def spawn(c, pos: None = None):
			if c.allowed_to_spawn:
				p = c.protocol
				fog_pkt = loaders.FogColor()
				fog_pkt.color = make_color(*p.fog_color)
				c.send_contained(fog_pkt)
				return connection.spawn(c, pos)
			else:
				c.allowed_to_spawn = True
			
	
	
	return protocol, spawn_limbo_c

