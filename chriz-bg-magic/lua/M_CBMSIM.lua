-- Simulacrum: the copy keeps the special abilities its class and kit give at its own, lower level,
-- as often as that level gives them. Abilities of items, quests and scripts go. What the original
-- had used up stays used up. SIMULACR.SPL calls CBMSIMU through opcode 402. LuaJIT-compatible syntax.

if not (EEex_Resource_Load2DA and EEex_Utility_IterateCPtrList and EEex_Utility_FreeCPtrList
        and EEex_GameObject_ApplyEffect) then
    return
end

CBMSimulacrum = CBMSimulacrum or {}
local S = CBMSimulacrum

-- CLASS.IDS: the classes of each class, with the stat that holds the level of each (LEVEL,
-- LEVEL2, LEVEL3).
local PARTS = {
    [1] = { { 1, 34 } }, [2] = { { 2, 34 } }, [3] = { { 3, 34 } }, [4] = { { 4, 34 } }, [5] = { { 5, 34 } },
    [6] = { { 6, 34 } }, [7] = { { 2, 34 }, { 1, 68 } }, [8] = { { 2, 34 }, { 3, 68 } },
    [9] = { { 2, 34 }, { 4, 68 } }, [10] = { { 2, 34 }, { 1, 68 }, { 4, 69 } }, [11] = { { 11, 34 } },
    [12] = { { 12, 34 } }, [13] = { { 1, 34 }, { 4, 68 } }, [14] = { { 3, 34 }, { 1, 68 } },
    [15] = { { 3, 34 }, { 4, 68 } }, [16] = { { 2, 34 }, { 11, 68 } }, [17] = { { 2, 34 }, { 1, 68 }, { 3, 69 } },
    [18] = { { 3, 34 }, { 12, 68 } }, [19] = { { 19, 34 } }, [20] = { { 20, 34 } }, [21] = { { 21, 34 } },
}
local NAMES = {
    [1] = "MAGE", [2] = "FIGHTER", [3] = "CLERIC", [4] = "THIEF", [5] = "BARD", [6] = "PALADIN",
    [7] = "FIGHTER_MAGE", [8] = "FIGHTER_CLERIC", [9] = "FIGHTER_THIEF", [10] = "FIGHTER_MAGE_THIEF",
    [11] = "DRUID", [12] = "RANGER", [13] = "MAGE_THIEF", [14] = "CLERIC_MAGE", [15] = "CLERIC_THIEF",
    [16] = "FIGHTER_DRUID", [17] = "FIGHTER_MAGE_CLERIC", [18] = "CLERIC_RANGER", [19] = "SORCERER",
    [20] = "MONK", [21] = "SHAMAN",
}
-- The game's own ability table of a class without a kit. Mages have none.
local BASE = {
    [2] = "CLABFI01", [3] = "CLABPR01", [4] = "CLABTH01", [5] = "CLABBA01", [6] = "CLABPA01", [11] = "CLABDR01",
    [12] = "CLABRN01", [19] = "CLABSO01", [20] = "CLABMO01", [21] = "CLABSH01",
}
local TRUECLASS = 0x4000
-- High-level abilities come with the experience of the Throne of Bhaal.
local HLA_XP = 3000000

local function rows(name)
    local ok, array = pcall(EEex_Resource_Load2DA, name)
    if not ok or not array then return function() return nil end end
    return array:getRowTableItr(true)
end

local function columnLevels(name)
    local ok, array = pcall(EEex_Resource_Load2DA, name)
    if not ok or not array then return {} end
    local sizeX = array:getDimensions()
    local levels = {}
    for i = 0, sizeX - 2 do levels[i + 2] = tonumber(array:getColumnLabel(i)) end
    return levels
end

-- The table of a kit, from KITLIST.2DA, and the class it belongs to.
local function kitTable(kit)
    if kit == 0 or kit == TRUECLASS then return nil end
    for row in rows("KITLIST") do
        local ids = tonumber(row[10] or "")
        if ids == kit then return row[6], tonumber(row[9] or "") end
    end
    return nil
end

-- {resref = times} for every ability a class table gives up to this level.
local function addTable(allowed, name, level)
    if not name or name == "*" or name == "****" then return end
    local levels = columnLevels(name)
    for row in rows(name) do
        for column = 2, #row do
            local at = levels[column]
            local value = row[column]
            if at and at <= level and value and value:upper():sub(1, 3) == "GA_" then
                local spell = value:sub(4):upper()
                allowed[spell] = (allowed[spell] or 0) + 1
            end
        end
    end
end

local function levelForXP(className, xp)
    for row in rows("XPLEVEL") do
        if row[1]:upper() == className then
            local level = 0
            for column = 2, #row do
                local need = tonumber(row[column])
                if need and need <= xp then level = column - 1 end
            end
            return level
        end
    end
    return 99
end

-- What the copy may keep: counts from its class and kit tables at its levels, and the high-level
-- abilities if its levels reach the Throne of Bhaal's.
function S.allowed(sprite)
    local class = sprite.m_typeAI.m_Class
    local parts = PARTS[class] or {}
    local kitName, kitClass = kitTable(EEex_Sprite_GetStat(sprite, 152))
    local allowed, keep = {}, {}
    local reachesHLA = #parts > 0
    for _, part in ipairs(parts) do
        local partClass, stat = part[1], part[2]
        local level = EEex_Sprite_GetStat(sprite, stat)
        local name = BASE[partClass]
        if kitName and (kitClass == partClass or #parts == 1) then name = kitName end
        addTable(allowed, name, level)
        if level < levelForXP(NAMES[partClass] or "", HLA_XP) then reachesHLA = false end
    end
    if reachesHLA then
        for row in rows("LUABBR") do
            if row[1]:upper() == (NAMES[class] or "") then
                for hla in rows("LU" .. row[2]:upper()) do
                    local value = hla[2] or ""
                    if value:upper():sub(1, 3) == "GA_" then keep[value:sub(4):upper()] = true end
                end
            end
        end
    end
    return allowed, keep
end

-- {resref = uses left}, as the special abilities button shows them.
function S.ready(sprite)
    local ready = {}
    local list = sprite:GetQuickButtons(4, false)
    EEex_Utility_IterateCPtrList(list, function(button)
        local spell = button.m_abilityId.m_res:get():upper()
        ready[spell] = (ready[spell] or 0) + button.m_count
    end)
    EEex_Utility_FreeCPtrList(list)
    return ready
end

local function apply(sprite, opcode, spell)
    EEex_GameObject_ApplyEffect(sprite, { effectID = opcode, res = spell, durationType = 1,
                                          sourceID = sprite.m_id, sourceTarget = sprite.m_id })
end

local function trim(sprite)
    local allowed, keep = S.allowed(sprite)
    local ready = S.ready(sprite)
    local known = {}
    for _, _, spell in sprite:getKnownInnateSpellsIterator() do known[spell:upper()] = true end
    for spell in pairs(known) do
        local times = allowed[spell] or 0
        if keep[spell] then
            -- a high-level ability of a copy that is high enough stays as the original had it
        elseif times == 0 then
            apply(sprite, 172, spell)
        elseif (ready[spell] or 0) > times then
            -- As many uses as its level gives; never more than were left.
            apply(sprite, 172, spell)
            for _ = 1, times do apply(sprite, 171, spell) end
        end
    end
end

-- Opcode 402 requires an uppercase global name of at most eight characters. The effect is called
-- again on every pass unless it is marked done.
function CBMSIMU(effect, sprite)
    effect.m_done = true
    local ok, err = pcall(trim, sprite)
    if not ok then print("CBMSimulacrum: " .. tostring(err)) end
end
