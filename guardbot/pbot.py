'''
portions of this file are from BR's original script: https://github.com/BR-/aos_replay

PlaybackBot. 
pick a demo and play it. a sort of server is created from which u can connect to and operate from it
using ur aos client. make sure to change ur password and login within the login time. 

compatible with openspades. maybe compatible with betterspades. definetely not compatible with voxlap. 

commands:
	/login password
	/play folder 00-00-00 0000-00-00    -> doesnt need exact time and date, allthough advised to be as precise as possible. 
	              H  M  S    Y  M  D       will pick most recent demo occured before specified time and date. 
	/play folder 00-00-00               -> plays demo before the specified time with most recent possible date in folder. 
	/play folder                        -> plays most recent demo in folder
	/play                               -> plays most recent demo
	/yes                                -> confirm /play command
	/replay                             -> restart current demo. when at home replay last viewed demo
	
	
author: VierEck.
''' 

import toml
import os
import time
import struct
import enet
from datetime import datetime

try:
	config = toml.load('config.toml')
except:
	print('abort. no config.toml or invalid config content')
	import sys
	sys.exit(1)

for cfg in config["playback"]:
	PASSWORD        = cfg['password']
	LOGIN_TIME      = cfg["login_time"]
	KICK_AFK        = cfg["kick_afk"]
	MAX_CONNECTIONS = cfg["max_connections"]
	LOGIN_ATTEMPT   = cfg["login_attempt"]
	PORT            = cfg["port"]
	HOME            = cfg["home"]

FILE_VERSION = 1
AOS_VERSION = 3

path = os.path.dirname(__file__)
test = False
testfile = "test.demo" #rename a working demo to this


def search_demo(cl, chat):
	args = chat.split()
	if len(args) == 3:
		folder = os.path.join(path, args[0])
		date_time = args[1] + "-" + args[2]
	elif len(args) == 2:
		folder = os.path.join(path, args[0])
		date_time = datetime.now().strftime('%Y-%m-%d') + "-" + args[1]
	elif len(args) == 1:
		folder = os.path.join(path, args[0])
		date_time = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
	elif len(args) < 1:
		folder = None
		date_time = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
	if len(args) > 0 and not os.path.exists(folder):
		cl.send_chat("folder " + args[0] + " not found")
		return
	if folder is None:
		import pathlib
		demos = []
		for folders in os.listdir(path):
			if os.path.isdir(os.path.join(path, folders)):
				for demo in os.listdir(folders):
					demos.append(folders + "/" + demo)
	else:
		demos = os.listdir(folder)
	demos.append(date_time)
	demos.sort()
	i = demos.index(date_time)
	try:
		cl.demo = os.path.join(folder, demos[i-1])
	except:
		cl.demo = os.path.join(path, demos[i-1])
	cl.send_chat("found " + demos[i-1])
	cl.send_chat("continue?")


