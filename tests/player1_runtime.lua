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
        :gsub("%%CBM_P1_STONE_SPELLS%%", '["SPWI625"] = true, '):gsub("%%CBM_P1_STONE_ITEMS%%", '["SCRLPET"] = true, ["RING29"] = true, ')
        :gsub("%%CBM_P1_FREE_SPELLS%%", '["SPWI917"] = true, '):gsub("%%CBM_P1_FREE_ITEMS%%", '["SCRL9Z"] = true, ')
    check(not source:find("%%CBM_"), "every placeholder is filled")

    local function ref(value) return { get = function() return value end } end
    local function list(items)
        local head
        for i = #items, 1, -1 do head = { data = items[i], pNext = head } end
        return { m_pNodeHead = head }
    end
    local function flatten(t, out)
        out = out or {}
        for _, v in ipairs(t) do
            if type(v) == "table" then flatten(v, out) else out[#out + 1] = v end
        end
        return out
    end

    local function world()
        local w = { sprites = {}, applied = {}, queued = {}, hooks = {}, memory = {}, labels = {}, logs = {},
                    scriptsSet = {}, globals = {}, cells = {}, characters = { -1, -1, -1, -1, -1, -1 }, time = 1000 }
        local env = setmetatable({}, { __index = _G })
        env.print = function(text) w.logs[#w.logs + 1] = text end
        env.EEex_BAnd = band
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
        env.EEex_Malloc = function(size)
            local address = 0x7000000 + #w.cells * 16
            w.cells[#w.cells + 1] = address
            return address
        end
        env.EEex_WritePtr = function(address, value) w.memory[address] = value end
        env.EEex_FlattenTable = function(t) return flatten(t) end
        env.EEex_HookIntegrityWatchdogRegister = { RAX = "rax", RDX = "rdx" }
        env.EEex_DisableCodeProtection = function() w.protection = false end
        env.EEex_EnableCodeProtection = function() w.protection = true end
        env.EEex_HookConditionalJumpOnFailWithLabels = function(address, restore, labels, assembly)
            local text = {}
            for _, part in ipairs(assembly) do text[#text + 1] = tostring(part) end
            w.hooks[#w.hooks + 1] = { address = address, restore = restore, labels = labels, text = table.concat(text, " ") }
        end
        env.EEex_Trigger_ParseConditionalString = function(text)
            local item = text:match('^HasItem%("([^"]+)",Myself%)$')
            assert(item, "an item check: " .. text)
            w.parsed = (w.parsed or 0) + 1
            return { evalConditionalAsAIBase = function(_, s) return s.items[item] == true end }
        end
        env.EEex_Utility_FreeCPtrList = function(l) l.freed = true w.freed = (w.freed or 0) + 1 end
        env.EEex_Area_GetVariableInt = function(area, name) return (area.vars or {})[name] or 0 end
        local function book(field)
            return function(s)
                local i = 0
                return function()
                    i = i + 1
                    if s[field][i] then return 5, i - 1, s[field][i] end
                end
            end
        end
        env.EEex_Sprite_GetKnownMageSpellsIterator = book("mage")
        env.EEex_Sprite_GetKnownPriestSpellsIterator = book("priest")
        env.EEex_GameState_GetGlobalInt = function(name) return w.globals[name] or 0 end
        env.EEex_GameState_SetGlobalInt = function(name, value)
            w.globals[name] = value
            w.globalWrites = (w.globalWrites or 0) + 1
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

    local function place(area, flags, vars)
        return { m_resref = ref(area), m_header = { m_flags = flags or 0 }, vars = vars }
    end
    local function sprite(w, id, area, x, y)
        local s = { m_id = id, m_pArea = place(area), m_pos = { x = x, y = y }, m_activeImprisonment = 1,
                    states = {}, state = 0, locals = {}, m_equipedEffectList = list({}), m_timedEffectList = list({}),
                    scripts = {}, address = 0x10000 * id, items = {}, mage = {}, priest = {}, buttons = {} }
        s.GetQuickButtons = function(self, kind, disabled)
            assert(disabled == false, "castable only")
            local out = {}
            for _, resref in ipairs(self.buttons[kind] or {}) do out[#out + 1] = { m_abilityId = { m_res = ref(resref) } } end
            return list(out)
        end
        w.sprites[id] = s
        return s
    end
    local function effect(opcode, fields)
        local e = { m_effectId = opcode, m_dWFlags = 0, m_savingThrow = 0, m_saveMod = 0, m_spellLevel = 0,
                    m_sourceId = 77, m_sourceRes = ref(""), m_res = ref(""), m_sourceType = 1, m_durationType = 0 }
        for k, v in pairs(fields or {}) do e[k] = v end
        return e
    end
    -- What our spells leave in his effect list.
    local net = effect(403, { m_res = ref("CBMP1SCR"), m_sourceRes = ref("CBMP1NT"), m_durationType = 9 })
    local statueMark = effect(328, { m_dWFlags = STATUE, m_sourceRes = ref("CBMP1ST") })
    local prisonMark = effect(328, { m_dWFlags = PRISON, m_sourceRes = ref("cbmp1im") })
    local maze = effect(213, { m_dWFlags = 1, m_sourceRes = ref("CBMP1IM") })
    local function carry(s, ...) s.m_timedEffectList = list({ ... }) end
    local function party(w, ...)
        local ids = { ... }
        for i = 1, 6 do w.characters[i] = ids[i] or -1 end
    end
    local function hookable(w)
        w.labels["CBMP1-LeaveArea-DeadTest"], w.labels["CBMP1-LeaveAreaName-DeadTest"] = 0x5000, 0x6000
        for _, a in ipairs({ 0x5000, 0x6000 }) do
            for i, byte in ipairs({ 0x0F, 0x85, 1, 2, 3, 4, 0x33, 0xD2, 0x48, 0x8B, 0xCF }) do w.memory[a + i - 1] = byte end
        end
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
    carry(p1, effect(101, { m_dWFlags = 134 }))
    check(screen(nil, stone, p1) == true and #w.applied == 0, "Protection from Petrification stops it")
    carry(p1, effect(101, { m_dWFlags = 134, m_durationType = 4 }))
    screen(nil, stone, p1)
    check(#w.applied == 1, "a protection still waiting for its delay does not")
    w.applied = {}
    carry(p1)
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
    -- In the prison his spell states read unset; only his effect list tells.
    carry(p1, net, maze, prisonMark)
    p1.m_pArea = place("AR0402")
    check(screen(nil, effect(211), p1) == true and #w.applied == 0 and p1.locals.CBMP1AR == "AR0400",
        "a second imprisonment changes nothing")

    check(screen(nil, effect(212), p1) == true and #w.applied == 0, "Freedom elsewhere is blocked")
    check(screen(nil, effect(212, { m_durationType = 4 }), p1) == false, "the maze's own delayed Freedom is let be")
    p1.m_pArea = place("ar0400")
    check(screen(nil, effect(212), p1) == false and #w.applied == 0 and #w.queued == 0,
        "Freedom where he vanished passes; the tick tidies up")
    carry(p1, net)
    p1.m_pArea = place("AR0402")
    check(screen(nil, effect(212), p1) == false, "Freedom on a free man passes anywhere")
    p1.m_pArea = place("AR0400")

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

    -- The travel hooks ------------------------------------------------------------------------
    w = world()
    p1, p2 = sprite(w, 1, "AR0400", 100, 200), sprite(w, 2, "AR0400", 120, 210)
    local p3 = sprite(w, 3, "AR0400", 130, 220)
    party(w, 1, 2, 3)
    hookable(w)
    local tick = w.env.CBMP1_Tick
    check(tick() == false and #w.hooks == 2 and w.env.CBMPlayer1.hook.status == "active" and w.protection == true,
        "the hooks go in at the first tick, code protection back on")
    local hook, cell = w.hooks[1], w.cells[1]
    check(hook.address == 0x5000 and hook.restore == 5 and w.hooks[2].address == 0x6000, "at both dead tests")
    check(hook.text:find("mov rax, qword ptr ds:%[#%$%(1%)%]") and hook.text:find(tostring(cell), 1, true)
        and hook.text:find("cmp rdi, rax") and hook.text:find("je #L%(jmp_success%)"),
        "the member in the cell skips like a dead one: " .. hook.text)
    check(not hook.text:find("je jmp_success"), "the label is written the way the assembler resolves it")
    check(hook.labels[1][1] == "hook_integrity_watchdog_ignore_registers" and hook.labels[1][2][1] == "rax", "rax is declared")
    check(w.memory[cell] == 0, "nobody is out at first")

    local w2 = world()
    sprite(w2, 1, "AR0400", 0, 0)
    party(w2, 1)
    w2.labels["CBMP1-LeaveArea-DeadTest"] = 0x5000
    for i, byte in ipairs({ 0x0F, 0x85, 1, 2, 3, 4, 0x33, 0xD2, 0x48, 0x8B, 0xCF }) do w2.memory[0x5000 + i - 1] = byte end
    w2.env.CBMP1_Tick()
    check(#w2.hooks == 0 and w2.env.CBMPlayer1.hook.status:find("not found"), "no hook without both patterns")
    local w3 = world()
    sprite(w3, 1, "AR0400", 0, 0)
    party(w3, 1)
    hookable(w3)
    w3.memory[0x6006] = 0xE9
    w3.env.CBMP1_Tick()
    check(#w3.hooks == 0 and w3.env.CBMPlayer1.hook.status:find("other code"), "no hook where another mod hooked")
    w3.time = w3.time + 15
    check(w3.env.CBMP1_Tick() == false and #w3.hooks == 0, "and no second try")

    -- The tick --------------------------------------------------------------------------------
    check(#w.applied == 3 and w.applied[1].args.res == "CBMP1NT", "the screen goes on every member")
    w.time = w.time + 15
    tick()
    check(#w.applied == 3, "not again while it has not taken")
    w.time = w.time + 75
    tick()
    check(#w.applied == 4 and w.applied[4].who == 1, "on him again after five seconds without it")
    w.applied = {}
    carry(p1, net)
    p2.states[NET], p3.states[NET] = true, true
    w.time = w.time + 5
    check(tick() == false and #w.applied == 0, "nothing within a second")

    -- Companions coming back.
    p2.locals.CBMP1KO, p2.locals.CBMP1DS, p2.locals.CBMP1PS = 1, "BDFIGHT", 1
    p2.scripts[7] = { cResRef = ref("DPLAYER2"), m_bPlayerScript = 0 }
    p3.locals.CBMP1KO, p3.locals.CBMP1DS = 1, "WTASIGHT"
    p3.scripts[7] = { cResRef = ref("wtasight"), m_bPlayerScript = 0 }
    w.time = w.time + 15
    tick()
    check(#w.scriptsSet == 1 and w.scriptsSet[1].who == 2 and w.scriptsSet[1].resref == "BDFIGHT"
        and w.scriptsSet[1].level == 7 and w.scriptsSet[1].player == true,
        "the companion's own party AI script replaces the one joining gave it")
    check(p2.locals.CBMP1KO == 0 and p3.locals.CBMP1KO == 0, "the marks go, also where the script is already his")

    -- A statue.
    carry(p1, net, statueMark)
    w.time = w.time + 15
    check(tick() == false, "others can act")
    check(w.memory[cell] == p1.address and w.globals.CBM_P1_OUT == 1, "the cell and the global say he is out")
    local writes = w.globalWrites
    w.time = w.time + 15
    tick()
    check(w.globalWrites == writes, "the global is written only when it changes")
    p2.state, p3.state = 0x800, 0x1000
    w.time = w.time + 15
    check(tick() == true, "nobody else can act: game over")
    p2.state, p3.state = 0, 0
    p2.m_activeImprisonment, p3.state = 0, 0x800
    w.time = w.time + 15
    check(tick() == true, "a mazed helper cannot act either")
    p2.m_activeImprisonment, p3.state = 1, 0

    -- Split by a script.
    w.queued = {}
    p2.m_pArea, p3.m_pArea = place("AR0402"), place("AR0400")
    w.time = w.time + 15
    tick()
    check(#w.queued == 0, "one member walking off alone pulls nobody")
    p3.m_pArea = place("AR0402")
    w.time = w.time + 15
    tick()
    check(#w.queued == 1 and w.queued[1].who == 2
        and w.queued[1].text == 'MoveGlobal("AR0402",Protagonist,[120.210])', "pulled after the party")
    p2.m_pArea, p3.m_pArea = place("AR0400"), place("AR0400")

    -- Cured.
    carry(p1, net)
    w.time = w.time + 15
    check(tick() == false and w.memory[cell] == 0 and w.globals.CBM_P1_OUT == 0, "cured: nobody is out")

    -- The prison: read from his effect list, whatever his spell states say.
    p1.locals.CBMP1AR, p1.locals.CBMP1X, p1.locals.CBMP1Y = "AR0400", 100, 200
    carry(p1, net, maze, prisonMark)
    p1.m_activeImprisonment = 0
    w.applied, w.queued = {}, {}
    w.time = w.time + 15
    check(tick() == false and #w.applied == 0 and w.memory[cell] == p1.address and w.globals.CBM_P1_OUT == 1,
        "imprisoned: out, nothing to do")
    p1.m_activeImprisonment = 1
    w.time = w.time + 15
    tick()
    check(#w.applied == 1 and w.applied[1].args.effectID == 213 and w.applied[1].args.dwFlags == 1
        and w.applied[1].args.m_sourceRes == "CBMP1IM", "imprisoned again after a cutscene woke him")
    w.time = w.time + 15
    tick()
    check(#w.applied == 1, "not every second while the engine keeps waking him")
    w.time = w.time + 15
    tick()
    check(#w.applied == 2, "again two seconds later")

    -- Freedom: the engine takes the maze away wherever it is cast.
    w.applied = {}
    carry(p1, net, prisonMark)
    p1.m_pArea = place("AR0402")
    w.time = w.time + 15
    check(tick() == false and #w.applied == 1 and w.applied[1].args.effectID == 213 and #w.queued == 0,
        "away from where he vanished the prison closes again")
    w.applied = {}
    p1.m_pArea = place("AR0400")
    w.time = w.time + 15
    check(tick() == false and #w.applied == 1 and w.applied[1].args.effectID == 146
        and w.applied[1].args.res == "CBMP1FR", "where he vanished the prison's marks are taken off")
    check(#w.queued == 1 and w.queued[1].who == 1 and w.queued[1].text == "JumpToPoint([100.200])",
        "and he stands on his spot again: " .. w.queued[1].text)
    w.time = w.time + 15
    tick()
    check(#w.applied == 1, "once, while the marks are still coming off")

    -- Dead ends ---------------------------------------------------------------------------------
    local P = w.env.CBMPlayer1
    local members = { p1, p2, p3 }
    check(P.has_cure(members, p1, "statue") == false and P.has_cure(members, p1, "prison") == false, "nobody carries a cure")
    p1.items.SCRLPET = true
    p1.buttons[2] = { "SPWI625" }
    check(P.has_cure(members, p1, "statue") == false, "what he carries himself is out of reach")
    p1.items.SCRLPET, p1.buttons[2] = nil, nil
    p3.items.SCRLPET = true
    check(P.has_cure(members, p1, "statue") == true and P.has_cure(members, p1, "prison") == false,
        "a scroll with a companion cures the statue, not the prison")
    p3.state = 0x800
    check(P.has_cure(members, p1, "statue") == false, "not with a dead companion")
    p3.state = 0
    p3.items.SCRLPET = nil
    p2.buttons[4] = { "spwi917" }
    check(P.has_cure(members, p1, "prison") == true and w.freed > 0, "a Freedom ready to cast, and the lists are freed")
    p2.buttons[4] = nil
    p2.mage = { "SPWI112", "SPWI625" }
    check(P.has_cure(members, p1, "statue") == true, "Stone to Flesh in a book counts where the party can rest")
    p1.m_pArea = place("AR0400", 0x20)
    check(P.has_cure(members, p1, "statue") == false, "not where nobody can rest")
    p2.m_activeImprisonment = 0
    p1.m_pArea = place("AR0400")
    check(P.has_cure(members, p1, "statue") == false, "nor with its owner in a maze")
    p2.m_activeImprisonment, p2.mage = 1, {}
    local parsed = w.parsed
    P.has_cure(members, p1, "statue")
    check(w.parsed == parsed, "each item check is compiled once")

    check(P.dead_end(p1) == false, "a street is no dead end")
    p1.m_pArea = place("ar2900")
    check(P.dead_end(p1) == true, "Hell is")
    p1.m_pArea = place("AR4500")
    check(P.dead_end(p1) == true, "the Pocket Plane before its exit works")
    w.globals.GavePocketPlane = 1
    check(P.dead_end(p1) == false, "not once it works")
    p1.m_pArea = place("AR6108", 0, { DeactivatePortal = 1 })
    check(P.dead_end(p1) == true, "Sendai's chamber with its portals shut (a variable of the area)")
    p1.m_pArea = place("AR6108", 0, { DeactivatePortal = 2 })
    check(P.dead_end(p1) == false, "and open")
    for _, name in ipairs({ "AR0602", "AR0603", "AR2300", "AR3001", "AR0700" }) do
        p1.m_pArea = place(name)
        check(P.dead_end(p1) == false, name .. " can be left: no dead end")
    end

    -- The clock: out, a dead end, no cure.
    for _, s in ipairs(members) do s.m_pArea = place("AR2900") end
    carry(p1, net, statueMark)
    w.time = w.time + 15
    check(tick() == false and w.globals.CBM_P1_STUCK == 1, "stuck in Hell as a statue without a cure")
    local stuck = w.env.CBMP1_Stuck
    check(stuck() == false and (w.globals.CBM_P1_CLOCK or 0) == 0, "the clock starts")
    w.time = w.time + 8
    check(stuck() == false and w.globals.CBM_P1_CLOCK == 8, "and runs while the scripts ask")
    w.time = w.time + 300
    check(stuck() == false and w.globals.CBM_P1_CLOCK == 8, "a fight, a pause or a scene in between does not count")
    for _ = 1, 54 do
        w.time = w.time + 8
        stuck()
    end
    check(w.globals.CBM_P1_CLOCK == 440 and stuck() == false, "not yet")
    w.time = w.time + 8
    check(stuck() == false, "448 ticks")
    w.time = w.time + 8
    check(stuck() == true, "after 30 seconds the game is over")
    p3.items.SCRLPET = true
    w.time = w.time + 15
    tick()
    check(w.globals.CBM_P1_STUCK == 0 and w.globals.CBM_P1_CLOCK == 0, "a cure in the party stops and clears the clock")
    p3.items.SCRLPET = nil
    carry(p1, net, statueMark, maze, prisonMark)
    p1.m_activeImprisonment = 0
    p3.items.SCRLPET = true
    w.time = w.time + 15
    tick()
    check(w.globals.CBM_P1_STUCK == 1, "a statue in a prison needs both cures")
    p3.items.SCRL9Z = true
    w.time = w.time + 15
    tick()
    check(w.globals.CBM_P1_STUCK == 0, "with both it is not stuck")
    p3.items = {}
    p1.m_activeImprisonment = 1
    carry(p1, net)
    w.time = w.time + 15
    tick()
    check(w.globals.CBM_P1_STUCK == 0, "free: not stuck")
    for _, s in ipairs(members) do s.m_pArea = place("AR0400") end

    -- No main character, or a dead one.
    carry(p1, net, statueMark)
    w.time = w.time + 15
    tick()
    check(w.memory[cell] == p1.address, "out again")
    p1.state = 0x800
    w.time = w.time + 15
    check(tick() == false and w.memory[cell] == 0 and w.globals.CBM_P1_OUT == 0, "dead is not out")
    p1.state = 0
    w.characters[1] = -1
    w.time = w.time + 15
    check(tick() == false, "no main character, nothing to do")
    return checks
end
