from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_deck_builder_uses_data_actions_instead_of_inline_click_handlers():
    template = (PROJECT_ROOT / "templates" / "deck_builder.html").read_text()

    assert "onclick=" not in template
    assert "onchange=" not in template
    assert "oninput=" not in template
    assert 'data-deck-action="add"' in template
    assert 'data-deck-action="remove"' in template
    assert "data-quick-filter-kind" in template


def test_support_page_uses_scoped_css_module():
    template = (PROJECT_ROOT / "templates" / "support.html").read_text()
    css = (PROJECT_ROOT / "static" / "css" / "support.css").read_text()

    assert "css/support.css" in template
    assert "support-page" in template
    assert ".support-page" in css


def test_arena_keeps_socket_critical_ids_after_ux_polish():
    template = (PROJECT_ROOT / "templates" / "arena.html").read_text()
    required_ids = [
        "join-queue-btn",
        "ready-btn",
        "join-private-room-btn",
        "join-bot-match-btn",
        "private-room-code",
        "queue-status",
        "battle-log",
        "hand",
        "my-name",
        "enemy-name",
        "my-hp",
        "enemy-hp",
        "my-deck",
        "enemy-deck",
        "my-ready",
        "enemy-ready",
        "my-monster-slot",
        "enemy-monster-slot",
        "my-st-slot",
        "enemy-st-slot",
        "phase-label",
        "round-label",
    ]

    for element_id in required_ids:
        assert f'id="{element_id}"' in template


def test_arena_uses_single_screen_layout_module():
    template = (PROJECT_ROOT / "templates" / "arena.html").read_text()
    css = (PROJECT_ROOT / "static" / "css" / "arena_clean_v48.css").read_text()

    assert "arena-page-v154" in template
    assert "css/arena_clean_v48.css" in template
    assert "css/arena3d.css" in template
    assert "js/arena_renderer_adapter.js" in template
    assert "js/arena_clean_v48.js" in template
    assert "dist/arena3d/arena3d.js" in template
    assert "data-arena-renderer" in template
    assert ".az48-arena" in css
    assert ".az48-card-v2" in css


def test_pwa_install_assets_are_declared():
    manifest = (PROJECT_ROOT / "static" / "manifest.webmanifest").read_text()
    pwa_js = (PROJECT_ROOT / "static" / "js" / "pwa.js").read_text()
    service_worker = (PROJECT_ROOT / "static" / "js" / "service-worker.js").read_text()
    homepage = (PROJECT_ROOT / "templates" / "index.html").read_text()

    assert '"/static/icons/icon-192.png"' in manifest
    assert '"/static/icons/icon-512.png"' in manifest
    assert '"/static/icons/maskable-icon-512.png"' in manifest
    assert '"display": "standalone"' in manifest
    assert 'navigator.serviceWorker.register("/service-worker.js", { scope: "/" })' in pwa_js
    assert 'CACHE_NAME = "ambitionz-web-app-v181"' in service_worker
    assert '"/static/js/arena_clean_v48.js"' in service_worker
    assert '"/static/dist/arena3d/arena3d.js"' in service_worker
    assert '"/static/assets/arena3d/manifest.json"' in service_worker
    assert "apple-touch-icon.png" in homepage


def test_public_home_product_contract():
    homepage = (PROJECT_ROOT / "templates" / "index.html").read_text()
    css = (PROJECT_ROOT / "static" / "css" / "style.css").read_text()

    assert "https://ambitionzgame.com/" in homepage
    assert "Jogar Agora" in homepage
    assert "turn-based battles" in homepage
    assert "intent choices" in homepage
    assert "lane control" in homepage
    assert "url_for('training')" in homepage
    assert "url_for('arena')" in homepage
    assert "url_for('collection')" in homepage
    assert "url_for('deck_builder')" in homepage
    assert "url_for('leaderboard')" in homepage
    assert "url_for('login')" in homepage
    assert "url_for('register')" in homepage
    assert "az-home-page-v2" in homepage
    assert ".az-home-hero-v2" in css
    assert ".az-home-route-grid-v2" in css


