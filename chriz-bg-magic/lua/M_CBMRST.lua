-- Lesser Restoration ends temporary attribute drain. The spell's opcode 402 calls CBMLRES on
-- the recipient; nothing that drains is rewritten. LuaJIT-compatible syntax.

if not (EEex_Utility_IterateCPtrList and EEex_BAnd) then
    return
end

-- Attribute opcodes, the drain they make, and what goes with a drain: icon, sounds, visuals.
local DRAIN = { [6] = true, [10] = true, [15] = true, [19] = true, [44] = true, [49] = true }
local LEFTOVER = { [142] = true, [174] = true, [215] = true }
-- Spells whose own weakness stays: filled in by the installer.
local SPARED = { %CBM_RESTORATION_SPARED% }
local ABSOLUTE = 4096

local function resref(value)
    if type(value) == "string" then return value:upper() end
    return value:get():upper()
end

-- A lower value, a low fixed value or a lower share, the way the game's drain spells and attacks
-- write it. Disease (opcode 78) and permanent loss are not in the list at all.
local function drains(effect)
    local amount, mode = effect.m_effectAmount, effect.m_dWFlags
    return (mode == 0 and amount < 0) or (mode == 1 and amount < 12) or (mode == 2 and amount < 100)
end

-- A timed effect that runs now; its end is a point in game time.
local function running(effect)
    return effect.m_done == 0 and EEex_BAnd(effect.m_durationType, 0xFF) == 0
        and EEex_BAnd(effect.m_durationType, ABSOLUTE) ~= 0
end

local function key(effect)
    return resref(effect.m_sourceRes) .. "|" .. tostring(effect.m_sourceId)
end

local function restore(sprite)
    local now = EngineGlobals.g_pBaldurChitin.m_pObjectGame.m_worldTime.m_gameTime
    local ended, kept, leftovers = {}, {}, {}
    EEex_Utility_IterateCPtrList(sprite.m_timedEffectList, function(effect)
        if not running(effect) then return end
        local source = key(effect)
        if DRAIN[effect.m_effectId] and drains(effect) and not SPARED[resref(effect.m_sourceRes)] then
            effect.m_duration = now
            ended[source] = true
        elseif LEFTOVER[effect.m_effectId] then
            leftovers[#leftovers + 1] = effect
        else
            kept[source] = true
        end
    end)
    -- What a drain brought along goes with it, unless its source still does something else.
    for _, effect in ipairs(leftovers) do
        local source = key(effect)
        if ended[source] and not kept[source] then effect.m_duration = now end
    end
end

-- Opcode 402 requires an uppercase global name of at most eight characters. The effect is
-- called again on every pass unless it is marked done.
function CBMLRES(effect, sprite)
    effect.m_done = true
    local ok, err = pcall(restore, sprite)
    if not ok then print("CBMRestore: " .. tostring(err)) end
end
