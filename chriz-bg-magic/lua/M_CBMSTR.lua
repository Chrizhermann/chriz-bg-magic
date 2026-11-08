-- Strength floors. A spell of this mod that gives a fixed Strength never lowers a higher one, and
-- bonuses and penalties from other sources count on top of it, in whatever order they came.
-- Such a spell carries a marker instead of setting the stat: opcode 44 by 0 with the resource
-- CBTSTRF and Strength * 1000 + exceptional Strength in its special field, plus the spell state
-- below. A creature in another form keeps the values of its form. LuaJIT-compatible syntax.

if not (EEex_Opcode_AddListsResolvedListener and EEex_Utility_IterateCPtrList and EEex_BAnd
        and EEex_LShift and EEex_Resource_Demand) then
    return
end

CBMStrength = CBMStrength or {}
local S = CBMStrength

local FLOOR_STATE = %CBM_STR_FLOOR_STATE%
local FLOOR_WORD, FLOOR_MASK = math.floor(FLOOR_STATE / 32), EEex_LShift(1, FLOOR_STATE % 32)
local TAG = "CBTSTRF"

local function resref(value)
    if type(value) == "string" then return value end
    return value:get()
end

local function pending(effect)
    -- Active timed effects use 4096 (low byte zero). Encoded delays 3..5 and live pending delays
    -- 6..8 have not contributed their stat yet.
    local timing = EEex_BAnd(effect.m_durationType, 0xFF)
    return timing >= 3 and timing <= 8
end

-- One Strength score to compare: 18/00 is below 19, and exceptional Strength counts only at 18.
function S.score(strength, extra)
    if strength == 18 then return 18000 + math.max(0, math.min(100, extra)) end
    return strength * 1000
end

-- The best floor and the sums of everything that adds to Strength, following opcode 177 into its
-- EFF the way the engine applies it.
local function visit(effect, sums, path, depth)
    local opcode = effect.m_effectId
    if opcode == 177 then
        local name = resref(effect.m_res):upper()
        if path[name] then error("external effect cycle: " .. name) end
        if depth >= 32 then error("external effect chain exceeds 32 links") end
        local child = EEex_Resource_Demand(name, "EFF")
        if not child then return end
        path[name] = true
        visit(child, sums, path, depth + 1)
        path[name] = nil
    elseif opcode == 44 then
        if resref(effect.m_res) == TAG then
            if effect.m_special > sums.floor then sums.floor = effect.m_special end
        elseif effect.m_dWFlags == 0 then
            sums.strength = sums.strength + effect.m_effectAmount
        end
    elseif opcode == 97 then
        if effect.m_dWFlags == 0 then sums.extra = sums.extra + effect.m_effectAmount end
    elseif opcode == 132 then
        -- Draw Upon Divine Might counts once, the oldest one, as in the engine.
        if not sums.might then
            sums.might = true
            sums.strength = sums.strength + effect.m_effectAmount
        end
    end
end

function S.resolve(sprite)
    local stats = sprite.m_derivedStats
    if not stats then return end
    if EEex_BAnd(stats.m_spellStates:get(FLOOR_WORD), FLOOR_MASK) == 0 then return end
    if stats.m_bPolymorphed ~= 0 then return end
    local sums = { floor = 0, strength = 0, extra = 0 }
    local function each(effect)
        if pending(effect) then return end
        if effect.m_effectId == 177 and (effect.m_done ~= 0 or not effect.m_effectAmount4
                or effect.m_effectAmount4 == 0) then
            return
        end
        visit(effect, sums, {}, 0)
    end
    EEex_Utility_IterateCPtrList(sprite.m_equipedEffectList, each)
    EEex_Utility_IterateCPtrList(sprite.m_timedEffectList, each)
    if sums.floor <= 0 then return end
    local strength = math.max(1, math.min(25, math.floor(sums.floor / 1000) + sums.strength))
    local extra = 0
    if strength == 18 then extra = math.max(0, math.min(100, sums.floor % 1000 + sums.extra)) end
    -- Only ever up: what the game worked out without the floor stays when it is higher. Writing the
    -- same values again on the passes without a rebuild changes nothing.
    if S.score(strength, extra) > S.score(stats.m_nSTR, stats.m_nSTRExtra) then
        stats.m_nSTR = strength
        stats.m_nSTRExtra = extra
    end
end

local function logError(cause)
    local message = "CBMStrength: " .. tostring(cause)
    print(message)
    if io and io.open then
        pcall(function()
            local file = io.open("CBMStrength.log", "a")
            if file then file:write(message, "\n"); file:close() end
        end)
    end
end

S.failures = S.failures or 0
function S.Listener(sprite)
    if S.disabled then return end
    local ok, err = pcall(S.resolve, sprite)
    if not ok then
        S.failures = S.failures + 1
        logError(err)
        if S.failures >= 10 then
            S.disabled = true
            print("CBMStrength: listener disabled after 10 errors")
        end
    end
end

-- One engine registration even if the module is loaded a second time.
if not S.registered then
    EEex_Opcode_AddListsResolvedListener(function(sprite) CBMStrength.Listener(sprite) end)
    S.registered = true
end
