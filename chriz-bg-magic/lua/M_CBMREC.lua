-- The character record lists portrait icons. Invisibility, Sanctuary and the images have
-- none, and the smaller deflection spells show the row of the big one. A fixed entry would
-- stay after a state ends early (an attack, the last image, the last deflected level), so
-- this one follows the state itself, whatever caused it. Only party members have a record.
-- The installer supplies the row labels. LuaJIT-compatible, also checked under plain Lua 5.3.

CBMRecord = CBMRecord or {}
local R = CBMRecord

if not (EEex_Opcode_AddDeferredListsResolvedListener and EEex_Utility_IterateCPtrList and EEex_BAnd
        and EEex_Sprite_GetPortraitIndex and EEex_GameObject_ApplyEffect) then
    if not R.noEEexLogged then
        R.noEEexLogged = true
        print("CBMRecord: EEex not detected; live record entries inactive")
    end
    return
end

local STATE_INVISIBLE, STATE_IMPROVED_INVISIBILITY = 0x10, 0x400000
local OP_PORTRAIT_ICON, OP_REMOVE_PORTRAIT_ICON = 142, 240
local OP_TURNING, OP_DEFLECTION, OP_IMAGES = 200, 201, 159
local ROW_TURNING, ROW_DEFLECTION = 65, 67
-- Longer than any state; what runs out anyway is added again on the next look.
local ENTRY_SECONDS = 100000
-- The engine reports about 15 passes a second for every sprite.
local PASSES_PER_LOOK = 4

local function hasState(stats, mask)
    return EEex_BAnd(stats.m_generalState, mask) ~= 0
end

-- Entries of their own: an opcode 142 while `test` holds, or while the sprite has effects of
-- opcode `op` from these `sources`.
local watches = {
    { row = %CBM_ROW_INVISIBLE%, test = function(stats)
        return hasState(stats, STATE_INVISIBLE) and not hasState(stats, STATE_IMPROVED_INVISIBILITY)
    end },
    { row = %CBM_ROW_IMPROVED_INVISIBILITY%, test = function(stats)
        return hasState(stats, STATE_IMPROVED_INVISIBILITY)
    end },
    { row = %CBM_ROW_SANCTUARY%, test = function(stats) return stats.m_bSanctuary ~= 0 end },
    { row = %CBM_ROW_MIRROR_IMAGE%, test = function(_, sprite, found)
        return sprite.m_nMirrorImages > 0 and not found[OP_IMAGES .. ":SPWI120"]
    end },
    { row = %CBM_ROW_REFLECTED_IMAGE%, op = OP_IMAGES, sources = { SPWI120 = true } },
}

-- The engine's row for these opcodes names the big spell and no effect can keep it off. It adds
-- the row whenever it rebuilds the list and removes it with the effect, so the entry itself
-- takes the other name, as long as nothing else stands behind that row. `frame`: a cycle of
-- STATES.BAM, for a spell that has an icon of its own there.
local renames = {
    { from = ROW_DEFLECTION, op = OP_DEFLECTION, row = %CBM_ROW_ARCHONS%, frame = 116 + 65,
      sources = { SPPR701 = true, DGARCHON = true } },
    { from = ROW_DEFLECTION, op = OP_DEFLECTION, row = %CBM_ROW_MINOR_DEFLECTION%, sources = { SPWI318 = true } },
    { from = ROW_TURNING, op = OP_TURNING, row = %CBM_ROW_MINOR_TURNING%, sources = { SPWI522 = true, SPIN920 = true } },
}

local function sourceOf(effect)
    return effect.m_sourceRes:get():upper()
end

local function apply(sprite, opcode, row, durationType, duration)
    EEex_GameObject_ApplyEffect(sprite, {
        effectID = opcode, dwFlags = row, targetType = 2,
        durationType = durationType, duration = duration,
        sourceID = sprite.m_id, sourceTarget = sprite.m_id,
    })
end

local function wanted(watch, stats, sprite, found)
    if watch.test then return watch.test(stats, sprite, found) end
    for source in pairs(watch.sources) do
        if found[watch.op .. ":" .. source] then return true end
    end
    return false
end

local function look(sprite)
    local stats = sprite:getActiveStats()
    local listed, found = {}, {}
    EEex_Utility_IterateCPtrList(sprite.m_timedEffectList, function(effect)
        if effect.m_done == 0 then
            if effect.m_effectId == OP_PORTRAIT_ICON then
                listed[effect.m_dWFlags] = true
            elseif effect.m_effectId == OP_IMAGES then
                found[OP_IMAGES .. ":" .. sourceOf(effect)] = true
            end
        end
    end)
    for _, watch in ipairs(watches) do
        local want = wanted(watch, stats, sprite, found)
        if want and not listed[watch.row] then
            apply(sprite, OP_PORTRAIT_ICON, watch.row, 0, ENTRY_SECONDS)
        elseif listed[watch.row] and not want then
            apply(sprite, OP_REMOVE_PORTRAIT_ICON, watch.row, 1, 0)
        end
    end
end

-- The rename that fits, if all the effects behind the row belong to one spell family.
local function renameFor(row, sources)
    for _, rename in ipairs(renames) do
        if rename.from == row then
            local behind = sources[rename.op]
            local fits = behind ~= nil
            for source in pairs(behind or {}) do
                if not rename.sources[source] then fits = false end
            end
            if fits then return rename end
        end
    end
end

local function rename(sprite)
    local entries
    EEex_Utility_IterateCPtrList(sprite.m_portraitIcons, function(entry)
        if entry.icon == ROW_DEFLECTION or entry.icon == ROW_TURNING then
            entries = entries or {}
            entries[#entries + 1] = entry
        end
    end)
    if not entries then return end
    local sources = {}
    EEex_Utility_IterateCPtrList(sprite.m_timedEffectList, function(effect)
        local op = effect.m_effectId
        if (op == OP_DEFLECTION or op == OP_TURNING) and effect.m_done == 0 then
            sources[op] = sources[op] or {}
            sources[op][sourceOf(effect)] = true
        end
    end)
    for _, entry in ipairs(entries) do
        local fitting = renameFor(entry.icon, sources)
        if fitting then
            entry.icon = fitting.row
            if fitting.frame then entry.frame = fitting.frame end
        end
    end
end

R.passes = R.passes or {}

function R.Listener(sprite)
    local portrait = EEex_Sprite_GetPortraitIndex(sprite)
    if portrait < 0 then return end
    -- On every pass: the engine brings its row back with each rebuild of the list.
    rename(sprite)
    local passes = (R.passes[portrait] or 0) + 1
    if passes < PASSES_PER_LOOK then
        R.passes[portrait] = passes
        return
    end
    R.passes[portrait] = 0
    look(sprite)
end

-- Deferred: effects may be added here, at the end of the sprite's AI pass, not while the
-- engine is still resolving its effect lists.
if not R.registered then
    EEex_Opcode_AddDeferredListsResolvedListener(function(sprite) CBMRecord.Listener(sprite) end)
    R.registered = true
end
