--[[
lib_packet_unsafe

functions to generate strings containing packet data to be sent via the 
send_packet and send_packet_unreliable api functions. 
broadcast functions with callable parameter for customizable rules wether to 
send packet to player. broadcast functions dont have invalid pid checks. 


VierEck.
]]


if (lib_packet_unsafe) then 
	return;
end

local ffi = require("ffi");


lib_packet_unsafe = {}; --TODO: come up with better name?

	--rule_func(pid) make ur own callable rule to determine wether to send packet to a player
	function lib_packet_unsafe.broadcast(broadcast_id, data_str, rule_func)
		for i in piditer(broadcast_id) do
			if (not rule_func or rule_func(i)) then
				send_packet(i, data_str);
			end
		end
	end

	--rule_func(pid) make ur own callable rule to determine wether to send packet to a player
	function lib_packet_unsafe.broadcast_unreliable(broadcast_id, data_str, rule_func)
		for i in piditer(broadcast_id) do
			if (not rule_func or rule_func(i)) then
				send_packet_unreliable(i, data_str);
			end
		end
	end


--table append

	function lib_packet_unsafe.tbl_append_ubyte(t, t_len, n)
		--TODO: should ffi be used here?
		if (not n or n < 0) then
			n = 0;
		elseif (n > 255) then
			n = math.floor(n - math.floor(n / 2^8) * 2^8);
		else
			n = math.floor(n);
		end
		t_len = t_len + 1;
		t[t_len] = string.char(n);
		return t_len;
	end

	function lib_packet_unsafe.tbl_append_ushort(t, t_len, n)
		--TODO: should ffi be used here?
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, n);
		return tbl_append_ubyte(t, t_len, n / 2^8);
	end

	function lib_packet_unsafe.tbl_append_uint32(t, t_len, n)
		--TODO: should ffi be used here?
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, n);
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, n / 2^8);
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, n / 2^16);
		return lib_packet_unsafe.tbl_append_ubyte(t, t_len, n / 2^24);
	end
	
	function lib_packet_unsafe.tbl_append_uint64(t, t_len, n)
		--TODO: should ffi be used here?
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, n);
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, n / 2^8);
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, n / 2^16);
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, n / 2^24);
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, n / 2^32);
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, n / 2^40);
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, n / 2^48);
		return lib_packet_unsafe.tbl_append_ubyte(t, t_len, n / 2^56);
	end

	--loss of precision
	function lib_packet_unsafe.tbl_append_float(t, t_len, n)
		local f = ffi.new("float[1]");
		f[0] = n;
		local s = ffi.string(f, 4);
		for i = 1, 4 do 
			--if not done individually, 0 chars r lost on table.concat
			t[t_len + i] = string.sub(s, i, i);
		end
		return t_len + 4;
	end
	
	function lib_packet_unsafe.tbl_append_double(t, t_len, n)
		local d = ffi.new("double[1]");
		d[0] = n;
		local s = ffi.string(d, 8);
		for i = 1, 8 do 
			--if not done individually, 0 chars r lost on table.concat
			t[t_len + i] = string.sub(s, i, i);
		end
		return t_len + 8;
	end

	function lib_packet_unsafe.tbl_append_char(t, t_len, c)
		t_len = t_len + 1;
		t[t_len] = string.byte(c);
		return t_len;
	end

	--chars with 0 value may get lost
	function lib_packet_unsafe.tbl_append_str(t, t_len, s)
		t[t_len + 1] = s;
		return t_len + string.len(s);
	end


