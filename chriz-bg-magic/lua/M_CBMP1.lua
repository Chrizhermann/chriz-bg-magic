-- The main character as a statue or imprisoned: not the end of the game.
--
-- * A screen (opcode 403) on him turns incoming petrification (opcode 134, opcode 13 "stoned") and
--   imprisonment (opcode 211) into this mod's states, CBMP1ST and CBMP1IM. The screen sees an effect
--   before the engine rolls its save and checks immunity, so it blocks the effect and casts the
--   state through opcode 146 with the old effect's save; Protection from Petrification and the like
--   (opcode 101) are checked here. Stone to Flesh (opcode 43) ends the statue; Freedom (opcode 212)
--   ends the prison only in the area where he vanished, and puts him back on that spot.
-- * While a creature is imprisoned the engine does not keep its spell states up (lab: they read
--   unset, and bits written into its stats are wiped within seconds). So the prison is read from
--   his effect list, the travel hooks compare against a cell the tick keeps, and scripts get the
--   global CBM_P1_OUT.
-- * Travel: the party takes him along. Two jump hooks in the engine's gather check let him pass
--   like a dead member while he is out; the engine then moves him with the party.
-- * The world scripts call CBMP1_Tick(): it ends the game when nobody else can act, imprisons him
--   again after a cutscene freed him, and pulls him after the party when a script split them.
-- * Companions keep the game's petrification and imprisonment, which put them out of the party
--   and empty their party AI slot. The screen keeps that script first; when Stone to Flesh or
--   Freedom brings them back, they rejoin the party (if there is room) with their script.
--
-- Nothing of this shows a technical message in the game; problems go to the log. LuaJIT syntax.

if not (EEex_GameObject_ApplyEffect and EEex_HookConditionalJumpOnFailWithLabels and EEex_LabelDefault
        and EEex_Utility_IterateCPtrList and EEex_Sprite_GetSpellState and EEex_GameObject_Get
        and EEex_Sprite_GetCharacterIndex and EEex_AIBase_GetScriptLevel and EEex_AIBase_SetScriptLevelResRef
        and EEex_Malloc and EEex_WritePtr and EEex_HookIntegrityWatchdogRegister and EEex_FlattenTable
        and EEex_GameState_GetGlobalInt and EEex_GameState_SetGlobalInt) then
    return
end

CBMPlayer1 = CBMPlayer1 or {}
local P = CBMPlayer1

P.NET, P.OUT, P.STATUE, P.PRISON = %CBM_P1_NET_STATE%, %CBM_P1_OUT_STATE%, %CBM_P1_STATUE_STATE%, %CBM_P1_PRISON_STATE%
P.STATUE_SPELL, P.PRISON_SPELL, P.CURE_SPELL, P.FREE_SPELL, P.NET_SPELL = "CBMP1ST", "CBMP1IM", "CBMP1CU", "CBMP1FR", "CBMP1NT"
P.PRISON_DURATION = 60000000

local function log(text)
    print("chriz-bg-magic: main character: " .. text)
end

local function game()
    return EngineGlobals.g_pBaldurChitin.m_pObjectGame
end

-- The main character is the first character by join order, as for the engine's game over.
function P.protagonist()
    local id = game().m_characters:get(0)
    if not id or id == -1 then return nil end
    return EEex_GameObject_Get(id)
end

local function is_protagonist(sprite)
    local p1 = P.protagonist()
    return p1 ~= nil and p1.m_id == sprite.m_id
end

local function has(sprite, state)
    return EEex_Sprite_GetSpellState(sprite, state)
end

local function pending(effect)
    local timing = EEex_BAnd(effect.m_durationType, 0xFF)
    return timing >= 3 and timing <= 8
end

-- Immunity to an opcode (opcode 101) from equipment or timed effects.
function P.immune(sprite, opcode)
    local found = false
    local function look(effect)
        if not found and effect.m_effectId == 101 and effect.m_dWFlags == opcode and not pending(effect) then
            found = true
        end
    end
    EEex_Utility_IterateCPtrList(sprite.m_equipedEffectList, look)
    EEex_Utility_IterateCPtrList(sprite.m_timedEffectList, look)
    return found
end

