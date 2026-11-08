-- The main character as a statue or imprisoned: not the end of the game.
--
-- * A screen (opcode 403) on him turns incoming petrification (opcode 134, opcode 13 "stoned") and
--   imprisonment (opcode 211) into this mod's states, CBMP1ST and CBMP1IM. The screen sees an effect
--   before the engine rolls its save and checks immunity, so it blocks the effect and casts the
--   state through opcode 146 with the old effect's save; Protection from Petrification and the like
--   (opcode 101) are checked here. Stone to Flesh (opcode 43) ends the statue; Freedom (opcode 212)
--   ends the prison only in the area where he vanished, and puts him back on that spot.
-- * Travel: the party takes him along. Two jump hooks in the engine's gather check let a member
--   with the state CBM_P1_OUT pass like a dead one; the engine then moves him with the party.
-- * The world scripts call CBMP1_Tick(): it ends the game when nobody else can act, imprisons him
--   again after a cutscene freed him, and pulls him after the party when a script split them.
-- * Companions keep the game's petrification and imprisonment, which put them out of the party
--   and empty their party AI slot. The screen keeps that script first; when Stone to Flesh or
--   Freedom brings them back, they rejoin the party (if there is room) with their script.
--
-- Nothing of this shows a technical message in the game; problems go to the log. LuaJIT syntax.

if not (EEex_GameObject_ApplyEffect and EEex_HookConditionalJumpOnFail and EEex_LabelDefault
        and EEex_Utility_IterateCPtrList and EEex_Sprite_GetSpellState and EEex_GameObject_Get
        and EEex_Sprite_GetCharacterIndex and EEex_AIBase_GetScriptLevel and EEex_AIBase_SetScriptLevelResRef) then
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
        if has(sprite, P.PRISON) or P.immune(sprite, 211) then return true end
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
        if has(sprite, P.PRISON) then
            if not at_prison_place(sprite) then return true end
            cast_instead(sprite, effect, P.FREE_SPELL)
            local x, y = EEex_Sprite_GetLocalInt(sprite, "CBMP1X"), EEex_Sprite_GetLocalInt(sprite, "CBMP1Y")
            EEex_Action_QueueResponseStringOnAIBase(string.format("ClearActions(Myself)\nJumpToPoint([%d.%d])", x, y), sprite)
            log("Freedom in " .. current_area(sprite))
        end
        return false
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
-- members ("test [rax], 800h; jne"); a member with CBM_P1_OUT skips the same way. rax holds the
-- active stats there; spell states 0-255 are a bit array at +0xC88 in 2.7.3.0.
P.STATES_AT = 0xC88
P.hook = P.hook or {status = "not installed"}

local function expected(address)
    local want = {0x0F, 0x85, false, false, false, false, 0x33, 0xD2, 0x48, 0x8B, 0xCF}
    for i = 1, #want do
        if want[i] and EEex_ReadU8(address + i - 1) ~= want[i] then return false end
    end
    return true
end

local function layout_ok(sprite)
    -- The bit of our net state must sit where the hook reads.
    if P.NET < 0 or P.NET > 255 or not has(sprite, P.NET) then return nil end
    local stats = EEex_UDToPtr(sprite:getActiveStats())
    local byte = EEex_ReadU8(stats + P.STATES_AT + math.floor(P.NET / 8))
    return EEex_BAnd(byte, ({1, 2, 4, 8, 16, 32, 64, 128})[P.NET % 8 + 1]) ~= 0
end

function P.install_travel(sprite)
    local hook = P.hook
    if hook.done then return end
    local check = layout_ok(sprite)
    if check == nil then return end          -- try again once the net is on him
    hook.done = true
    if not check then hook.status = "off: spell states are not where expected" log("travel: " .. hook.status) return end
    if P.OUT < 0 or P.OUT > 255 then hook.status = "off: state out of range" log("travel: " .. hook.status) return end
    local addresses = {}
    for _, label in ipairs({"CBMP1-LeaveArea-DeadTest", "CBMP1-LeaveAreaName-DeadTest"}) do
        local address = EEex_LabelDefault(label, nil)
        if not address then hook.status = "off: pattern " .. label .. " not found" log("travel: " .. hook.status) return end
        if not expected(address) then hook.status = "off: other code at " .. label log("travel: " .. hook.status) return end
        addresses[#addresses + 1] = address
    end
    local offset = P.STATES_AT + math.floor(P.OUT / 8)
    local mask = ({1, 2, 4, 8, 16, 32, 64, 128})[P.OUT % 8 + 1]
    EEex_DisableCodeProtection()
    local ok, err = pcall(function()
        for _, address in ipairs(addresses) do
            EEex_HookConditionalJumpOnFail(address, 5, {[[
                test byte ptr ds:[rax+]], offset, [[], ]], mask, [[ #ENDL
                jnz jmp_success #ENDL
            ]]})
        end
    end)
    EEex_EnableCodeProtection()
    hook.status = ok and "active" or ("off: " .. tostring(err))
    log("travel: " .. hook.status)
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
    if has(s, P.OUT) then return false end
    return s.m_activeImprisonment ~= 0
end

-- A companion back in the party: the party AI script the game emptied comes back. One whose save
-- kept it in the party just loses the mark.
local function companion_back(s)
    local stored = EEex_Sprite_GetLocalString(s, "CBMP1DS") or ""
    if stored ~= "" and EEex_AIBase_GetScriptLevelResRef(s, 7) == "" then
        EEex_AIBase_SetScriptLevelResRef(s, 7, stored, EEex_Sprite_GetLocalInt(s, "CBMP1PS") == 1)
        log("party AI script back: " .. stored)
    end
    EEex_Sprite_SetLocalInt(s, "CBMP1KO", 0)
end

P.net_for = P.net_for or {}

local function tick()
    local p1 = P.protagonist()
    if not p1 then return false end
    local members = party()
    for _, s in ipairs(members) do
        if EEex_BAnd(EEex_Sprite_GetState(s), STATE_DEAD) == 0 then
            if not has(s, P.NET) then
                if not P.net_for[s.m_id] then
                    P.net_for[s.m_id] = true
                    EEex_GameObject_ApplyEffect(s, {effectID = 146, dwFlags = 1, res = P.NET_SPELL, durationType = 1,
                        sourceID = s.m_id, sourceTarget = s.m_id})
                end
            elseif s.m_id ~= p1.m_id and EEex_Sprite_GetLocalInt(s, "CBMP1KO") == 1 then
                companion_back(s)
            end
        end
    end
    if EEex_BAnd(EEex_Sprite_GetState(p1), STATE_DEAD) ~= 0 or not has(p1, P.NET) then return false end
    P.install_travel(p1)
    if not has(p1, P.OUT) then return false end
    local helpers = 0
    for _, s in ipairs(members) do
        if s.m_id ~= p1.m_id and can_act(s) then helpers = helpers + 1 end
    end
    if helpers == 0 then
        log("nobody else can act: game over")
        return true
    end
    -- A cutscene sets every imprisoned party member active again; imprison him again after it.
    if has(p1, P.PRISON) and p1.m_activeImprisonment ~= 0 then
        EEex_GameObject_ApplyEffect(p1, {effectID = 213, dwFlags = 1, durationType = 0,
            duration = P.PRISON_DURATION, sourceID = p1.m_id, sourceTarget = p1.m_id,
            m_sourceRes = P.PRISON_SPELL})
        log("imprisoned again after a cutscene")
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
        return tick()
    end)
    if ok then return result == true end
    P.errors = P.errors + 1
    if P.errors <= 10 then log("tick error: " .. tostring(result)) end
    return false
end
