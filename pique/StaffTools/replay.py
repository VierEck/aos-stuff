'''
record gameplay on your server. base script


this script is based on aos_replay by BR:
	https://github.com/BR-/aos_replay

Authors:
	VierEck.
	DryByte  (https://github.com/DryByte)
	BR       (https://github.com/BR-)
'''


from os import path, mkdir
from datetime import datetime
from time import strftime, monotonic as time
from enet import Address
from struct import pack
from twisted.internet.reactor import callLater
from twisted.logger import Logger
from piqueserver.commands import command
from piqueserver.config import config
from pyspades.contained import MapStart, MapChunk, WorldUpdate, ExistingPlayer, ChatMessage
from pyspades.packet import load_server_packet
from pyspades.bytes import ByteReader
from pyspades.constants import GAME_VERSION
from pyspades.common import make_color
from pyspades.player import ServerConnection


AOS_REPLAY_VERSION = 1
USE_GZIP = False

replay_cfg = config.section("replay")
REPLAY_DIR   = replay_cfg.option("directory"   , "demos").get()
PARALLEL_UPS = replay_cfg.option("parallel_ups", 0).get() #0 for disable
MIN_PLAYERS  = replay_cfg.option("min_players" , 2).get()
MAX_LEN      = replay_cfg.option("max_length"  , 60).get() #in min

log = Logger()
REPLAY_DIR = path.join(config.config_dir, REPLAY_DIR)
MAX_LEN *= 60


if USE_GZIP:
	from gzip import open
if PARALLEL_UPS:
	from asyncio import ensure_future, sleep


@command("replay", admin_only=True)
def replay_cmd(c, *args):
	if len(args) < 1:
		return "No arguments given"
	p = c.protocol
	notif = "Invalid argument"
	val   = args[0].lower()
	t     = None if len(args) <= 1 else max(1, min(MAX_LEN, int(args[1]) * 60)) #in minutes
	if t and p.replay_end_call is not None:
		p.replay_end_call.cancel()
		p.replay_end_call = None
	if val in ["start", "on"]:
		if len(p.players) < 1:
			return "No players"
		p.replay_start(None, t)
		notif = "Demo started. "
		if len(p.players) < MIN_PLAYERS:
			notif += "Warning, below minimum player count. "
	elif val in ["end", "off"] and not t:
		notif = "Demo ended. " if p.replay_file else "There is no active demo already."
		p.replay_end()
	if t and p.replay_file:
		if notif == "Invalid argument":
			notif = ""
		notif += "Ending demo in " + str(int(t / 60)) + "min"
		def end():
			notif_later = "demo must have ended now after " + str(int(t / 60)) + "min"
			if not c.disconnected:
				c.send_chat(notif_later)
				if c.name is not None:
					notif_later = c.name + ", " + notif_later
		callLater(t, end)
	return notif


def get_new_file(p, fn):
	if not path.exists(REPLAY_DIR):
		mkdir(REPLAY_DIR)
	fn = fn.replace("{server}", p.name)
	fn = fn.replace("{map}", p.map_info.rot_info.name)
	fn = fn.replace("{time}", datetime.now().strftime("%Y-%m-%d_%H-%M-%S_"))
	fn += ".demo"
	if USE_GZIP:
		fn += ".gz"
	fn = path.join(REPLAY_DIR, fn)
	if path.exists(fn):
		log.info("WARNING: demo file with same name already exists: " + fn)
		i = 0
		while path.exists(fn):
			if i >= 100:
				return False
			fn = (fn if i == 0 else fn[:-2]) + "{:2d}".format(i)
		log.info("         instead opening new file: " + fn)
	return open(fn, "wb")

def set_new_id(p):
	if p.replay_id <= 31:
		p.player_ids.put_back(p.replay_id)
	p.replay_id = 33 if len(p.connections) > 31 else p.player_ids.pop()

def signature(p):
	#this is absolutely necessary. its crucial to the workings of this script 100%
	chat_pkt = ChatMessage()
	chat_pkt.chat_type = 2
	chat_pkt.player_id = 33
	chat_pkt.value = "recorded with replay.py by VierEck."
	p.replay_write(chat_pkt)

