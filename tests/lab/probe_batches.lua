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
                              ea = s.m_typeAI.m_EnemyAlly, id = s.m_id, x = s.m_pos.x, y = s.m_pos.y,
                              class_script = s:getScriptLevelResRef(4) }
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

-- What a summoned creature is in the game, after everything the game adds to its file.
function P.being(name)
    local s = named(name)
    if not s then return nil end
    local out, ai = P.stats(name), s.m_typeAI
    out.id, out.ea, out.gender, out.specific, out.alignment = s.m_id, ai.m_EnemyAlly, ai.m_Gender, ai.m_Specifics, ai.m_Alignment
    out.level = EEex_Sprite_GetStat(s, 34)
    local function stats(list)
        local got = {}
        for _, id in ipairs(list) do got[#got + 1] = EEex_Sprite_GetStat(s, id) end
        return got
    end
    out.saves = stats({ 9, 10, 11, 12, 13 })
    out.resist = stats({ 14, 15, 16, 17, 18, 21, 22, 23, 24 })
    out.attributes = stats({ 36, 38, 39, 40, 41, 42 })
    out.known = {}
    for level, _, res in s:getKnownPriestSpellsIterator() do out.known[#out.known + 1] = level .. ":" .. res end
    out.equipped = {}
    EEex_Utility_IterateCPtrList(s.m_equipedEffectList, function(e)
        local key = tostring(e.m_effectId)
        out.equipped[key] = (out.equipped[key] or 0) + 1
    end)
    return out
end

-- An effect on a portrait as a creature's spell or weapon would leave it.
function P.fx_from(who, from, res, kind, op, p1, p2, seconds)
    local s, f = party(who), named(from)
    EEex_GameObject_ApplyEffect(s, { effectID = op, effectAmount = p1, dwFlags = p2, durationType = 0,
                                     duration = seconds, m_sourceRes = res, m_sourceType = kind,
                                     sourceID = f.m_id, sourceTarget = s.m_id })
    return true
end

function P.attributes(who)
    local s = party(who)
    local out = {}
    for name, id in pairs({ str = 36, int = 38, wis = 39, dex = 40, con = 41, chr = 42, level = 34 }) do
        out[name] = EEex_Sprite_GetStat(s, id)
    end
    out.saves = {}
    for _, id in ipairs({ 9, 10, 11, 12, 13 }) do out.saves[#out.saves + 1] = EEex_Sprite_GetStat(s, id) end
    return out
end

-- A sprite's special abilities: known, and how many uses are ready; class, kit and levels.
function P.innates(who)
    local s
    if type(who) == "number" and who < 6 then s = party(who) else
        local o = EEex_GameObject_Get(who)
        s = o and EEex_GameObject_CastUserType(o)
    end
    if not s then return nil end
    local out = { known = {}, ready = {}, class = s.m_typeAI.m_Class, kit = EEex_Sprite_GetStat(s, 152),
                  levels = { EEex_Sprite_GetStat(s, 34), EEex_Sprite_GetStat(s, 68), EEex_Sprite_GetStat(s, 69) },
                  name = EEex_Sprite_GetName(s) }
    for _, _, spell in s:getKnownInnateSpellsIterator() do out.known[#out.known + 1] = spell:upper() end
    local list = s:GetQuickButtons(4, false)
    EEex_Utility_IterateCPtrList(list, function(button)
        local spell = button.m_abilityId.m_res:get():upper()
        out.ready[spell] = (out.ready[spell] or 0) + button.m_count
    end)
    EEex_Utility_FreeCPtrList(list)
    return out
end

function P.order_party(who, text)
    EEex_Action_QueueResponseStringOnAIBase(text, party(who))
    return true
end

function P.give_innate(who, res, times)
    local s = type(who) == "number" and party(who) or named(who)
    for _ = 1, times do
        EEex_GameObject_ApplyEffect(s, { effectID = 171, res = res, durationType = 1, sourceID = s.m_id, sourceTarget = s.m_id })
    end
    return true
end

-- Whether a script trigger holds for this creature.
function P.holds(name, text)
    return EEex_Trigger_EvalConditionalStringAsAIBase(text, named(name))
end

function P.order(name, text)
    EEex_Action_QueueResponseStringOnAIBase(text, named(name))
    return true
end

-- A creature casts a spell on itself at once (opcode 146, its own level), past whatever it is doing.
function P.cast_now(name, res)
    local s = named(name)
    if not s then return false end
    EEex_GameObject_ApplyEffect(s, { effectID = 146, dwFlags = 1, res = res, durationType = 1,
                                     sourceID = s.m_id, sourceTarget = s.m_id })
    return true
end

-- Strength now and every effect on a creature that can change it, from both effect lists.
function P.strength_effects(name)
    local s = type(name) == "number" and party(name) or named(name)
    local out = { str = s.m_derivedStats.m_nSTR, strex = s.m_derivedStats.m_nSTRExtra,
                  base = s.m_baseStats.m_STRBase, effects = {} }
    for _, list in ipairs({ "m_equipedEffectList", "m_timedEffectList" }) do
        EEex_Utility_IterateCPtrList(s[list], function(e)
            local op = e.m_effectId
            if op == 44 or op == 97 or op == 132 or op == 177 or op == 328 then
                out.effects[#out.effects + 1] = { list = list:sub(3, 6), op = op, p1 = e.m_effectAmount, p2 = e.m_dWFlags,
                    res = e.m_res:get(), src = e.m_sourceRes:get(), dt = e.m_durationType, special = e.m_special,
                    done = e.m_done }
            end
        end)
    end
    return out
end

-- What a creature's body is now: attributes, armour, attacks, look, the item in the magic weapon slot.
function P.form_state(name)
    local s = type(name) == "number" and party(name) or named(name)
    if not s then return nil end
    local st = s.m_derivedStats
    local out = { str = st.m_nSTR, strex = st.m_nSTRExtra, dex = st.m_nDEX, ac = st.m_nArmorClass,
                  apr = st.m_nNumberOfAttacks, missile = EEex_Sprite_GetStat(s, 3), polymorphed = st.m_bPolymorphed,
                  mr = st.m_nResistMagic, fire = EEex_Sprite_GetStat(s, 14), cold = EEex_Sprite_GetStat(s, 15),
                  hp = s.m_baseStats.m_hitPoints, base_anim = s.m_baseStats.m_animationType,
                  state = st.m_generalState }
    local ok, anim = pcall(function() return s.m_animation.m_animation.m_animationID end)
    out.anim = ok and anim or tostring(anim)
    out.items = {}
    for i = 0, 38 do
        local ok, item = pcall(function() return s.m_equipment.m_items:get(i) end)
        if ok and item and item.pRes then out.items[#out.items + 1] = item.pRes.resref:get():upper() end
    end
    out.selected = s.m_equipment.m_selectedWeapon
    out.innates = {}
    for _, _, spell in s:getKnownInnateSpellsIterator() do out.innates[#out.innates + 1] = spell:upper() end
    return out
end

-- The party AI button. Returns what it says now.
function P.party_ai(on)
    local now = game:GetPartyAI()
    now = now == true or now == 1
    if now ~= on then game:ToggleAI() end
    return game:GetPartyAI()
end

-- A creature applies a spell to itself (no projectile, no casting).
function P.self_apply(key, res)
    local s = named(key)
    if not s then return false end
    EEex_Action_QueueResponseStringOnAIBase(string.format('ApplySpellRES("%s",Myself)', res), s)
    return true
end

-- Attacks of a party member, the tagged extra attacks on it, and a spell cast on it.
function P.attacks(who)
    local s = party(who)
    local tagged = {}
    EEex_Utility_IterateCPtrList(s.m_timedEffectList, function(e)
        if e.m_effectId == 1 and e.m_res:get() == "CBTAPR" then tagged[#tagged + 1] = e.m_effectAmount end
    end)
    return { apr = s.m_derivedStats.m_nNumberOfAttacks, tagged = tagged }
end

-- Level of a portrait: what a spell of this caster reads, for a single class.
function P.level(who)
    return EEex_Sprite_GetStat(party(who), 34)
end

function P.on_member(who, res)
    EEex_Action_QueueResponseStringOnAIBase(string.format('ApplySpellRES("%s",Myself)', res), party(who))
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

-- The rows the character record lists: one entry per row, however many effects ask for it.
function P.icons(who)
    local s = type(who) == "number" and party(who) or named(who)
    local out = {}
    EEex_Utility_IterateCPtrList(s.m_portraitIcons, function(v) out[#out + 1] = v.icon end)
    table.sort(out)
    return out
end

-- Leaves `amount` spell levels in every effect of this opcode, so that one spell spends them.
function P.spend(who, opcode, amount)
    local n = 0
    EEex_Utility_IterateCPtrList(party(who).m_timedEffectList, function(e)
        if e.m_effectId == opcode then e.m_effectAmount = amount n = n + 1 end
    end)
    return n
end

-- The Record of portrait 1: opened, read and closed. Its screen polls no console either.
function P.record_open()
    if not CBMP_NEXT_LEVEL then
        CBMP_NEXT_LEVEL = getNextLevelString
        getNextLevelString = function()
            EEexRemote.Poll()
            return CBMP_NEXT_LEVEL()
        end
    end
    Infinity_OnPortraitLClick(1)
    e:GetActiveEngine():OnLeftPanelButtonClick(4)
    return true
end

function P.record_read()
    local out = {}
    for _, v in pairs(characters[currentID].statusEffects) do
        out[#out + 1] = { text = Infinity_FetchString(v.strRef), bam = v.bam, current = v.current }
    end
    e:SelectEngine(worldScreen)
    return out
end

-- Sets a single-class caster's first class level and rebuilds derived stats so ability min_level uses it.
function P.set_level(who, level)
    local s = type(who) == "number" and party(who) or named(who)
    s.m_baseStats.m_level1 = level
    P.bonus_rebuild(who)
    return EEex_Sprite_GetStat(s, 34)
end

-- Logs every Grease (SPWI101) opcode-158 pulse before saving throws roll, with the game tick.
CBMP.grease_log = {}
CBMGRLOG = function(op403, effect, sprite)
    pcall(function()
        local src = effect.m_sourceRes:get():upper()
        if src == "SPWI101" and effect.m_effectId == 158 then
            CBMP.grease_log[#CBMP.grease_log + 1] = {
                who = EEex_Sprite_GetName(sprite),
                tick = EngineGlobals.g_pBaldurChitin.m_pObjectGame.m_worldTime.m_gameTime,
            }
        end
    end)
    return false
end

function P.grease_watch(who, seconds)
    local s = type(who) == "number" and party(who) or named(who)
    EEex_GameObject_ApplyEffect(s, { effectID = 403, res = "CBMGRLOG", durationType = 0,
        duration = seconds or 200, sourceID = s.m_id, sourceTarget = s.m_id })
    return true
end

function P.take_grease_log()
    local out = CBMP.grease_log
    CBMP.grease_log = {}
    return out
end

-- Teaches wizard spells (opcode 147, no XP, ignore cap/school) so the Mage Book UI lists them.
function P.learn_wizard(who, spells)
    local s = party(who)
    for _, res in ipairs(spells) do
        EEex_GameObject_ApplyEffect(s, { effectID = 147, dwFlags = 5, res = res, durationType = 1,
            sourceID = s.m_id, sourceTarget = s.m_id })
    end
    return true
end

-- Teaches priest spells (opcode 171, skipping already-known ones) so the Priest Scroll UI lists Druid spells too.
function P.learn_priest(who, spells)
    local s = party(who)
    local known = {}
    for _, _, r in s:getKnownPriestSpellsIterator() do known[r:upper()] = true end
    for _, res in ipairs(spells) do
        if not known[res:upper()] then
            EEex_GameObject_ApplyEffect(s, { effectID = 171, res = res, durationType = 1,
                sourceID = s.m_id, sourceTarget = s.m_id })
            known[res:upper()] = true
        end
    end
    return true
end

-- Opens the Mage Book ("mage") or Priest Scroll ("priest") while keeping EEexRemote.Poll active.
function P.book_open(kind, who)
    P.book_console()
    if not CBMP_PRIEST_PAGE and type(priestPageInfo) == "function" then
        CBMP_PRIEST_PAGE = priestPageInfo
        priestPageInfo = function()
            EEexRemote.Poll()
            return CBMP_PRIEST_PAGE()
        end
    end
    Infinity_OnPortraitLClick(who)
    e:GetActiveEngine():OnLeftPanelButtonClick(kind == "priest" and 6 or 5)
    return true
end

function P.book_read(kind)
    local out = {}
    local char = characters and characters[id]
    local table_key = kind == "priest" and "priestSpells" or "mageSpells"
    local max_lvl = kind == "priest" and 7 or 9
    if char and char[table_key] then
        for lvl = 1, max_lvl do
            if kind == "priest" and type(setPriestBookLevel) == "function" then
                pcall(setPriestBookLevel, lvl)
            elseif kind ~= "priest" and type(setMageBookLevel) == "function" then
                pcall(setMageBookLevel, lvl)
            end
            local list = char[table_key][lvl]
            if list then
                for idx, entry in pairs(list) do
                    if type(entry) == "table" and entry.resref then
                        currentBookSpell = idx
                        local pane = ""
                        if kind == "priest" and type(priestBookDescription) == "function" then
                            pane = priestBookDescription() or ""
                        elseif kind ~= "priest" and type(mageBookDescription) == "function" then
                            pane = mageBookDescription() or ""
                        end
                        out[entry.resref:upper()] = {
                            level = lvl,
                            name = Infinity_FetchString(entry.name),
                            desc = Infinity_FetchString(entry.description),
                            pane = pane,
                        }
                    end
                end
            end
        end
    end
    e:SelectEngine(worldScreen)
    return out
end

-- Live resource headers and fetched TLK strings from the running engine.
function P.res_meta(spells, items, cres)
    local out = { spells = {}, items = {}, cres = {} }
    for _, res in ipairs(spells or {}) do
        local h = EEex_Resource_Demand(res, "SPL")
        if h then
            local ptr = EEex_UDToPtr(h)
            out.spells[res:upper()] = {
                name = Infinity_FetchString(EEex_Read32(ptr + 0x08)),
                desc = Infinity_FetchString(EEex_Read32(ptr + 0x50)),
                school = EEex_ReadU8(ptr + 0x25),
                excl = EEex_ReadU16(ptr + 0x1E),
                level = EEex_Read32(ptr + 0x34),
            }
        end
    end
    for _, res in ipairs(items or {}) do
        local h = EEex_Resource_Demand(res, "ITM")
        if h then
            local ptr = EEex_UDToPtr(h)
            local id_desc = EEex_Read32(ptr + 0x54)
            local gen_desc = EEex_Read32(ptr + 0x50)
            out.items[res:upper()] = {
                desc = Infinity_FetchString(id_desc >= 0 and id_desc or gen_desc),
                gen_desc = gen_desc >= 0 and Infinity_FetchString(gen_desc) or "",
                u3 = EEex_ReadU8(ptr + 0x2D),
                u4 = EEex_ReadU8(ptr + 0x2F),
            }
        end
    end
    for _, res in ipairs(cres or {}) do
        local h = EEex_Resource_Demand(res, "CRE")
        if h then
            local ptr = EEex_UDToPtr(h)
            out.cres[res:upper()] = {
                cur_hp = EEex_ReadU16(ptr + 0x24),
                max_hp = EEex_ReadU16(ptr + 0x26),
            }
        end
    end
    return out
end

return true
