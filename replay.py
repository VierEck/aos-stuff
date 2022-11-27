'''
latest version of replay.py: https://github.com/VierEck/aos-scripts/blob/main/replay.py
LICENSE: GPL-3.0
codeauthor: VierEck.

original aos_replay by BR: (https://github.com/BR-/aos_replay)

recordings resulting from this script r compatible with BR's
Playback.py

this script records gameplay for later examination by staff. a 
lot of things can happen in the absence of staff, most of all 
cheating. this script aims to provide staff an eye on the server 
at all times. nothing will be unseen anymore, there will be no 
hiding >:D

another use for this script would be recording the game just for 
fun. u may want to capture some of ur favorite precious moments 
u experience playing on ur server. u could do this with a simple 
screen recorder aswell, sure, but with an actual gameplay 
recorder tool, like this script, u r practically recording the 
game in 3d, from all perspectives!

! IMPORTANT ! pls read everything down below. 
auto mode only starts to record if there is more than 1 player 
present. auto mode will try to start a recording on map change. 
recording will always be automatically ended if there is less 
than 2 players present or if the map ends. 

always creates a new file when recording is started. 

autorecording setting basically makes server always record if 
there r enough players. 

config.toml copypaste template:
[replay]
autorecording = false #change this to true if u always want to record
recorded_ups = 20
file_name = "rpy_{server}_{time}_{map}"

'''

from piqueserver.commands import command
from pyspades import contained as loaders
from piqueserver.config import config
from pyspades.bytes import ByteWriter
import struct
from time import time, strftime
from datetime import datetime
import os.path
import enet
from pyspades.mapgenerator import ProgressiveMapGenerator
from typing import Optional
from pyspades.constants import CTF_MODE, TC_MODE
from pyspades.common import make_color
import asyncio

replay_config = config.section('replay')
auto_replay = replay_config.option('autorecording', False).get()
rec_ups = replay_config.option('recorded_ups', 20).get()
file_name = replay_config.option('file_name', default='rpy_{server}_{time}_{map}').get()

FILE_VERSION = 1
version = 3

def get_replays_dir():
    return (os.path.join(config.config_dir, 'replays'))

@command('replay', 'rpy',admin_only=True)
def replay(connection, value, name_length_ups=None, length_ups=None, ups_=None):
    p = connection.protocol
    value = value.lower()
    msg = 'Invalid value. type ON or OFF' #we want explicit command use. 
    if value == 'on':
        msg = 'recording is already ON'
        if not p.recording:
            msg = 'not enough players'
            if len(p.connections) >= 1:
                msg = 'demo recording turned ON'
                if name_length_ups is not None:
                    if 'ups' in name_length_ups:
                        p.record_ups = int(name_length_ups[3:])
                        msg += '. %.f ups' % p.record_ups
                        name_length_ups = None
                    else:
                        if name_length_ups.isdigit():
                            p.record_length = int(name_length_ups)
                            msg += '. %.f seconds' % p.record_length
                            name_length_ups = None
                        if length_ups is not None:
                            if 'ups' in length_ups:
                                p.record_ups = int(length_ups[3:])
                                msg += '. %.f ups' % p.record_ups
                            elif length_ups.isdigit() and name_length_ups is not None:
                                p.record_length = int(length_ups)
                                msg += '. %.f seconds' % p.record_length
                                if ups_ is not None:
                                    p.record_ups = int(ups_[3:])
                                    msg += '. %.f ups' % p.record_ups
                        if name_length_ups is not None:
                            msg += '. filename: %s' % name_length_ups
                p.start_recording(name_length_ups)
    elif value == 'off':
        msg = 'recording is already OFF'
        if p.recording:
            p.end_recording()
            msg = 'demo recording turned OFF'
    if connection.name is not None:
        msg += '. %s' % connection.name
    p.irc_say(msg)
    return msg
        