class tempAckCatcher_C(ServerConnection):
	
	class LocalPeer:
		address = Address(str.encode("localhost"), 0)
		roundTripTime = 0.0
		
		def __init__(self, protocol):
			self.p = protocol

		def send(self, channel, pkt):
			self.p.replay_write(load_server_packet(ByteReader(pkt.data)))

		def reset(self):
			pass
	
	def __init__(c, p, pl_id):
		ServerConnection.__init__(c, p, c.LocalPeer(p))
		c.player_id = pl_id
		c._connection_ack()
		for pl in p.players.values():
			if pl.name is not None:
				ex_pkt = ExistingPlayer()
				ex_pkt.name      = pl.name
				ex_pkt.player_id = pl.player_id
				ex_pkt.tool      = pl.tool or 0
				ex_pkt.weapon    = pl.weapon
				ex_pkt.kills     = pl.kills
				ex_pkt.team      = pl.team.id
				ex_pkt.color     = make_color(*pl.color)
				c.saved_loaders.append(ex_pkt.generate())
	
	def on_join(c):
		p = c.protocol
		p.replay_ack_catcher = None #job is done
	
	def send_contained(c, pkt, seq=False):
		p = c.protocol
		if c.saved_loaders is None or pkt.id in (MapChunk.id, MapStart.id):
			p.replay_write(pkt)
		else:
			c.saved_loaders.append(pkt.generate())
		return False


def apply_script(pro, con, cfg):
	
	
	class replay_C(con):
		
		def on_disconnect(c):
			p = c.protocol
			if len(p.players) - 1 < MIN_PLAYERS:
				p.replay_end()
			return con.on_disconnect(c)
		
		def _connection_ack(c):
			p = c.protocol
			if p.replay_file and p.replay_id != 33 and len(p.connections) > 31:
				chat_pkt = ChatMessage()
				chat_pkt.chat_type = 2
				chat_pkt.player_id = 33
				chat_pkt.value = "Your ID is going to change to 33, if your client doesnt support it please use https://github.com/VierEck/openspades"
				p.write_pack(chat_pkt)
				
				set_new_id(p)
				p.replay_ack_catcher = tempAckCatcher_C(p, p.replay_id)
			return con._connection_ack(c)
	
	
	class replay_P(pro):
		replay_file        = None
		replay_start_time  = None
		replay_loop_task   = None
		replay_end_call    = None
		replay_ack_catcher = None
		replay_id          = 0
		
		def replay_start(p, fn=None, t=None):
			p.replay_end()
			if len(p.players) < 1:
				return False
			nf = get_new_file(p, fn or "{time}_{server}_{map}")
			if nf is False:
				return False
			p.replay_file = nf
			p.replay_file.write(pack("BB", AOS_REPLAY_VERSION, GAME_VERSION))
			p.replay_start_time = time()
			set_new_id(p)
			p.replay_ack_catcher = tempAckCatcher_C(p, p.replay_id)
			if PARALLEL_UPS and p.replay_loop_task is None:
				p.replay_loop_task = ensure_future(p.replay_loop_ups())
			if p.replay_end_call is not None:
				p.replay_end_call.cancel()
			p.replay_end_call = callLater(t or MAX_LEN, p.replay_end, True)
			return True
		
		def replay_end(p, is_later = False):
			if not is_later and p.replay_end_call is not None:
				p.replay_end_call.cancel()
			p.replay_end_call = None
			if p.replay_loop_task:
				p.replay_loop_task.cancel()
				p.replay_loop_task = None
			if p.replay_file:
				p.replay_file.close()
				p.replay_file = None
				log.info("Demo ended")
			p.replay_start_time = None
		
		async def replay_loop_ups(p):
			while p.replay_file:
				if not len(p.players) or p.replay_ack_catcher is not None:
					continue
				items = []
				highest_player_id = max(p.players)
				for i in range(highest_player_id + 1):
					pos = ori = None
					try:
						pl = p.players[i]
						if not (pl.filter_visibility_data and pl.team.spectator):
							w_obj = pl.world_object
							pos = w_obj.position.get()
							ori = w_obj.orientation.get()
					except (KeyError, TypeError, AttributeError):
						pass
					if pos is None:
						pos = (0.0, 0.0, 0.0)
						ori = (0.0, 0.0, 0.0)
					items.append((pos, ori))
				ups_pkt = loaders.WorldUpdate()
				ups_pkt.items = items[:highest_player_id+1]
				p.replay_write(ups_pkt)
				sleep(1/PARALLEL_UPS)
		
		def replay_write(p, pkt):
			data = bytes(pkt.generate())
			p.replay_file.write(pack("fH", time() - p.replay_start_time, len(data)))
			p.replay_file.write(data)
		
		def broadcast_contained(p, pkt, unsequenced=False, sender=None, team=None, save=False, rule=None):
			if p.replay_file is not None and (not PARALLEL_UPS or pkt.id != WorldUpdate.id):
				if not p.replay_ack_catcher:
					p.replay_write(pkt)
				elif save:
					p.replay_ack_catcher.send_contained(pkt)
			return pro.broadcast_contained(p, pkt, unsequenced, sender, team, save, rule)
		
		def update_network(p):
			if p.replay_ack_catcher is not None and p.replay_ack_catcher.map_data is not None:
				p.replay_ack_catcher.continue_map_transfer()
			return pro.update_network(p)
		
		def on_map_leave(p):
			p.replay_end()
			return pro.on_map_leave(p)
	
	return replay_P, replay_C