-- Cast one of our spells on him in place of an incoming effect, with that effect's save, level and
-- source, so that the save, spell immunities and resource protections still decide.
local function cast_instead(sprite, effect, spell)
    EEex_GameObject_ApplyEffect(sprite, {
        effectID = 146, dwFlags = 1, res = spell, durationType = 1,
        spellLevel = effect.m_spellLevel,
        savingThrow = effect.m_savingThrow, saveMod = effect.m_saveMod,
        sourceID = effect.m_sourceId, sourceTarget = sprite.m_id,
        m_sourceRes = effect.m_sourceRes:get(), m_sourceType = effect.m_sourceType,
    })
end

local function stoned(effect)
    return effect.m_effectId == 13 and EEex_BAnd(effect.m_dWFlags, 0x10) ~= 0
end

local function current_area(sprite)
    return sprite.m_pArea and sprite.m_pArea.m_resref:get() or ""
end

local function at_prison_place(sprite)
    return current_area(sprite):upper() == (EEex_Sprite_GetLocalString(sprite, "CBMP1AR") or ""):upper()
end

-- What he carries of ours, read from his effect list.
function P.scan(sprite)
    local found = {net = false, statue = false, marker = false, maze = false}
    EEex_Utility_IterateCPtrList(sprite.m_timedEffectList, function(effect)
        local id = effect.m_effectId
        if id == 403 then
            if effect.m_res:get():upper() == "CBMP1SCR" then found.net = true end
        elseif id == 328 then
            local source = effect.m_sourceRes:get():upper()
            if source == P.STATUE_SPELL and effect.m_dWFlags == P.STATUE then found.statue = true end
            if source == P.PRISON_SPELL and effect.m_dWFlags == P.PRISON then found.marker = true end
        elseif id == 213 then
            if effect.m_sourceRes:get():upper() == P.PRISON_SPELL then found.maze = true end
        end
    end)
    return found
end

-- A companion: the game's own petrification and imprisonment stay, without the return bug.
local function companion(effect, sprite)
    local id = effect.m_effectId
    if id == 134 or stoned(effect) or id == 211 then
        if EEex_Sprite_GetCharacterIndex(sprite) > 0 then
            local script = EEex_AIBase_GetScriptLevel(sprite, 7)
            local player = 0
            pcall(function() if script and script.m_bPlayerScript ~= 0 then player = 1 end end)
            EEex_Sprite_SetLocalString(sprite, "CBMP1DS", script and script.cResRef:get() or "")
            EEex_Sprite_SetLocalInt(sprite, "CBMP1PS", player)
            EEex_Sprite_SetLocalInt(sprite, "CBMP1KO", 1)
        end
    elseif (id == 43 or id == 212) and EEex_Sprite_GetLocalInt(sprite, "CBMP1KO") == 1
            and EEex_Sprite_GetCharacterIndex(sprite) < 0 then
        EEex_Action_QueueResponseStringOnAIBase('SetGlobal("KickedOut","LOCALS",0)\nJoinParty()', sprite)
        log("a companion comes back")
    end
    return false
end

local function screen(effect, sprite)
    if not is_protagonist(sprite) then return companion(effect, sprite) end
    local id = effect.m_effectId
    if id == 134 or stoned(effect) then
        if has(sprite, P.STATUE) or P.immune(sprite, 134) then return true end
        cast_instead(sprite, effect, P.STATUE_SPELL)
        return true
    elseif id == 211 then
        if P.immune(sprite, 211) or P.scan(sprite).marker then return true end
        -- Where he stands now is where Freedom must find him.
        EEex_Sprite_SetLocalString(sprite, "CBMP1AR", current_area(sprite))
        EEex_Sprite_SetLocalInt(sprite, "CBMP1X", sprite.m_pos.x)
        EEex_Sprite_SetLocalInt(sprite, "CBMP1Y", sprite.m_pos.y)
        cast_instead(sprite, effect, P.PRISON_SPELL)
        return true
    elseif id == 43 then
        if has(sprite, P.STATUE) then
            cast_instead(sprite, effect, P.CURE_SPELL)
            -- Orders given to the statue wait in its queue; none of them may run late.
            EEex_Action_QueueResponseStringOnAIBase("ClearActions(Myself)", sprite)
            log("Stone to Flesh")
        end
        return false
    elseif id == 212 then
        -- A maze brings a Freedom of its own, set for the end of its duration: that one is no cast
        -- Freedom. A cast one works only where he vanished; the tick then tidies up after it.
        if pending(effect) then return false end
        return P.scan(sprite).marker and not at_prison_place(sprite)
    end
    return false
end

