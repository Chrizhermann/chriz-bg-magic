-- Typed spell bonuses and Pierce Magic. The installer supplies private spell
-- states; no spell resrefs or allocated state numbers are fixed at runtime.
-- LuaJIT-compatible syntax, also checked under plain Lua 5.3.

CBMBonus = CBMBonus or {}
local B = CBMBonus

if not (EEex_Opcode_AddListsResolvedListener and EEex_Utility_IterateCPtrList
        and EEex_BAnd and EEex_BOr and EEex_LShift) then
    if not B.noEEexLogged then
        B.noEEexLogged = true
        print("CBMBonus: EEex not detected; typed bonus correction inactive")
    end
    return
end

local PASS_STATE = %CBM_BONUS_PASS_STATE%
local TYPED_STATE = %CBM_BONUS_TYPED_STATE%
local PASS_WORD, PASS_MASK = math.floor(PASS_STATE / 32), EEex_LShift(1, PASS_STATE % 32)
local TYPED_WORD, TYPED_MASK = math.floor(TYPED_STATE / 32), EEex_LShift(1, TYPED_STATE % 32)

local tags = {
    CBTMORAL = true, CBTFAVOR = true, CBTLUCK = true,
    CBTDODGE = true, CBTDEFLE = true, CBTCURSE = true,
}
local fields = {
    [0] = "m_nArmorClass", [22] = "m_nLuck", [54] = "m_nTHAC0",
    [73] = "m_nDamageBonus", [33] = "m_nSaveVSDeath", [34] = "m_nSaveVSWands",
    [35] = "m_nSaveVSPoly", [36] = "m_nSaveVSBreath", [37] = "m_nSaveVSSpell",
}
local ascending = { m_nDamageBonus = true, m_nLuck = true }

local function resref(value)
    if type(value) == "string" then return value end
    return value:get()
end

local function logError(label, cause)
    local message = "CBMBonus " .. label .. ": " .. tostring(cause)
    print(message)
    -- LuaJIT supplies io; keep failure reporting harmless if it is unavailable
    -- or the working directory is read-only. Never show UI at module load.
    if io and io.open then
        pcall(function()
            local file = io.open("CBMBonus.log", "a")
            if file then file:write(message, "\n"); file:close() end
        end)
    end
end

local function collect(group, field, amount)
    local entry = group[field]
    if not entry then
        entry = { sum = 0, best = 0, worst = 0 }
        group[field] = entry
    end
    entry.sum = entry.sum + amount
    if amount > entry.best then entry.best = amount end
    if amount < entry.worst then entry.worst = amount end
end

-- Extra attacks. Righteous Wrath and Improved Haste give theirs through a tagged opcode 1, native
-- Haste through its state. While more than one runs, only one counts: Haste leaves the tagged
-- ones out, and of those the strongest stays. Such an effect is set to 0 instead of being taken
-- back from the stat, because the engine derives hasted attacks from that stat. Its value stays
-- in the effect's special field, so a save made in between keeps it.
local function noteAttack(attacks, effect)
    local opcode = effect.m_effectId
    if opcode == 16 then
        -- Mode 2 only speeds movement.
        if effect.m_dWFlags == 2 then attacks.movementOnly = true else attacks.hasted = true end
    elseif opcode == 1 and resref(effect.m_res) == "CBTAPR" then
        attacks.tagged = true
        if effect.m_special > attacks.best then attacks.best = effect.m_special end
    end
end

local function pending(effect)
    -- Active timed effects use 4096 (low byte zero). Encoded delays 3..5
    -- and live pending delays 6..8 have not contributed their stat yet.
    local timing = EEex_BAnd(effect.m_durationType, 0xFF)
    return timing >= 3 and timing <= 8
end

local function settleAttacks(sprite, stats, attacks)
    EEex_Utility_IterateCPtrList(sprite.m_equipedEffectList, function(effect)
        noteAttack(attacks, effect)
    end)
    -- Haste delivered through opcode 177 shows only in the state.
    local state = EEex_BAnd(stats.m_generalState or 0, 0x8000) ~= 0
    local counted = attacks.hasted or (state and not attacks.movementOnly)
    local changed = false
    EEex_Utility_IterateCPtrList(sprite.m_timedEffectList, function(effect)
        if effect.m_effectId == 1 and not pending(effect) and resref(effect.m_res) == "CBTAPR" then
            local amount = 0
            if not counted and effect.m_special == attacks.best then
                amount, counted = effect.m_special, true
            end
            if effect.m_effectAmount ~= amount then
                effect.m_effectAmount = amount
                changed = true
            end
        end
    end)
    -- The engine applies the new amounts at its next rebuild; ask for it now.
    if changed then sprite.m_newEffect = 1 end
end

