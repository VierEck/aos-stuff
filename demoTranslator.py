'''
Translate a demo into a readable text file.

based on aos_replay by BR
	https://github.com/BR-/aos_replay

Authors:
	VierEck.
	BR-
'''


from struct import unpack, calcsize


AOS_PROTOCOL_VER = 3 #0.75
AOS_REPLAY_VER   = 1

TOOL_IDs  = { 0: "spade", 1: "block", 2: "weap" , 3: "nade", }
WEAP_IDs  = { 0: "semi" , 1: "smg"  , 2: "pump" , }
BLOCK_IDs = { 0: "block", 1: "lmb"  , 2: "rmb"  , 3: "nade", }
KILL_IDs  = { 0: "body" , 1: "head" , 2: "melee", 3: "nade", 4: "fall", 5: "team", 6: "class", }

players    = {}
packets    = {}
pkt_filter = [ 2, 3, 4]
#recommended to filter worldupdate, inputdata and weapondata due to sheer amount of these in a demo.


def PositionData(data):
	x, y, z = unpack("fff", data[0:12])
	return ("00/PositionData: (pos: " 
		+ "{:5.2f}".format(x) + ", " + "{:5.2f}".format(y) + ", " + "{:5.2f}".format(z) + ")")
packets[0] = PositionData

def OrientationData(data):
	x, y, z = unpack("fff", data[0:12])
	return ("01/OrientationData: (ori: " 
		+ "{:5.2f}".format(x) + ", " + "{:5.2f}".format(y) + ", " + "{:5.2f}".format(z) + ")")
packets[1] = OrientationData

def WorldUpdate(data):
	info = ""
	i = 0
	j = -1
	while i < len(data):
		x, y, z, a, b, c = unpack("ffffff", data[i:i+24])
		i += 24
		j += 1
		for val in [x, y, z, a, b, c]:
			if val != 0:
				info += str(j)
				info += "(pos: " + "{:5.2f}".format(x) + ", " + "{:5.2f}".format(y) + ", " + "{:5.2f}".format(z) + ")"
				info += "(ori: " + "{:5.2f}".format(a) + ", " + "{:5.2f}".format(b) + ", " + "{:5.2f}".format(c) + "); "
				break;
	return "02/WorldUpdate: " + info
packets[2] = WorldUpdate

def InputData(data):
	pl_id = data[0]
	pl_info = str(pl_id)
	if pl_id in players:
		pl_info += ": " + players[pl_id]
	inp_info = ""
	if data[1] & 0b00000001:
		inp_info += "up "
	if data[1] & 0b00000010:
		inp_info += "down "
	if data[1] & 0b00000100:
		inp_info += "left "
	if data[1] & 0b00001000:
		inp_info += "right "
	if data[1] & 0b00010000:
		inp_info += "jump "
	if data[1] & 0b00100000:
		inp_info += "crouch "
	if data[1] & 0b01000000:
		inp_info += "sneak "
	if data[1] & 0b10000000:
		inp_info += "sprint "
	return "03/InputData: (" + pl_info + ")( " + inp_info + ")"
packets[3] = InputData

def WeaponInput(data):
	pl_id = data[0]
	pl_info = str(pl_id)
	if pl_id in players:
		pl_info += ": " + players[pl_id]
	weap_info = ""
	if data[1] & 0b00000001:
		weap_info += "pri "
	if data[1] & 0b00000010:
		weap_info += "sec "
	return "04/WeaponInput: (" + pl_info + ")( " + weap_info + ")"
packets[4] = WeaponInput

def SetHp(data):
	hp, type_, x, y, z = unpack("BBfff", data[0:14])
	sType = "fall" if not type_ else "weap"
	return ("05/SetHp: (hp: " + str(hp) + ")(type: " + sType
		+ ")(pos: " + "{:5.2f}".format(x) + ", " + "{:5.2f}".format(y) + ", " + "{:5.2f}".format(z) + ")")
packets[5] = SetHp