def handle_command(cl, chat):
	chat = chat.lower()
	if chat == "test" and test: #if test is enabled anyone could start a test run so be careful with this
		cl.start_demo(testfile)
		return
		
	if chat[:6] == "login ":
		msg = cl.name + " failed to login"
		if chat[6:] == PASSWORD:
			cl.login = True
			msg = cl.name + " logged in"
			cl.send_chat("you logged in")
		else:
			cl.login_attempt += 1
			if cl.login_attempt >= LOGIN_ATTEMPT:
				cl.peer.disconnect(0)
				msg = cl.name + " kicked. too many failed login attempts"
				cl.fh.close()
				del clients[cl.peer.data]
			else:
				cl.send_chat("attempts left: %.f" % (LOGIN_ATTEMPT - cl.login_attempt))
		print(msg)
		return
	
	if not cl.login:
		cl.send_chat("login to use commands")
		return
	if chat == "yes" or chat == "y":
		if cl.demo is not None:
			cl.start_demo(cl.demo)
			cl.demo = None
		else:
			cl.send_chat("no demo selected")
		return
	if chat[:4] == "play":
		search_demo(cl, chat[5:])
		return
	if chat == "replay":
		cl.start_demo(cl.saved_fh)
		return
	
	if cl.at_home:
		cl.send_chat("either unkown command or command cant be used at home")
		return
	if chat == "home":
		cl.sending_home = True
		cl.start_demo(HOME)
		return
	if chat == "pause" and cl.pause_time == 0:
		cl.pause_time = time.time()
		for i in range(32):
			pkt = struct.pack("bbb", 3, i, 0) #input data
			event.peer.send(0, enet.Packet(pkt, enet.PACKET_FLAG_RELIABLE))
			pkt = struct.pack("bbb", 4, i, 0) #weapon data
			event.peer.send(0, enet.Packet(pkt, enet.PACKET_FLAG_RELIABLE))
		return
	if chat == "unpause" and cl.pause_time > 0:
		cl.start_time += time.time() - cl.pause_time
		cl.pause_time = 0
		for i in range(32):
			pkt = struct.pack("bbb", 3, i, cl.playerinfo[i][0]) #input data
			event.peer.send(0, enet.Packet(pkt, enet.PACKET_FLAG_RELIABLE))
			pkt = struct.pack("bbb", 4, i, cl.playerinfo[i][1]) #weapon data
			event.peer.send(0, enet.Packet(pkt, enet.PACKET_FLAG_RELIABLE))
		return
	if chat[:3] == "ff ":
		try:
			skip = int(chat[3:])
		except:
			pass
		else:
			cl.start_time = cl.start_time - skip
		return
	if chat == "time":
		if cl.spam_time is None:
			cl.spam_time = 0
		else:
			cl.spam_time = None
		return


class Client(object):
	def __init__(self, peer, fh, start_time):
		self.peer = peer
		self.sending_home = True
		self.start_demo(fh)
		self.demo = None
		self.playerid = None
		self.name = None
		self.login = False
		self.login_attempt = 0
		self.afk = start_time
		
	def get_next_packet(self):
		fmt = "fH"
		fmtlen = struct.calcsize(fmt)
		meta = self.fh.read(fmtlen)
		if len(meta) < fmtlen:
			raise EOFError("replay file finished")
		self.timedelta, size = struct.unpack(fmt, meta)
		self.data = self.fh.read(size)
		if self.data[0] == 15: # state data
			if self.sending_home:
				#get new player id for home.
				i = 0
				for cl in list(clients.values()):
					if i == cl.playerid:
						i += 1
				self.playerid = i
				#insert new id into state data
				data = self.data[0:1]
				data += struct.pack("b", i)
				data += self.data[2:]
				self.data = data
				#send already joined players. createplayer instead of existingplayer cuz that works aswell
				for player in list(clients.values()): 
					if player is self:
						continue
					pkt = struct.pack("bbbbfff16s", 12, player.playerid, 1, -1, 255., 255., 60., player.name.encode('cp437'))
					self.peer.send(0, enet.Packet(pkt, enet.PACKET_FLAG_RELIABLE))
			self.playerid = self.data[1]
	
	def start_demo(self, fh):
		try:
			self.fh.close
		except:
			pass
		self.fh = open(fh, "rb")
		if not self.sending_home:
			self.saved_fh = fh
		self.start_time = time.time()
		self.pause_time = 0
		self.fh.read(struct.calcsize("BB"))
		self.get_next_packet()
		self.spawned = False
		self.spam_time = None
		self.playerinfo = [[0,0] for _ in range(32)]
		self.at_home = False
		
	def send_chat(self, chat): #send a system/server message to client
		pkt = struct.pack('bbb', 17, 33, 2) + chat.encode('cp437')
		self.peer.send(0, enet.Packet(pkt, enet.PACKET_FLAG_RELIABLE))