local function correct(sprite)
    local stats = sprite.m_derivedStats
    if not stats then return end
    local states = stats.m_spellStates
    local word = states:get(PASS_WORD)
    if EEex_BAnd(word, PASS_MASK) ~= 0 then return end

    -- This bit lives in exactly the struct whose values will be adjusted.
    -- Mark and verify BEFORE any stat write: unchanged passes cannot drift,
    -- and a binding returning an array copy cannot create repeated corrections.
    states:set(PASS_WORD, EEex_BOr(word, PASS_MASK))
    if EEex_BAnd(stats.m_spellStates:get(PASS_WORD), PASS_MASK) == 0 then
        error("pass marker spell state did not persist")
    end
    if EEex_BAnd(states:get(TYPED_WORD), TYPED_MASK) == 0 then return end

    local groups = {}
    local function visit(effect, timing, path, depth)
        local opcode = effect.m_effectId
        if opcode == 177 then
            -- Native 177 decodes its child, applies it inline, then destroys
            -- that child. Only the wrapper remains on the timed effect list.
            -- Child timing is overwritten by the wrapper on every application.
            local name = resref(effect.m_res):upper()
            if path[name] then error("external effect cycle: " .. name) end
            if depth >= 32 then error("external effect chain exceeds 32 links") end
            local child = EEex_Resource_Demand(name, "EFF")
            if not child then error("external effect resource missing: " .. name) end
            path[name] = true
            visit(child, timing, path, depth + 1)
            path[name] = nil
            return
        end
        -- Cast-spell delivery opcodes are deliberately not followed here:
        -- their spawned effects already have their own entries on the list.
        local tag = resref(effect.m_res)
        if not tags[tag] then return end
        if effect.m_dWFlags ~= 0 then return end
        local amount = effect.m_effectAmount
        if not fields[opcode] and opcode ~= 325 then return end
        if opcode == 0 and amount <= 0 then return end -- AC penalties remain untyped.
        if tag == "CBTCURSE" and amount >= 0 then return end
        local group = groups[tag]
        if not group then group = {}; groups[tag] = group end
        if opcode == 325 then
            for save = 33, 37 do collect(group, fields[save], amount) end
        else
            collect(group, fields[opcode], amount)
        end
    end
    local attacks = { best = 0 }
    EEex_Utility_IterateCPtrList(sprite.m_timedEffectList, function(effect)
        if pending(effect) then return end
        noteAttack(attacks, effect)
        local timing = EEex_BAnd(effect.m_durationType, 0xFF)
        if effect.m_effectId == 177 then
            -- BG2:EE 2.7.3.0 sets parameter 5 before applying a decoded child;
            -- an IDS or CheckAdd rejection marks the wrapper done, as does a
            -- done child. Keep those conditions entirely engine-owned.
            if effect.m_done ~= 0 or not effect.m_effectAmount4
                    or effect.m_effectAmount4 == 0 then return end
        end
        visit(effect, timing, {}, 0)
    end)
    if attacks.tagged then settleAttacks(sprite, stats, attacks) end

    local corrections = {}
    for _, group in pairs(groups) do
        for field, entry in pairs(group) do
            local extra = entry.sum - entry.best - entry.worst
            corrections[field] = (corrections[field] or 0) + extra
        end
    end
    -- Resolve every read before the first write. A malformed stat binding
    -- fails without leaving an arbitrary subset of the corrections applied.
    local values = {}
    for field, extra in pairs(corrections) do
        if extra ~= 0 then
            values[field] = stats[field] + (ascending[field] and -extra or extra)
        end
    end
    for field, value in pairs(values) do stats[field] = value end
end

B.failures = B.failures or 0
function B.Listener(sprite)
    if B.disabled then return end
    local ok, err = pcall(correct, sprite)
    if not ok then
        B.failures = B.failures + 1
        logError("listener error " .. B.failures, err)
        if B.failures >= 10 then
            B.disabled = true
            print("CBMBonus: listener disabled after 10 errors")
        end
    end
end

-- One engine registration even if the module is loaded a second time. The
-- trampoline always reaches the current implementation, without sprite caches.
if not B.registered then
    EEex_Opcode_AddListsResolvedListener(function(sprite) CBMBonus.Listener(sprite) end)
    B.registered = true
end

local function pierceMagic(effect, targetSprite)
    -- The engine's MR value is integral. Round the halved reduction down before
    -- clamping it to 10..40 percentage points, for five rounds (30 seconds).
    local resistance = EEex_Sprite_GetStat(targetSprite, 18)
    local reduction = math.max(10, math.min(40, math.floor(resistance / 2)))
    EEex_GameObject_ApplyEffect(targetSprite, {
        effectID = 166, effectAmount = -reduction, dwFlags = 0,
        durationType = 0, duration = 30, targetType = 2,
        spellLevel = effect.m_spellLevel, m_flags = effect.m_flags,
        sourceID = effect.m_sourceId, sourceTarget = effect.m_sourceTarget,
        m_sourceRes = resref(effect.m_sourceRes), m_sourceType = effect.m_sourceType,
        m_sourceFlags = effect.m_sourceFlags, m_casterLevel = effect.m_casterLevel,
        m_school = effect.m_school, m_secondaryType = effect.m_secondaryType,
    })
end

-- Opcode 402 requires an uppercase global name of at most eight characters.
-- Errors must not escape into the engine's Invoke Lua panic handler.
function CBMBPM(effect, targetSprite)
    -- The effect stays on the list and is called again on every pass unless it is
    -- marked done: measured in the lab, Magic Resistance fell to -128 within seconds.
    effect.m_done = true
    local ok, err = pcall(pierceMagic, effect, targetSprite)
    if not ok then logError("Pierce Magic", err) end
end