def test_profile_progression_snapshot_contract():
    profile = (PROJECT_ROOT / "templates" / "profile.html").read_text()
    progression = (PROJECT_ROOT / "templates" / "progression.html").read_text()
    css = (PROJECT_ROOT / "static" / "css" / "style.css").read_text()
    app_py = (PROJECT_ROOT / "app.py").read_text()

    assert 'id="az-profile-summary"' in profile
    assert "profile_stats.mode_most_played" in profile
    assert "profile_stats.latest_result" in profile
    assert "profile_stats.xp_to_next" in profile
    assert 'id="az-progression-summary"' in progression
    assert "progression_stats.total_matches" in progression
    assert "progression_stats.first_training_completed" in progression
    assert '"mode_most_played"' in app_py
    assert '"latest_result"' in app_py
    assert ".az-retention-snapshot-v1" in css
    assert ".az-retention-stat-grid-v1" in css


def test_collection_and_deck_builder_v2_contract():
    collection = (PROJECT_ROOT / "templates" / "collection.html").read_text()
    deck_builder = (PROJECT_ROOT / "templates" / "deck_builder.html").read_text()
    deck_js = (PROJECT_ROOT / "static" / "js" / "deck_builder.js").read_text()
    css = (PROJECT_ROOT / "static" / "css" / "style.css").read_text()
    app_py = (PROJECT_ROOT / "app.py").read_text()

    assert 'id="az-collection-summary"' in collection
    assert "collection_stats.total_cards" in collection
    assert "collection_stats.monsters" in collection
    assert "az-empty-collection-v2" in collection
    assert 'id="az-deck-validation-summary"' in deck_builder
    assert "deck_status.rules_label" in deck_builder
    assert "az-deck-summary-duplicates" in deck_builder
    assert "Save Active Deck" in deck_builder
    assert "duplicates" in deck_js
    assert "az-deck-validity-pill" in deck_js
    assert ".az-collection-summary-v2" in css
    assert ".az-deck-validation-summary-v2" in css
    assert "ensure_user_has_playable_inventory(user)" in app_py


def test_collection_desire_loop_contract():
    collection = (PROJECT_ROOT / "templates" / "collection.html").read_text()
    css = (PROJECT_ROOT / "static" / "css" / "style.css").read_text()
    app_py = (PROJECT_ROOT / "app.py").read_text()

    assert 'id="az-collection-desire-loop"' in collection
    assert "collection_stats.completion_percent" in collection
    assert "collection_stats.element_counts" in collection
    assert "collection_stats.rarity_counts" in collection
    assert 'id="filter-ownership"' in collection
    assert 'id="filter-rarity"' in collection
    assert "data-ownership" in collection
    assert "az-card-lock-overlay-v1" in collection
    assert "include_zero=True" in app_py
    assert '"catalog_cards"' in app_py
    assert ".az-collection-desire-v1" in css
    assert ".az-collection-progress-fill-v1" in css


def test_blocks_25_32_product_polish_contract():
    homepage = (PROJECT_ROOT / "templates" / "index.html").read_text()
    collection = (PROJECT_ROOT / "templates" / "collection.html").read_text()
    deck_builder = (PROJECT_ROOT / "templates" / "deck_builder.html").read_text()
    profile = (PROJECT_ROOT / "templates" / "profile.html").read_text()
    arena = (PROJECT_ROOT / "templates" / "arena.html").read_text()
    cards_js = (PROJECT_ROOT / "static" / "js" / "ambitionz_cards.js").read_text()
    deck_js = (PROJECT_ROOT / "static" / "js" / "deck_builder.js").read_text()
    arena_js = (PROJECT_ROOT / "static" / "js" / "arena_clean_v48.js").read_text()
    css = (PROJECT_ROOT / "static" / "css" / "style.css").read_text()
    arena_css = (PROJECT_ROOT / "static" / "css" / "arena_clean_v48.css").read_text()

    assert "url_for('tutorial')" in homepage
    assert 'id="az-collection-no-results"' in collection
    assert "filterCollectionCards" in cards_js
    assert 'id="az-deck-card-preview"' in deck_builder
    assert "Auto Build Legal Deck" in deck_builder
    assert "updateDeckPreview" in deck_js
    assert 'id="az-profile-progress-preview"' in profile
    assert 'id="az48-result-progress"' in arena
    assert "renderResultProgress" in arena_js
    assert "dataset.az48PrimaryAction = primaryAction" in arena_js
    assert "Blocks 25-32" in css
    assert "Arena Premium UX Clarity" in arena_css


