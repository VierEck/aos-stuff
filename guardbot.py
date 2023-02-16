#!/usr/bin/env python3
'''
author: VierEck.

GuardBot. 
record gameplay from a server around the clock. 
afterwards, review the demos with BR's Playback.py. 

original script: https://github.com/BR-/aos_replay
'''

FOLDER = "demos"					#where the demos of ur server r stored and handled. 
FILE_NAME = "ur_server_{time}"		#{time} -> time of start of recording, this is important so that files wont overwrite and r distinguishable. 
SERVER_NAME = "ur_server"			#needed to print some console messages. 
SERVER_URL = "aos://16777343:32887"	#needed for search on master.
MIN_LENGTH = 60						#how long a demo should be to not get deleted. u dont want to clutter ur system with mostly map junk. 
MAX_LENGTH = 600					#how long a demo should be till ended. recommended since fast forwarding demos too much can break some clients. 
MAX_AGE = 604800					#how old demos get till they get deleted. (in seconds. everythings in seconds here) (604800 = a week)
SEARCH_PERIOD = 15					#pause time between iterations.
MIN_PLAYERS = 4						#4 is the bare minimum. no less than that is worth ur resources imo.
AFK_PERIOD = 60						#time between input changes to delay afk kick.
test = False						#for test runs. if u dont want ur folder to be cluttered with mere test demos.
test_url = "aos://16777343:32887"	#for test runs. ur testing server. 


import urllib.request, json
import os
import time
from datetime import datetime
import struct
import enet

FILE_VERSION = 1
AOS_VERSION = 3

#do folder
path = os.path.dirname(__file__)
folder = os.path.join(path, FOLDER)
if not os.path.exists(folder):
	os.mkdir(os.path.join(folder))
		
#ingame behaviour
def send_join():
	pkt = struct.pack('BBbBBI', 9, 0, 0, 0, 2, 0) + 'Deuce'.encode('cp437')
	event.peer.send(0, enet.Packet(pkt, enet.PACKET_FLAG_RELIABLE))

def send_crouch(crouched):
	if crouched:
		pkt = struct.pack('BBB', 3, local_player_id, 0)
		event.peer.send(0, enet.Packet(pkt, enet.PACKET_FLAG_RELIABLE))
	else:
		pkt = struct.pack('BBB', 3, local_player_id, 32)
		event.peer.send(0, enet.Packet(pkt, enet.PACKET_FLAG_RELIABLE))

def send_space():
	pkt = struct.pack('bbb', 17, local_player_id, 1) + ' '.encode('cp437')
	event.peer.send(0, enet.Packet(pkt, enet.PACKET_FLAG_RELIABLE))

def send_ups():
	pkt = struct.pack('bbb', 17, local_player_id, 1) + '/ups 60'.encode('cp437')
	event.peer.send(0, enet.Packet(pkt, enet.PACKET_FLAG_RELIABLE))
	
#write edited packets
def write_state():
	fh.write(struct.pack('fH', time.time() - start_time, len(event.packet.data)))
	fh.write(struct.pack('b', event.packet.data[0]))
	fh.write(struct.pack('b', record_id))
	fh.write(event.packet.data[2:])

def signature():
	msg = 'This demo was recorded with guardbot.py by VierEck.'.encode('cp437', 'replace')
	pkt = struct.pack('bbb', 17, record_id, 2) + msg
	fh.write(struct.pack('fH', time.time() - start_time, len(pkt)))
	fh.write(pkt)
				
#
while True:
	ip = port = None
	found = connected = limbo = dead = crouched = False
	record_id = local_player_id = 33
	ingame_players = []

	if test:
		aos_name = 'test server'
		aos_url_full = test_url
		aos_url = aos_url_full[6:]
		dec, port = aos_url.rsplit(':', 1)
		dec = int(dec)
		port = int(port)
		ip = ""
		for _ in range(4):
			ip += str(dec % 256) + "."
			dec //= 256
		ip = ip[:-1]
		found = True
	#search and check on master if server is listed and has valid player count. 
	while not found:
		with urllib.request.urlopen('http://services.buildandshoot.com/serverlist-json') as url:
			server_list = json.load(url)
		for server in server_list:
			if SERVER_URL in server['identifier'] and not found:
				if server['players_max'] > server['players_current'] >= MIN_PLAYERS:
					aos_name = server['name']
					aos_url_full = server['identifier']
					aos_url = aos_url_full[6:]
					dec, port = aos_url.rsplit(':', 1)
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
						print('search delayed. server full: ' + SERVER_NAME)
						print('-                          : ' + SERVER_URL)
					if server['players_current'] < MIN_PLAYERS:
						print('search delayed. server not enough players: ' + SERVER_NAME)
						print('-                                        : ' + SERVER_URL)
				search_success = True
		if not found:
			try:
				search_success = not search_success
			except NameError:
				print('search delayed. server not found: ' + SERVER_NAME)
				print('-                               : ' + SERVER_URL)
			import time
			time.sleep(SEARCH_PERIOD)

	#do the file
	file = FILE_NAME
	if '{time}' in file:
		file = file.replace('{time}', datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))
	file += '.demo'
	file = os.path.join(folder, file)
	if test:
		file = 'test.demo'
		
	#connect and record
	con = enet.Host(None, 1, 1)
	con.compress_with_range_coder()
	print('Trying to connect to: ' + aos_name)
	print('-                   : ' + aos_url_full)
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
				print('successfully connected to: ' + aos_name)
				print('-                        : ' + aos_url_full)
				start_time = delay_afk = time.time()
			elif event.type == enet.EVENT_TYPE_DISCONNECT:
				try:
					reason = ["generic error", "banned", "kicked", "wrong version", "server is full"][event.data]
				except IndexError:
					reason = "unknown reason (%s)" % event.data
				print('lost connection to server:', reason)
				break
			elif event.type == enet.EVENT_TYPE_RECEIVE:
				if event.packet.data[0] == 15: #statedata
					write_state()
					local_player_id = event.packet.data[1]
					time_since_limbo = check_stuff = time.time()
					connected = True
					limbo = True
					continue
				fh.write(struct.pack('fH', time.time() - start_time, len(event.packet.data)))
				fh.write(event.packet.data)
				if test and limbo:
					send_join()
				if event.packet.data[0] == 16: #killaction
					if limbo:
						send_join()
					if event.packet.data[1] == local_player_id:
						dead = True
				if event.packet.data[0] == 12: #createplayer
					player_id = event.packet.data[1]
					if player_id == local_player_id:
						if limbo:
							name = event.packet.data[16:].decode('cp437', 'replace')
							print('joined as: ' + name)
							send_ups()
						dead = limbo = crouched = False
						signature()
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
						if time.time() >= delay_afk + AFK_PERIOD:
							if dead:
								send_space()
							else:
								send_crouch(crouched)
								crouched = not crouched
							delay_afk = time.time()
					if time.time() >= check_stuff + 10:
						if len(ingame_players) < MIN_PLAYERS:
							peer.disconnect(0)
							print('voluntarily disconnected: not enough players')
							break
						if time.time() - time_since_limbo > MAX_LENGTH:
							peer.disconnect(0)
							print('voluntarily disconnected: max recording length reached')
							break
						check_stuff = time.time()
	
	#delete recording if too small or old
	if time.time() - time_since_limbo < MIN_LENGTH:
		os.remove(file)
		print('deleted recording. too short')
	for f in os.listdir(folder):
		if '.demo' in f:
			if os.stat(os.path.join(folder, f)).st_mtime < time.time() - MAX_AGE:
				os.remove(os.path.join(folder, f))
	
	time.sleep(SEARCH_PERIOD)
