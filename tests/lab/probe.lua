-- probe.lua: in-game checks of chriz-bg-magic's changes, driven from outside through the
-- EEex Remote Console (tests/lab/run_probe.py). Loaded once with
-- assert(loadfile(...))(); it defines the global table CBMP. Every function returns plain
-- tables the console serialises to JSON; the driver decides what passed.
--
-- The game must be in the world with a party. Casts are queued as script actions on a
-- party member, so the world has to run (CBMP.unpause). Nothing is saved.

CBMP = {}
local P = CBMP

local function party(i) return EEex_Sprite_GetInPortrait(i) end

local function safe(f, ...)
    local ok, v = pcall(f, ...)
    if ok then return v end
    return "ERR " .. tostring(v)
end

local function effects(s, res)
    local out = {}
    EEex_Utility_IterateCPtrList(s.m_timedEffectList, function(e)
        local src = e.m_sourceRes:get():upper()
        if res == nil or src == res then
            out[#out + 1] = { op = e.m_effectId, src = src, p1 = e.m_effectAmount, p2 = e.m_dWFlags,
                              save = safe(function() return e.m_savingThrow end) }
        end
    end)
    return out
end

local function describe(s)
    return {
        id = s.m_id, name = EEex_Sprite_GetName(s), dv = s.m_scriptName:get(),
        hp = s.m_baseStats.m_hitPoints, state = EEex_Sprite_GetState(s),
        x = s.m_pos.x, y = s.m_pos.y,
        saves = { death = EEex_Sprite_GetStat(s, 9), breath = EEex_Sprite_GetStat(s, 12),
                  spell = EEex_Sprite_GetStat(s, 13) },
    }
end

local function apply(s, args)
    args.sourceID = args.sourceID or s.m_id
    args.sourceTarget = args.sourceTarget or s.m_id
    EEex_GameObject_ApplyEffect(s, args)
end

-- Creatures in the party's area whose name or script name matches. A creature asleep
-- without an icon moves to the area's back list (IESDP opcode 39), so every list counts.
local function find(key)
    local found, seen = {}, {}
    local area = party(0).m_pArea
    for _, list in ipairs({ "m_lVertSort", "m_lVertSortBack", "m_lVertSortFlight" }) do
        local ok, l = pcall(function() return area[list] end)
        if ok and l then
            EEex_Utility_IterateCPtrList(l, function(id)
                local obj = EEex_GameObject_Get(id)
                if obj and not seen[id] and EEex_GameObject_IsSprite(obj, false) then
                    seen[id] = true
                    local s = EEex_GameObject_CastUserType(obj)
                    if s.m_objectType == 49 and (EEex_Sprite_GetName(s) == key or s.m_scriptName:get():lower() == key:lower()) then
                        found[#found + 1] = s
                    end
                end
            end)
        end
    end
    return found
end

local function one(key)
    local f = find(key)
    assert(#f == 1, "CBMP: expected one " .. key .. ", found " .. #f)
    return f[1]
end

function P.unpause()
    local paused = worldScreen:CheckIfPaused()
    if paused then EEex_GameState_TogglePause() end
    return { was_paused = paused }
end

-- Keeps the party alive and reports it.
function P.party()
    local out = {}
    for i = 0, 5 do
        local s = party(i)
        if s then
            out[#out + 1] = describe(s)
        end
    end
    return out
end

function P.protect_party()
    for i = 0, 5 do
        local s = party(i)
        if s then apply(s, { effectID = 208, effectAmount = 1, durationType = 0, duration = 1200 }) end
    end
    return true
end

-- Restores a party member's hit points (heal opcode 17, plenty).
function P.heal(i)
    apply(party(i), { effectID = 17, effectAmount = 500, durationType = 1 })
    return party(i).m_baseStats.m_hitPoints
end

-- Sets saves on a portrait (index) or a creature (name/script name): opcode 33 death,
-- 36 breath, 37 spell, parameter 2 = 1 (set), for `seconds`.
function P.set_saves(who, saves, seconds)
    local s = type(who) == "number" and party(who) or one(who)
    local ops = { death = 33, breath = 36, spell = 37 }
    for kind, value in pairs(saves) do
        apply(s, { effectID = ops[kind], effectAmount = value, dwFlags = 1, durationType = 0, duration = seconds or 300 })
    end
    return describe(s)
end

-- Queues a spell cast by portrait `caster` at `target` (an object string such as
-- Myself, Player2 or "aegnoll").
function P.cast(caster, res, target)
    EEex_Action_QueueResponseStringOnAIBase(string.format('ReallyForceSpellRES("%s",%s)', res, target), party(caster))
    return true
end

-- Applies a spell's effects to a target directly (no projectile, no casting).
function P.apply_spell(caster, res, target)
    EEex_Action_QueueResponseStringOnAIBase(string.format('ApplySpellRES("%s",%s)', res, target), party(caster))
    return true
end

function P.cast_point(caster, res, x, y)
    EEex_Action_QueueResponseStringOnAIBase(string.format('ReallyForceSpellPointRES("%s",[%d.%d])', res, x, y), party(caster))
    return true
end

-- Spawns a creature next to portrait 0, offset by dx/dy.
function P.spawn(res, dx, dy)
    local s = party(0)
    local x, y = s.m_pos.x + dx, s.m_pos.y + dy
    EEex_Action_QueueResponseStringOnAIBase(string.format('CreateCreature("%s",[%d.%d],0)', res, x, y), s)
    return { x = x, y = y }
end

-- A spawned creature stays hostile (many area spells hit only enemies), cannot die
-- (opcode 208) and is held where it stands (opcode 109, all creatures, as the base
-- game's Web uses it) for `seconds`.
function P.pin(key, seconds)
    local s = one(key)
    apply(s, { effectID = 208, effectAmount = 1, durationType = 0, duration = 1200 })
    apply(s, { effectID = 109, effectAmount = 0, dwFlags = 2, durationType = 0, duration = seconds or 120 })
    return describe(s)
end

function P.creature(key, res)
    local s = one(key)
    local d = describe(s)
    d.effects = effects(s, res)
    return d
end

function P.portrait(i, res)
    local s = party(i)
    local d = describe(s)
    d.effects = effects(s, res)
    return d
end

-- One point of damage (opcode 12, crushing, no flags).
function P.damage(key, amount)
    local s = one(key)
    apply(s, { effectID = 12, effectAmount = amount or 1, dwFlags = 0, durationType = 1 })
    return describe(s)
end

-- Ends any sleep (opcode 2).
function P.cure_sleep(key)
    local s = one(key)
    apply(s, { effectID = 2, durationType = 1 })
    return describe(s)
end

-- Logs every effect added to a portrait or creature (EEex opcode 403) into CBMP.log.
CBMP.log = {}
CBMLOG = function(op403, effect, sprite)
    pcall(function()
        CBMP.log[#CBMP.log + 1] = { who = EEex_Sprite_GetName(sprite), op = effect.m_effectId,
                                    src = effect.m_sourceRes:get(), p1 = effect.m_effectAmount,
                                    p2 = effect.m_dWFlags, save = effect.m_savingThrow,
                                    bonus = effect.m_saveMod }
    end)
    return false
end

function P.watch(who, seconds)
    local s = type(who) == "number" and party(who) or one(who)
    apply(s, { effectID = 403, res = "CBMLOG", durationType = 0, duration = seconds or 20 })
    return true
end

function P.take_log(op)
    local out = {}
    for _, e in ipairs(CBMP.log) do
        if op == nil or e.op == op then out[#out + 1] = e end
    end
    CBMP.log = {}
    return out
end

return true
