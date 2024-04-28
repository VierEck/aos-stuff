'''
translate a demo translation back into a replayable demo byte file


based on aos_replay by BR:
	https://github.com/BR-/aos_replay

Authors:
	VierEck.
	BR-
'''


from struct import pack


AOS_PROTOCOL_VER = 3 #0.75
AOS_REPLAY_VER   = 1
TRANSLATOR_VER   = 0


TOOL_IDs  = { "spade": 0, "block": 1, "weap" : 2, "nade": 3, }
WEAP_IDs  = { "semi" : 0, "smg"  : 1, "pump" : 2, }
BLOCK_IDs = { "block": 0, "lmb"  : 1, "rmb"  : 2, "nade": 3, }
KILL_IDs  = { "body" : 0, "head" : 1, "melee": 2, "nade": 3, "fall": 4, "team": 5, "class": 6, }

packets = {}


def get_nums(s): #either a list of ints or a list of floats. 
	is_float = False
	n = [""]
	for c in s:
		if c.isdigit():
			n[-1] += c
		elif c == ".":
			is_float = True
			n[-1] += c
		elif c == "-" and len(n[-1]) <= 0:
			n[-1] += c
		elif len(n[-1]) > 0:
			if n[-1] == "-":
				n = ""
			else:
				n.append("")
	if len(n[-1]) <= 0:
		n = n[:-1]
	for i in range(len(n)):
		n[i] = float(n[i]) if is_float else int(n[i])
	return n


def Positiondata(data):
	return pack("fff", *get_nums(data[0]))
packets[0] = Positiondata

def Orientationdata(data):
	return pack("fff", *get_nums(data[0]))
packets[1] = Orientationdata

def WorldUpdate(data):
	b = b""
	i = 0
	while i < len(data):
		b += pack("ffffff", *get_nums(data[i + 1]), *get_nums(data[i + 2]))
		i += 3
	return b
packets[2] = WorldUpdate

def Inputdata(data):
	inp_str = data[1].lower()
	inp     = 0
	if "up" in inp_str:
		inp |= 0b00000001
	if "down" in inp_str:
		inp |= 0b00000010
	if "left" in inp_str:
		inp |= 0b00000100
	if "right" in inp_str:
		inp |= 0b00001000
	if "jump" in inp_str:
		inp |= 0b00010000
	if "crouch" in inp_str:
		inp |= 0b00100000
	if "sneak" in inp_str:
		inp |= 0b01000000
	if "spring" in inp_str:
		inp |= 0b10000000
	return pack("BB", get_nums(data[0])[0], inp)
packets[3] = Inputdata

def WeaponInput(data):
	weap_str = data[1].lower()
	weap     = 0
	if "pri" in weap_str:
		inp |= 0b00000001
	if "sec" in weap_str:
		inp |= 0b00000010
	return pack("BB", get_nums(data[0])[0], weap)
packets[4] = WeaponInput

def SetHp(data):
	type_ = 0 #=fall
	if "weap" in data[1].lower():
		type_ = 1
	return pack("BBfff", get_nums(data[0])[0], type_, *get_nums(data[2]))
packets[5] = SetHp

def GrenadePacket(data):
	nums = [get_nums(data[0])[0]]
	for d in data[1:]:
		nums.extend(get_nums(d))
	return pack("Bfffffff", *nums)
packets[6] = GrenadePacket

def SetTool(data):
	tool = 0
	for k in TOOL_IDs.keys():
		if k in data[1]:
			tool = TOOL_IDs(k)
			break
	return pack("BB", get_nums(data[0])[0], tool)
packets[7] = SetTool

def SetColor(data):
	return pack("BBBB", get_nums(data[0])[0], *get_nums(data[1])[::-1])
packets[8] = SetColor	