--string packet data

	function lib_packet_unsafe.str_position(x, y, z)
		local t = {string.char(0)}; --PositionData
		local t_len = lib_packet_unsafe.tbl_append_float(t, 1, x);
		t_len = lib_packet_unsafe.tbl_append_float(t, t_len, y);
		lib_packet_unsafe.tbl_append_float(t, t_len, z);
		return table.concat(t);
	end

	function lib_packet_unsafe.str_orientation(x, y, z)
		local t = {string.char(1)}; --OrientationData
		local t_len = lib_packet_unsafe.tbl_append_float(t, 1, x);
		t_len = lib_packet_unsafe.tbl_append_float(t, t_len, y);
		lib_packet_unsafe.tbl_append_float(t, t_len, z);
		return table.concat(t);
	end

	--pos_t and ori_t index start at 0.
	--pos_ori_len == (highest index with entry not nil) + 1, 
	function lib_packet_unsafe.str_player_update(pos_t, ori_t, pos_ori_len)
		local t = {string.char(2)}; --WorldUpdate
		local t_len = 1;
		for i=0, pos_ori_len - 1 do
			if (not pos_t[i]) then
				for k=1, 12 do
					t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, 0);
				end
			else
				t_len = lib_packet_unsafe.tbl_append_float(t, t_len, pos_t[i].x);
				t_len = lib_packet_unsafe.tbl_append_float(t, t_len, pos_t[i].y);
				t_len = lib_packet_unsafe.tbl_append_float(t, t_len, pos_t[i].z);
			end
			if (not ori_t[i]) then
				for k=1, 12 do
					t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, 0);
				end
			else
				t_len = lib_packet_unsafe.tbl_append_float(t, t_len, ori_t[i].x);
				t_len = lib_packet_unsafe.tbl_append_float(t, t_len, ori_t[i].y);
				t_len = lib_packet_unsafe.tbl_append_float(t, t_len, ori_t[i].z);
			end
		end
		return table.concat(t);
	end

	function lib_packet_unsafe.str_move_input(from, forward, backward, left, right, jump, crouch, sneak, sprint)
		local t = {string.char(3)}; --InputData
		lib_packet_unsafe.tbl_append_ubyte(t, 1, from);
		local n = 0;
		if (forward) then
			n = n + 1;
		end
		if (backward) then
			n = n + 2;
		end
		if (left) then
			n = n + 4;
		end
		if (right) then
			n = n + 8;
		end
		if (jump) then
			n = n + 16;
		end
		if (crouch) then
			n = n + 32;
		end
		if (sneak) then
			n = n + 64;
		end
		if (sprint) then
			n = n + 128;
		end
		lib_packet_unsafe.tbl_append_ubyte(t, 2, n);
		return table.concat(t);
	end

	function lib_packet_unsafe.str_mouse_input(primary, secondary, from)
		local t = {string.char(4)}; --WeaponInput
		lib_packet_unsafe.tbl_append_ubyte(t, 1, from);
		local n = 0;
		if (primary) then
			n = n + 1;
		end
		if (secondary) then
			n = n + 2;
		end
		lib_packet_unsafe.tbl_append_ubyte(t, 2, n);
		return table.concat(t);
	end

	--c2s. useless?
	function lib_packet_unsafe.str_hit_packet(from, hit_type)
		local t = {string.char(5)}; --HitPacket
		lib_packet_unsafe.tbl_append_ubyte(t, 1, from);
		lib_packet_unsafe.tbl_append_ubyte(t, 2, hit_type);
		return table.concat(t);
	end
	
	--s2c
	function lib_packet_unsafe.str_set_hp(hp, hit_type, x, y, z)
		local t = {string.char(5)}; --SetHP
		local t_len = lib_packet_unsafe.tbl_append_ubyte(t, 1, hit_type);
		t_len = lib_packet_unsafe.tbl_append_float(t, t_len, x);
		t_len = lib_packet_unsafe.tbl_append_float(t, t_len, y);
		lib_packet_unsafe.tbl_append_float(t, t_len, z);
		return table.concat(t);
	end
	
	function lib_packet_unsafe.str_grenade(pos_x, pos_y, pos_z, vel_x, vel_y, vel_z, fuse, from)
		local t = {string.char(6)}; --GrenadePacket
		local t_len = lib_packet_unsafe.tbl_append_ubyte(t, 1, from);
		t_len = lib_packet_unsafe.tbl_append_float(t, t_len, fuse);
		t_len = lib_packet_unsafe.tbl_append_float(t, t_len, pos_x);
		t_len = lib_packet_unsafe.tbl_append_float(t, t_len, pos_y);
		t_len = lib_packet_unsafe.tbl_append_float(t, t_len, pos_z);
		t_len = lib_packet_unsafe.tbl_append_float(t, t_len, vel_x);
		t_len = lib_packet_unsafe.tbl_append_float(t, t_len, vel_y);
		lib_packet_unsafe.tbl_append_float(t, t_len, vel_z);
		return table.concat(t);
	end
	
	function lib_packet_unsafe.str_set_tool(tool)
		local t = {string.char(7)}; --SetTool
		lib_packet_unsafe.tbl_append_ubyte(tool);
		return table.concat(t);
	end
	
	function lib_packet_unsafe.str_set_block_color(block_r, block_g, block_b)
		local t = {string.char(8)}; --SetColor
		local t_len = lib_packet_unsafe.tbl_append_ubyte(t, 1, block_b);
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, block_g);
		lib_packet_unsafe.tbl_append_ubyte(t, t_len, block_r);
		return table.concat(t);
	end

	function lib_packet_unsafe.str_existing_player(team, gun, tool, score, block_r, block_g, block_b, name, from)
		local t = {string.char(9)}; --ExistingPlayer
		local t_len = lib_packet_unsafe.tbl_append_ubyte(t, 1, from);
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, team);
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, gun);
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, tool);
		t_len = lib_packet_unsafe.tbl_append_uint32(t, t_len, score);
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, block_b);
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, block_g);
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, block_r);
		lib_packet_unsafe.tbl_append_str(t, t_len, name);
		return table.concat(t);
	end

	function lib_packet_unsafe.str_short_player(team, gun, from)
		local t = {string.char(10)}; --ShortPlayer
		local t_len = lib_packet_unsafe.tbl_append_ubyte(t, 1, from);
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, team);
		lib_packet_unsafe.tbl_append_ubyte(t, t_len, gun);
		return table.concat(t);
	end
	
	function lib_packet_unsafe.str_move_object(pos_x, pos_y, pos_z, id, team)
		local t = {string.char(11)}; --MoveObject
		local t_len = lib_packet_unsafe.tbl_append_ubyte(t, 1, id);
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, id);
		t_len = lib_packet_unsafe.tbl_append_float(t, t_len, pos_x);
		t_len = lib_packet_unsafe.tbl_append_float(t, t_len, pos_y);
		lib_packet_unsafe.tbl_append_float(t, t_len, pos_z);
		return table.concat(t);
	end
	
	function lib_packet_unsafe.str_spawn_player(pos_x, pos_y, pos_z, gun, team, name, from)
		local t = {string.char(12)}; --CreatePlayer
		local t_len = lib_packet_unsafe.tbl_append_ubyte(t, 1, from);
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, gun);
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, team);
		t_len = lib_packet_unsafe.tbl_append_float(t, t_len, pos_x);
		t_len = lib_packet_unsafe.tbl_append_float(t, t_len, pos_y);
		t_len = lib_packet_unsafe.tbl_append_float(t, t_len, pos_z);
		lib_packet_unsafe.tbl_append_str(t, t_len, name);
		return table.concat(t);
	end
	
	function lib_packet_unsafe.str_block_action(pos_x, pos_y, pos_z, type_, from)
		local t = {string.char(13)} --BlockAction
		local t_len = lib_packet_unsafe.tbl_append_ubyte(t, 1, from);
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, 1, type_);
		t_len = lib_packet_unsafe.tbl_append_uint32(t, t_len, pos_x);
		t_len = lib_packet_unsafe.tbl_append_uint32(t, t_len, pos_y);
		lib_packet_unsafe.tbl_append_uint32(t, t_len, pos_z);
		return table.concat(t);
	end
	
	function lib_packet_unsafe.str_block_line(start_x, start_y, start_z, end_x, end_y, end_z, from)
		local t = {string.char(14)} --BlockLine
		local t_len = lib_packet_unsafe.tbl_append_ubyte(t, 1, from);
		t_len = lib_packet_unsafe.tbl_append_uint32(t, t_len, start_x);
		t_len = lib_packet_unsafe.tbl_append_uint32(t, t_len, start_y);
		t_len = lib_packet_unsafe.tbl_append_uint32(t, t_len, start_z);
		t_len = lib_packet_unsafe.tbl_append_uint32(t, t_len, end_x);
		t_len = lib_packet_unsafe.tbl_append_uint32(t, t_len, end_y);
		lib_packet_unsafe.tbl_append_uint32(t, t_len, end_z);
		return table.concat(t);
	end
	
	--TODO: 15 StateData
	
	function lib_packet_unsafe.str_kill(spawndelta, type_, killer, from)
		local t = {string.char(16)}; --KillAction
		local t_len = lib_packet_unsafe.tbl_append_ubyte(t, 1, from);
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, killer);
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, type_);
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, spawndelta);
		return table.concat(t);
	end
	
	function lib_packet_unsafe.str_chat(msg, type_, from)
		local t = {string.char(17)}; --ChatMessage
		local t_len = lib_packet_unsafe.tbl_append_ubyte(t, 1, from);
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, type_);
		lib_packet_unsafe.tbl_append_str(t, t_len, msg);
		return table.concat(t);
	end
	
	function lib_packet_unsafe.str_map_start(size)
		local t = {string.char(18)}; --MapStart
		lib_packet_unsafe.tbl_append_uint32(t, 1, size);
		return table.concat(t);
	end
	
	--TODO: 19 MapChunk

	function lib_packet_unsafe.str_disconnect(from)
		local t = {string.char(20)}; --PlayerLeft
		lib_packet_unsafe.tbl_append_ubyte(t, 1, from);
		return table.concat(t);
	end

	function lib_packet_unsafe.str_territory_capture(id, win, team, from)
		local t = {string.char(21)}; --TerritoryCapture
		local t_len = lib_packet_unsafe.tbl_append_ubyte(t, 1, from);
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, id);
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, win);
		lib_packet_unsafe.tbl_append_ubyte(t, t_len, team);
		return table.concat(t);
	end

	function lib_packet_unsafe.str_progress_bar(id, team, rate, progress)
		local t = {string.char(22)}; --ProgressBar
		local t_len = lib_packet_unsafe.tbl_append_ubyte(t, 1, id);
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, team);
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, rate);
		lib_packet_unsafe.tbl_append_float(t, t_len, progress);
		return table.concat(t);
	end
	
	function lib_packet_unsafe.str_intel_capture(win, from)
		local t = {string.char(23)}; --IntelCapture
		local t_len = lib_packet_unsafe.tbl_append_ubyte(t, 1, from);
		lib_packet_unsafe.tbl_append_ubyte(t, t_len, win);
		return table.concat(t);
	end
	
	function lib_packet_unsafe.str_intel_pickup(from)
		local t = {string.char(24)}; --IntelPickup
		lib_packet_unsafe.tbl_append_ubyte(t, 1, from);
		return table.concat(t);
	end
	
	function lib_packet_unsafe.str_intel_drop(pos_x, pos_y, pos_z, from)
		local t = {string.char(25)}; --IntelDrop
		local t_len = lib_packet_unsafe.tbl_append_ubyte(t, 1, from);
		t_len = lib_packet_unsafe.tbl_append_float(t, t_len, pos_x);
		t_len = lib_packet_unsafe.tbl_append_float(t, t_len, pos_y);
		lib_packet_unsafe.tbl_append_float(t, t_len, pos_z);
		return table.concat(t);
	end
	
	function lib_packet_unsafe.str_restock(from)
		local t = {string.char(26)}; --Restock
		lib_packet_unsafe.tbl_append_ubyte(t, 1, from);
		return table.concat(t);
	end
	
	function lib_packet_unsafe.str_fog(red, green, blue, alpha)
		local t = {string.char(27)}; --FogColor
		local t_len = lib_packet_unsafe.tbl_append_ubyte(t, 1, alpha or 0);
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, blue);
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, green);
		lib_packet_unsafe.tbl_append_ubyte(t, t_len, red);
		return table.concat(t);
	end
	
	function lib_packet_unsafe.str_reload(mag, reserve, from)
		local t = {string.char(28)}; --WeaponReload
		local t_len = lib_packet_unsafe.tbl_append_ubyte(t, 1, from);
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, mag);
		lib_packet_unsafe.tbl_append_ubyte(t, t_len, reserve);
		return table.concat(t);
	end
	
	function lib_packet_unsafe.str_change_team(team, from)
		local t = {string.char(29)}; --ChangeTeam
		local t_len = lib_packet_unsafe.tbl_append_ubyte(t, 1, from);
		lib_packet_unsafe.tbl_append_ubyte(t, t_len, team);
		return table.concat(t);
	end
	
	function lib_packet_unsafe.str_change_weapon(gun, from)
		local t = {string.char(30)}; --ChangeWeapon
		local t_len = lib_packet_unsafe.tbl_append_ubyte(t, 1, from);
		lib_packet_unsafe.tbl_append_ubyte(t, t_len, gun);
		return table.concat(t);
	end
	
	function lib_packet_unsafe.str_handshake_init(challenge)
		local t = {string.char(31)}; --HandShakeInit
		lib_packet_unsafe.tbl_append_uint32(t, 1, challenge);
		return table.concat(t);
	end
	
	function lib_packet_unsafe.str_handshake_return(challenge)
		local t = {string.char(32)}; --HandShakeReturn
		lib_packet_unsafe.tbl_append_uint32(t, 1, challenge);
		return table.concat(t);
	end
	
	function lib_packet_unsafe.str_version_request()
		return string.char(33); --VersionRequest
	end
	
	function lib_packet_unsafe.str_version_response(id_char, major, minor, patch, msg)
		local t = {string.char(34)}; --VersionResponse
		local t_len = lib_packet_unsafe.tbl_append_char(t, 1, id_char);
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, major);
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, minor);
		t_len = lib_packet_unsafe.tbl_append_ubyte(t, t_len, patch);
		lib_packet_unsafe.tbl_append_str(t, t_len, msg);
		return table.concat(t);
	end
	
	--TODO: 60 ProtocolExtensionInfo
	
--end lib_packet_unsafe