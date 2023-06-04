'''
LICENSE: GPL-3.0
author: VierEck.


complementory pique script for OpenSpades MapEditor. 
	https://github.com/VierEck/openspades/tree/map

this script changes protocol and game physics. 
this causes desync with normal clients making them incompatible. 
incompatible clients are automatically kicked.

this script is to be put as 1st in the script priority.
better yet dont include other scripts unrelated to the MapEditor 
to ensure everything working as supposed to. 

todo:
	fix ball and cylinder volume tool
	send "full" map data
		fix dirt block colors
	setmapobject tool
'''


from enum import IntEnum, auto
from piqueserver.config import config
from pyspades.bytes import ByteReader as reader, ByteWriter as writer
from pyspades.packet import register_packet, register_packet_handler
from pyspades.loaders import Loader
from pyspades import contained as loaders
from piqueserver.scheduler import Scheduler
from pyspades.constants import *
from pyspades.common import Vertex3, get_color
from pyspades import world
from piqueserver.commands import command
from twisted.logger import Logger as log
from twisted.internet import reactor
from pyspades.player import check_nan


mapeditor_config = config.section('MapEditor')

@command('max_volume', 'max_vol', admin_only=True)
def max_vol(self, val):
	#adjust max build volume ingame. 
	self.protocol.max_build_volume = int(val)


class volume_type(IntEnum):
	BlockSingle = 0
	BlockLine = auto()
	Box = auto()
	Ball = auto()
	Cylinder_x = auto()
	Cylinder_y = auto()
	Cylinder_z = auto()
	VOLUMETYPEMAX = auto()

class tool_type(IntEnum):
	Destroy	= 0
	Build = auto()
	Paint = auto()
	TextureBuild = auto() #not supported
	TexturePaint = auto() #not supported
	Move = auto()
	TOOLTYPEMAX = auto()


def create_block(self, x, y, z, color):
	#build block without the need for neighbor blocks
	map = self.protocol.map
	if map.is_valid_position(x, y, z):
		map.set_point(x, y, z, color)

def edit_volume(self, volume, tool, x1, y1, z1, x2, y2, z2, x3 = None, y3 = None, z3 = None):
	map = self.protocol.map
	if tool == tool_type.Move:
		if (x3 == None or y3 == None or z3 == None):
			return False
		x3 = x3 - x1
		y3 = y3 - y1
		z3 = z3 - z1
	
	if (x1 == x2 and y1 == y2 and z1 == z2) or volume == volume_type.BlockSingle:
		if tool == tool_type.Destroy:
			map.remove_point(x1, y1, z1)
		elif tool == tool_type.Build:
			create_block(self, x1, y1, z1, self.color)
		elif tool == tool_type.Paint:
			if map.get_solid(x1, y1, z1):
				create_block(self, x1, y1, z1)
		elif tool == tool_type.Move and allow:
			color = map.get_color(x, y, z)
			create_block(self, x + x3, y + y3, z + z3, color)
			map.remove_point(x, y, z)
		return True
	
	x, y = cx, cy = x1, y1
	z = z1
	xi = yi = zi = 1
	diff_x = x2 - x1
	diff_y = y2 - y1
	diff_z = z2 - z1
	check_x, check_y, check_z = diff_x, diff_y, diff_z
	if diff_x < 0:
		xi = -1
		check_x *= -1
	if diff_y < 0:
		yi = -1
		check_y *= -1
	if diff_z < 0:
		zi = -1
		check_y *= -1
	
	mx = my = mz = 0
	if volume > volume_type.Box:
		if (check_x < 3 and check_y < 3) or (check_y < 3 and check_z < 3) or (check_z < 3 and check_x < 3):
			volume = volume_type.Box
		elif check_x < 3:
			volume = volume_type.Cylinder_x
		elif check_y < 3:
			volume = volume_type.Cylinder_y
		elif check_z < 3:
			volume = volume_type.Cylinder_z
		
		diff_x *= 0.5
		diff_y *= 0.5
		diff_z *= 0.5
		mx, my, mz = x + diff_x, y + diff_y, z + diff_z
		diff_x **= 2
		diff_y **= 2
		diff_z **= 2
	
	while True:
		allow = True
		if volume == volume_type.Ball:
			if (((x - mx)**2 / diff_x) + ((y - my)**2 / diff_y) + ((z - mz)**2 / diff_z)) > 1.1:
				allow = False
		elif volume == volume_type.Cylinder_x:
			if (((y - my)**2 / diff_y) + ((z - mz)**2 / diff_z)) > 1.1:
				allow = False
		elif volume == volume_type.Cylinder_y:
			if (((x - mx)**2 / diff_x) + ((z - mz)**2 / diff_z)) > 1.1:
				allow = False
		elif volume == volume_type.Cylinder_z:
			if (((x - mx)**2 / diff_x) + ((y - my)**2 / diff_y)) > 1.1:
				allow = False
		
		if tool == tool_type.Destroy and allow:
			map.remove_point(x, y, z)
		elif tool == tool_type.Build and allow:
			create_block(self, x, y, z, self.color)
		elif tool == tool_type.Paint and allow:
			if map.get_solid(x, y, z):
				create_block(self, x, y, z, self.color)
		elif tool == tool_type.Move and allow:
			color = map.get_color(x, y, z)
			create_block(self, x + x3, y + y3, z + z3, color)
			map.remove_point(x, y, z)
			
		if x == x2 and y == y2 and z == z2:
			break
		
		if x != x2:
			x += xi
		elif y != y2:
			x = cx
			y += yi
		elif z != z2:
			x = cx
			y = cy
			z += zi
	return True
	