def test_blocks_33_40_beta_retention_loop_contract():
    app_py = (PROJECT_ROOT / "app.py").read_text()
    homepage = (PROJECT_ROOT / "templates" / "index.html").read_text()
    campaign = (PROJECT_ROOT / "templates" / "campaign.html").read_text()
    missions = (PROJECT_ROOT / "templates" / "missions.html").read_text()
    daily = (PROJECT_ROOT / "templates" / "daily.html").read_text()
    progression = (PROJECT_ROOT / "templates" / "progression.html").read_text()
    match_history = (PROJECT_ROOT / "templates" / "match_history.html").read_text()
    arena = (PROJECT_ROOT / "templates" / "arena.html").read_text()
    pwa_js = (PROJECT_ROOT / "static" / "js" / "pwa.js").read_text()
    arena_js = (PROJECT_ROOT / "static" / "js" / "arena_clean_v48.js").read_text()
    progression_js = (PROJECT_ROOT / "static" / "js" / "ambitionz_progression.js").read_text()
    css = (PROJECT_ROOT / "static" / "css" / "style.css").read_text()

    for event_name in [
        "home_cta_play",
        "tutorial_start",
        "training_start_click",
        "training_result_view",
        "collection_view",
        "deck_builder_view",
        "deck_save_attempt",
        "campaign_view",
        "mission_cta_click",
        "daily_view",
    ]:
        assert event_name in app_py

    assert 'id="az-beta-journey"' in homepage
    assert "build_beta_journey" in app_py
    assert "build_campaign_chapters" in app_py
    assert "First Signal" in app_py
    assert "Beta Campaign" in campaign
    assert "Reward Preview" in campaign
    assert "mission_guides" in missions
    assert "Beta Journey Missions" in missions
    assert "daily_checkin.state" in daily
    assert "az-daily-checkin-track-v1" in daily
    assert "collection_progress.completion_percent" in progression
    assert "deck_status.is_valid" in progression
    assert "No matches yet" in match_history
    assert "url_for('match_history')" in arena
    assert "pageEventMap" in pwa_js
    assert "data-retention-event" in pwa_js
    assert "training_result_view" in arena_js
    assert "/campaign" in progression_js
    assert ".az-beta-journey-v1" in css
    assert ".az-beta-guide-grid-v1" in css


def test_arena_has_compact_turn_hud_contract():
    js = (PROJECT_ROOT / "static" / "js" / "arena_clean_v48.js").read_text()
    css = (PROJECT_ROOT / "static" / "css" / "arena_clean_v48.css").read_text()

    assert "az48-next-action" in js
    assert "az48-card-preview-name" in js
    assert "az48-event-lines" in js
    assert "data-az48-primary-action" in css
    assert "az48-help-drawer" in css