P.errors = P.errors or 0
function CBMP1SCR(op403, effect, sprite)
    local ok, result = pcall(screen, effect, sprite)
    if ok then return result == true end
    P.errors = P.errors + 1
    if P.errors <= 10 then log("screen error: " .. tostring(result)) end
    return false
end

-- Travel. The gather check of LeaveArea (map edge, world map) and LeaveAreaName (exits) skips dead
-- members ("test [rax], 800h; jne"). The hooks let one more member skip the same way: the one whose
-- address stands in a cell the tick keeps, the main character while he is out. rdi is the member;
-- rax is free there (both paths load it anew). The hook's own labels need #L(...): a bare
-- "je jmp_success" assembles to a jump to the next instruction.
P.hook = P.hook or {status = "not installed"}

local function expected(address)
    local want = {0x0F, 0x85, false, false, false, false, 0x33, 0xD2, 0x48, 0x8B, 0xCF}
    for i = 1, #want do
        if want[i] and EEex_ReadU8(address + i - 1) ~= want[i] then return false end
    end
    return true
end

function P.install_travel()
    local hook = P.hook
    if hook.done then return end
    hook.done = true
    local addresses = {}
    for _, label in ipairs({"CBMP1-LeaveArea-DeadTest", "CBMP1-LeaveAreaName-DeadTest"}) do
        local address = EEex_LabelDefault(label, nil)
        if not address then hook.status = "off: pattern " .. label .. " not found" log("travel: " .. hook.status) return end
        if not expected(address) then hook.status = "off: other code at " .. label log("travel: " .. hook.status) return end
        addresses[#addresses + 1] = address
    end
    local cell = EEex_Malloc(8)
    EEex_WritePtr(cell, 0)
    EEex_DisableCodeProtection()
    local ok, err = pcall(function()
        for _, address in ipairs(addresses) do
            EEex_HookConditionalJumpOnFailWithLabels(address, 5, {
                {"hook_integrity_watchdog_ignore_registers", {EEex_HookIntegrityWatchdogRegister.RAX}}},
                EEex_FlattenTable({{[[
                    mov rax, qword ptr ds:[#$(1)] ]], {cell}, [[ #ENDL
                    cmp rdi, rax
                    je #L(jmp_success)
                ]]}}))
        end
    end)
    EEex_EnableCodeProtection()
    if ok then hook.cell = cell end
    hook.status = ok and "active" or ("off: " .. tostring(err))
    log("travel: " .. hook.status)
end

-- Who is out, for the hooks (the cell) and for scripts (the global).
local function set_out(sprite)
    if P.hook.cell then EEex_WritePtr(P.hook.cell, sprite and EEex_UDToPtr(sprite) or 0) end
    local value = sprite and 1 or 0
    if EEex_GameState_GetGlobalInt("CBM_P1_OUT") ~= value then EEex_GameState_SetGlobalInt("CBM_P1_OUT", value) end
end

-- The world tick, about once a second from the top of the campaign world scripts. Returns true when
-- the game must end.
P.last = P.last or -1
local STATE_DEAD, STATE_CHARMED = 0x800, 0x1000

local function party()
    local out = {}
    for i = 0, 5 do
        local id = game().m_characters:get(i)
        if id and id ~= -1 then
            local s = EEex_GameObject_Get(id)
            if s then out[#out + 1] = s end
        end
    end
    return out
end

local function can_act(s)
    local state = EEex_Sprite_GetState(s)
    if EEex_BAnd(state, STATE_DEAD) ~= 0 or EEex_BAnd(state, STATE_CHARMED) ~= 0 then return false end
    return s.m_activeImprisonment ~= 0
end

-- A companion back in the party: the party AI script it had comes back. The game emptied the slot
-- when it left, and joining puts a standard script there (lab: DPLAYER2). One whose save kept it
-- in the party just loses the mark.
local function companion_back(s)
    local stored = EEex_Sprite_GetLocalString(s, "CBMP1DS") or ""
    if stored ~= "" and EEex_AIBase_GetScriptLevelResRef(s, 7):upper() ~= stored:upper() then
        EEex_AIBase_SetScriptLevelResRef(s, 7, stored, EEex_Sprite_GetLocalInt(s, "CBMP1PS") == 1)
        log("party AI script back: " .. stored)
    end
    EEex_Sprite_SetLocalInt(s, "CBMP1KO", 0)
end

P.net_for = P.net_for or {}
P.net_at, P.prison_at, P.free_at = P.net_at or -1000, P.prison_at or -1000, P.free_at or -1000

local function net_on(s)
    EEex_GameObject_ApplyEffect(s, {effectID = 146, dwFlags = 1, res = P.NET_SPELL, durationType = 1,
        sourceID = s.m_id, sourceTarget = s.m_id})
end

local function tick(now)
    P.install_travel()
    local p1 = P.protagonist()
    if not p1 then set_out(nil) return false end
    local members = party()
    for _, s in ipairs(members) do
        -- An imprisoned companion's states cannot be read; it has left the party anyway.
        if s.m_id ~= p1.m_id and s.m_activeImprisonment ~= 0 and EEex_BAnd(EEex_Sprite_GetState(s), STATE_DEAD) == 0 then
            if not has(s, P.NET) then
                if not P.net_for[s.m_id] then
                    P.net_for[s.m_id] = true
                    net_on(s)
                end
            elseif EEex_Sprite_GetLocalInt(s, "CBMP1KO") == 1 then
                companion_back(s)
            end
        end
    end
    if EEex_BAnd(EEex_Sprite_GetState(p1), STATE_DEAD) ~= 0 then set_out(nil) return false end
    local mine = P.scan(p1)
    set_out((mine.statue or mine.maze) and p1 or nil)
    if not mine.net then
        if now - P.net_at >= 75 or now < P.net_at then
            P.net_at = now
            net_on(p1)
        end
        return false
    end
    local function imprison(why)
        EEex_GameObject_ApplyEffect(p1, {effectID = 213, dwFlags = 1, durationType = 0,
            duration = P.PRISON_DURATION, sourceID = p1.m_id, sourceTarget = p1.m_id,
            m_sourceRes = P.PRISON_SPELL})
        log(why)
    end
    if mine.marker and not mine.maze then
        -- A Freedom took the maze away. The engine frees every prisoner of an area through whoever
        -- the spell reaches there, past his own screen (lab), so the place is checked here: where
        -- he vanished he is free and back on his spot; anywhere else the prison closes again.
        if not at_prison_place(p1) then
            imprison("Freedom away from where he vanished: imprisoned again")
            return false
        end
        if now - P.free_at >= 30 or now < P.free_at then
            P.free_at = now
            EEex_GameObject_ApplyEffect(p1, {effectID = 146, dwFlags = 1, res = P.FREE_SPELL, durationType = 1,
                sourceID = p1.m_id, sourceTarget = p1.m_id})
            -- No ClearActions in front: it would take the jump with it.
            EEex_Action_QueueResponseStringOnAIBase(string.format("JumpToPoint([%d.%d])",
                EEex_Sprite_GetLocalInt(p1, "CBMP1X"), EEex_Sprite_GetLocalInt(p1, "CBMP1Y")), p1)
            log("Freedom in " .. current_area(p1))
        end
        return false
    end
    if mine.maze and p1.m_activeImprisonment ~= 0 and (now - P.prison_at >= 30 or now < P.prison_at) then
        -- A cutscene sets every imprisoned party member active again; imprison him again after it.
        -- The engine keeps waking him for a few seconds after a scene, hence the pause.
        P.prison_at = now
        imprison("imprisoned again after a cutscene")
    end
    if not (mine.statue or mine.maze) then return false end
    local helpers = 0
    for _, s in ipairs(members) do
        if s.m_id ~= p1.m_id and can_act(s) then helpers = helpers + 1 end
    end
    if helpers == 0 then
        log("nobody else can act: game over")
        return true
    end
    -- A script moved everyone who can act away without him: follow them. A member who walked off
    -- alone through an exit for one does not count while another stays with him.
    local here, first = current_area(p1):upper(), nil
    for _, s in ipairs(members) do
        if s.m_id ~= p1.m_id and can_act(s) then
            if current_area(s):upper() == here then return false end
            first = first or s
        end
    end
    if first and current_area(first) ~= "" then
        EEex_Action_QueueResponseStringOnAIBase(string.format('MoveGlobal("%s",Protagonist,[%d.%d])',
            current_area(first), first.m_pos.x, first.m_pos.y), first)
        log("pulled after the party to " .. current_area(first))
    end
    return false
end

function CBMP1_Tick()
    local ok, result = pcall(function()
        local now = game().m_worldTime.m_gameTime
        if now >= P.last and now - P.last < 15 then return false end
        P.last = now
        return tick(now)
    end)
    if ok then return result == true end
    P.errors = P.errors + 1
    if P.errors <= 10 then log("tick error: " .. tostring(result)) end
    return false
end
