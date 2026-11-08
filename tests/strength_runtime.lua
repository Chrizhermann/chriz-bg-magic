-- Standalone runtime suite for lua/M_CBMSTR.lua. Returns a function taking the template text; the
-- Python harness runs it with Lua 5.3 and LuaJIT 2.1. Every engine object is a mock.
return function(template)
    local checks = 0
    local function equal(actual, expected, label)
        checks = checks + 1
        assert(actual == expected, (label or "value") .. ": expected " .. tostring(expected)
            .. ", got " .. tostring(actual))
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
    local floorState = 223 -- bit 31 of word 6
    local source = template:gsub("%%CBM_STR_FLOOR_STATE%%", tostring(floorState))

    local function loadIn(env)
        local chunk
        if setfenv then
            chunk = assert(loadstring(source, "@M_CBMSTR.lua"))
            setfenv(chunk, env)
        else
            chunk = assert(load(source, "@M_CBMSTR.lua", "t", env))
        end
        chunk()
    end
    local function environment(eeex)
        local env = setmetatable({ logs = {}, registrations = {}, resources = {} }, { __index = _G })
        env.print = function(message) env.logs[#env.logs + 1] = message end
        env.io = { open = function() return nil end }
        if eeex then
            env.EEex_BAnd = band
            env.EEex_LShift = function(value, shift) return value * 2 ^ shift end
            env.EEex_Opcode_AddListsResolvedListener = function(callback)
                env.registrations[#env.registrations + 1] = callback
            end
            env.EEex_Utility_IterateCPtrList = function(list, callback)
                if list.broken then error("list unreadable") end
                local node = list.m_pNodeHead
                while node do
                    if callback(node.data) then break end
                    node = node.pNext
                end
            end
            env.EEex_Resource_Demand = function(name, extension)
                equal(extension, "EFF", "external effects are EFF files")
                return env.resources[name]
            end
        end
        loadIn(env)
        return env
    end
    local function ref(value) return { get = function() return value end } end
    local function effect(opcode, amount, mode, tag, special, timing)
        return { m_effectId = opcode, m_effectAmount = amount, m_dWFlags = mode or 0, m_res = ref(tag or ""),
                 m_special = special or 0, m_durationType = timing or 4096, m_done = 0, m_effectAmount4 = 1 }
    end
    local function floor(value, timing) return effect(44, 0, 0, "CBTSTRF", value, timing) end
    local function list(effects)
        local out, tail = {}, nil
        for _, e in ipairs(effects) do
            local node = { data = e }
            if tail then tail.pNext = node else out.m_pNodeHead = node end
            tail = node
        end
        return out
    end
    -- `strength`/`extra`: what the game worked out from everything else before the listener.
    local function sprite(strength, extra, timed, equipped, options)
        options = options or {}
        local words = {}
        if options.state ~= false then words[math.floor(floorState / 32)] = 2 ^ (floorState % 32) end
        local data = { m_spellStates = { get = function(_, index) return words[index] or 0 end },
                       m_nSTR = strength, m_nSTRExtra = extra or 0, m_bPolymorphed = options.polymorphed or 0 }
        local s = { m_timedEffectList = list(timed or {}), m_equipedEffectList = list(equipped or {}), writes = 0 }
        s.m_derivedStats = setmetatable({}, {
            __index = function(_, key) return data[key] end,
            __newindex = function(_, key, value) s.writes = s.writes + 1; data[key] = value end,
        })
        return s
    end

    local plain = environment(false)
    equal(#plain.registrations, 0, "no listener without EEex")
    equal(plain.CBMStrength, nil, "nothing defined without EEex")

    local env = environment(true)
    equal(#env.registrations, 1, "one registration")
    loadIn(env)
    equal(#env.registrations, 1, "loading again registers nothing more")
    local function run(s) env.registrations[1](s); return s.m_derivedStats end
    local function pair(stats) return stats.m_nSTR .. "/" .. stats.m_nSTRExtra end

    -- Raised to the floor, never lowered by it.
    equal(pair(run(sprite(10, 0, { floor(18100) }))), "18/100", "Divine Power lifts 10 to 18/00")
    equal(pair(run(sprite(19, 0, { floor(18100) }))), "19/0", "Divine Power leaves 19")
    equal(pair(run(sprite(18, 90, { floor(18075) }))), "18/90", "Strength of One leaves 18/90")
    equal(pair(run(sprite(12, 0, { floor(18075) }))), "18/75", "Strength of One lifts 12 to 18/75")
    equal(pair(run(sprite(22, 0, { floor(19000) }))), "22/0", "a giant's potion stays above Animal Rage")

    -- Bonuses count on top of the floor, wherever they sit in the list.
    local might = effect(132, 3)
    equal(pair(run(sprite(13, 0, { might, floor(18100) }))), "21/0", "Draw Upon Divine Might before Divine Power")
    equal(pair(run(sprite(13, 0, { floor(18100), effect(132, 3) }))), "21/0", "Draw Upon Divine Might after it")
    equal(pair(run(sprite(13, 0, { effect(132, 3), effect(132, 2), floor(18100) }))), "21/0",
        "a second Draw Upon Divine Might does not count, as in the game")
    equal(pair(run(sprite(11, 0, { floor(19000) }, { effect(44, 1) }))), "20/0", "an item's +1 on Animal Rage")
    equal(pair(run(sprite(10, 50, { floor(18000), effect(97, 50) }))), "18/50", "Strength lifts 10 to 18/50")
    equal(pair(run(sprite(18, 80, { floor(18000), effect(97, 50) }))), "18/80", "Strength keeps 18/30 + 50")
    equal(pair(run(sprite(18, 100, { floor(18075), effect(97, 50) }))), "18/100", "Strength of One and Strength")
    equal(pair(run(sprite(10, 100, { floor(18075), effect(97, 50) }))), "18/100", "exceptional Strength caps at 100")
    equal(pair(run(sprite(8, 0, { floor(18100), effect(44, -2) }))), "16/0", "a drain lowers the floor too")
    equal(pair(run(sprite(25, 0, { floor(18100), effect(44, 9) }))), "25/0", "Strength caps at 25")
    equal(pair(run(sprite(5, 0, { effect(44, 5, 1), floor(18100) }))), "18/100", "Ray of Enfeeblement under the floor")
    equal(pair(run(sprite(10, 0, { floor(18100), effect(44, 2, 2) }))), "18/100", "a percentage counts only in the game")

    -- Not counted: other states, forms, effects still waiting, other tags.
    equal(pair(run(sprite(10, 0, { floor(18100) }, nil, { state = false }))), "10/0", "no state, no change")
    equal(pair(run(sprite(10, 0, { floor(18100) }, nil, { polymorphed = 1 }))), "10/0", "a form keeps its values")
    equal(pair(run(sprite(10, 0, { floor(18100) }, { effect(135, 0, 1, "CBMPRTC") }))), "10/0",
        "a form from an item that changes only the look keeps its values too")
    equal(pair(run(sprite(10, 0, { floor(18100, 4096 + 4) }))), "10/0", "a delayed floor waits")
    equal(pair(run(sprite(10, 0, { effect(44, 0, 0, "CBTOTHER", 18100) }))), "10/0", "another tag is no floor")
    equal(pair(run(sprite(10, 0, { effect(44, 3, 0, "", 18100) }))), "10/0", "a special field alone is no floor")

    -- Opcode 177 carries a floor in its EFF; a wrapper the game finished or rejected does not.
    env.resources.CBMFLOOR = floor(18100)
    local wrapper = effect(177, 0, 2, "CBMFLOOR")
    equal(pair(run(sprite(10, 0, { wrapper }))), "18/100", "a floor inside an EFF")
    local done = effect(177, 0, 2, "CBMFLOOR"); done.m_done = 1
    equal(pair(run(sprite(10, 0, { done }))), "10/0", "a finished wrapper")
    local rejected = effect(177, 0, 2, "CBMFLOOR"); rejected.m_effectAmount4 = 0
    equal(pair(run(sprite(10, 0, { rejected }))), "10/0", "a rejected wrapper")
    equal(pair(run(sprite(10, 0, { effect(177, 0, 2, "MISSING"), floor(18000) }))), "18/0", "a missing EFF is skipped")

    -- The same pass again, and passes without a rebuild, write nothing more.
    local s = sprite(10, 0, { floor(18100), effect(132, 2) })
    run(s)
    local writes = s.writes
    for _ = 1, 15 * 60 do run(s) end
    equal(pair(s.m_derivedStats), "20/0", "sixty seconds of passes")
    equal(s.writes, writes, "passes without a rebuild write nothing")

    -- A fault is logged; ten switch the listener off for good.
    local broken = sprite(10, 0, {})
    broken.m_timedEffectList.broken = true
    for _ = 1, 10 do run(broken) end
    equal(env.CBMStrength.disabled, true, "ten errors switch it off")
    equal(env.logs[1]:find("list unreadable", 1, true) ~= nil, true, "the error is logged")
    equal(pair(run(sprite(10, 0, { floor(18100) }))), "10/0", "switched off, nothing changes")
    return checks
end