def test_arena_command_v1_and_lane_target_selection_contract():
    template = (PROJECT_ROOT / "templates" / "arena.html").read_text()
    js = (PROJECT_ROOT / "static" / "js" / "arena_clean_v48.js").read_text()
    adapter = (PROJECT_ROOT / "static" / "js" / "arena_renderer_adapter.js").read_text()
    css = (PROJECT_ROOT / "static" / "css" / "arena_clean_v48.css").read_text()

    assert "arena_command_v1" in js
    assert "ARENA_COMMAND_SCHEMA" in js
    assert "data-az48-lane" in js
    assert "selectionMode === \"lane\"" in js
    assert "selectionMode === \"target\"" in js
    assert 'data-az48-target="enemy_hero"' in template
    assert 'data-az48-target="self"' in template
    assert ".az48-selecting-lane" in css
    assert ".az48-selecting-target" in css
    assert "keywordRegistry" in adapter


def test_arena_round_summary_text_panel_contract():
    template = (PROJECT_ROOT / "templates" / "arena.html").read_text()
    js = (PROJECT_ROOT / "static" / "js" / "arena_clean_v48.js").read_text()
    adapter = (PROJECT_ROOT / "static" / "js" / "arena_renderer_adapter.js").read_text()
    css = (PROJECT_ROOT / "static" / "css" / "arena_clean_v48.css").read_text()

    assert 'id="az48-round-summary"' in template
    assert "Round Summary" in template
    assert "A resolução da rodada aparecerá aqui." in template
    assert "function getRoundCombatLog" in js
    assert "function renderRoundSummary" in js
    assert "function renderCombatEvent" in js
    assert "function renderSummaryItem" in js
    assert "JSON.stringify" not in js[js.index("function renderRoundSummary"):js.index("function cardStateMap")]
    assert "combatLog" in adapter
    assert "shield_gain" in js
    assert "ambition_gain" in js
    assert "intent_selected" in js
    assert "match_finished" in js
    assert "function renderBattleHighlights" in js
    assert "battle_highlights" in js
    assert "az48-highlight-grid" in js

    for class_name in [
        ".az48-round-summary",
        ".az48-summary-title",
        ".az48-summary-list",
        ".az48-summary-item",
        ".az48-summary-item-attack",
        ".az48-summary-item-damage",
        ".az48-summary-item-death",
        ".az48-summary-item-keyword",
        ".az48-summary-item-end",
        ".az48-summary-item-shield",
        ".az48-summary-item-ambition",
        ".az48-highlight-card",
        ".az48-highlight-grid",
    ]:
        assert class_name in css


def test_blocks_49_56_battle_core_polish_contract():
    rulebook = (PROJECT_ROOT / "docs" / "BE2_RULEBOOK.md").read_text()
    engine = (PROJECT_ROOT / "services" / "battle_engine_v2.py").read_text()
    resolver = (PROJECT_ROOT / "services" / "card_effect_resolver.py").read_text()
    balance_sim = (PROJECT_ROOT / "tools" / "qa" / "battle_balance_sim.py").read_text()
    gauntlet = (PROJECT_ROOT / "tools" / "qa" / "qa_battle_gauntlet.py").read_text()

    assert "Battle Engine V2 Rulebook Snapshot" in rulebook
    assert "def stable_match_snapshot" in engine
    assert "random.shuffle" not in engine
    assert "resolve_card_effect" in resolver
    assert "--matches" in balance_sim
    assert "--seed" in balance_sim
    assert "--max-rounds" in balance_sim
    assert "PASS battle_gauntlet" in gauntlet


def test_arena_turn_guidance_and_server_error_contract():
    js = (PROJECT_ROOT / "static" / "js" / "arena_clean_v48.js").read_text()
    css = (PROJECT_ROOT / "static" / "css" / "arena_clean_v48.css").read_text()

    assert "function getArenaUiStep" in js
    assert "function uiCopyForStep" in js
    assert "function renderStepList" in js
    assert "function setServerError" in js
    assert "az48-step-list" in js
    assert "az48-server-error" in js
    assert "document.body.dataset.az48UiStep" in js
    assert ".az48-step-list" in css
    assert ".az48-step-active" in css
    assert ".az48-server-error" in css


