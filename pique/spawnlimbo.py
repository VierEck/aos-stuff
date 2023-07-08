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
from random import randrange
import enet


spawn_distance = 64


def send_notice_msg(c):
	spawn_time = c.spawn_time - time()
	if spawn_time < 0:
		spawn_time = 0
	notice_msg = ("respawn in %.f. left or right to switch between territories. forward to spawn" % spawn_time)
	c.send_chat_notice(notice_msg)


def limbo_plattform(c, action = 0):
	if action == 0:
		block_pkt = loaders.BlockAction()
		block_pkt.player_id = c.player_id
		block_pkt.value = DESTROY_BLOCK
		block_pkt.x, block_pkt.y, block_pkt.z = c.dead_pos
		block_pkt.z += 3
		c.send_contained(block_pkt)
		block_pkt.y -= 1
		c.send_contained(block_pkt)
	if action == 1:
		block_pkt = loaders.BlockAction()
		block_pkt.player_id = c.player_id
		block_pkt.value = BUILD_BLOCK
		block_pkt.x, block_pkt.y, block_pkt.z = c.dead_pos
		block_pkt.z += 3
		c.send_contained(block_pkt)
		block_pkt.y -= 1
		c.send_contained(block_pkt)

def limbo_orientation(c, entity):
	x, y, z = c.dead_pos
	ori = Vertex3(entity.x - x, entity.y - y, entity.z - z)
	ori /= ori.length()
	ori *= 1.5 #zoom effect
	ori_pkt = loaders.OrientationData()
	ori_pkt.x, ori_pkt.y, ori_pkt.z = ori.x, ori.y, ori.z
	c.send_contained(ori_pkt)


def fake_world_update(c):
	p = c.protocol
	if not len(p.players):
		return
	items = []
	highest_player_id = max(p.players)
	for i in range(highest_player_id + 1):
		position = orientation = (1.0, 1.0, 1.0)
		items.append((position, orientation))
	world_update = loaders.WorldUpdate()
	world_update.items = items[:highest_player_id+1]
	c.send_contained(world_update)


def send_saved_packets(c):
	for data in c.saved_loaders:
		packet = enet.Packet(bytes(data), enet.PACKET_FLAG_RELIABLE)
		c.peer.send(0, packet)
	c.saved_loaders = None


def rotate_dead_pos(c, dir):
	if c.current_entity_id is not None:
		c.dead_time = time()
		
		limbo_plattform(c)
	
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
		offset = 8
		if c.team.id == 1:
			offset = -8
		x, y, z = current_entity.x - offset, current_entity.y, current_entity.z - 8
		while p.map.get_solid(x, y, z):
			z -= 1
		c.dead_pos = x, y, z
		
		pos_pkt = loaders.PositionData()
		pos_pkt.x, pos_pkt.y, pos_pkt.z = c.dead_pos
		c.send_contained(pos_pkt)
		
		limbo_plattform(c, 1)
		limbo_orientation(c, current_entity)


async def spawn_limbo(c):
	p = c.protocol
	c.dead_time_start = c.dead_time = time()
	c.current_entity_id = 0
	while p.entities[c.current_entity_id].team != c.team:
		c.current_entity_id += 1
	first_entity = p.entities[c.current_entity_id]
	offset = 8
	if c.team.id == 1:
		offset = -8
	x, y, z = first_entity.x - offset, first_entity.y, first_entity.z - 8
	while p.map.get_solid(x, y, z):
		z -= 1
	c.dead_pos = x, y, z
	
	spawn_pkt = loaders.CreatePlayer()
	spawn_pkt.player_id = c.player_id
	spawn_pkt.team = c.team.id
	spawn_pkt.x, spawn_pkt.y, spawn_pkt.z = c.dead_pos
	spawn_pkt.weapon = c.weapon
	spawn_pkt.name = c.name
	c.send_contained(spawn_pkt)
	
	limbo_plattform(c, 1)
	limbo_orientation(c, first_entity)
	
	c.saved_loaders = []
	while True:
		if c.hp:
			break
		
		send_notice_msg(c)
		
		pos_pkt = loaders.PositionData()
		pos_pkt.x, pos_pkt.y, pos_pkt.z = c.dead_pos
		pos_pkt.z += 0.74
		c.send_contained(pos_pkt)
		
		if time() > c.dead_time + 5:
			rotate_dead_pos(c, 1)
			
		fake_world_update(c)
		
		await asyncio.sleep(1/10)
	c.spawn_limbo_loop.cancel()
	
	send_saved_packets(c)
	
	limbo_plattform(c)
	
	c.spawn_limbo_loop = asyncio.ensure_future(live_fog_transition(c))
	c.dead_pos = None
	c.dead_time = None
	c.dead_time_start = None
	c.current_entity_id = None


