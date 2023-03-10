#!/usr/bin/env python3
'''
portions of this file are from BR's original script: https://github.com/BR-/aos_replay

RecordBot. 
record gameplay from a server around the clock. 
customize configs in config.toml

author: VierEck.
'''

import toml
import urllib.request, json
import os
import time
from datetime import datetime
import struct
import enet

FILE_VERSION = 1
AOS_VERSION = 3

PATH = os.path.dirname(__file__)

def config():
	try:
		config = toml.load('config.toml')
	except:
		print('abort. no config.toml or invalid config content')
		import sys
		sys.exit(1)
	return config

class Server(object):
	def __init__(self, sv_config):
		self.folder        = sv_config['folder']
		self.server_name   = sv_config['server_name']
		self.server_url    = sv_config['server_url']
		self.min_players   = sv_config['min_players']
		self.afk_period    = sv_config['afk_period']
		self.afk_behavior  = sv_config['afk_behavior']
		self.min_length    = sv_config['min_length']
		self.max_length    = sv_config['max_length']
		self.max_age       = sv_config['max_age']
		self.search_period = sv_config['search_period']
		
	def server_loop(self):
		#do folder
		folder = os.path.join(PATH, self.folder)
		if not os.path.exists(folder):
			os.mkdir(os.path.join(folder))
		#
		while True:
			ip = port = None
			found = connected = limbo = dead = crouched = False
			record_id = local_player_id = 33
			ingame_players = []
			#search on master
			while not found:
				with urllib.request.urlopen('http://services.buildandshoot.com/serverlist-json') as url:
					server_list = json.load(url)
				search_success = False
				for server in server_list:
					if self.server_url == server['identifier'] and not found:
						if server['players_max'] > server['players_current'] >= self.min_players:
							dec, port = self.server_url[6:].rsplit(':', 1)
							dec = int(dec)
							port = int(port)
							ip = ""
							for _ in range(4):
								ip += str(dec % 256) + "."
								dec //= 256
							ip = ip[:-1]
							found = True
						else:
							if server['players_current'] >= server['players_max']:
								print('search delayed. server full: ' + self.server_name)
							if server['players_current'] < self.min_players:
								print('search delayed. server not enough players: ' + self.server_name)
						search_success = True
				if not found:
					if not search_success:
						print('search delayed. server not found: ' + self.server_name)
					time.sleep(self.search_period)
			#do the file
			file = datetime.now().strftime('[%Y-%m-%d-%H-%M-%S]_') + self.server_name + '_[].demo'
			file = os.path.join(self.folder, file)
			#connect and record
			con = enet.Host(None, 1, 1)
			con.compress_with_range_coder()
			print('Trying to connect to: ' + self.server_name)
			peer = con.connect(enet.Address(bytes(ip, 'utf-8'), port), 1, AOS_VERSION)
			with open(file, "wb") as fh:
				fh.write(struct.pack('BB', FILE_VERSION, AOS_VERSION))
				while found:
					try:
						event = con.service(1000)
					except IOError:
						continue
					if event is None:
						continue
					elif event.type == enet.EVENT_TYPE_CONNECT:
						print('successfully connected to: ' + self.server_name)
						start_time = delay_afk = time.time()
					elif event.type == enet.EVENT_TYPE_DISCONNECT:
						try:
							reason = ["generic error", "banned", "kicked", "wrong version", "server is full"][event.data]
						except IndexError:
							reason = "unknown reason (%s)" % event.data
						print(self.server_name + ' lost connection:' + reason)
						break
					elif event.type == enet.EVENT_TYPE_RECEIVE:
						if event.packet.data[0] == 15: #statedata
							#modify state
							fh.write(struct.pack('fH', time.time() - start_time, len(event.packet.data)))
							fh.write(struct.pack('b', event.packet.data[0]))
							fh.write(struct.pack('b', record_id))
							fh.write(event.packet.data[2:])
							#prepare some values
							local_player_id = event.packet.data[1]
							time_since_limbo = check_stuff = time.time()
							connected = limbo = True
							continue
						fh.write(struct.pack('fH', time.time() - start_time, len(event.packet.data)))
						fh.write(event.packet.data)
						if event.packet.data[0] == 16: #killaction
							if limbo:
								#send join
								pkt = struct.pack('BBbBBI', 9, 0, 0, 0, 2, 0) + 'Deuce'.encode('cp437')
								event.peer.send(0, enet.Packet(pkt, enet.PACKET_FLAG_RELIABLE))
							if event.packet.data[1] == local_player_id:
								dead = True
						if event.packet.data[0] == 12: #createplayer
							player_id = event.packet.data[1]
							if player_id == local_player_id:
								if limbo:
									name = event.packet.data[16:].decode('cp437', 'replace')
									print(self.server_name + ' joined as: ' + name)
									#request 60 ups
									pkt = struct.pack('bbb', 17, local_player_id, 1) + '/ups 60'.encode('cp437')
									event.peer.send(0, enet.Packet(pkt, enet.PACKET_FLAG_RELIABLE))
								dead = limbo = crouched = False
								#signature
								msg = 'This demo was recorded with rbot.py by VierEck.'.encode('cp437', 'replace')
								pkt = struct.pack('bbb', 17, record_id, 2) + msg
								fh.write(struct.pack('fH', time.time() - start_time, len(pkt)))
								fh.write(pkt)
							if player_id not in ingame_players:
								ingame_players.append(player_id)
						if event.packet.data[0] == 9: #existplayer
							player_id = event.packet.data[1]
							if player_id not in ingame_players:
								ingame_players.append(player_id)
						if event.packet.data[0] == 20: #playerleft
							player_id = event.packet.data[1]
							if player_id in ingame_players:
								ingame_players.remove(player_id)
						if connected:
							if not limbo:
								if time.time() >= delay_afk + self.afk_period:
									if self.afk_behavior == 'chat':
										#send empty chat
										pkt = struct.pack('bbb', 17, local_player_id, 1) + ' '.encode('cp437')
										event.peer.send(0, enet.Packet(pkt, enet.PACKET_FLAG_RELIABLE))
									elif self.afk_behavior == 'input':	
										if dead:
											#send empty chat
											pkt = struct.pack('bbb', 17, local_player_id, 1) + ' '.encode('cp437')
											event.peer.send(0, enet.Packet(pkt, enet.PACKET_FLAG_RELIABLE))
										else:
											#crouch/uncrouch
											if crouched:
												input_value = 0  #00000000
											else:
												input_value = 32 #00100000
											pkt = struct.pack('BBB', 3, local_player_id, input_value)
											event.peer.send(0, enet.Packet(pkt, enet.PACKET_FLAG_RELIABLE))
											crouched = not crouched
									delay_afk = time.time()
							if time.time() >= check_stuff + 10:
								if len(ingame_players) < self.min_players:
									peer.disconnect(0)
									print(self.server_name + ' voluntarily disconnected: not enough players')
									break
								if time.time() - time_since_limbo > self.max_length:
									peer.disconnect(0)
									print(self.server_name + ' voluntarily disconnected: max recording length reached')
									break
								check_stuff = time.time()
			#delete if demo too short
			if time.time() - time_since_limbo < self.min_length:
				os.remove(file)
				print(self.server_name + ' deleted recording: too short')
			else: #add length to file name (in minutes)
				length = (time.time() - start_time) / 60
				add_length = file.replace('[].demo', '[%.0f].demo' % length)
				os.rename(file, add_length)
			#delete old demos
			for f in os.listdir(self.folder):
				if '.demo' in f: 
					if os.stat(os.path.join(folder, f)).st_mtime < time.time() - self.max_age:
						os.remove(os.path.join(folder, f))
			time.sleep(self.search_period)

if __name__ == "__main__":
	sv = Server(config()["server"][0])
	sv.server_loop()
