'''
LimbOVL. Secret Spectating from limbo.


Authors: 
	VierEck.
'''


from ipaddress import ip_address
from twisted.internet.reactor import callLater
from piqueserver.commands import command
from pyspades.contained import CreatePlayer


def notification(c, msg):
	p = c.protocol
	if c in p.players.values():
		c.send_chat(msg)
		if "you are" == msg[:7].lower():
			msg = c.name + " is " + msg[7:]
	p.irc_say("* " + msg)


def do_limbovl(pl):
	create_pkt = CreatePlayer()
	create_pkt.player_id = pl.player_id
	create_pkt.name      = "secret Deuce"
	create_pkt.weapon    = 0
	create_pkt.team      = -1
	create_pkt.x, create_pkt.y, create_pkt.z = 256, 256, 0
	pl.send_contained(create_pkt)
	notification(pl, "you are now using LimbOVL")


@command("limbovl", "lovl", admin_only=True)
def limbovl(c, ip):
	p = c.protocol
	ip = ip_address(str(ip))
	for pl in p.connections.values():
		if pl.name is None and ip == ip_address(pl.address[0]):
			do_limbovl(pl)
			return
	p.limbovl_ip_list.append(ip)
	def remove_ip():
		if ip in p.limbovl_ip_list:
			p.limbovl_ip_list.remove(ip)
	callLater(300, remove_ip)
	notification(c, "ip %s marked for LimbOVL. you have 5min to connect" % ip)


def apply_script(pro, con, cfg):
	
	
	class limbovl_C(con):
		
		def on_join(c) -> None:
			p = c.protocol
			if ip_address(c.address[0]) in p.limbovl_ip_list:
				def send_a_bit_later():
					p.limbovl_ip_list.remove(ip_address(c.address[0]))
					do_limbovl(c)
				callLater(1, send_a_bit_later)
			return con.on_join(c)
	
	
	class limbovl_P(pro):
		limbovl_ip_list = []
	
	
	return limbovl_P, limbovl_C