async def dead_fog_transition(c):
	p = c.protocol
	r, g, b = p.fog_color
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
	c.spawn_limbo_loop = asyncio.ensure_future(spawn_limbo(c))


async def live_fog_transition(c):
	p = c.protocol
	r, g, b = 255, 100, 100
	x, y, z = p.fog_color
	diff_r, diff_g, diff_b = 10, 10, 10
	if r > x:
		diff_r = -10
	if g > y:
		diff_g = -10
	if b > z:
		diff_b = -10
	while True:
		r += diff_r
		g += diff_g
		b += diff_b
		
		if max(r, x) - min(r, x) <= abs(diff_r):
			r = x
		if max(g, y) - min(g, y) <= abs(diff_g):
			g = y
		if max(b, z) - min(b, z) <= abs(diff_b):
			b = z
		
		fog_pkt = loaders.FogColor()
		fog_pkt.color = make_color(r, g, b)
		c.send_contained(fog_pkt)
		
		if r == x and g == y and b == z:
			break
		
		await asyncio.sleep(1/10)
	c.spawn_limbo_loop.cancel()
	c.spawn_limbo_loop = None


def apply_script(protocol, connection, config):
	
	class spawn_limbo_c(connection):
		dead_pos = None
		dead_time = None
		dead_time_start = None
		spawn_time = None
		current_entity_id = None
		allowed_to_spawn = True
		spawn_limbo_loop = None
		
		def on_kill(c, by, kill_type, grenade):
			entities = list(c.team.get_entities())
			if len(entities) < 1:
				return connection.on_kill(c, by, kill_type, grenade)

			p = c.protocol
			c.allowed_to_spawn = False
			c.spawn_time = time() + c.get_respawn_time()
			send_notice_msg(c)
			if c.spawn_limbo_loop is not None:
				c.spawn_limbo_loop.cancel()
			c.spawn_limbo_loop = asyncio.ensure_future(dead_fog_transition(c))
			return connection.on_kill(c, by, kill_type, grenade)
		
		def on_team_join(c, team):
			if c.world_object is not None:
				if not c.hp and c.team.id < 2:
					return False #dont allow switching while in spawn limbo
			return connection.on_team_join(c, team)
		
		@register_packet_handler(loaders.InputData)
		def on_input_data_recieved(c, contained: loaders.InputData):
			if not c.hp:
				if c.dead_pos is not None:
					p = c.protocol
					if contained.left:
						rotate_dead_pos(c, -1)
					elif contained.right:
						rotate_dead_pos(c, 1)
					elif c.allowed_to_spawn:
						if contained.jump or contained.up or contained.down:
							x, y, z = c.dead_pos
							dir = Vertex3(0, 0, 0)
							dir.x = randrange(-100, 100)
							dir.y = randrange(-100, 100)
							dir /= dir.length()
							dir *= spawn_distance
							x += dir.x
							y += dir.y
							z = 60
							while p.map.get_solid(x, y, z + 1):
								z -= 1
							pos = x, y, z
							c.spawn(pos)
			return connection.on_input_data_recieved(c, contained)
		
		def spawn(c, pos: None = None):
			if c.allowed_to_spawn:
				return connection.spawn(c, pos)
			else:
				c.allowed_to_spawn = True
	
	
	return protocol, spawn_limbo_c