def ExistingPlayer(data):
	nums = [0, 0, 0, 0, 0]
	nums[0] = get_nums(data[0])[0]
	nums[1] = get_nums(data[1])[0]
	for k in WEAP_IDs.keys():
		if k in data[2]:
			nums[2] = WEAP_IDs[k]
			break
	for k in TOOL_IDs.keys():
		if k in data[3]:
			nums[3] = TOOL_IDs[k]
			break
	nums[4] = get_nums(data[4])[0]
	nums.extend(get_nums(data[-2])[::-1])
	return pack("BBBBIBBB", *nums) + data[-1].encode("cp437")
packets[9] = ExistingPlayer

def ShortPlayer(data):
	nums = [get_nums(data[0])[0], 0, 0]
	nums[1] = get_nums(data[1])[0]
	for k in WEAP_IDs.keys():
		if k in data[2]:
			nums[2] = WEAP_IDs[k]
			break
	return pack("BBB", *nums)
packets[10] = ShortPlayer

def MoveObject(data):
	return pack("BBfff", get_nums(data[0])[0], get_nums(data[1])[0], *get_nums(data[2]))
packets[11] = MoveObject

def CreatePlayer(data):
	nums = [get_nums(data[0])[0], 0, 0]
	for k in WEAP_IDs.keys():
		if k in data[1]:
			nums[1] = WEAP_IDs[k]
			break
	nums[2] = get_nums(data[2])[0]
	nums.extend(get_nums(data[3]))
	return pack("BBBfff", *nums) + data[-1].encode("cp437")
packets[12] = CreatePlayer

def BlockAction(data):
	nums = [get_nums(data[0])[0], 0]
	for k in BLOCK_IDs.keys():
		if k in data[1]:
			nums[1] = BLOCK_IDs[k]
			break
	nums.extend(get_nums(data[2]))
	return pack("BBIII", *nums)
packets[13] = BlockAction

def BlockLine(data):
	return pack("BIIIIII", get_nums(data[0])[0], *get_nums(data[1]), *get_nums(data[2]))
packets[14] = BlockLine

def CTFState(data):
	pass #TODO

def TCState(data):
	pass #TODO

GAME_STATEs = { 0: CTFState, 1: TCState, }

def StateData(data):
	return False #TODO
packets[15] = StateData

def KillAction(data):
	nums = [0, 0, 0, 0]
	nums[0] = get_nums(data[0])[0]
	nums[1] = get_nums(data[1])[0]
	for k in KILL_IDs.keys():
		if k in data[2]:
			nums[2] = KILL_IDs[k]
	nums[3] = get_nums(data[3])[0]
	return pack("BBBB", *nums)
packets[16] = KillAction

def ChatMessage(data):
	type_ = 0
	if "team" in data[1]:
		type_ = 1
	elif "sys" in data[1]:
		type_ = 2
	return pack("BB", get_nums(data[0])[0], type_) + data[-1].encode("cp437")
packets[17] = ChatMessage

def MapStart(data):
	return pack("I", get_nums(data[0])[0])
packets[18] = MapStart

def MapChunk(data):
	print("ignoring MapChunk. cannot be retranslated")
	return False
packets[19] = MapChunk

def PlayerLeft(data):
	return pack("B", get_nums(data[0])[0])
packets[20] = PlayerLeft

def TerritoryCapture(data):
	nums[0, 0, 0, 0]
	nums[0] = get_nums(data[0])[0]
	if "w" in data[1]:
		nums[1] = 1
	nums[2] = get_nums(data[2])[0]
	nums[3] = get_nums(data[3])[0]
	return pack("BBBB", *nums)
packets[21] = TerritoryCapture

def ProgressBar(data):
	nums = [0, 0, 0, 0]
	for i in range(len(nums)):
		nums[i] = get_nums(data[i])[0]
	nums[3] /= 100
	return pack("BBbf", *nums)
packets[22] = ProgressBar

def IntelCapture(data):
	win = 1 if "w" in data[1] else 0
	return pack("BB", get_nums(data[0])[0], win)
packets[23] = IntelCapture

def IntelPickup(data):
	return pack("B", get_nums(data[0])[0])
