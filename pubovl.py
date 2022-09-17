'''
spectate players without them knowing or give someone else that ability. 
when using pubovl the server sends a create_player packet only to you or
the player you want it to use on. 
essentially you are now spectator only on ur side while you are still a 
normal player server-side/to everyone else. 

scoreboard statistics may get out of sync. Ammo and blocks get out of 
sync since leaving ovl refills you only client-side. this is not much of 
a problem though since the server still keeps track of ur correct amount 
of ammo and blocks. 

``/ovl`` to become a "hidden spectator". 
         use command again to leave that mode. 
``/ovl <player>`` to make someone else become a "hidden spectator". 
                  use again to make the player leave that mode. 

codeauthors: VierEck., DryByte (https://github.com/DryByte)
'''

from piqueserver.commands import command, target_player
from pyspades.common import Vertex3, make_color
from pyspades.constants import WEAPON_TOOL
from pyspades import contained as loaders
from pyspades import world


@command('pubovl', 'ovl', admin_only=True)
@target_player
def pubovl(connection, player):
    protocol = connection.protocol
    player.hidden = not player.hidden

    x, y, z = player.world_object.position.get()

    # full compatibility
    create_player = loaders.CreatePlayer()
    create_player.player_id = player.player_id
    create_player.name = player.name
    create_player.x = x
    create_player.y = y
    create_player.z = z
    create_player.weapon = player.weapon

    if player.hidden:
        create_player.team = -1

        player.send_contained(create_player)
        player.send_chat("you are now using pubovl")
        protocol.irc_say('* %s is using pubovl' % player.name) #let the rest of the staff team know u r using this
    else:
        create_player.team = player.team.id

        set_color = loaders.SetColor()
        set_color.player_id = player.player_id
        set_color.value = make_color(*player.color)

        player.send_contained(create_player, player)

        player.send_chat('you are no longer using pubovl')
        protocol.irc_say('* %s is no longer using pubovl' % player.name)

def apply_script(protocol, connection, config):
    class pubovlConnection(connection):
        hidden = False
        
        def kill(self, by, kill_type, grenade):
            if self.hp is None:
                return
            if self.on_kill(by, kill_type, grenade) is False:
                return
            self.drop_flag()
            self.hp = None
            self.weapon_object.reset()
            kill_action = loaders.KillAction()
            kill_action.kill_type = kill_type
            if by is None:
                kill_action.killer_id = kill_action.player_id = self.player_id
            else:
                kill_action.killer_id = by.player_id
                kill_action.player_id = self.player_id
            if by is not None and by is not self:
                by.add_score(1)
            kill_action.respawn_time = self.get_respawn_time() + 1
            if self.hidden: 
                for players in self.protocol.players.values():  #dont send kill packet to user of pubovl otherwise
                    if players.player_id is not self.player_id: #it immediately kicks them out of spectator mode
                        players.send_contained(kill_action)
            else:
                 self.protocol.broadcast_contained(kill_action, save=True)   
            self.world_object.dead = True
            self.respawn()

            return connection.kill(self, by, kill_type, grenade)
            
        def spawn(self, pos):
            self.spawn_call = None
            if self.team is None:
                return
            spectator = self.team.spectator
            create_player = loaders.CreatePlayer()
            if not spectator:
                if pos is None:
                    x, y, z = self.get_spawn_location()
                    x += 0.5
                    y += 0.5
                    z -= 2.4
                else:
                    x, y, z = pos
                returned = self.on_spawn_location((x, y, z))
                if returned is not None:
                    x, y, z = returned
                if self.world_object is not None:
                    self.world_object.set_position(x, y, z, True)
                else:
                    position = Vertex3(x, y, z)
                    self.world_object = self.protocol.world.create_object(
                        world.Character, position, None, self._on_fall)
                self.world_object.dead = False
                self.tool = WEAPON_TOOL
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
                if self.hidden: 
                    for players in self.protocol.players.values():
                        if players.player_id is not self.player_id:
                            players.send_contained(create_player)
                else:
                    self.protocol.broadcast_contained(create_player, save=True)
            if not spectator:
                self.on_spawn((x, y, z))

            if not self.client_info:
                handshake_init = loaders.HandShakeInit()
                self.send_contained(handshake_init)

            return connection.spawn(self, pos)

        def on_team_changed(self, old_team):                    #normally server rejects ur teamchange when ur in ovl cause
            if self.hidden:                                     #teamid dont align. however if an admin force switches u the
                self.send_chat('you are no longer using pubovl')#script looses track of wether u r using ovl or not. 
                self.hidden = False                             #idk why i cant irc relay this. 

            return connection.on_team_changed(self, old_team)
            
    return protocol, pubovlConnection
