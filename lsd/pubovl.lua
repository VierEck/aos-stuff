--[[
pubovl

secretly join spectator to observe players without them knowing. 
also includes limbo spectating. 
based on the secret spectator feature of topo's ovl. 
some code is based on other parts of the lsd project by notaburner. 


VierEck.
]]


local mod = init_mod();
local lpu = lib_packet_unsafe;
local DUMMY_ID = MAX_PLAYERS;
local pubovl_users = pid_joined_table(nil);
local dummy_owners = pid_joined_table(nil);

local console_no_player_msg = {
	en="You can't give yourself pubovl unless you're in-game. ",
	de="Um pubovl zu nutzen muessen Sie dem Server beigetreten sein. "
};
local need_cap_msg = {
	en="You need the %(cap) capability to use pubovl. ",
	de="Sie brauchen %(cap) Zulassung um pubovl zu nutzen. "
};


local function create_dummy(pid)
	if (not get_client_char(pid) or not lpu) then
		return; --user probably on voxlap. voxlap is too dumb for the dummy
	end
	
	local block_col = get_block_color(pid);
	send_packet(
		pid, 
		lpu.str_existing_player( --TODO: when player score is added to the api, send the correct score here
			get_team(pid), get_gun(pid), get_tool(pid), --[[score]]0, 
			block_col[0], block_col[1], block_col[2], get_name(pid), DUMMY_ID
		)
	);
	
	local pos_t = {};
	local ori_t = {};
	for i=0, MAX_PLAYERS - 1 do
		if (is_alive(i)) then
			pos_t[i] = get_position(i)
			ori_t[i] = get_position(i)
		end
	end
	pos_t[DUMMY_ID] = get_position(pid);
	ori_t[DUMMY_ID] = get_orientation(pid);
	send_packet(pid, lpu.str_player_update(pos_t, ori_t, DUMMY_ID + 1));
	
	dummy_owners[pid] = true;
end

local function remove_dummy(pid)
	if (dummy_owners[pid]) then
		dummy_owners[pid] = false;
		if (lpu) then
			send_packet(pid, lpu.str_disconnect(DUMMY_ID));
		end
	end
end


local function become_pubovl_user(pid)
	pubovl_users[pid] = true;
	if (is_joined(pid)) then
		send_spawn_player(pid, get_position(pid), get_gun(pid), SPECTATOR, get_name(pid), pid);
		create_dummy(pid);
		if (not is_alive(pid)) then
			--dummy dies here instead.
			--death animation played again, but this is still better than
			--showing the dummy alive when it should be dead. 
			send_kill(pid, get_spawn_time(pid),5--[[team switch]], pid, pid);
		end
		return;
	end
	--if limbo
	--we dont know the pubovl user's name yet
	send_spawn_player(pid, get_position(pid), get_gun(pid), SPECTATOR, "Secret Deuce", pid);
end

local function revert_pubovl_user(pid)
	if (pubovl_users[pid]) then
		pubovl_users[pid] = false;
		if (is_joined(pid)) then
			remove_dummy(pid);
			local pos = get_position(pid);
			pos.z = pos.z + 2;
			send_spawn_player(pid, pos, get_gun(pid), get_team(pid), get_name(pid), pid);
			if (is_alive(pid)) then
				send_orientation(pid, get_orientation(pid));
			else
				send_kill(pid, get_spawn_time(pid),5--[[team switch]], pid, pid);
			end
		end
		--users in limbo must remove pubovl by joining a team. 
		--we dont know their actual name yet. 
	end
end

local dummy_owner_ruled_out = DUMMY_ID;
local function broadcast_rule_dummy_owner(pid)
	if (dummy_owner_ruled_out == pid) then
		return false;
	end
	return true;
end


function mod.send_packet(pid, data)
	if (lpu) then
		--is this slow? is there any better way?
		local pkt_id_str = string.sub(data, 1, 1);
		local pkt_id = tonumber(string.byte(pkt_id_str));
		if (pkt_id == 12 or pkt_id == 16) then
			local from = tonumber(string.byte(string.sub(data, 2, 2)));
			if (dummy_owners[from]) then
				local data_dummy = pkt_id_str .. string.char(DUMMY_ID) .. string.sub(data, 3);
				if (from == pid) then
					return mod.next.send_packet(pid, data_dummy);
				end
				if (pid < 0 or pid > MAX_PLAYERS - 1) then
					dummy_owner_ruled_out = from;
					lpu.broadcast(pid, data, broadcast_rule_dummy_owner);
					return send_packet(from, data_dummy);
				end
			end
		end
	end
	return mod.next.send_packet(pid, data);
end

function mod.on_join(pid, team, gun, name)
	revert_pubovl_user(pid)
	return mod.next.on_join(pid, team, gun, name);
end

function mod.on_switch(pid, team, gun)
	revert_pubovl_user(pid);
	return mod.next.on_switch(pid, team, gun);
end

function mod.on_disconnect(pid)
	revert_pubovl_user(pid);
	return mod.next.on_disconnect(pid);
end

function mod.finish_map_load()
	for i in piditer(PID_BROADCAST) do
		revert_pubovl_user(i);
	end
	return mod.next.finish_map_load();
end


local cmd = {name="pubovl", caps="pubovl", fakepid=true, usage="[player]", desc="secretly become spectator. "};
function cmd.func(pid, argv)
	cmd_assert(pid, cmd, #argv <= 1);
	local target_pid = pid;
	
	if (argv[1]) then
		if (not has_cap(pid, "pubovl")) then
			l10n_send_chat(pid, need_cap_msg, {cap="pubovl"});
			return;
		end
		target_pid = get_arg_pid("player", pid, cmd, argv[1]);
	end
	
	if (is_fakepid(target_pid)) then
		-- player was not specified and running pid is a fakepid, that's illegal
		send_usage(pid, cmd);
		l10n_send_chat(pid, console_no_player_msg);
		return;
	end
	
	if (pubovl_users[target_pid]) then
		revert_pubovl_user(target_pid);
	else
		become_pubovl_user(target_pid);
	end
end
register_command(cmd);


return mod;