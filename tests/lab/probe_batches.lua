-- probe_batches.lua: extra helpers for tests/lab/run_batches.py. Loaded after probe.lua, it
-- extends the global table CBMP. Every function returns plain tables the console serialises
-- to JSON; the driver decides what passed.

local P = CBMP

local function party(i) return EEex_Sprite_GetInPortrait(i) end

local function sprites()
    local out, seen = {}, {}
    local area = party(0).m_pArea
    for _, list in ipairs({ "m_lVertSort", "m_lVertSortBack", "m_lVertSortFlight" }) do
        local ok, l = pcall(function() return area[list] end)
        if ok and l then
            EEex_Utility_IterateCPtrList(l, function(id)
                local obj = EEex_GameObject_Get(id)
                if obj and not seen[id] and EEex_GameObject_IsSprite(obj, false) then
                    seen[id] = true
                    local s = EEex_GameObject_CastUserType(obj)
                    if s.m_objectType == 49 then out[#out + 1] = s end
                end
            end)
        end
    end
    return out
end

local function named(key)
    for _, s in ipairs(sprites()) do
        if EEex_Sprite_GetName(s) == key or s.m_scriptName:get():lower() == key:lower() then return s end
    end
end

-- A timed effect on a portrait (number) or creature (name), `seconds` long.
function P.fx(who, op, p1, p2, seconds)
    local s = type(who) == "number" and party(who) or named(who)
    EEex_GameObject_ApplyEffect(s, { effectID = op, effectAmount = p1, dwFlags = p2, durationType = 0,
                                     duration = seconds or 120, sourceID = s.m_id, sourceTarget = s.m_id })
    return true
end

function P.stats(who)
    local s = type(who) == "number" and party(who) or named(who)
    local st = s.m_derivedStats
    return { str = EEex_Sprite_GetStat(s, 36), strex = EEex_Sprite_GetStat(s, 37), mr = st.m_nResistMagic,
             thac0 = st.m_nTHAC0, dmg = st.m_nDamageBonus, ac = st.m_nArmorClass, luck = st.m_nLuck,
             apr = st.m_nNumberOfAttacks, maxhp = st.m_nMaxHitPoints, hp = s.m_baseStats.m_hitPoints }
end

-- Name, script name, hit points and EA of every creature in the area outside the party.
function P.others()
    local out = {}
    local members = {}
    for i = 0, 5 do local s = party(i); if s then members[s.m_id] = true end end
    for _, s in ipairs(sprites()) do
        if not members[s.m_id] then
            out[#out + 1] = { name = EEex_Sprite_GetName(s), dv = s.m_scriptName:get(), hp = s.m_baseStats.m_hitPoints,
                              ea = s.m_typeAI.m_EnemyAlly }
        end
    end
    return out
end

-- The effects with these opcodes on a sprite, whatever their source.
function P.ops(who, list)
    local s = type(who) == "number" and party(who) or named(who)
    local want, out = {}, {}
    for _, op in ipairs(list) do want[op] = true end
    EEex_Utility_IterateCPtrList(s.m_timedEffectList, function(e)
        if want[e.m_effectId] then
            out[#out + 1] = { op = e.m_effectId, src = e.m_sourceRes:get():upper(), p1 = e.m_effectAmount, p2 = e.m_dWFlags,
                              dur = e.m_duration, dt = e.m_durationType }
        end
    end)
    return out
end

-- A creature applies a spell to itself (no projectile, no casting).
function P.self_apply(key, res)
    local s = named(key)
    if not s then return false end
    EEex_Action_QueueResponseStringOnAIBase(string.format('ApplySpellRES("%s",Myself)', res), s)
    return true
end

function P.remove_all_others()
    local members = {}
    for i = 0, 5 do local s = party(i); if s then members[s.m_id] = true end end
    for _, s in ipairs(sprites()) do
        if not members[s.m_id] then
            EEex_GameObject_ApplyEffect(s, { effectID = 168, durationType = 1, sourceID = s.m_id, sourceTarget = s.m_id })
        end
    end
    return true
end

-- Clears a portrait of what earlier casts left: dispel by resource for each given spell.
function P.clear(i, list)
    local s = party(i)
    for _, res in ipairs(list) do
        EEex_GameObject_ApplyEffect(s, { effectID = 321, res = res, durationType = 1, sourceID = s.m_id, sourceTarget = s.m_id })
    end
    return true
end

return true
