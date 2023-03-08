#!/usr/bin/env python3
'''
portions of this file are from BR's original script: https://github.com/BR-/aos_replay

MultiRecordBot. 
record gameplay from multiple servers around the clock. 
configurate script behavior with config.toml.
spawns a process for each server. idk but might become heavy if too many servers r watched. 

needs rbot.py in the same directory

author: VierEck.
'''

import rbot
from multiprocessing import Process

servers    = {}
server_id  = 0
for sv in rbot.config()['server']:
	servers[server_id] = rbot.Server(sv)
	server_id += 1
	
if __name__ == '__main__':
	for sv in list(servers.values()):
		Process(target=sv.server_loop).start()
