'''
Command to not receive messages from a specific player. 
the message from that player is still sent to everyone else, just not to you.

This script is to be put high on the script hirarchie, 
above all other scripts that overwrite on_chat.

Authors:
	VierEck.
'''


from piqueserver.commands import command, target_player
from pyspades.contained import ChatMessage
from pyspades.constants import CHAT_ALL, CHAT_TEAM


@command("muteplayer", "mutep")
@target_player
def p_mute(c, pl):
	if c is pl:
		if len(c.MutePlayer_muted) <= 0:
			return "noone is muted by you"
		msg = "players you muted:\n"
		for plr in c.MutePlayer_muted:
			msg += "[#" + str(plr.player_id)
			if plr.name is not None:
				msg += ": " + plr.name
			msg += "], "
		return msg
	if pl in c.MutePlayer_muted:
		c.MutePlayer_muted.remove(pl)
		return pl.name + " unmuted"
	c.MutePlayer_muted.append(pl)
	return pl.name + " muted."

@command("unmuteall")
def unmuteall(c):
	c.MutePlayer_muted = []
	return "unmuted everyone"


def apply_script(pro, con, cfg):
	
	
	class MutePlayer_C(con):
		
		def __init__(c, *arg, **kw):
			con.__init__(c, *arg, **kw)
			c.MutePlayer_muted = []
		
		def on_chat(c, msg, is_global):
			#copy paste latter half of on_chat_message_recieved from source. modified
			p = c.protocol
			msg = msg.replace('\n', '')
			chat_pkt = ChatMessage()
			chat_pkt.chat_type = CHAT_ALL if is_global else CHAT_TEAM
			chat_pkt.value     = msg
			chat_pkt.player_id = c.player_id
			for pl in p.players.values():
				if not pl.deaf and (is_global or c.team is pl.team):
					if c in pl.MutePlayer_muted:
						continue
					pl.send_contained(chat_pkt)
			c.on_chat_sent(msg, is_global)
			return False #hijacks both on_chat and on_chat_message_recieved
		
		def on_disconnect(c):
			p = c.protocol
			for pl in p.players.values():
				if c in pl.MutePlayer_muted:
					pl.MutePlayer_muted.remove(c)
			return con.on_disconnect(c)
	
	
	return pro, MutePlayer_C