def test_arena_card_detail_readability_contract():
    js = (PROJECT_ROOT / "static" / "js" / "arena_clean_v48.js").read_text()
    css = (PROJECT_ROOT / "static" / "css" / "arena_clean_v48.css").read_text()

    assert "az48-card-detail-stats" in js
    assert "az48-card-keyword-lines" in js
    assert "function keywordDescription" in js
    assert "Guarded: reduces incoming damage" in js
    assert "Focused: generates Ambition" in js
    assert "Shield: absorbs hero damage" in js
    assert "Strike: offensive intent" in js
    assert "Monster: enters a lane" in js
    assert "function educationTermsForCard" in js
    assert "friendlyDisabledReason" in js
    assert "setCardDetailFromElement" in js
    assert ".az48-card-stats" in css
    assert ".az48-card-detail-stats" in css
    assert ".az48-card-keyword-lines" in css


def test_arena_state_safety_and_result_panel_contract():
    template = (PROJECT_ROOT / "templates" / "arena.html").read_text()
    js = (PROJECT_ROOT / "static" / "js" / "arena_clean_v48.js").read_text()
    css = (PROJECT_ROOT / "static" / "css" / "arena_clean_v48.css").read_text()

    assert "pendingCommand" in js
    assert "COMMAND_TIMEOUT_MS" in js
    assert "isStalePayload" in js
    assert "requestState();" in js
    assert "az48-command-pending" in css
    assert 'id="az48-result-meta"' in template
    assert 'id="az48-result-missions"' in template
    assert 'data-result-action="missions"' in template
    assert "function resultReason" in js
    assert "function renderResultMissions" in js
    assert ".az48-result-meta" in css
    assert ".az48-result-missions" in css


def test_arena_premium_hud_contract():
    template = (PROJECT_ROOT / "templates" / "arena.html").read_text()
    js = (PROJECT_ROOT / "static" / "js" / "arena_clean_v48.js").read_text()
    adapter = (PROJECT_ROOT / "static" / "js" / "arena_renderer_adapter.js").read_text()
    css = (PROJECT_ROOT / "static" / "css" / "arena_clean_v48.css").read_text()

    for element_id in [
        "az48-me-hp",
        "az48-enemy-hp",
        "az48-me-ambition",
        "az48-round",
        "az48-me-intent",
        "az48-enemy-status",
    ]:
        assert f'id="{element_id}"' in template

    assert "function intentLabel" in js
    assert "function opponentStatusLabel" in js
    assert "document.body.dataset.az48PlayerIntent" in js
    assert "az48-me-ready" in js
    assert "az48-enemy-ready" in js
    assert "card.currentHp" in adapter
    assert "card.maxHp" in adapter

    for class_name in [
        ".az48-hud-pill",
        ".az48-hp-pill",
        ".az48-ambition-pill",
        ".az48-intent-pill",
        ".az48-opponent-status-pill",
        ".az48-round-badge",
    ]:
        assert class_name in css


def test_arena_light_combat_feedback_contract():
    js = (PROJECT_ROOT / "static" / "js" / "arena_clean_v48.js").read_text()
    css = (PROJECT_ROOT / "static" / "css" / "arena_clean_v48.css").read_text()

    assert "function combatFeedbackFromState" in js
    assert "function feedbackClassesForLane" in js
    assert "az48-lane-resolved" in js
    assert "az48-card-damaged" in js
    assert "az48-card-defeated" in js
    assert "az48-me-hero-hit" in js
    assert "az48-enemy-hero-hit" in js
    assert "list.scrollTop = list.scrollHeight" in js

    for class_name in [
        ".az48-lane-resolved",
        ".az48-card-damaged",
        ".az48-card-defeated",
        "az48HeroPulse",
        "prefers-reduced-motion",
    ]:
        assert class_name in css