class BuildMode(Loader):
	id = 100

	def read(self, reader):
		return

	def write(self, writer):
		writer.writeByte(self.id, True)

register_packet(BuildMode)

@register_packet_handler(BuildMode)
def on_BuildMode(self, contained) -> None:
	self.bmode = True
	

class BlockVolume(Loader):
	id = 101

	def read(self, reader):
		self.player_id = reader.readByte(True)
		self.volume = reader.readByte(True)
		self.tool = reader.readByte(True)
		self.x1 = reader.readShort(True, False)
		self.y1 = reader.readShort(True, False)
		self.z1 = reader.readShort(True, False)
		self.x2 = reader.readShort(True, False)
		self.y2 = reader.readShort(True, False)
		self.z2 = reader.readShort(True, False)
		if self.tool == tool_type.Move:
			self.x3 = reader.readShort(True, False)
			self.y3 = reader.readShort(True, False)
			self.z3 = reader.readShort(True, False)

	def write(self, writer):
		writer.writeByte(self.id, True)
		writer.writeByte(self.player_id, True)
		writer.writeByte(self.volume, True)
		writer.writeByte(self.tool, True)
		writer.writeShort(self.x1, True, False)
		writer.writeShort(self.y1, True, False)
		writer.writeShort(self.z1, True, False)
		writer.writeShort(self.x2, True, False)
		writer.writeShort(self.y2, True, False)
		writer.writeShort(self.z2, True, False)
		if self.tool == tool_type.Move:
			writer.writeShort(self.x3, True, False)
			writer.writeShort(self.y3, True, False)
			writer.writeShort(self.z3, True, False)

register_packet(BlockVolume)

@register_packet_handler(BlockVolume)
def on_BlockVolume(self, contained: BlockVolume) -> None:
	world_object = self.world_object
	map = self.protocol.map
	
	player_id = contained.player_id
	if player_id != self.player_id:
		log.info("unusual behaviour: %s sent BlockVolume packet containing wrong player_id" % self.name)
	volume = contained.volume
	if volume >= volume_type.VOLUMETYPEMAX:
		return
	tool = contained.tool
	if tool >= tool_type.TOOLTYPEMAX:
		return
	x1 = contained.x1
	y1 = contained.y1
	z1 = contained.z1
	x2 = contained.x2
	y2 = contained.y2
	z2 = contained.z2
	if not map.is_valid_position(x1, y1, z1) and not map.is_valid_position(x2, y2, z2):
		return
	
	diff_x, diff_y, diff_z = (x2 - x1), (y2 - y1), (z2 - z1)
	if diff_x >= 0:
		diff_x += 1
	else:
		diff_x -= 1
	if diff_y >= 0:
		diff_y += 1
	else:
		diff_y -= 1
	if diff_z >= 0:
		diff_z += 1
	else:
		diff_z -= 1
	check_volume = diff_x * diff_y * diff_z
	if check_volume < 0:
		check_volume *= -1
	if check_volume > self.protocol.max_build_volume:
		return
	
	edit = False
	if tool == tool_type.Move:
		x3 = contained.x3
		y3 = contained.y3
		z3 = contained.z3
		if map.is_valid_position(x3, y3, z3):
			edit = edit_volume(self, volume, tool, x1, y1, z1, x2, y2, z2, x3, y3, z3)
	else:
		edit = edit_volume(self, volume, tool, x1, y1, z1, x2, y2, z2)
	
	if edit is False:
		return
	
	block_volume = BlockVolume()
	block_volume.player_id = self.player_id
	block_volume.volume = contained.volume
	block_volume.tool = contained.tool
	block_volume.x1 = x1
	block_volume.y1 = y1
	block_volume.z1 = z1
	block_volume.x2 = x2
	block_volume.y2 = y2
	block_volume.z2 = z2
	if block_volume.tool == tool_type.Move:
		block_volume.x3 = contained.x3
		block_volume.y3 = contained.y3
		block_volume.z3 = contained.z3
	self.protocol.broadcast_contained(block_volume, save=True)