def GrenadePacket(data):
	pl_id = data[0]
	pl_name = ""
	if pl_id in players:
		pl_name = ": " + players[pl_id]
	fuse, x, y, z, a, b, c = unpack("fffffff", data[1:29])
	return ("06/GrenadePacket: (" + str(pl_id) + pl_name + ")(fuse: " + str(fuse) 
		+ ")(pos: " + "{:5.2f}".format(x) + ", " + "{:5.2f}".format(y) + ", " + "{:5.2f}".format(z) 
		+ ")(vel: " + "{:5.2f}".format(a) + ", " + "{:5.2f}".format(b) + ", " + "{:5.2f}".format(c) + ")")
packets[6] = GrenadePacket

def SetTool(data):
	pl_id = data[0]
	pl_name = ""
	if pl_id in players:
		pl_name = ": " + players[pl_id]
	return "07/SetTool: (" + str(pl_id) + pl_name + ")(tool: " + TOOL_IDs[data[1]] + ")"
packets[7] = SetTool

def SetColor(data):
	pl_id = data[0]
	pl_name = ""
	if pl_id in players:
		pl_name = ": " + players[pl_id]
	return ("08/SetColor: (" + str(pl_id) + pl_name 
		+ ")(color: " + str(data[3]) + ", " + str(data[2]) + ", " + str(data[1]) + ")")
packets[8] = SetColor	

def ExistingPlayer(data):
	pl_id = data[0]
	decode_name = data[11:-1].decode()
	pl_name = ""
	if pl_id in players:
		pl_name = ": " + players[pl_id]
	players[pl_id] = decode_name
	kills = unpack("B", data[4:8])
	return ("09/ExistingPlayer: (" + str(pl_id) + pl_name + ")(team: " + str(data[1]) 
		+ ")(weap: " + WEAP_IDs[data[2]] + ")(tool: " + TOOL_IDs[data[3]] + ")(kills: " + str(kills)
		+ ")(color: " + str[data[8]] + ", " + str[data[9]] + ", " + str[data[10]] + ")"
		+ "(name: " + decode_name + ")")
packets[9] = ExistingPlayer

def ShortPlayer(data):
	pl_id = data[0]
	pl_name = ""
	if pl_id in players:
		pl_name = ": " + players[pl_id]
	return ("10/ShortPlayer: (" + str(pl_id) + pl_name 
		+ ")(team: " + str(data[1]) + ")(weap: " + WEAP_IDs[data[2]] + ")")
packets[10] = ShortPlayer

def MoveObject(data):
	x, y, z = unpack("fff", data[2:14])
	return ("11/MoveObject: (obj: " + str(data[0]) + ")(team: " + str(data[1]) 
		+ ")(pos: " + "{:5.2f}".format(x) + ", " + "{:5.2f}".format(y) + ", " + "{:5.2f}".format(z) + ")")
packets[11] = MoveObject

def CreatePlayer(data):
	pl_id = data[0]
	decode_name = data[15:-1].decode()
	pl_name = ""
	if pl_id in players:
		pl_name = ": " + players[pl_id]
	players[pl_id] = decode_name
	x, y, z = unpack("fff", data[3:15])
	return ("12/CreatePlayer: (" + str(pl_id) + pl_name 
		+ ")(weap: " + WEAP_IDs[data[1]] + ")(team: " + str(data[2])
		+ ")(pos: " + "{:5.2f}".format(x) + ", " + "{:5.2f}".format(y) + ", " + "{:5.2f}".format(z)
		+ ")(name: " + decode_name + ")")
packets[12] = CreatePlayer

def BlockAction(data):
	pl_id = data[0]
	pl_name = ""
	if pl_id in players:
		pl_name = ": " + players[pl_id]
	x, y, z = unpack("fff", data[2:14])
	return ("13/BlockAction: (" + str(pl_id) + pl_name + ")(action: " + BLOCK_IDs[data[1]]
		+ ")(pos: " + "{:5.2f}".format(x) + ", " + "{:5.2f}".format(y) + ", " + "{:5.2f}".format(z) + ")")
