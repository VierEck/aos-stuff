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
local OSBS_DUMMY_ID = MAX_PLAYERS;
local voxlap_dummy_id = 0;
local pubovl_users = pid_joined_table(nil);
local dummy_owners = pid_joined_table(nil); --if owner, contains their dummy id
local dummy_owners_count = 0;

local console_no_player_msg = {
	en="You can't give yourself pubovl unless you're in-game.",
	de="Um pubovl zu nutzen muessen Sie dem Server beigetreten sein."
};
local need_cap_msg = {
	en="You need the %(cap) capability to use pubovl.",
	de="Sie brauchen %(cap) Zulassung um pubovl zu nutzen."
};
local spec_no_pubovl_msg = {
	en="Spectators don't need pubovl.",
	de="Zuschauer brauchen kein pubovl."
};


local function create_dummy(pid)
	if (not lpu) then
		return;
	end
	
	if (not get_client_char(pid)) then
		if (voxlap_dummy_id >= MAX_PLAYERS) then
			return; --voxlap cant handle pid outside the valid pool.
		end
		dummy_owners[pid] = voxlap_dummy_id;
		
		send_spawn_player(
			pid, get_position(pid), get_gun(pid), get_team(pid), get_name(pid), dummy_owners[pid]
		);
	else
		--lets assume every client other than voxlap can handle pid outside the valid pool.
		--which they should if they want to be good clients.
		dummy_owners[pid] = OSBS_DUMMY_ID;
		
		local block_col = get_block_color(pid);
		send_packet(
			pid, 
			lpu.str_existing_player(
				get_team(pid) - 1, get_gun(pid), get_tool(pid), get_score(pid), 
				block_col.r, block_col.g, block_col.b, get_name(pid), dummy_owners[pid]
			)
		);
	end
	
	if (dummy_owners_count < 0) then
		dummy_owners_count = 0;
	end
	dummy_owners_count = dummy_owners_count + 1;
end

local function remove_dummy(pid)
	if (dummy_owners[pid]) then
		dummy_owners_count = dummy_owners_count - 1;
		if (dummy_owners_count < 0) then
			dummy_owners_count = 0;
		end
		
		if (lpu) then
			send_packet(pid, lpu.str_disconnect(dummy_owners[pid]));
		end
		dummy_owners[pid] = false;
	end
end

local function update_voxlap_dummy()
	local voxlap_dummy_owners = {};
	local new_voxlap_dummy_id = 0;
	for i in piditer(PID_BROADCAST) do
		if (new_voxlap_dummy_id == i) then
			new_voxlap_dummy_id = new_voxlap_dummy_id + 1;
		end
		if (dummy_owners[i] and dummy_owners[i] ~= OSBS_DUMMY_ID) then
			voxlap_dummy_owners[i] = true;
			remove_dummy(i);
		end
	end
	voxlap_dummy_id = new_voxlap_dummy_id;
	
	if (voxlap_dummy_id < MAX_PLAYERS) then
		for i, useless in pairs(voxlap_dummy_owners) do
			create_dummy(i);
		end
	end
end

local function become_pubovl_user(pid)
	if (get_team(pid) == SPECTATOR) then
		return; --spectators dont need pubovl
	end
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

function mod.send_spawn_player(pid, pos, gun, team, name, from)
	if (not lpu or not dummy_owners[from] or dummy_owners_count <= 0) then
		return mod.next.send_spawn_player(pid, pos, gun, team, name, from);
	end
	
	for i in piditer(pid) do
		if (i == from) then
			send_packet(i, lpu.str_spawn_player(pos.x, pos.y, pos.z, gun, team, name, dummy_owners[pid]));
		else
			mod.next.send_spawn_player(i, pos, gun, team, name, from);
		end
	end
end

function mod.send_kill(pid, spawndelta, type_, killer, from)
	if (not lpu or not dummy_owners[from] or dummy_owners_count <= 0) then
		return mod.next.send_kill(pid, spawndelta, type_, killer, from);
	end
	
	for i in piditer(pid) do
		if (i == from) then
			send_packet(i, lpu.str_kill(spawndelta, type_, killer, dummy_owners[pid]));
		else
			mod.next.send_kill(i, spawndelta, type_, killer, from);
		end
	end
end

function mod.send_move_input(pid, inputs, from)
	if (not lpu or not dummy_owners[from] or dummy_owners_count <= 0) then
		return mod.next.send_move_input(pid, inputs, from);
	end
	
	for i in piditer(pid) do
		if (i == from) then
			send_packet(i, lpu.str_move_input(inputs, dummy_owners[pid]));
		else
			mod.next.send_move_input(pid, inputs, from);
		end
	end
end

function mod.send_player_update(pid)
	if (not lpu or dummy_owners_count <= 0) then
		return mod.next.send_player_update(pid);
	end
	
	local pos_t = {};
	local ori_t = {};
	for i=0, MAX_PLAYERS - 1 do
		if (is_alive(i)) then
			pos_t[i] = get_position(i);
			ori_t[i] = get_orientation(i);
		end
	end
	for i in piditer(pid) do
		if (dummy_owners[i]) then
			local dodi = dummy_owners[i];
			pos_t[dodi] = get_position(i);
			ori_t[dodi] = get_orientation(i);
			send_packet(i, lpu.str_player_update(pos_t, ori_t, dodi + 1));
		else
			mod.next.send_player_update(i);
		end
	end
end

function mod.demand_fingerprint(pid)
	if (voxlap_dummy_id == pid) then
		update_voxlap_dummy();
	end
	return mod.next.demand_fingerprint(pid);
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


local cmd = {name="pubovl", caps="pubovl", fakepid=true, usage="[player]", desc="Secretly become spectator."};
function cmd.func(pid, argv)
	cmd_assert(pid, cmd, #argv <= 1);
	local target_pid = get_arg_pid_opt("player", pid, cmd, argv[1]) or pid;
	
	if (is_fakepid(target_pid)) then
		-- player was not specified and running pid is a fakepid, that's illegal
		send_usage(pid, cmd);
		l10n_send_chat(pid, console_no_player_msg);
		return;
	end
	
	if (get_team(target_pid) == SPECTATOR) then
		l10n_send_chat(pid, spec_no_pubovl_msg);
		return; 
	end
	
	if (pubovl_users[target_pid]) then
		revert_pubovl_user(target_pid);
	else
		become_pubovl_user(target_pid);
	end
end
register_command(cmd, mod);


return mod;