def apply_script(protocol, connection, config):

	class mapeditor_c(connection):
		bmode = False
		builder_position = None
	
		def check_bmode(self):
			if not self.bmode:
				self.disconnect(ERROR_WRONG_VERSION)
				print("kicked %s. Client failed to send back BuildMode confirmation packet in time" % self.name)
		
		def on_team_join(self, team):
			build_mode = BuildMode()
			self.send_contained(build_mode)
			schedule = Scheduler(self.protocol)
			schedule.call_later(10, self.check_bmode)
			return connection.on_team_join(self, team)
		
			
		def spawn(self, pos: None = None) -> None:
			self.spawn_call = None
			if self.team is None:
				return
			spectator = self.team.spectator
			create_player = loaders.CreatePlayer()
			if pos is None:
				x, y, z = self.get_spawn_location()
				x += 0.5
				y += 0.5
				z -= 2.4
			else:
				x, y, z = pos
			if self.builder_position is not None:
				x, y, z = self.builder_position
			returned = self.on_spawn_location((x, y, z))
			if returned is not None:
				x, y, z = returned
			if self.world_object is not None:
				self.world_object.set_position(x, y, z, True)
			else:
				position = Vertex3(x, y, z)
				self.builder_position = position
				self.world_object = self.protocol.world.create_object(
					world.Character, position, None, self._on_fall)
			self.world_object.dead = False
			self.tool = BLOCK_TOOL
			self.refill(True)
			create_player.x = x
			create_player.y = y
			create_player.z = z
			create_player.weapon = self.weapon
			create_player.player_id = self.player_id
			create_player.name = self.name
			create_player.team = self.team.id
			if self.filter_visibility_data and not spectator:
				self.send_contained(create_player)
			else:
				self.protocol.broadcast_contained(create_player, save=True)
			self.on_spawn((x, y, z))
			set_tool = loaders.SetTool()
			set_tool.player_id = self.player_id
			set_tool.value = BLOCK_TOOL
			self.protocol.broadcast_contained(set_tool, save=True)
		
		
		@register_packet_handler(loaders.PositionData)
		def on_position_update_recieved(self, contained: loaders.PositionData) -> None:
			x, y, z = contained.x, contained.y, contained.z
			if check_nan(x, y, z):
				self.on_hack_attempt('Invalid position data received')
				return
			if self.team.spectator:
				self.builder_position = Vertex3(x, y, z)
			else:
				self.world_object.set_position(x, y, z)
			self.on_position_update()
			return
	
	
	class mapeditor_p(protocol):
		
		max_build_volume = mapeditor_config.option('max_build_volume', 100000).get()
		
		
		def update_network(self):
			if not len(self.players):
				return
			items = []
			highest_player_id = max(self.players)
			for i in range(highest_player_id + 1):
				position = orientation = None
				try:
					player = self.players[i]
					if (not player.filter_visibility_data and not player.team.spectator):
						world_object = player.world_object
						position = world_object.position.get()
						orientation = world_object.orientation.get()
					elif player.team.spectator and player.builder_position is not None:
						position = player.builder_position.get()
						orientation = player.world_object.orientation.get()
				except (KeyError, TypeError, AttributeError):
					pass
				if position is None:
					position = (0.0, 0.0, 0.0)
					orientation = (0.0, 0.0, 0.0)
				items.append((position, orientation))
			world_update = loaders.WorldUpdate()
			# we only want to send as many items of the player list as needed, so
			# we slice it off at the highest player id
			world_update.items = items[:highest_player_id+1]
			self.broadcast_contained(world_update, unsequenced=True)
	
	return mapeditor_p, mapeditor_c