packets[13] = BlockAction

def BlockLine(data):
	pl_id = data[0]
	pl_name = ""
	if pl_id in players:
		pl_name = ": " + players[pl_id]
	x, y, z, a, b, c = unpack("ffffff", data[1:25])
	return ("14/BlockLine: (" + str(pl_id) + pl_name
		+ ")(start: " + "{:5.2f}".format(x) + ", " + "{:5.2f}".format(y) + ", " + "{:5.2f}".format(z) 
		+ ")(end: " + "{:5.2f}".format(a) + ", " + "{:5.2f}".format(b) + ", " + "{:5.2f}".format(c) + ")")
packets[14] = BlockLine

def StateData(data):
	#TODO
	return "15/StateData: "
packets[15] = StateData

def KillAction(data):
	victim_id = data[0]
	victim_name = ""
	if victim_id in players:
		victim_name = ": " + players[victim_id]
	killer_id = data[1]
	killer_name = ""
	if killer_id in players:
		killer_name = ": " + players[killer_id]
	respawn_time = unpack("f", data[3:7])
	return ("16/KillAction: (victim: " + str(victim_id) + victim_name + ")(killer: " + str(killer_id) + killer_name 
		+ ")(type: " + KILL_IDs[data[2]] + ")(respawn: " + str(respawn_time) + ")")
packets[16] = KillAction

def ChatMessage(data):
	messenger = "#server" #afaik ppl r not allowed to have # infront their names so this is unambigious
	chat_type = "global"
	pl_id = data[0]
	if data[0] in players:
		messenger = players[pl_id]
	if data[1] == 1:
		chat_type = "team"
	return "17/ChatMessage: (" + chat_type + ", " + messenger + ": " + data[2:-1].decode() + ")"
packets[17] = ChatMessage

def MapStart(data):
	size = unpack("I", data)
	return "18/MapStart: (size: " + str(size[0]) + ")"
packets[18] = MapStart

def MapChunk(data):
	return "19/MapChunk: (size: " + str(len(data)) + ")"
packets[19] = MapChunk

def PlayerLeft(data):
	pl_info = "(player doesnt exist)"
	pl_id = data[0]
	if pl_id in players:
		pl_info = "(" + str(pl_id) + ": " + players[pl_id] + ")"
		del players[pl_id]
	return "20/PlayerLeft: " + pl_info
packets[20] = PlayerLeft

def TerritoryCapture(data):
	pl_id = data[0]
	pl_name = ""
	if pl_id in players:
		pl_name = ": " + players[pl_id]
	win = "win"
	if data[2] < 1:
		win = "lose"
	return ("20/TerritoryCapture: (" + str(pl_id) + pl_name 
		+ ")(obj: " + str(data[1]) + ")(" + win + ")(team: " + str(data[3]) + ")")
packets[21] = TerritoryCapture

def ProgressBar(data):
	rate, progress = unpack("bf", data[2:7])
	return ("21/ProgressBar: (obj: " + str(data[0]) + ")(team: " + str(data[1]) 
		+ ")(rate: " + str(rate) + ")(progress: " + "{:5.2f}".format(progress * 100) + "%)")
packets[22] = ProgressBar

def IntelCapture(data):
	pl_id = data[0]
	pl_name = ""
	if pl_id in players:
		pl_name = ": " + players[pl_id]
	win = "win"
	if data[2] < 1:
		win = "lose"
	return "23/IntelCapture: (" + str(pl_id) + pl_name + ")(" + win + ")"
packets[23] = IntelCapture

def IntelPickup(data):
	pl_id = data[0]
	pl_name = ""
	if pl_id in players:
		pl_name = ": " + players[pl_id]
	return "24/IntelPickup: (" + str(pl_id) + pl_name + ")"
packets[24] = IntelPickup