def test_arena_browser_qa_regression_contract():
    browser_flow = (PROJECT_ROOT / "tools" / "qa" / "qa_browser_flow.py").read_text()
    full_match = (PROJECT_ROOT / "tools" / "qa" / "qa_browser_full_match_flow.py").read_text()
    real_round = (PROJECT_ROOT / "tools" / "qa" / "qa_browser_real_round_flow.py").read_text()
    runner = (PROJECT_ROOT / "tools" / "qa" / "run_local_browser_qa.py").read_text()

    for required in [
        "body_has_raw_json",
        "Console errors detected",
        "combat_feedback_visible",
        "finished_text_visible",
        "training_result_visible",
    ]:
        assert required in browser_flow

    assert "safe_round_limit_reached" in full_match
    assert "body_has_raw_json" in full_match
    assert "finished_text_visible" in full_match
    assert "training_result_visible" in full_match
    assert "ensure_browser_user()" in real_round
    assert "MOBILE REAL ROUND QA" in runner
    assert "browser_full_match" in runner
    assert "raise SystemExit(1)" in runner


def test_training_bot_polish_contract():
    template = (PROJECT_ROOT / "templates" / "arena.html").read_text()
    js = (PROJECT_ROOT / "static" / "js" / "arena_clean_v48.js").read_text()
    css = (PROJECT_ROOT / "static" / "css" / "arena_clean_v48.css").read_text()

    assert 'id="az48-training-panel"' in template
    assert "Training Mode" in template
    assert "Easy" in template
    assert "Normal" in template
    assert "Hard" in template
    assert 'id="az48-training-result"' in template
    assert 'id="az48-training-restart"' in template
    assert "Jogar novamente" in template
    assert "url_for('collection')" in template
    assert "url_for('deck_builder')" in template
    assert "post_match_summary" in js
    assert "function renderTrainingResult" in js
    assert "latestPostMatchSummary" in js
    assert "Bot thinking" in js
    assert ".az48-training-panel" in css
    assert ".az48-training-result" in css
    assert ".az48-result-actions" in css


def test_art_direction_system_contract():
    css = (PROJECT_ROOT / "static" / "css" / "style.css").read_text()
    arena_css = (PROJECT_ROOT / "static" / "css" / "arena_clean_v48.css").read_text()
    template = (PROJECT_ROOT / "templates" / "arena.html").read_text()

    for token in [
        "--az-bg",
        "--az-panel",
        "--az-panel-strong",
        "--az-gold",
        "--az-gold-soft",
        "--az-arcane",
        "--az-danger",
        "--az-success",
        "--az-text",
        "--az-muted",
        "--az-border",
        "--az-radius",
        "--az-shadow",
    ]:
        assert token in css
        assert token in arena_css

    assert "Ambitionz Art Direction System V1" in css
    assert "az-art-direction-v1" in css
    assert "az-rarity-badge" in css
    assert "az-element-badge" in css
    assert "var(--az48-board-fog)" in arena_css
    assert "arena_clean_v48.css') }}?v=81" in template


def test_card_frame_premium_contract():
    collection = (PROJECT_ROOT / "templates" / "collection.html").read_text()
    deck_builder = (PROJECT_ROOT / "templates" / "deck_builder.html").read_text()
    js = (PROJECT_ROOT / "static" / "js" / "arena_clean_v48.js").read_text()
    css = (PROJECT_ROOT / "static" / "css" / "style.css").read_text()
    arena_css = (PROJECT_ROOT / "static" / "css" / "arena_clean_v48.css").read_text()
    arena_template = (PROJECT_ROOT / "templates" / "arena.html").read_text()

    assert "az-premium-card-frame-v1" in collection
    assert "az-premium-card-frame-v1" in deck_builder
    assert "az-premium-card-shell-v1" in deck_builder
    assert "az-premium-stat-attack-v1" in collection
    assert "az-premium-stat-health-v1" in deck_builder
    assert "data-card-id" in deck_builder
    assert "data-az48-lane" in js
    assert "az48-card-frame-premium-v1" in js
    assert "az48-card-stat-pair" in js
    assert "az48-keyword-chip" in js
    assert "data-rarity" in js
    assert ".az-premium-card-frame-v1" in css
    assert ".az-premium-card-shell-v1" in css
    assert ".az48-card-frame-premium-v1" in arena_css
    assert ".az48-card-element-mark" in arena_css
    assert "arena_clean_v48.js') }}?v=81" in arena_template


