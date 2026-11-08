-- Standalone runtime suite for lua/M_CBMP1.lua. Returns a function taking the template text; the
-- Python harness runs it with Lua 5.3 and LuaJIT 2.1. Every engine object is a mock.
return function(template)
    local checks = 0
    local function check(condition, label)
        checks = checks + 1
        assert(condition, label)
    end
    local function band(a, b)
        a, b = a % 4294967296, b % 4294967296
        local result, bit = 0, 1
        for _ = 1, 32 do
            if a % 2 == 1 and b % 2 == 1 then result = result + bit end
            a, b, bit = math.floor(a / 2), math.floor(b / 2), bit * 2
        end
        return result
    end
    local NET, OUT, STATUE, PRISON = 230, 231, 232, 233
    local source = template:gsub("%%CBM_P1_NET_STATE%%", tostring(NET)):gsub("%%CBM_P1_OUT_STATE%%", tostring(OUT))
        :gsub("%%CBM_P1_STATUE_STATE%%", tostring(STATUE)):gsub("%%CBM_P1_PRISON_STATE%%", tostring(PRISON))
    check(not source:find("%%CBM_"), "every placeholder is filled")

    local function ref(value) return { get = function() return value end } end
    local function list(items)
        local head
        for i = #items, 1, -1 do head = { data = items[i], pNext = head } end
        return { m_pNodeHead = head }
    end

    local function world()
        local w = { sprites = {}, applied = {}, queued = {}, hooks = {}, memory = {}, labels = {}, logs = {}, scriptsSet = {},
                    characters = { -1, -1, -1, -1, -1, -1 }, time = 1000 }
        local env = setmetatable({}, { __index = _G })
        env.print = function(text) w.logs[#w.logs + 1] = text end
        env.EEex_BAnd = band
        env.EEex_LShift = function(value, shift) return value * 2 ^ shift end
        env.EEex_Utility_IterateCPtrList = function(l, callback)
            local node = l.m_pNodeHead
            while node do
                if callback(node.data) then break end
                node = node.pNext
            end
        end
        env.EEex_GameObject_Get = function(id) return w.sprites[id] end
        env.EEex_Sprite_GetSpellState = function(s, state) return s.states[state] == true end
        env.EEex_Sprite_GetState = function(s) return s.state end
        env.EEex_GameObject_ApplyEffect = function(s, args)
            w.applied[#w.applied + 1] = { who = s.m_id, args = args }
        end
        env.EEex_Action_QueueResponseStringOnAIBase = function(text, s)
            w.queued[#w.queued + 1] = { who = s.m_id, text = text }
        end
        env.EEex_Sprite_GetLocalString = function(s, name) return s.locals[name] end
        env.EEex_Sprite_SetLocalString = function(s, name, value) s.locals[name] = value end
        env.EEex_Sprite_GetLocalInt = function(s, name) return s.locals[name] or 0 end
        env.EEex_Sprite_SetLocalInt = function(s, name, value) s.locals[name] = value end
        env.EEex_LabelDefault = function(label, default) return w.labels[label] or default end
        env.EEex_Sprite_GetCharacterIndex = function(s)
            for i = 1, 6 do if w.characters[i] == s.m_id then return i - 1 end end
            return -1
        end
        env.EEex_AIBase_GetScriptLevel = function(s, level) return s.scripts[level] end
        env.EEex_AIBase_GetScriptLevelResRef = function(s, level)
            return s.scripts[level] and s.scripts[level].cResRef:get() or ""
        end
        env.EEex_AIBase_SetScriptLevelResRef = function(s, level, resref, player)
            s.scripts[level] = { cResRef = ref(resref), m_bPlayerScript = player and 1 or 0 }
            w.scriptsSet[#w.scriptsSet + 1] = { who = s.m_id, level = level, resref = resref, player = player }
        end
        env.EEex_ReadU8 = function(address) return w.memory[address] or 0 end
        env.EEex_UDToPtr = function(ud) return ud.address end
        env.EEex_DisableCodeProtection = function() w.protection = false end
        env.EEex_EnableCodeProtection = function() w.protection = true end
        env.EEex_HookConditionalJumpOnFail = function(address, restore, assembly)
            local text = {}
            for _, part in ipairs(assembly) do text[#text + 1] = tostring(part) end
            w.hooks[#w.hooks + 1] = { address = address, restore = restore, text = table.concat(text) }
        end
        env.EngineGlobals = { g_pBaldurChitin = { m_pObjectGame = {
            m_characters = { get = function(_, i) return w.characters[i + 1] end },
            m_worldTime = setmetatable({}, { __index = function(_, key)
                if key == "m_gameTime" then return w.time end
            end }),
        } } }
        local chunk
        if setfenv then
            chunk = assert(loadstring(source, "@M_CBMP1.lua"))
            setfenv(chunk, env)
        else
            chunk = assert(load(source, "@M_CBMP1.lua", "t", env))
        end
        chunk()
        w.env = env
        return w
    end

    local function sprite(w, id, area, x, y)
        local s = { m_id = id, m_pArea = { m_resref = ref(area) }, m_pos = { x = x, y = y }, m_activeImprisonment = 1,
                    states = {}, state = 0, locals = {}, m_equipedEffectList = list({}), m_timedEffectList = list({}),
                    scripts = {} }
        s.stats = { address = 0x10000 * id }
        s.getActiveStats = function(self) return self.stats end
        w.sprites[id] = s
        return s
    end
    local function effect(opcode, fields)
        local e = { m_effectId = opcode, m_dWFlags = 0, m_savingThrow = 0, m_saveMod = 0, m_spellLevel = 0,
                    m_sourceId = 77, m_sourceRes = ref(""), m_sourceType = 1, m_durationType = 0 }
        for k, v in pairs(fields or {}) do e[k] = v end
        return e
    end
    local function party(w, ...)
        local ids = { ... }
        for i = 1, 6 do w.characters[i] = ids[i] or -1 end
    end

    -- The screen ------------------------------------------------------------------------------
    local w = world()
    local p1, p2 = sprite(w, 1, "AR0400", 100, 200), sprite(w, 2, "AR0400", 120, 210)
    party(w, 1, 2)
    local screen = w.env.CBMP1SCR

    local stone = effect(134, { m_savingThrow = 1, m_saveMod = -2, m_spellLevel = 6, m_sourceRes = ref("SPWI604") })
    check(screen(nil, stone, p1) == true, "petrification on him is blocked")
    local cast = w.applied[1]
    check(cast and cast.who == 1 and cast.args.effectID == 146 and cast.args.res == "CBMP1ST"
        and cast.args.dwFlags == 1, "and cast as the statue")
    check(cast.args.savingThrow == 1 and cast.args.saveMod == -2 and cast.args.spellLevel == 6
        and cast.args.m_sourceRes == "SPWI604" and cast.args.sourceID == 77, "with the old effect's save and source")

    w.applied = {}
    p1.m_timedEffectList = list({ effect(101, { m_dWFlags = 134 }) })
    check(screen(nil, stone, p1) == true and #w.applied == 0, "Protection from Petrification stops it")
    p1.m_timedEffectList = list({ effect(101, { m_dWFlags = 134, m_durationType = 4 }) })
    screen(nil, stone, p1)
    check(#w.applied == 1, "a protection still waiting for its delay does not")
    w.applied = {}
    p1.m_timedEffectList = list({})
    p1.m_equipedEffectList = list({ effect(101, { m_dWFlags = 134 }) })
    check(screen(nil, stone, p1) == true and #w.applied == 0, "nor does one from equipment")
    p1.m_equipedEffectList = list({})

    p1.states[STATUE] = true
    check(screen(nil, stone, p1) == true and #w.applied == 0, "a statue is not petrified twice")
    p1.states[STATUE] = nil

    check(screen(nil, effect(13, { m_dWFlags = 0x10 }), p1) == true and w.applied[1].args.res == "CBMP1ST",
        "a stoned death becomes the statue")
    w.applied = {}
    check(screen(nil, effect(13, { m_dWFlags = 0x4 }), p1) == false and #w.applied == 0, "a normal death stays")
    check(screen(nil, effect(13, { m_dWFlags = 0x40 }), p1) == false, "an exploding stoned death stays")

    check(screen(nil, effect(211, { m_sourceRes = ref("SPWI910") }), p1) == true
        and w.applied[1].args.res == "CBMP1IM", "imprisonment becomes the prison")
    check(p1.locals.CBMP1AR == "AR0400" and p1.locals.CBMP1X == 100 and p1.locals.CBMP1Y == 200, "the place is kept")
    w.applied = {}
    p1.states[PRISON] = true
    p1.m_pArea = { m_resref = ref("AR0402") }
    check(screen(nil, effect(211), p1) == true and #w.applied == 0 and p1.locals.CBMP1AR == "AR0400",
        "a second imprisonment changes nothing")

    check(screen(nil, effect(212), p1) == true and #w.applied == 0, "Freedom elsewhere is blocked")
    p1.m_pArea = { m_resref = ref("ar0400") }
    check(screen(nil, effect(212), p1) == false and w.applied[1].args.res == "CBMP1FR", "Freedom where he vanished")
    local jump = w.queued[#w.queued]
    check(jump.who == 1 and jump.text:find("JumpToPoint%(%[100%.200%]%)"), "puts him back on the spot: " .. jump.text)
    p1.states[PRISON] = nil

    w.applied, w.queued = {}, {}
    check(screen(nil, effect(43), p1) == false and #w.applied == 0, "Stone to Flesh on flesh does nothing")
    p1.states[STATUE] = true
    check(screen(nil, effect(43), p1) == false and w.applied[1].args.res == "CBMP1CU", "Stone to Flesh cures the statue")
    check(w.queued[1].text == "ClearActions(Myself)", "and clears old orders")
    p1.states[STATUE] = nil

    w.applied = {}
    p2.scripts[7] = { cResRef = ref("BDFIGHT"), m_bPlayerScript = 1 }
    check(screen(nil, stone, p2) == false and #w.applied == 0, "a companion keeps the game's own petrification")
    check(p2.locals.CBMP1DS == "BDFIGHT" and p2.locals.CBMP1PS == 1 and p2.locals.CBMP1KO == 1,
        "but its party AI script is kept first")
    check(screen(nil, effect(12), p1) == false, "other effects pass")
    w.queued = {}
    check(screen(nil, effect(43), p2) == false and #w.queued == 0, "a cure while still in the party does nothing")
    party(w, 1)
    check(screen(nil, effect(43), p2) == false and w.queued[1].who == 2
        and w.queued[1].text == 'SetGlobal("KickedOut","LOCALS",0)\nJoinParty()', "cured, it rejoins")
    party(w, 1, 2)

    -- The tick --------------------------------------------------------------------------------
    w = world()
    p1, p2 = sprite(w, 1, "AR0400", 100, 200), sprite(w, 2, "AR0400", 120, 210)
    local p3 = sprite(w, 3, "AR0400", 130, 220)
    party(w, 1, 2, 3)
    local tick = w.env.CBMP1_Tick
    check(tick() == false and #w.applied == 3 and w.applied[1].args.res == "CBMP1NT" and w.applied[2].who == 2
        and w.applied[3].who == 3, "the screen goes on every member")
    w.time = w.time + 15
    check(tick() == false and #w.applied == 3, "only once while it has not taken")
    w.time = w.time + 5
    w.applied = {}
    p1.states[NET], p2.states[NET], p3.states[NET] = true, true, true
    w.memory[p1.stats.address + 0xC88 + 28] = 64 -- state 230: byte 28, bit 6, as the engine keeps it
    check(tick() == false and #w.applied == 0, "nothing within a second")

    w.labels["CBMP1-LeaveArea-DeadTest"], w.labels["CBMP1-LeaveAreaName-DeadTest"] = 0x5000, 0x6000
    for _, a in ipairs({ 0x5000, 0x6000 }) do
        for i, byte in ipairs({ 0x0F, 0x85, 1, 2, 3, 4, 0x33, 0xD2, 0x48, 0x8B, 0xCF }) do w.memory[a + i - 1] = byte end
    end

    -- Companions coming back.
    p2.locals.CBMP1KO, p2.locals.CBMP1DS, p2.locals.CBMP1PS = 1, "BDFIGHT", 1
    p3.locals.CBMP1KO, p3.locals.CBMP1DS = 1, "WTASIGHT"
    p3.scripts[7] = { cResRef = ref("WTASIGHT"), m_bPlayerScript = 0 }
    w.time = w.time + 15
    tick()
    check(#w.scriptsSet == 1 and w.scriptsSet[1].who == 2 and w.scriptsSet[1].resref == "BDFIGHT"
        and w.scriptsSet[1].level == 7 and w.scriptsSet[1].player == true, "the emptied party AI script comes back")
    check(p2.locals.CBMP1KO == 0 and p3.locals.CBMP1KO == 0, "the marks go, also where nothing was emptied")

    -- Travel hook: the net's bit must be where the hook reads.
    check(#w.hooks == 2, "the hooks are in")
    check(w.hooks[1].address == 0x5000 and w.hooks[1].restore == 5
        and w.hooks[1].text:find("test byte ptr ds:%[rax%+3236%], 128") and w.hooks[1].text:find("jnz jmp_success"),
        "test the OUT bit like the dead bit: " .. w.hooks[1].text)
    check(w.protection == true and w.env.CBMPlayer1.hook.status == "active", "code protection back on")

    local w2 = world()
    local q1 = sprite(w2, 1, "AR0400", 0, 0)
    party(w2, 1)
    q1.states[NET] = true
    w2.labels["CBMP1-LeaveArea-DeadTest"], w2.labels["CBMP1-LeaveAreaName-DeadTest"] = 0x5000, 0x6000
    w2.env.CBMP1_Tick()
    check(#w2.hooks == 0 and w2.env.CBMPlayer1.hook.status:find("spell states"), "no hook when the layout differs")
    local w3 = world()
    local r1 = sprite(w3, 1, "AR0400", 0, 0)
    party(w3, 1)
    r1.states[NET] = true
    w3.memory[r1.stats.address + 0xC88 + 28] = 64
    w3.labels["CBMP1-LeaveArea-DeadTest"] = 0x5000
    for i, byte in ipairs({ 0x0F, 0x85, 1, 2, 3, 4, 0x33, 0xD2, 0x48, 0x8B, 0xCF }) do w3.memory[0x5000 + i - 1] = byte end
    w3.env.CBMP1_Tick()
    check(#w3.hooks == 0 and w3.env.CBMPlayer1.hook.status:find("not found"), "no hook without both patterns")
    local w4 = world()
    local t1 = sprite(w4, 1, "AR0400", 0, 0)
    party(w4, 1)
    t1.states[NET] = true
    w4.memory[t1.stats.address + 0xC88 + 28] = 64
    w4.labels["CBMP1-LeaveArea-DeadTest"], w4.labels["CBMP1-LeaveAreaName-DeadTest"] = 0x5000, 0x6000
    for i, byte in ipairs({ 0x0F, 0x85, 1, 2, 3, 4, 0x33, 0xD2, 0x48, 0x8B, 0xCF }) do w4.memory[0x5000 + i - 1] = byte end
    for i, byte in ipairs({ 0x0F, 0x85, 1, 2, 3, 4, 0xE9, 0xD2, 0x48, 0x8B, 0xCF }) do w4.memory[0x6000 + i - 1] = byte end
    w4.env.CBMP1_Tick()
    check(#w4.hooks == 0 and w4.env.CBMPlayer1.hook.status:find("other code"), "no hook where another mod hooked")

    -- Out: who can still act.
    p1.states[OUT], p1.states[STATUE] = true, true
    w.time = w.time + 15
    check(tick() == false, "others can act")
    p2.state = 0x800
    p3.state = 0x1000
    w.time = w.time + 15
    check(tick() == true, "nobody else can act: game over")
    p2.state, p3.state = 0, 0

    -- Prison and cutscenes.
    p1.states[STATUE], p1.states[PRISON] = nil, true
    p1.m_activeImprisonment = 1
    w.applied = {}
    w.time = w.time + 15
    tick()
    check(#w.applied == 1 and w.applied[1].args.effectID == 213 and w.applied[1].args.dwFlags == 1,
        "imprisoned again after a cutscene")
    p1.m_activeImprisonment = 0
    w.applied = {}
    w.time = w.time + 15
    tick()
    check(#w.applied == 0, "not while still imprisoned")
    check(tick() == false, "a prisoner among helpers is no game over")

    -- Split by a script.
    w.queued = {}
    p2.m_pArea, p3.m_pArea = { m_resref = ref("AR0402") }, { m_resref = ref("AR0400") }
    w.time = w.time + 15
    tick()
    check(#w.queued == 0, "one member walking off alone pulls nobody")
    p3.m_pArea = { m_resref = ref("AR0402") }
    w.time = w.time + 15
    tick()
    check(#w.queued == 1 and w.queued[1].who == 2
        and w.queued[1].text == 'MoveGlobal("AR0402",Protagonist,[120.210])', "pulled after the party")

    w.characters[1] = -1
    w.time = w.time + 15
    check(tick() == false, "no main character, nothing to do")
    return checks
end