def apply_script(protocol, connection, config):
    class replayconnection(connection):
        def on_disconnect(self):
            if len(self.protocol.connections) <= 2 and self.protocol.recording:
                self.protocol.end_recording()
                self.protocol.irc_say('* demo recording turned OFF. not enough players')
            return connection.on_disconnect(self)
        
        def on_join(self):
            if auto_replay and len(self.protocol.connections) >= 2 and not self.protocol.recording:
                self.protocol.start_recording()
                self.protocol.irc_say('* demo recording turned ON. there are enough players now')
            return connection.on_join(self)
              
    class replayprotocol(protocol):
        recording = False
        write_broadcast = False
        record_length = None
        record_loop_task = None
        last_mapdata_written = time()
        last_length_check = time()
        record_ups = rec_ups
        
        async def record_loop(self):
            while True:
                if self.recording:
                    if self.mapdata is not None:
                        if time() - self.last_mapdata_written >= 1/4: 
                            self.write_map()
                            self.last_mapdata_written = time()
                    if self.record_length is not None:
                        if time() - self.last_length_check >= 1:
                            if self.record_length <= (time() - self.start_time):
                                self.end_recording()
                                self.irc_say('* demo recording has turned OFF after %.f seconds' % self.record_length)
                                self.record_length = None
                            self.last_length_check = time()
                    if self.write_broadcast:
                        self.write_ups()
                await asyncio.sleep(1/self.record_ups)
        
        def on_map_change(self, map_):
            if auto_replay and len(self.connections) >= 2 and not self.recording: 
                self.start_recording()
                self.irc_say('* demo recording turned ON. there are enough players on map start')
            return protocol.on_map_change(self, map_)
        
        def on_map_leave(self):
            if self.recording:
                self.end_recording()
                self.irc_say('* demo recording turned OFF. map ended')
            protocol.on_map_leave(self)
        
        def create_demo_file(self, custom_name_command=None):
            if not os.path.exists(get_replays_dir()):
                os.mkdir(os.path.join(get_replays_dir()))
            fn = file_name
            if '{server}' in fn:
                fn = fn.replace('{server}', self.name)
            if '{map}' in fn:
                fn = fn.replace('{map}', self.map_info.rot_info.name)
            if '{time}' in fn:
                fn = fn.replace('{time}', datetime.now().strftime('%Y-%m-%d_%H-%M-%S_'))
            self.replay_filename = fn
            if custom_name_command is not None:
                self.replay_filename = custom_name_command
            self.replay_filename += '.demo'
            self.replayfile = os.path.join(get_replays_dir(), self.replay_filename)
        
        def start_recording(self, custom_name_command=None):
            self.create_demo_file(custom_name_command)
            self.replay_file = open(self.replayfile, 'wb')
            self.replay_file.write(struct.pack('BB', FILE_VERSION, version))
            self.start_time = time()
            self.record_loop_task = asyncio.ensure_future(self.record_loop())
            self.write_map(ProgressiveMapGenerator(self.map))
            self.recording = True
        
        def end_recording(self):
            self.record_loop_task.cancel()
            self.record_loop_task = None
            self.record_ups = rec_ups
            self.write_broadcast = False
            self.recording = False
            self.replay_file.close()
        
        def write_pack(self, contained):
            data = ByteWriter()
            contained.write(data)
            data = bytes(data)
            self.replay_file.write(struct.pack('fH', time() - self.start_time, len(data)))
            self.replay_file.write(data)
        
        def broadcast_contained(self, contained, unsequenced=False, sender=None, team=None, save=False, rule=None):
            if self.write_broadcast and contained.id != 2:
                self.write_pack(contained)
            return protocol.broadcast_contained(self, contained, unsequenced, sender, team, save, rule)
            
        def write_ups(self):
            if not len(self.players):
                return
            items = []
            highest_player_id = max(self.players)
            for i in range(highest_player_id + 1):
                position = orientation = None
                try:
                    player = self.players[i]
                    if (not player.filter_visibility_data and
                            not player.team.spectator):
                        world_object = player.world_object
                        position = world_object.position.get()
                        orientation = world_object.orientation.get()
                except (KeyError, TypeError, AttributeError):
                    pass
                if position is None:
                    position = (0.0, 0.0, 0.0)
                    orientation = (0.0, 0.0, 0.0)
                items.append((position, orientation))
            world_update = loaders.WorldUpdate()
            world_update.items = items[:highest_player_id+1]
            self.write_pack(world_update)
                
        def write_map(self, data: Optional[ProgressiveMapGenerator] = None) -> None:
            if data is not None:
                self.mapdata = data
                map_start = loaders.MapStart()
                map_start.size = data.get_size()
                self.write_pack(map_start)
            elif self.mapdata is None:
                return
            if not self.mapdata.data_left():
                self.mapdata = None
                self.write_state()
                self.write_broadcast = True
                self.sig_vier()
                return
            for _ in range(10):
                if not self.mapdata.data_left():
                    break
                mapdata = loaders.MapChunk()
                mapdata.data = self.mapdata.read(8192)
                self.write_pack(mapdata)
        
        def write_state(self):
            for player in self.players.values():
                if player.name is None:
                    continue
                existing_player = loaders.ExistingPlayer()
                existing_player.name = player.name
                existing_player.player_id = player.player_id
                existing_player.tool = player.tool or 0
                existing_player.weapon = player.weapon
                existing_player.kills = player.kills
                existing_player.team = player.team.id
                existing_player.color = make_color(*player.color)
                self.write_pack(existing_player)
               
            self.recorder_id = 33 #u will need a modified client that will accept this!
                    
            blue = self.blue_team
            green = self.green_team
    
            state_data = loaders.StateData()
            state_data.player_id = self.recorder_id
            state_data.fog_color = self.fog_color
            state_data.team1_color = blue.color
            state_data.team1_name = blue.name
            state_data.team2_color = green.color
            state_data.team2_name = green.name
    
            game_mode = self.game_mode
    
            if game_mode == CTF_MODE:
                blue_base = blue.base
                blue_flag = blue.flag
                green_base = green.base
                green_flag = green.flag
                ctf_data = loaders.CTFState()
                ctf_data.cap_limit = self.max_score
                ctf_data.team1_score = blue.score
                ctf_data.team2_score = green.score
    
                ctf_data.team1_base_x = blue_base.x
                ctf_data.team1_base_y = blue_base.y
                ctf_data.team1_base_z = blue_base.z
    
                ctf_data.team2_base_x = green_base.x
                ctf_data.team2_base_y = green_base.y
                ctf_data.team2_base_z = green_base.z
    
                if green_flag.player is None:
                    ctf_data.team1_has_intel = 0
                    ctf_data.team2_flag_x = green_flag.x
                    ctf_data.team2_flag_y = green_flag.y
                    ctf_data.team2_flag_z = green_flag.z
                else:
                    ctf_data.team1_has_intel = 1
                    ctf_data.team2_carrier = green_flag.player.player_id
    
                if blue_flag.player is None:
                    ctf_data.team2_has_intel = 0
                    ctf_data.team1_flag_x = blue_flag.x
                    ctf_data.team1_flag_y = blue_flag.y
                    ctf_data.team1_flag_z = blue_flag.z
                else:
                    ctf_data.team2_has_intel = 1
                    ctf_data.team1_carrier = blue_flag.player.player_id
    
                state_data.state = ctf_data
    
            elif game_mode == TC_MODE:
                state_data.state = tc_data
            
            self.write_pack(state_data)
            
        def sig_vier(self): #yes i just had to do this lol
            chat_message = loaders.ChatMessage()
            chat_message.chat_type = 2
            chat_message.player_id = 35
            chat_message.value = 'recorded with replay.py by VierEck.'
            self.write_pack(chat_message)
    
    return replayprotocol, replayconnection