host = enet.Host(enet.Address(bytes('0.0.0.0', 'utf-8'), PORT), 128, 1)
host.compress_with_range_coder()
clients = {}
client_id = 0
while True:
	#sending demo packets and handle afk
	for cl in list(clients.values()):
		if cl.at_home:
			if cl.afk + KICK_AFK <= time.time():
				cl.peer.disconnect(0)
				print("kicked. afk", cl.peer.data)
				cl.fh.close()
				del clients[cl.peer.data]
			if not cl.login and cl.start_time + LOGIN_TIME <= time.time():
				cl.peer.disconnect(0)
				print("kicked. not logged in", cl.peer.data)
				cl.fh.close()
				del clients[cl.peer.data]
			continue
		if cl.pause_time > 0:
			continue
		if cl.spam_time is not None and cl.spam_time <= time.time():
			pkt = struct.pack("bbb", 17, 35, 2) + str(cl.timedelta).encode('cp437', 'replace') #chat message
			cl.peer.send(0, enet.Packet(pkt, enet.PACKET_FLAG_RELIABLE))
			cl.spam_time = time.time() + 1
		while cl.start_time + cl.timedelta <= time.time() and not cl.at_home:
			if cl.data[0] == 3: #input data
				player, data = struct.unpack("xbb", cl.data)
				cl.playerinfo[player][0] = data
			elif cl.data[0] == 4: #weapon data
				player, data = struct.unpack("xbb", cl.data)
				cl.playerinfo[player][1] = data
			cl.peer.send(0, enet.Packet(cl.data, enet.PACKET_FLAG_RELIABLE))
			try:
				cl.get_next_packet()
			except EOFError:
				if cl.sending_home:
					cl.at_home = True
					cl.sending_home = False
					cl.send_chat("welcome home. u r using pbot.py by VierEck.")
					continue
				print(cl.peer.data, "finished playback")
				cl.sending_home = True
				cl.start_demo(HOME)
	#handle connections and incoming packets
	try:
		event = host.service(0)
	except IOError:
		continue
	if event is None:
		continue
	elif event.type == enet.EVENT_TYPE_CONNECT:
		if event.peer.eventData == AOS_VERSION:
			event.peer.data = bytes(str(client_id), 'utf-8')
			client_id += 1
			clients[event.peer.data] = Client(event.peer, HOME, time.time())
			print("received client connection", event.peer.data)
		else:
			print("WRONG CLIENT VERSION: replay is version %s and client was version %s" % (AOS_VERSION, event.peer.eventData))
			event.peer.disconnect_now(3) #ERROR_WRONG_VERSION
	elif event.type == enet.EVENT_TYPE_DISCONNECT:
		if event.peer.data in clients:
			clients[event.peer.data].fh.close()
			del clients[event.peer.data]
		print("lost client connection", event.peer.data)
	elif event.type == enet.EVENT_TYPE_RECEIVE:
		cl = clients[event.peer.data]
		data = event.packet.data
		if cl.at_home and data[0] not in [0, 1, 2]: #pos-, ori-, ups packets
			if data[0] == 9: #existingplayer. when player joins home
				cl.afk = time.time()
				cl.name = data[12:-1].decode('cp437')
				cl.spawned = True
				#broadcast join
				pkt = struct.pack("bbbbfff16s", 12, cl.playerid, 1, -1, 255., 255., 60., data[12:-1])
				for client in list(clients.values()):
					client.peer.send(0, enet.Packet(pkt, enet.PACKET_FLAG_RELIABLE))
				print(cl.name + " joined")
				continue
			if data[0] == 17:
				cl.afk = time.time()
				print(cl.name + ": " + data[3:-1].decode('cp437'))
				if data[3:4].decode('cp437') == "/":
					chat = data[4:-1].decode('cp437', 'replace')
					handle_command(cl, chat)
					continue
			#broadcast packet
			for client in list(clients.values()):
				client.peer.send(0, enet.Packet(event.packet.data, enet.PACKET_FLAG_RELIABLE))
		elif data[0] == 9: #existingplayer. when player joins demo
			cl.spawned = True
			pkt = struct.pack("bbbbfff16s", 12, cl.playerid, 1, -1, 255., 255., 60., cl.name.encode('cp437'))
			cl.peer.send(0, enet.Packet(pkt, enet.PACKET_FLAG_RELIABLE))
		elif data[0] == 17:
			chat = data[3:-1].decode('cp437', 'replace')
			handle_command(cl, chat)

