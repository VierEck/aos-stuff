'''
latest version of replay.py: https://github.com/VierEck/aos-scripts/blob/main/replay.py

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

codeauthor: VierEck.
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
from pyspades.common import Vertex3, make_color

replay_config = config.section('replay')
auto_replay = replay_config.option('autorecording', False).get()

FILE_VERSION = 1
version = 3

def get_replays_dir(connection):
    return (os.path.join(config.config_dir, 'replays'))

@command('replay', 'rpy',admin_only=True)
def replay(connection, value, time_length=None):
    protocol = connection.protocol
    value = value.lower()
    if value == 'on':
        if not protocol.recording:
            if len(protocol.connections) >= 1:
                if time_length is not None:
                    protocol.record_length = int(time_length)
                protocol.start_recording()
                if connection in connection.protocol.players:
                    connection.send_chat('demo recording turned ON')
                    protocol.irc_say('* %s turned demo recording ON' % connection.name)
                else:
                    protocol.irc_say('* demo recording turned ON')
                    return ('demo recording turned ON')
            else:
                if connection in connection.protocol.players:
                    connection.send_chat('not enough players')
                else:
                    protocol.irc_say('* not enough players')
                    return ('not enough players')
        else:
            if connection in connection.protocol.players:
                connection.send_chat('recording is already ON')
            else:
                protocol.irc_say('* recording is already ON')
                return ('recording is already ON')
    elif value == 'off':
        if protocol.recording:
            protocol.end_recording()
            if connection in connection.protocol.players:
                connection.send_chat('demo recording turned OFF')
                protocol.irc_say('* %s turned demo recording OFF' % connection.name)
            else:
                protocol.irc_say('* demo recording turned OFF')
                return ('demo recording turned OFF')
        else:
            if connection in connection.protocol.players:
                connection.send_chat('recording is already OFF')
            else:
                protocol.irc_say('* recording is already OFF')
                return ('recording is already OFF')
    else:
        connection.send_chat('Invalid value. type ON or OFF')
        return 'Invalid value. type ON or OFF' #we want explicit command use. 
        
def apply_script(protocol, connection, config):

    class replayconnection(connection):
        def on_disconnect(self):
            if len(self.protocol.connections) <= 2 and self.protocol.recording:
                self.protocol.end_recording()
                self.protocol.irc_say('* demo recording turned OFF')
            return connection.on_disconnect(self)
              
    class replayprotocol(protocol):
        recording = False
        write_broadcast = False
        record_length = None
        
        def on_world_update(self):
            if self.recording:
                if self.mapdata is not None:
                    self.write_map() #maybe handle this somewhere else?
                if self.record_length is not None:
                    if self.record_length <= (time() - self.start_time):
                        self.end_recording()
                        self.irc_say('* demo recording turned OFF')
            return protocol.on_world_update(self)
        
        def on_connect(self, peer):
            if auto_replay and len(self.connections) >= 1 and not self.recording:
                self.start_recording()
                self.irc_say('* demo recording turned ON')
            return protocol.on_connect(self, peer)
        
        def on_map_change(self, map_):
            if auto_replay and len(self.connections) >= 2 and not self.recording: 
                self.start_recording()
                self.irc_say('* demo recording turned ON')
            return protocol.on_map_change(self, map_)
        
        def on_map_leave(self):
            if self.recording:
                self.end_recording()
                self.irc_say('* demo recording turned OFF')
            protocol.on_map_leave(self)
        
        def start_recording(self):
            if not os.path.exists(get_replays_dir(connection)):
                os.mkdir(os.path.join(get_replays_dir(connection)))
            time_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            map_name = self.map_info.rot_info.name + '_'
            self.replay_filename = 'rpy_' + map_name + time_str + '.demo'
            self.replayfile = os.path.join(get_replays_dir(connection), self.replay_filename)
            self.replay_file = open(self.replayfile, 'wb')
            self.replay_file.write(struct.pack('BB', FILE_VERSION, version))
            self.start_time = time()
            self.write_map(ProgressiveMapGenerator(self.map))
            self.recording = True
        
        def end_recording(self):
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
            if self.write_broadcast:
                self.write_pack(contained)
            return protocol.broadcast_contained(self, contained, unsequenced, sender, team, save, rule)
        
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
               
            if len(self.connections) <= 30:              #this is not a solution. 
                self.recorder_id = self.player_ids.pop() #the only real solution i can figure out is to always have recorder_id
            else:                                        #set to greater than 31, but then having a modified client that can
                self.recorder_id = 33                    #handle it as local player id when reviewing the resulting recording. 
                    
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
