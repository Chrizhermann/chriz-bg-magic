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

-- Bonus probes always resolve a fresh sprite, including after a manual save reload.
local function bonus_sprite(who)
    return assert(type(who) == "number" and party(who) or named(who), "bonus probe: missing sprite")
end

-- Opcode 177 runs its EFF internally; that child is absent from the timed list.
-- This independent read-only probe inspects the resource, not the bonus listener.
local function bonus_external_payload(wrapper, row)
    local effect, seen, chain = wrapper, {}, {}
    while effect.m_effectId == 177 do
        local res = effect.m_res:get():upper()
        assert(res ~= "" and not seen[res], "bonus probe: empty or cyclic external effect")
        assert(#chain < 32, "bonus probe: external effect chain exceeds 32 links")
        seen[res] = true
        chain[#chain + 1] = res
        -- EFF demand returns CGameEffectBase. Never mutate or retain the userdata.
        effect = assert(EEex_Resource_Demand(res, "EFF"), "bonus probe: missing EFF " .. res)
    end
    return { op = effect.m_effectId, src = row.src, tag = effect.m_res:get():upper(),
        p1 = effect.m_effectAmount, p2 = effect.m_dWFlags, dur = row.dur, dt = row.dt,
        external_chain = chain }
end

function P.bonus_snapshot(who)
    local s = bonus_sprite(who)
    local out = P.stats(who)
    out.saves = {}
    for _, id in ipairs({9, 10, 11, 12, 13}) do out.saves[#out.saves + 1] = EEex_Sprite_GetStat(s, id) end
    out.time = EngineGlobals.g_pBaldurChitin.m_pObjectGame.m_worldTime.m_gameTime
    out.effects = {}
    EEex_Utility_IterateCPtrList(s.m_timedEffectList, function(e)
        local row = {
            op = e.m_effectId, src = e.m_sourceRes:get():upper(), tag = e.m_res:get():upper(),
            p1 = e.m_effectAmount, p2 = e.m_dWFlags, dur = e.m_duration, dt = e.m_durationType,
        }
        out.effects[#out.effects + 1] = row
        if row.op == 177 then
            row.done, row.initialized = e.m_done, e.m_effectAmount4
            local active = (row.dt == 4096 and row.dur > out.time)
                or row.dt == 1 or row.dt == 2 or row.dt == 9
            -- Failed IDS/CheckAdd matches and finished children mark the wrapper done.
            if active and row.done == 0 and row.initialized and row.initialized ~= 0 then
                local ok, payload = pcall(bonus_external_payload, e, row)
                if ok then row.external = payload else row.external_error = tostring(payload) end
            end
        end
    end)
    return out
end

-- Apply the installed spell to a sprite directly. This tests its effects and nested
-- deliveries; projectile targeting and normal spellbook casting remain separate checks.
function P.bonus_apply(who, res)
    assert(res:match("^[%w_#]+$") and #res <= 8, "bonus probe: invalid spell resource")
    local s = bonus_sprite(who)
    EEex_Action_QueueResponseStringOnAIBase(string.format('ApplySpellRES("%s",Myself)', res), s)
    return true
end

-- The enemy is the caster, so Prayer's ally/enemy filtering uses the other side.
function P.bonus_enemy_prayer(who, target, res)
    assert(res:match("^[%w_#]+$") and #res <= 8, "bonus probe: invalid spell resource")
    local s, t = bonus_sprite(who), bonus_sprite(target)
    EEex_Action_QueueResponseStringOnAIBase(
        string.format('ReallyForceSpellPointRES("%s",[%d.%d])', res, t.m_pos.x, t.m_pos.y), s)
    return true
end

function P.bonus_clear(who, sources)
    local s = bonus_sprite(who)
    for _, res in ipairs(sources) do
        EEex_GameObject_ApplyEffect(s, { effectID = 321, res = res, durationType = 1,
            sourceID = s.m_id, sourceTarget = s.m_id })
    end
    return true
end

-- Shorten only already active timed effects for the expiry checks. The engine then
-- expires them normally; no cast or removal is used when observing the weaker bonus.
function P.bonus_expire(who, sources, seconds)
    local s, want, changed = bonus_sprite(who), {}, 0
    for _, res in ipairs(sources) do want[res:upper()] = true end
    local deadline = EngineGlobals.g_pBaldurChitin.m_pObjectGame.m_worldTime.m_gameTime + seconds * 15
    EEex_Utility_IterateCPtrList(s.m_timedEffectList, function(e)
        if want[e.m_sourceRes:get():upper()] and e.m_durationType == 4096 then
            e.m_duration = deadline
            changed = changed + 1
        end
    end)
    return changed
end

function P.bonus_fx(who, op, amount, mode, tag, state, seconds)
    local s = bonus_sprite(who)
    EEex_GameObject_ApplyEffect(s, { effectID = op, effectAmount = amount, dwFlags = mode,
        res = tag, m_sourceRes = "CBMQLAB", durationType = 0, duration = seconds or 180,
        sourceID = s.m_id, sourceTarget = s.m_id })
    if state then
        EEex_GameObject_ApplyEffect(s, { effectID = 328, effectAmount = 1, dwFlags = state, special = 1,
            m_sourceRes = "CBMQLAB", durationType = 0, duration = seconds or 180,
            sourceID = s.m_id, sourceTarget = s.m_id })
    end
    return true
end

-- A zero AC modifier requests a real engine rebuild without changing the measured values.
function P.bonus_rebuild(who)
    return P.bonus_fx(who, 0, 0, 0, "", nil, 1)
end

-- The spell book answers no console: only a few menus poll it. The book calls this function
-- every frame, so polling from it keeps the console alive while the book is open.
function P.book_console()
    if not CBMP_MAGE_PAGE then
        CBMP_MAGE_PAGE = magePageInfo
        magePageInfo = function()
            EEexRemote.Poll()
            return CBMP_MAGE_PAGE()
        end
    end
    return true
end

-- What the Contingency, Spell Sequencer and Spell Trigger screens list for this spell level.
function P.book_list(level)
    local rows, before = {}, currentSpellLevel
    currentSpellLevel = level
    for _, v in ipairs(filterContingencyMageSpells()) do
        rows[#rows + 1] = { res = v.resref, master = v.masterResref, name = Infinity_FetchString(v.name),
                            icon = v.icon, desc = v.description }
    end
    currentSpellLevel = before
    return { mode = bookMode, screen = contingencyResRef, slots = contingencyMaxSpells, rows = rows }
end

-- Chooses spells as a click on the list does; each pick is { resref, master resref }.
function P.book_pick(picks)
    for _, pick in ipairs(picks) do mageScreen:SequenceSpell(pick[1], pick[2]) end
    refreshMageBook()
    return #bottomSpells
end

function P.book_done()
    mageScreen:DoneSequencingSpells()
    e:SelectEngine(worldScreen)
    return true
end

function P.force(who, res)
    EEex_Action_QueueResponseStringOnAIBase(string.format('ReallyForceSpellRES("%s",Myself)', res), party(who))
    return true
end

return true
