-- Standalone runtime checks of the record listener. Return a function accepting the Lua
-- template text; the Python harness runs it with Lua 5.3 and LuaJIT 2.1. Every engine object
-- below is a mock; this never opens or controls a game.
return function(template)
    local checks = 0
    local function equal(actual, expected, label)
        checks = checks + 1
        assert(actual == expected, (label or "value") .. ": expected " .. tostring(expected)
            .. ", got " .. tostring(actual))
    end
    local function band(a, b)
        local result, bit = 0, 1
        for _ = 1, 32 do
            if a % 2 == 1 and b % 2 == 1 then result = result + bit end
            a, b, bit = math.floor(a / 2), math.floor(b / 2), bit * 2
        end
        return result
    end
    local rows = { INVISIBLE = 301, IMPROVED_INVISIBILITY = 302, SANCTUARY = 303, MIRROR_IMAGE = 304,
                   REFLECTED_IMAGE = 305, ARCHONS = 306, MINOR_DEFLECTION = 307, MINOR_TURNING = 308 }
    local source = template:gsub("%%CBM_ROW_([A-Z_]+)%%", function(name) return tostring(rows[name]) end)
    equal(source:find("%CBM_", 1, true), nil, "every row is stamped")

    local listener, applied
    local env = setmetatable({
        EEex_Opcode_AddDeferredListsResolvedListener = function(fn) listener = fn end,
        EEex_Utility_IterateCPtrList = function(list, fn) for _, v in ipairs(list) do fn(v) end end,
        EEex_BAnd = band,
        EEex_Sprite_GetPortraitIndex = function(sprite) return sprite.portrait end,
        EEex_GameObject_ApplyEffect = function(_, args) applied[#applied + 1] = args end,
    }, { __index = _G })
    env.print = function() end
    local chunk
    if setfenv then
        chunk = assert(loadstring(source, "@M_CBMREC.lua"))
        setfenv(chunk, env)
    else
        chunk = assert(load(source, "@M_CBMREC.lua", "t", env))
    end
    chunk()
    assert(listener, "the listener is registered")
    local CBMRecord = env.CBMRecord

    local function effect(id, flags, res)
        return { m_effectId = id, m_dWFlags = flags, m_done = 0,
                 m_sourceRes = { get = function() return res or "" end } }
    end
    local function sprite(portrait, state, list)
        local stats = { m_generalState = state or 0, m_bSanctuary = 0 }
        return { portrait = portrait, m_id = 1, m_nMirrorImages = 0, m_timedEffectList = list or {}, m_portraitIcons = {},
                 getActiveStats = function() return stats end, stats = stats }
    end
    -- Enough passes for one look.
    local function look(s)
        applied = {}
        for _ = 1, 4 do CBMRecord.Listener(s) end
        return applied
    end
    local function added(result, row)
        for _, args in ipairs(result) do
            if args.effectID == 142 and args.dwFlags == row then return true end
        end
        return false
    end
    local function removed(result, row)
        for _, args in ipairs(result) do
            if args.effectID == 240 and args.dwFlags == row then return true end
        end
        return false
    end

    -- Nobody outside the party, and nothing for a plain character.
    equal(#look(sprite(-1, 0x10)), 0, "no record, no entry")
    equal(#look(sprite(0)), 0, "nothing to list")
    -- The look comes on every fourth pass, not on each.
    applied = {}
    local passes = sprite(1, 0x10)
    for _ = 1, 3 do CBMRecord.Listener(passes) end
    equal(#applied, 0, "no look before the fourth pass")
    CBMRecord.Listener(passes)
    equal(#applied, 1, "a look on the fourth pass")

    -- Invisible, and only that one entry for improved invisibility.
    equal(added(look(sprite(0, 0x10)), rows.INVISIBLE), true, "invisible")
    local both = look(sprite(0, 0x400010))
    equal(added(both, rows.IMPROVED_INVISIBILITY), true, "improved")
    equal(added(both, rows.INVISIBLE), false, "improved shows once")
    equal(added(look(sprite(0, 0x400000)), rows.IMPROVED_INVISIBILITY), true, "improved after an attack")
    -- Listed and true: nothing to do. Listed and over: it goes.
    equal(#look(sprite(0, 0x10, { effect(142, rows.INVISIBLE) })), 0, "already listed")
    equal(removed(look(sprite(0, 0, { effect(142, rows.INVISIBLE) })), rows.INVISIBLE), true, "visible again")
    equal(#look(sprite(0, 0, { effect(142, 50) })), 0, "other rows are not ours")
    -- An effect that is done does not count as listed.
    local finished = effect(142, rows.INVISIBLE)
    finished.m_done = 1
    equal(added(look(sprite(0, 0x10, { finished })), rows.INVISIBLE), true, "done effects are gone")

    -- Sanctuary.
    local holy = sprite(0)
    holy.stats.m_bSanctuary = 1
    equal(added(look(holy), rows.SANCTUARY), true, "sanctuary")
    holy.stats.m_bSanctuary = 0
    holy.m_timedEffectList = { effect(142, rows.SANCTUARY) }
    equal(removed(look(holy), rows.SANCTUARY), true, "sanctuary broken")

    -- Images: Reflected Image by its source, any other by the count.
    local images = sprite(0, 0, { effect(159, 0, "SPWI212") })
    images.m_nMirrorImages = 3
    local result = look(images)
    equal(added(result, rows.MIRROR_IMAGE), true, "mirror image")
    equal(added(result, rows.REFLECTED_IMAGE), false, "not reflected image")
    images.m_timedEffectList = { effect(159, 0, "spwi120") }
    images.m_nMirrorImages = 1
    result = look(images)
    equal(added(result, rows.REFLECTED_IMAGE), true, "reflected image, any case")
    equal(added(result, rows.MIRROR_IMAGE), false, "not mirror image")
    images.m_timedEffectList = { effect(142, rows.MIRROR_IMAGE) }
    images.m_nMirrorImages = 0
    equal(removed(look(images), rows.MIRROR_IMAGE), true, "the last image is gone")

    -- The engine's rows take the small spell's name, on every pass.
    local function pass(s)
        applied = {}
        CBMRecord.Listener(s)
        return s.m_portraitIcons[1]
    end
    local function shield(row, list)
        local s = sprite(0, 0, list)
        s.m_portraitIcons = { { icon = row, frame = row + 65 } }
        return s
    end
    local entry = pass(shield(67, { effect(201, 1, "SPPR701"), effect(201, 2, "spPR701") }))
    equal(entry.icon, rows.ARCHONS, "archons")
    equal(entry.frame, 181, "archons have an icon of their own")
    equal(pass(shield(67, { effect(201, 1, "DGARCHON") })).icon, rows.ARCHONS, "archons, the other source")
    entry = pass(shield(67, { effect(201, 1, "SPWI318") }))
    equal(entry.icon, rows.MINOR_DEFLECTION, "minor deflection")
    equal(entry.frame, 132, "the big spell's icon stays")
    equal(pass(shield(65, { effect(200, 1, "SPIN920") })).icon, rows.MINOR_TURNING, "minor turning")
    equal(pass(shield(65, { effect(200, 1, "SPWI522") })).icon, rows.MINOR_TURNING, "minor turning, the other source")
    -- The big spell keeps the row, also when a small one runs beside it.
    equal(pass(shield(67, { effect(201, 1, "SPWI618") })).icon, 67, "the big spell")
    equal(pass(shield(67, { effect(201, 1, "SPWI318"), effect(201, 1, "SPWI618") })).icon, 67, "both: the big one")
    equal(pass(shield(65, { effect(200, 1, "SPWI701") })).icon, 65, "real spell turning")
    -- A spent effect counts no more, an effect of the other opcode is no reason.
    local spent = effect(201, 1, "SPWI618")
    spent.m_done = 1
    equal(pass(shield(67, { spent, effect(201, 1, "SPWI318") })).icon, rows.MINOR_DEFLECTION, "done effects do not count")
    equal(pass(shield(67, { effect(200, 1, "SPWI522") })).icon, 67, "turning does not rename deflection")
    equal(pass(shield(67, {})).icon, 67, "no effect behind the row")
    equal(#look(shield(rows.ARCHONS, {})), 0, "renamed entries need nothing else")

    -- Without the deferred listener nothing is registered and nothing breaks.
    local quiet = setmetatable({ print = function() end }, { __index = _G })
    local plain
    if setfenv then
        plain = assert(loadstring(source, "@M_CBMREC.lua"))
        setfenv(plain, quiet)
    else
        plain = assert(load(source, "@M_CBMREC.lua", "t", quiet))
    end
    plain()
    equal(quiet.CBMRecord.noEEexLogged, true, "no EEex, a line in the log")
    return checks
end
