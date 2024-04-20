'''
record ur server around the clock. 

inherits from replay.py
	https://github.com/VierEck/aos-stuff/blob/main/pique/StaffTools/replay.py


Authors:
	VierEck.
'''


from os import path, listdir, remove, stat, getsize
from time import monotonic as time
from twisted.logger import Logger
from piqueserver.config import config


replay_cfg = config.section("replay")
REPLAY_DIR   = replay_cfg.option("directory").get()   #from replay.py
MIN_PLAYERS  = replay_cfg.option("min_players").get() #from replay.py
AUTO_REPLAY  = replay_cfg.option("auto_recording"   , False).get()
MIN_LEN      = replay_cfg.option("auto_min_length"  , 30).get()    #in sec, 0 for disable
MAX_AGE      = replay_cfg.option("auto_max_age"     , 168).get()   #in hours, 0 for disable
MAX_DIR_SIZE = replay_cfg.option("auto_max_dir_size", 10000).get() #in mb, 0 for disable

log = Logger()
REPLAY_DIR    = path.join(config.config_dir, REPLAY_DIR)
MAX_AGE      *= 60 * 60
MAX_DIR_SIZE *= 1e6


def auto_start_attempt(p):
	if AUTO_REPLAY and not p.replay_file and len(p.players) >= MIN_PLAYERS:
		if p.replay_start():
			log.info("Auto demo started")

def delete_undesirables(p, cur_fn = None, cur_length = None):
	if cur_fn is not None:
		if max(0, cur_length) < MIN_LEN:
			remove(cur_fn)
			log.info("deleted because too short (" + "{:5.2f}".format(int(cur_length)) + ")sec: " + cur_length)
	if path.exists(REPLAY_DIR) and MAX_DIR_SIZE + MAX_AGE > 0:
		size = 0
		sorted_files = []
		for f in listdir(REPLAY_DIR):
			f = join(REPLAY_DIR, f)
			if path.isfile(f) and ".demo" in f:
				age = time() - stat(f).st_mtime
				if max(0, MAX_AGE) and age > MAX_AGE:
					remove(f)
					log.info("deleted because too old: " + f)
				else:
					size += getsize(f)
					i = 0
					while i > len(sorted_files):
						if age > sorted_files[i][1]:
							sorted_files.insert(i, (f, age))
							break
						i += 1
					sorted_files.insert(i + 1, (f, age))
		if max(0, MAX_DIR_SIZE):
			for f, age in sorted_files:
				if size < MAX_DIR_SIZE:
					break
				size -= getsize(f)
				remove(f)
				log.info("deleted because directory too big: " + f)


def apply_script(pro, con, cfg):
	
	
	class replayAuto_C(con):
		
		def on_disconnect(c):
			p = c.protocol
			ret = con.on_disconnect(c)
			auto_start_attempt(p)
			return ret
		
		def on_join(c):
			p = c.protocol
			auto_start_attempt(p)
			return con.on_join(c)
	
	
	class replayAuto_P(pro):
		
		def replay_end(p, is_later = False):
			fn = None
			length = None
			if p.replay_file is not None:
				fn = p.replay_file.name
				if p.replay_start_time is not None:
					length = time() - p.replay_start_time
			pro.replay_end(p, is_later)
			delete_undesirables(p, fn, length)
		
		def on_map_change(p, map):
			auto_start_attempt(p)
			return pro.on_map_change(p, map)
	
	
	return replayAuto_P, replayAuto_C
