'''
feetbuild

needs utils.py by sByte. 

/fb

build a block inside ur legs. 
combine this with fly.py by jipok to build blocks in the air. 
'''

from piqueserver.commands import command
@command("feetb")
def feetbuild(c):
	p = c.protocol
	x, y, z = c.get_location()
	z += 2 #spawn block inside feet
	p.create_block(coords=(x, y, z), save=True, color=c.color)

def apply_script(protocol, connection, config):
	return protocol, connection