packets[24] = IntelPickup

def IntelDrop(data):
	return pack("Bfff", get_nums(data[0])[0], *get_nums(data[1]))
packets[25] = IntelDrop

def Restock(data):
	return pack("B", get_nums(data[0])[0])
packets[26] = Restock

def FogColor(data):
	return pack("BBB", *get_nums(data[0])[::-1])
packets[27] = FogColor

def WeaponReload(data):
	return pack("BBB", get_nums(data[0])[0], get_nums(data[1])[0], get_nums(data[2])[0])
packets[28] = WeaponReload

def ChangeTeam(data):
	return pack("BB", get_nums(data[0])[0], get_nums(data[1])[0])
packets[29] = ChangeTeam

def ChangeWeapon(data):
	weap = 0
	for k in WEAP_IDs.keys():
		if k in data[1]:
			weap = WEAP_IDs[k]
			break
	return pack("BB", get_nums(data[0])[0], weap)
packets[30] = ChangeWeapon

def HandshakeInit(data):
	return pack("I", get_nums(data[0])[0])
packets[31] = HandshakeInit

def HandshakeResponse(data):
	return pack("I", get_nums(data[0])[0])
packets[32] = HandshakeResponse

def VersionGet(data):
	return b""
packets[33] = VersionGet

def VersionResponse(data):
	client = 'v' if len(data[0]) <= 8 else data[0][8].lower()
	nums   = ["", "", ""]
	i = 0
	for c in data[1]:
		if c.isdigit():
			nums[i] += c
		elif len(nums[i]) > 0:
			i += 1
			if i >= len(nums):
				break
	for j in range(len(nums)):
		nums[j] = 0 if len(nums[j]) <= 0 else int(nums[j])
	return pack("bbbb", client.encode("cp437"), *nums) + data[-1].encode("cp437")
packets[34] = VersionResponse



def retranslate(file_name):
	with open(file_name, "r") as of:
		if TRANSLATOR_VER != int(of.readline().split(":")[-1]):
			return -1
		if AOS_REPLAY_VER != int(of.readline().split(":")[-1]):
			return -2
		if AOS_PROTOCOL_VER != int(of.readline().split(":")[-1]):
			return -3
		with open(file_name + ".demo", "wb") as nf:
			nf.write(pack("BB", AOS_REPLAY_VER, AOS_PROTOCOL_VER))
			time = float(0)
			newTime = pkt_id = word = ""
			data = []
			while True:
				c = of.read(1)
				if c == "":
					break
				elif c == "[":
					newTime = pkt_id = word = ""
					data = []
				elif c == "]":
					try:
						data = packets[pkt_id](data)
						if type(data) is bytes:
							nf.write(pack("fHB", newTime - time, len(data) + 1, pkt_id))
							time = newTime
							nf.write(data)
					except Exception as e: #tell user where the mistake is in their (handwritten) demo txt
						print("Exception near packet (timestamp): " + str(time))
						print(e)
						return -4
				elif type(newTime) is str:
					if c.isdigit() or c == ".":
						newTime += c
					elif len(newTime) > 0:
						newTime = float(newTime)
				elif type(pkt_id) is str:
					if c.isdigit():
						pkt_id += c
					elif len(pkt_id) > 0:
						pkt_id = int(pkt_id)
				elif c == "(":
					word = ""
				elif c == ")":
					data.append(word)
				elif not c.isspace():
					word += c
			nf.close()
		of.close()
	return 0


if __name__ == "__main__":
	from os import path
	from argparse import ArgumentParser
	
	parser = ArgumentParser(description="Translate a demo translation into a demo file")
	parser.add_argument("file", help="File to read from")
	args = parser.parse_args()
	
	if path.exists(args.file):
		t = retranslate(args.file)
		if t == -1:
			print("wrong translator version")
		elif t == -2:
			print("wrong aos_replay version")
		elif t == -3:
			print("wrong aos protocol version")
	else:
		print("no such file exists")