def IntelDrop(data):
	pl_id = data[0]
	pl_name = ""
	if pl_id in players:
		pl_name = ": " + players[pl_id]
	x, y, z = unpack("fff", data[1:13])
	return ("25/IntelDrop: (" + str(pl_id) + pl_name 
		+ ")(pos: " + "{:5.2f}".format(x) + ", " + "{:5.2f}".format(y) + ", " + "{:5.2f}".format(z) + ")")
packets[25] = IntelDrop

def Restock(data):
	pl_id = data[0]
	pl_name = ""
	if pl_id in players:
		pl_name = ": " + players[pl_id]
	return "26/Restock: (" + str(pl_id) + pl_name + ")"
packets[26] = Restock

def FogColor(data):
	return ("27/FogColor: " 
		+ ")(color: " + str(data[3]) + ", " + str(data[2]) + ", " + str(data[1]) + str(data[0]) + ")")
packets[27] = FogColor

def WeaponReload(data):
	pl_id = data[0]
	pl_name = ""
	if pl_id in players:
		pl_name = ": " + players[pl_id]
	return ("28/WeaponReload: (" + str(pl_id) + pl_name 
		+ ")(mag: " + str(data[1]) + ")(reserve: " + str(data[2]) + ")")
packets[28] = WeaponReload

def ChangeTeam(data):
	pl_id = data[0]
	pl_name = ""
	if pl_id in players:
		pl_name = ": " + players[pl_id]
	return "28/ChangeTeam: (" + str(pl_id) + pl_name + ")(team: " + str(data[1]) + ")"
packets[29] = ChangeTeam

def ChangeWeapon(data):
	pl_id = data[0]
	pl_name = ""
	if pl_id in players:
		pl_name = ": " + players[pl_id]
	return "29/ChangeWeapon: (" + str(pl_id) + pl_name + ")(weap: " + WEAP_IDs[data[1]] + ")"
packets[30] = ChangeWeapon

def HandshakeInit(data):
	return "31/HandshakeInit"
packets[31] = HandshakeInit

def HandshakeResponse(data):
	return "32/HandshakeResponse"
packets[32] = HandshakeResponse

def VersionGet(data):
	return "33/VersionGet"
packets[33] = VersionGet

def VersionResponse(data):
	major   = unpack("b", data[1])
	minor   = unpack("b", data[2])
	rev1    = unpack("b", data[3])
	rev2    = unpack("b", data[4])
	os_info = data[5:].decode()
	return ("34/VersionResponse: (client: " + data[0].decode()
		+ ")(ver: " + str(major) + "." + str(minor) + "." + str(rev1) + str(rev2) + ")(os: " + os_info + ")")
packets[34] = VersionResponse


def translate(file_name):
	with open(file_name, "rb") as of:
		of.read(2)
		#if unpack("B", of.read(1)) != AOS_REPLAY_VER or unpack("B", of.read(1)) != AOS_PROTOCOL_VER:
		#	return False
		with open(file_name + ".txt", "w") as nf:
			time = 0
			while True:
				fmt = "fH"
				fmtlen = calcsize(fmt)
				meta = of.read(fmtlen)
				if len(meta) < fmtlen:
					print("done")
					break
				dt, size = unpack(fmt, meta)
				time += dt
				data = of.read(size)
				pkt_id = data[0]
				if pkt_id in pkt_filter:
					continue
				nf.write("{:015.4f}".format(time) + ": ")
				if pkt_id in packets:
					nf.write("[" + packets[pkt_id](data[1:]) + "]")
				nf.write("\n")
			nf.close()
		of.close()

if __name__ == "__main__":
	from os import path
	from argparse import ArgumentParser
	
	parser = ArgumentParser(description="Translate a demo into a readable text file and vice versa.")
	parser.add_argument("file", help="File to read")
	args = parser.parse_args()
	
	if path.exists(args.file):
		if translate(args.file) is False:
			print("wrong aos_replay version or wrong aos protocol version")
	else:
		print("no such file exists")