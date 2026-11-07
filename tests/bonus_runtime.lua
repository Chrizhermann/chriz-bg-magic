-- Standalone runtime regression suite. Return a function accepting the Lua
-- template text; the Python harness runs it with Lua 5.3 and LuaJIT 2.1.
-- Every engine object below is a mock; this never opens or controls a game.
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
    local function bor(a, b) return (a + b - band(a, b)) % 4294967296 end
    local pass, typed = 223, 224 -- Exercise bit 31 and a distinct state word.
    local source = template:gsub("%%CBM_BONUS_PASS_STATE%%", tostring(pass))
        :gsub("%%CBM_BONUS_TYPED_STATE%%", tostring(typed))

    local function loadIn(env)
        local chunk
        if setfenv then
            chunk = assert(loadstring(source, "@M_CBMBON.lua"))
            setfenv(chunk, env)
        else
            chunk = assert(load(source, "@M_CBMBON.lua", "t", env))
        end
        chunk()
    end
    local function environment(eeex)
        local env = setmetatable({ logs = {}, registrations = {}, applied = {}, scans = 0,
                resources = {}, demands = 0 },
            { __index = _G })
        env.print = function(message) env.logs[#env.logs + 1] = message end
        -- Error logging is tested without creating a file.
        env.io = { open = function() return nil end }
        if eeex then
            env.EEex_BAnd, env.EEex_BOr = band, bor
            env.EEex_LShift = function(value, shift) return value * 2 ^ shift end
            env.EEex_Opcode_AddListsResolvedListener = function(callback)
                env.registrations[#env.registrations + 1] = callback
            end
            env.EEex_Utility_IterateCPtrList = function(list, callback)
                env.scans = env.scans + 1
                local node = list.m_pNodeHead
                while node do
                    if callback(node.data) then break end
                    node = node.pNext
                end
            end
            env.EEex_Sprite_GetStat = function(sprite, id)
                equal(id, 18, "Pierce reads current MR")
                return sprite.currentMR
            end
            env.EEex_GameObject_ApplyEffect = function(sprite, args)
                env.applied[#env.applied + 1] = { sprite = sprite, args = args }
            end
            env.EEex_Resource_Demand = function(name, extension)
                equal(extension, "EFF", "external metadata resource type")
                env.demands = env.demands + 1
                return env.resources[name]
            end
        end
        loadIn(env)
        return env
    end
    local function ref(value) return { get = function() return value end } end
    local function effect(opcode, amount, tag, timing, mode)
        return {
            m_effectId = opcode, m_effectAmount = amount, m_res = ref(tag or ""),
            m_durationType = timing or 4096, m_dWFlags = mode or 0, m_special = 0,
        }
    end
    local function wrapper(name, timing, done, started)
        local e = effect(177, 0, name, timing, 2)
        e.m_done = done or 0
        e.m_effectAmount4 = started == nil and 1 or started
        return e
    end
    local statFields = {
        [0] = "m_nArmorClass", [22] = "m_nLuck", [54] = "m_nTHAC0",
        [73] = "m_nDamageBonus", [33] = "m_nSaveVSDeath", [34] = "m_nSaveVSWands",
        [35] = "m_nSaveVSPoly", [36] = "m_nSaveVSBreath", [37] = "m_nSaveVSSpell",
    }
    local function sprite(effects, hasTyped, brokenMarker)
        local words = {}
        local states = {
            get = function(_, index) return words[index] or 0 end,
            set = function(_, index, value)
                if not brokenMarker then words[index] = value end
            end,
        }
        if hasTyped ~= false then words[math.floor(typed / 32)] = 2 ^ (typed % 32) end
        words[2] = 17 -- Unrelated spell states must survive.
        local data = { m_spellStates = states, m_nMaxHitPoints = 71, m_nNumberOfAttacks = 6 }
        for _, field in pairs(statFields) do data[field] = 10 end
        local list, tail = {}, nil
        for _, e in ipairs(effects) do
            local node = { data = e }
            if tail then tail.pNext = node else list.m_pNodeHead = node end
            tail = node
            -- Native additive contributions before the listener, including
            -- untyped item/other-mod effects that the listener must preserve.
            local timing = band(e.m_durationType, 255)
            if e.m_dWFlags == 0 and not (timing >= 3 and timing <= 8) then
                if e.m_effectId == 325 then
                    for save = 33, 37 do
                        local field = statFields[save]
                        data[field] = data[field] - e.m_effectAmount
                    end
                else
                    local field = statFields[e.m_effectId]
                    if field then
                        local sign = (e.m_effectId == 73 or e.m_effectId == 22) and 1 or -1
                        data[field] = data[field] + sign * e.m_effectAmount
                    end
                end
            end
        end
        local s = { m_timedEffectList = list, m_equipedEffectList = {}, writes = 0 }
        s.m_derivedStats = setmetatable({}, {
            __index = function(_, key) return data[key] end,
            __newindex = function(_, key, value) s.writes = s.writes + 1; data[key] = value end,
        })
        s.words, s.data = words, data
        return s
    end

    local env = environment(true)
    equal(#env.registrations, 1, "one registration")
    local function run(s) env.registrations[1](s); return s.m_derivedStats end

    -- Each supported stat has the measured sign. Keep the strongest benefit
    -- and greatest penalty, never just the largest absolute effect.
    for opcode, field in pairs(statFields) do
        local effects = { effect(opcode, 3, "CBTFAVOR"), effect(opcode, 1, "CBTFAVOR"),
            effect(opcode, -2, "CBTFAVOR"), effect(opcode, -1, "CBTFAVOR") }
        local s = sprite(effects)
        local stats = run(s)
        local expected = (opcode == 73 or opcode == 22) and 11 or 9
        -- AC penalties are excluded by design, so both penalties still apply.
        if opcode == 0 then expected = 10 end
        equal(stats[field], expected, "stat sign opcode " .. opcode)
        equal(stats.m_nMaxHitPoints, 71, "HP excluded")
        equal(stats.m_nNumberOfAttacks, 6, "APR excluded")
        equal(s.words[2], 17, "unrelated spell states")
    end

    local s = sprite({ effect(325, 3, "CBTFAVOR"), effect(325, 1, "CBTFAVOR"),
        effect(37, 2, "CBTFAVOR"), effect(33, 4, "CBTDEFLE"),
        effect(325, -2, "CBTFAVOR"), effect(325, -1, "CBTFAVOR") })
    local stats = run(s)
    equal(stats.m_nSaveVSDeath, 5, "all saves plus independent Deflection")
    for save = 34, 37 do equal(stats[statFields[save]], 9, "all saves expansion " .. save) end

    -- Same-type stronger effect and a separate type; an untyped item remains
    -- fully additive. Unknown CBT prefixes are not claimed by this mod.
    s = sprite({ effect(54, 2, "CBTFAVOR"), effect(54, 1, "CBTFAVOR"),
        effect(54, 2, "CBTMORAL"), effect(54, 1),
        effect(54, 1, "CBTOTHER"), effect(54, 1, "CBTOTHER") })
    equal(run(s).m_nTHAC0, 3, "different types, item, and unknown tag stack")
    local scans, writes = env.scans, s.writes
    for _ = 1, 60 * 15 do run(s) end
    equal(s.m_derivedStats.m_nTHAC0, 3, "sixty seconds of unchanged passes")
    equal(s.writes, writes, "unchanged passes write no stats")
    equal(env.scans, scans, "unchanged passes scan no effects")

    -- A rebuild replaces the struct, clears the pass marker, and recomputes
    -- native effects. No cache of the previous sprite or stat may be needed.
    local rebuilt = sprite({ effect(54, 1, "CBTFAVOR"), effect(54, 2, "CBTMORAL") })
    s.m_derivedStats, s.m_timedEffectList = rebuilt.m_derivedStats, rebuilt.m_timedEffectList
    equal(run(s).m_nTHAC0, 7, "weaker bonus returns after stronger expiry")
    s = sprite({ effect(54, -2, "CBTCURSE"), effect(54, -1, "CBTCURSE") })
    equal(run(s).m_nTHAC0, 12, "worst Curse only on enemy")
    s = sprite({ effect(54, -1, "CBTCURSE") })
    equal(run(s).m_nTHAC0, 11, "weaker Curse returns")
    s = sprite({ effect(54, 2, "CBTFAVOR"), effect(54, 1, "CBTFAVOR"),
        effect(54, -2, "CBTFAVOR"), effect(54, -1, "CBTFAVOR") })
    equal(run(s).m_nTHAC0, 10, "friend benefit and enemy penalty both count")

    -- An untyped sprite gets its pass marker but never opens the effect list.
    s = sprite({ effect(54, 2, "CBTFAVOR"), effect(54, 1, "CBTFAVOR") }, false)
    s.m_timedEffectList = nil
    scans = env.scans
    equal(run(s).m_nTHAC0, 7, "missing typed state is a fast return")
    equal(env.scans, scans, "untyped pass never scans")
    equal(band(s.words[math.floor(pass / 32)], 2 ^ (pass % 32)) ~= 0, true, "pass marker persisted")

    local effects = { effect(54, 2, "CBTFAVOR"), effect(54, 1, "CBTFAVOR") }
    for timing = 3, 8 do effects[#effects + 1] = effect(54, 50, "CBTFAVOR", 4096 + timing) end
    effects[#effects + 1] = effect(54, 70, "CBTFAVOR", 4096, 1)
    effects[#effects + 1] = effect(54, 70, "CBTFAVOR", 4096, 2)
    effects[#effects + 1] = effect(1, 50, "CBTAPR")
    equal(run(sprite(effects)).m_nTHAC0, 8, "pending delays and non-add modes excluded")
    s = sprite({ effect(54, 1, "CBTFAVOR", 1), effect(54, 2, "CBTFAVOR", 9) })
    equal(run(s).m_nTHAC0, 8, "active permanent effects count")
    s = sprite({ effect(54, 1, "CBTFAVOR"), effect(54, 2, "CBTFAVOR") })
    s.m_timedEffectList.m_pNodeHead.data.m_res = "CBTFAVOR"
    equal(run(s).m_nTHAC0, 8, "string resref binding")

    -- Extra attacks: only one counts, Haste before the tagged ones, the strongest of those.
    local function attack(amount, current)
        local e = effect(1, current or amount, "CBTAPR")
        e.m_special = amount
        return e
    end
    local first, second = attack(1), attack(1)
    s = sprite({ first, second })
    run(s)
    equal(first.m_effectAmount + second.m_effectAmount, 1, "two extra attacks: one counts")
    equal(s.m_newEffect, 1, "a changed amount asks for a rebuild")
    s = sprite({ first, second })
    run(s)
    equal(s.m_newEffect, nil, "a settled pair changes nothing")
    first, second = attack(1), attack(2)
    run(sprite({ first, second }))
    equal(first.m_effectAmount, 0, "the weaker extra attack goes")
    equal(second.m_effectAmount, 2, "the stronger extra attack stays")
    first = attack(1)
    run(sprite({ first, effect(16, 0) }))
    equal(first.m_effectAmount, 0, "Haste leaves the tagged one out")
    first = attack(1)
    run(sprite({ first, effect(16, 0, "", 4096, 1) }))
    equal(first.m_effectAmount, 0, "the improved mode of Haste too")
    first = attack(1)
    run(sprite({ first, effect(16, 0, "", 4096, 2) }))
    equal(first.m_effectAmount, 1, "Haste for movement only gives no attack")
    first = attack(1, 0)
    s = sprite({ first })
    run(s)
    equal(first.m_effectAmount, 1, "the extra attack returns when Haste ends, also after a save")
    equal(s.m_newEffect, 1, "its return asks for a rebuild")
    first = attack(1)
    s = sprite({ first })
    s.m_equipedEffectList = { m_pNodeHead = { data = effect(16, 0) } }
    run(s)
    equal(first.m_effectAmount, 0, "Haste from an item counts")
    first = attack(1)
    s = sprite({ first })
    s.data.m_generalState = 0x8000
    run(s)
    equal(first.m_effectAmount, 0, "Haste seen only in the state counts")

    -- Native 177 keeps only the wrapper on the sprite. The inline child is
    -- never in this mock's linked list. Supply the observed native stat totals
    -- independently instead of using the listener's resource-walking logic.
    for opcode, field in pairs(statFields) do
        local child = effect(opcode, 3, "CBTFAVOR", 1)
        env.resources.CBBLEAF = child
        local outer = wrapper("cbbleaf")
        s = sprite({ outer, effect(opcode, 1, "CBTFAVOR") })
        local sign = (opcode == 73 or opcode == 22) and 1 or -1
        s.data[field] = 10 + sign * 4
        equal(run(s)[field], 10 + sign * 3, "inline EFF stat opcode " .. opcode)
        equal(child.m_durationType, 1, "resource timing never mutated")
        equal(child.m_effectAmount, 3, "resource amount never mutated")
        equal(outer.m_effectAmount4, 1, "native acceptance flag never mutated")
    end
    env.resources.CBBSAVES = effect(325, 3, "CBTFAVOR", 7)
    s = sprite({ wrapper("CBBSAVES"), effect(325, 1, "CBTFAVOR") })
    for save = 33, 37 do s.data[statFields[save]] = 6 end
    stats = run(s)
    for save = 33, 37 do
        equal(stats[statFields[save]], 7, "inline all saves uses wrapper timing " .. save)
    end

    env.resources.CBBPOS = effect(54, 3, "CBTFAVOR")
    env.resources.CBBNEG = effect(54, -2, "CBTFAVOR")
    env.resources.CBBNEST = wrapper("CBBPOS", 6, 1, 0)
    -- File-only nested wrappers do not have live m_done/started fields. These
    -- mock values deliberately conflict; only the live outer outcome is read.
    s = sprite({ wrapper("CBBNEST"), wrapper("CBBNEG"),
        effect(54, 1, "CBTFAVOR"), effect(54, -1, "CBTFAVOR") })
    s.data.m_nTHAC0 = 9 -- 10 - (3 - 2 + 1 - 1).
    equal(run(s).m_nTHAC0, 9, "nested EFF strongest benefit and penalty coexist")
    local demands = env.demands
    for _ = 1, 60 * 15 do run(s) end
    equal(s.m_derivedStats.m_nTHAC0, 9, "inline EFF does not drift across unchanged passes")
    equal(env.demands, demands, "unchanged passes do not demand EFF metadata")
    s = sprite({ effect(54, 1, "CBTFAVOR"), wrapper("CBBNEG") })
    s.data.m_nTHAC0 = 11
    equal(run(s).m_nTHAC0, 11, "direct weaker bonus returns after EFF expiry")
    env.resources.CBBWEAK = effect(54, 1, "CBTFAVOR")
    s = sprite({ wrapper("CBBWEAK") })
    s.data.m_nTHAC0 = 9
    equal(run(s).m_nTHAC0, 9, "EFF weaker bonus returns after stronger expiry")

    demands = env.demands
    s = sprite({ wrapper("MISSING", 4096, 1), wrapper("MISSING", 4096, 0, 0),
        wrapper("MISSING", 6), wrapper("MISSING", 4096 + 3),
        effect(146, 0, "MISSING"), effect(148, 0, "MISSING"),
        effect(326, 0, "MISSING"), effect(54, 2, "CBTFAVOR"),
        effect(54, 1, "CBTFAVOR") })
    equal(run(s).m_nTHAC0, 8, "done, rejected, unstarted, delayed wrappers do not count")
    equal(env.demands, demands, "ineligible wrappers and cast deliveries never load metadata")
    env.resources.CBBUNKNOWN = effect(54, 2, "CBTOTHER")
    env.resources.CBBUNTYPE = effect(54, 2, "")
    s = sprite({ wrapper("CBBUNKNOWN"), wrapper("CBBUNTYPE"),
        effect(54, 2, "CBTFAVOR"), effect(54, 1, "CBTFAVOR") })
    s.data.m_nTHAC0 = 3
    equal(run(s).m_nTHAC0, 4, "unknown and untyped EFF contributions remain additive")

    -- Malformed metadata fails before any correction and shares the listener
    -- fuse; each simulated rebuild provides a fresh marker array.
    for _, failure in ipairs({ "missing", "cycle", "depth" }) do
        local broken = environment(true)
        local name = "CBBBROKE"
        if failure == "cycle" then
            broken.resources[name] = wrapper(name)
        elseif failure == "depth" then
            name = "CBB1"
            for index = 1, 33 do
                broken.resources["CBB" .. index] = wrapper("CBB" .. (index + 1))
            end
        end
        for _ = 1, 12 do
            local victim = sprite({ effect(54, 2, "CBTFAVOR"),
                effect(54, 1, "CBTFAVOR"), wrapper(name) })
            broken.registrations[1](victim)
            equal(victim.writes, 0, failure .. " metadata writes no partial correction")
        end
        equal(broken.CBMBonus.failures, 10, failure .. " metadata fuse threshold")
        equal(broken.CBMBonus.disabled, true, failure .. " metadata retires listener")
        local diagnostic = failure == "depth" and "exceeds 32 links" or failure
        equal(broken.logs[1]:find(diagnostic, 1, true) ~= nil, true,
            failure .. " metadata records actual cause")
    end

    -- Reloading a module does not append another callback or reset its fuse.
    loadIn(env)
    equal(#env.registrations, 1, "module reload preserves one listener")
    local failed = environment(true)
    local bad = sprite({ effect(54, 2, "CBTFAVOR"), effect(54, 1, "CBTFAVOR") }, true, true)
    for _ = 1, 12 do failed.registrations[1](bad) end
    equal(bad.m_derivedStats.m_nTHAC0, 7, "marker failure occurs before stats change")
    equal(bad.writes, 0, "marker failure writes no stats")
    equal(failed.scans, 0, "marker failure occurs before scan")
    equal(failed.CBMBonus.failures, 10, "fuse counts exactly ten failures")
    equal(failed.CBMBonus.disabled, true, "listener retired")
    equal(failed.logs[1]:find("marker spell state did not persist", 1, true) ~= nil,
        true, "actual error cause logged")
    equal(#failed.logs, 11, "ten errors and one retirement diagnostic")
    loadIn(failed)
    failed.registrations[1](sprite({}))
    equal(failed.CBMBonus.disabled, true, "reload does not revive fused listener")

    local absent = environment(false)
    loadIn(absent)
    equal(#absent.registrations, 0, "no EEex means no listener")
    equal(absent.CBMBPM, nil, "no EEex means no opcode callback")
    equal(#absent.logs, 1, "no EEex diagnostic once")

    local invoking = {
        m_spellLevel = 6, m_flags = 3, m_sourceId = 73, m_sourceTarget = 91,
        m_sourceRes = ref("WIZPM001"), m_sourceType = 1, m_sourceFlags = 4,
        m_casterLevel = 16, m_school = 5, m_secondaryType = 4,
    }
    for _, pair in ipairs({ { -10, 10 }, { 0, 10 }, { 19, 10 }, { 20, 10 },
            { 21, 10 }, { 49, 24 }, { 50, 25 }, { 79, 39 }, { 80, 40 }, { 100, 40 } }) do
        local target = { currentMR = pair[1] }
        env.CBMBPM(invoking, target)
        local application = env.applied[#env.applied]
        local args = application.args
        equal(application.sprite, target, "Pierce applies to target")
        equal(args.effectID, 166, "Pierce uses native MR effect")
        equal(args.effectAmount, -pair[2], "Pierce amount for MR " .. pair[1])
        equal(args.dwFlags, 0, "Pierce additive mode")
        equal(args.durationType, 0, "Pierce timed seconds")
        equal(args.duration, 30, "Pierce five rounds")
        equal(args.m_flags, 3, "Pierce preserves dispel/resistance flags")
        equal(args.spellLevel, 6, "Pierce preserves power")
        equal(args.sourceID, 73, "Pierce preserves caster")
        equal(args.sourceTarget, 91, "Pierce preserves source target")
        equal(args.m_sourceRes, "WIZPM001", "Pierce preserves parent attribution")
        equal(args.m_sourceType, 1, "Pierce preserves source type")
        equal(args.m_sourceFlags, 4, "Pierce preserves source flags")
        equal(args.m_casterLevel, 16, "Pierce preserves dispel caster level")
        equal(args.m_school, 5, "Pierce preserves school")
        equal(args.m_secondaryType, 4, "Pierce preserves secondary type")
    end
    local applications = #env.applied
    env.CBMBPM(invoking, {})
    equal(#env.applied, applications, "unreadable MR produces no mutation")
    equal(env.logs[#env.logs]:find("Pierce Magic", 1, true) ~= nil, true,
        "callback contains and logs errors")
    return checks
end