def test_faction_identity_layer_contract():
    homepage = (PROJECT_ROOT / "templates" / "index.html").read_text()
    collection = (PROJECT_ROOT / "templates" / "collection.html").read_text()
    profile = (PROJECT_ROOT / "templates" / "profile.html").read_text()
    arena_js = (PROJECT_ROOT / "static" / "js" / "arena_clean_v48.js").read_text()
    css = (PROJECT_ROOT / "static" / "css" / "style.css").read_text()

    for faction in [
        "Ember Court",
        "Tideborn Order",
        "Stonebound Clan",
        "Verdant Pact",
        "Arcane Neutral",
    ]:
        assert faction in homepage

    assert 'id="az-faction-identity"' in homepage
    assert 'id="az-collection-factions"' in collection
    assert 'id="filter-faction"' in collection
    assert "data-faction" in collection
    assert 'id="az-profile-faction-identity"' in profile
    assert "function factionForElement" in arena_js
    assert '["Faction", c.faction || factionForElement(c.element)]' in arena_js
    assert ".az-faction-showcase-v1" in css
    assert ".az-faction-card-v1" in css
    assert ".az-faction-badge-v1" in css
    assert ".az-profile-faction-identity-v1" in css


def test_battle_presentation_v1_contract():
    js = (PROJECT_ROOT / "static" / "js" / "arena_clean_v48.js").read_text()
    css = (PROJECT_ROOT / "static" / "css" / "arena_clean_v48.css").read_text()

    assert "restartBodyPulse" in js
    assert "az48-card-played-feedback" in js
    assert "az48-ambition-gained" in js
    assert "meGainedAmbition" in js
    assert ".az48-enemy-field::before" in css
    assert ".az48-me-field::before" in css
    assert "az48CardPlayedV1" in css
    assert "az48AmbitionPulseV1" in css
    assert "body.az48-card-played-feedback .az48-me-field .az48-field-card" in css
    assert "body.az48-ambition-gained .az48-ambition-pill" in css


def test_sound_haptics_layer_contract():
    template = (PROJECT_ROOT / "templates" / "arena.html").read_text()
    js = (PROJECT_ROOT / "static" / "js" / "arena_clean_v48.js").read_text()
    sound = (PROJECT_ROOT / "static" / "js" / "arena_sound.js").read_text()

    assert "arena_sound.js') }}?v=2" in template
    assert "function haptic" in sound
    assert "navigator.vibrate" in sound
    assert "if (!Sound.unlocked) return;" in sound
    assert "death()" in sound
    assert "playCombatLogFeedback" in js
    assert "lastCombatAudioSignature" in js
    assert "cardSelect" in js
    assert "victory" in js
    assert "defeat" in js


def test_narrative_onboarding_contract():
    template = (PROJECT_ROOT / "templates" / "tutorial.html").read_text()
    css = (PROJECT_ROOT / "static" / "css" / "ambitionz_tutorial.css").read_text()
    app_py = (PROJECT_ROOT / "app.py").read_text()

    assert 'id="az-tutorial-narrative"' in template
    assert "Start Training" in template
    assert "View Collection" in template
    assert "View Deck" in template
    assert "Strike" in template
    assert "Guard" in template
    assert "Focus" in template
    assert "Round Summary" in template
    assert "az-tutorial-step-grid-v1" in template
    assert "Ready and Resolve" in app_py
    assert "Command Lanes" in app_py
    assert "One card per round" in app_py
    assert ".az-tutorial-narrative-v1" in css
    assert ".az-tutorial-step-card-v1" in css
