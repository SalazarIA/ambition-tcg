# Ambitionz Arena Breakage Scan

Generated: 2026-05-06T18:02:11.871670



## Files Present


- app.py: OK
- templates/arena.html: OK
- static/js/game.js: OK
- static/js/arena_app.js: OK
- static/js/arena_sound.js: OK
- static/css/arena_app.css: OK
- services/match_state_v1.py: OK
- services/match_actions_v1.py: OK
- services/arena_payload.py: OK
- sockets/game_socket.py: OK


## Socket Events - Backend Listeners


```text
app.py: claim_match_rewards_v1
app.py: declare_ready
app.py: play_card
app.py: request_match_state
app.py: set_intent
app.py: start_training
sockets/game_socket.py: cancel_queue
sockets/game_socket.py: choose_intent
sockets/game_socket.py: connect
sockets/game_socket.py: declare_ready
sockets/game_socket.py: disconnect
sockets/game_socket.py: join_bot_match
sockets/game_socket.py: join_private_room
sockets/game_socket.py: join_queue
sockets/game_socket.py: join_training
sockets/game_socket.py: play_to_field
sockets/game_socket.py: set_intent
sockets/game_socket.py: toggle_unleash
```



## Socket Events - Frontend Emits


```text
static/js/arena_app.js: claim_match_rewards_v1
static/js/arena_app.js: declare_ready
static/js/arena_app.js: play_card
static/js/arena_app.js: request_match_state
static/js/arena_app.js: set_intent
static/js/arena_app.js: start_training
static/js/game.js: cancel_queue
static/js/game.js: declare_ready
static/js/game.js: join_bot_match
static/js/game.js: join_private_room
static/js/game.js: join_queue
static/js/game.js: join_training
static/js/game.js: play_to_field
static/js/game.js: set_intent
static/js/game.js: toggle_unleash
```



## Frontend Emits Without Backend Listener


```text
OK
```



## Backend Listeners Not Emitted By Frontend


```text
choose_intent
connect
disconnect
```



## Frontend Socket On Handlers


```text
static/js/arena_app.js: action_error
static/js/arena_app.js: match_state
static/js/arena_app.js: reward_result
static/js/game.js: battle_events
static/js/game.js: battle_log
static/js/game.js: connect
static/js/game.js: disconnect
static/js/game.js: game_over
static/js/game.js: game_state_update
static/js/game.js: match_found
static/js/game.js: matchmaking_status
static/js/game.js: opponent_left
static/js/game.js: post_match_summary
static/js/game.js: presence_update
static/js/game.js: queue_status
```



## Arena HTML Body / Script / CSS


```text
templates/arena.html:14:                         <link rel="stylesheet" href="{{ url_for('static', filename='css/arena_app.css') }}?v=45">
templates/arena.html:17: <body class="az-arena-v45 az-arena-v40 az-arena-v4-body" data-page-kind="{% if training_mode %}training{% else %}arena{% endif %}">
templates/arena.html:34:                     <strong id="enemy-name">Opponent</strong>
templates/arena.html:38:                     <span>HP <strong id="enemy-hp">3600</strong></span>
templates/arena.html:39:                     <span>EN <strong id="enemy-energy">0/0</strong></span>
templates/arena.html:40:                     <span>AMB <strong id="enemy-ambition">0</strong></span>
templates/arena.html:41:                     <span>Intent <strong id="enemy-intent">Hidden</strong></span>
templates/arena.html:46:                 <span id="phase-label">Set Phase</span>
templates/arena.html:47:                 <strong id="round-number">Round 1</strong>
templates/arena.html:48:                 <small id="turn-status">Choose intent</small>
templates/arena.html:54:                     <strong id="my-name">{{ user.username if user else "Player" }}</strong>
templates/arena.html:58:                     <span>HP <strong id="my-hp">3600</strong></span>
templates/arena.html:59:                     <span>EN <strong id="my-energy">0/0</strong></span>
templates/arena.html:60:                     <span>AMB <strong id="my-ambition">0</strong></span>
templates/arena.html:61:                     <span>Intent <strong id="my-intent">Strike</strong></span>
templates/arena.html:69:                 <h2 id="next-move-title">{% if training_mode %}Start the training duel{% else %}Find an opponent{% endif %}</h2>
templates/arena.html:70:                 <p id="next-move-copy">
templates/arena.html:80:                 <span>Deck <strong id="my-deck">30</strong></span>
templates/arena.html:81:                 <span>GY <strong id="my-graveyard">0</strong></span>
templates/arena.html:82:                 <span>Ready <strong id="my-ready">No</strong></span>
templates/arena.html:90:                     <span id="enemy-ready">Ready No</span>
templates/arena.html:96:                         <div id="enemy-monster-zone" class="az-v4-zone-slot">Hidden</div>
templates/arena.html:101:                         <div id="enemy-spell-zone" class="az-v4-zone-slot">Set Zone</div>
templates/arena.html:106:                     <span>Deck <strong id="enemy-deck">30</strong></span>
templates/arena.html:107:                     <span>Hand <strong id="enemy-hand">0</strong></span>
templates/arena.html:112:                 <span id="battle-state-label">Waiting</span>
templates/arena.html:118:                     <span id="field-hint">Choose intent</span>
templates/arena.html:124:                         <div id="my-monster-zone" class="az-v4-zone-slot">Empty Monster Zone</div>
templates/arena.html:129:                         <div id="my-spell-zone" class="az-v4-zone-slot">Empty Spell/Trap Zone</div>
templates/arena.html:141:             <div id="my-hand" class="az-v4-hand">
templates/arena.html:153:                 <select id="bot-difficulty" class="az-v4-select" {% if not training_mode %}hidden{% endif %}>
templates/arena.html:161:                 <button id="intent-strike-btn" type="button" class="az-v4-action-btn" data-intent="Strike">
templates/arena.html:166:                 <button id="intent-guard-btn" type="button" class="az-v4-action-btn" data-intent="Guard">
templates/arena.html:171:                 <button id="intent-focus-btn" type="button" class="az-v4-action-btn" data-intent="Focus">
templates/arena.html:176:                 <button id="unleash-btn" type="button" class="az-v4-action-btn az-v4-risk-btn">
templates/arena.html:182:             <button id="ready-btn" type="button" class="az-v4-ready-btn">
templates/arena.html:186:             <div id="connection-status" class="az-v4-connection">Connecting...</div>
templates/arena.html:191:             <div id="battle-log" class="az-v4-battle-log">
templates/arena.html:206:             <button type="button" class="az-v4-dock-btn" data-v4-click="Strike">
templates/arena.html:211:             <button type="button" class="az-v4-dock-btn" data-v4-click="Guard">
templates/arena.html:216:             <button type="button" class="az-v4-dock-btn" data-v4-click="Focus">
templates/arena.html:221:             <button type="button" class="az-v4-dock-btn az-v4-dock-ready" data-v4-click="Ready">
templates/arena.html:231:     <script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
templates/arena.html:232:     <script src="{{ url_for('static', filename='js/game.js') }}"></script>
templates/arena.html:234:     <script src="{{ url_for('static', filename='js/arena_app.js') }}?v=1"></script>
```



## Arena Renderer Definitions


```text
static/js/arena_app.js:3:    Renders canonical `match_state` without DOM-reading overlays.
static/js/arena_app.js:25:     const $ = (selector) => document.querySelector(selector);
static/js/arena_app.js:111:     function renderCard(card, options = {}) {
static/js/arena_app.js:160:     function renderField(selector, field, enemy = false) {
static/js/arena_app.js:173:     function renderHand(match) {
static/js/arena_app.js:212:         let layer = document.querySelector("#az-event-layer");
static/js/arena_app.js:230:         let layer = document.querySelector("#az-event-layer");
static/js/arena_app.js:246:         const el = document.querySelector(selector);
static/js/arena_app.js:266:         let modal = document.querySelector("#az-reward-modal");
static/js/arena_app.js:296:             const rematch = document.querySelector("#az-reward-rematch");
static/js/arena_app.js:303:                     emit("start_training", {});
static/js/arena_app.js:304:                     setTimeout(() => emit("request_match_state", {}), 250);
static/js/arena_app.js:309:         const title = document.querySelector("#az-reward-title");
static/js/arena_app.js:310:         const copy = document.querySelector("#az-reward-copy");
static/js/arena_app.js:311:         const xp = document.querySelector("#az-reward-xp");
static/js/arena_app.js:312:         const coins = document.querySelector("#az-reward-coins");
static/js/arena_app.js:313:         const round = document.querySelector("#az-reward-round");
static/js/arena_app.js:314:         const boosterProgress = document.querySelector("#az-reward-booster-progress");
static/js/arena_app.js:315:         const boosterFill = document.querySelector("#az-reward-booster-fill");
static/js/arena_app.js:343:         let overlay = document.querySelector("#az-match-end-overlay");
static/js/arena_app.js:363:             const close = document.querySelector("#az-end-continue");
static/js/arena_app.js:364:             const rematch = document.querySelector("#az-end-rematch");
static/js/arena_app.js:373:                     emit("start_training", {});
static/js/arena_app.js:374:                     setTimeout(() => emit("request_match_state", {}), 250);
static/js/arena_app.js:379:         const title = document.querySelector("#az-end-title");
static/js/arena_app.js:380:         const copy = document.querySelector("#az-end-copy");
static/js/arena_app.js:426:         const app = document.querySelector(".az-arena-app");
static/js/arena_app.js:457:         const layer = document.querySelector("#az-event-layer");
static/js/arena_app.js:484:         return document.querySelector('#az-hand .az-arena-card[data-card-id="' + CSS.escape(String(cardId)) + '"]');
static/js/arena_app.js:491:             return document.querySelector("#az-me-field .az-arena-slot:nth-child(2), #az-me-field .az-arena-card:nth-child(2)");
static/js/arena_app.js:495:             return document.querySelector("#az-me-field .az-arena-slot:nth-child(3), #az-me-field .az-arena-card:nth-child(3)");
static/js/arena_app.js:498:         return document.querySelector("#az-me-field .az-arena-slot:nth-child(1), #az-me-field .az-arena-card:nth-child(1)");
static/js/arena_app.js:504:         const layer = document.querySelector("#az-event-layer");
static/js/arena_app.js:567:         const btn = document.querySelector('.az-arena-actions button[data-action="' + action + '"]');
static/js/arena_app.js:591:             if (event.type === "play_card") {
static/js/arena_app.js:596:             if (event.type === "bot_play_card") {
static/js/arena_app.js:603:             if (event.type === "set_intent") {
static/js/arena_app.js:610:             if (event.type === "declare_ready") {
static/js/arena_app.js:656:     function render(match) {
static/js/arena_app.js:667:         const azPhaseEl = document.querySelector("#az-phase");
static/js/arena_app.js:699:         document.querySelectorAll(".az-arena-actions button").forEach((btn) => {
static/js/arena_app.js:733:                     emit("set_intent", { intent: action });
static/js/arena_app.js:741:                     emit("declare_ready", {});
static/js/arena_app.js:760:                 emit("play_card", { card_id: cardId });
static/js/arena_app.js:775:             socket.on("match_state", (payload) => {
static/js/arena_app.js:776:                 console.debug("[ArenaApp] match_state", payload);
static/js/arena_app.js:794:                 socket.emit("start_training", {});
static/js/arena_app.js:797:             socket.emit("request_match_state", {});
static/js/arena_app.js:814:         const app = document.querySelector(".az-arena-app");
static/js/arena_app.js:847:         requestState: () => emit("request_match_state", {}),
static/js/arena_app.js:866:             el.querySelector("[data-cost]")?.textContent ||
static/js/arena_app.js:891:         let badge = el.querySelector("." + className);
static/js/arena_app.js:911:         document.querySelectorAll(selectors.join(",")).forEach((el) => {
static/js/arena_app.js:947:    match_state_v1 payloads into the frontend renderer.
static/js/arena_app.js:1047:             canPlayCards: Boolean(legal.can_play_cards ?? hand.length),
static/js/arena_app.js:1054:         let root = document.getElementById("az-arena-v45-root");
static/js/arena_app.js:1129:     function renderCardV45(card, options = {}) {
static/js/arena_app.js:1151:     function renderFieldV45(selector, field, enemy) {
static/js/arena_app.js:1152:         const el = document.querySelector(selector);
static/js/arena_app.js:1164:     function renderArenaV45(payload) {
static/js/arena_app.js:1170:             const el = document.getElementById(id);
static/js/arena_app.js:1190:         const hand = document.getElementById("az-v45-hand");
static/js/arena_app.js:1232:             emitV45("play_card", { card_id: card.dataset.cardId });
static/js/arena_app.js:1233:             emitV45("play_card_v1", { card_id: card.dataset.cardId });
static/js/arena_app.js:1243:             emitV45("start_training", {});
static/js/arena_app.js:1244:             emitV45("start_training_v1", {});
static/js/arena_app.js:1246:             emitV45("declare_ready", {});
static/js/arena_app.js:1247:             emitV45("declare_ready_v1", {});
static/js/arena_app.js:1250:             emitV45("set_intent", { intent });
static/js/arena_app.js:1251:             emitV45("set_intent_v1", { intent });
static/js/arena_app.js:1256:         renderArenaV45(event.detail || {});
static/js/arena_app.js:1259:     document.addEventListener("game_state_update", function (event) {
static/js/arena_app.js:1260:         renderArenaV45(event.detail || {});
static/js/arena_app.js:1263:     window.AmbitionzArenaV45 = {
static/js/arena_app.js:1266:         render: renderArenaV45,
static/js/arena_app.js:1274:             renderArenaV45(window.latestState);
static/js/arena_app.js:1281:    Bridges legacy game.js payloads and match_state_v1 payloads
static/js/arena_app.js:1282:    into AmbitionzArenaV45.render().
static/js/arena_app.js:1368:                     can_play_cards: true,
static/js/arena_app.js:1388:                     can_play_cards: true,
static/js/arena_app.js:1396:     function renderBridgePayload(payload, source) {
static/js/arena_app.js:1397:         if (!window.AmbitionzArenaV45 || typeof window.AmbitionzArenaV45.render !== "function") {
static/js/arena_app.js:1412:         window.AmbitionzArenaV45.render(normalized);
static/js/arena_app.js:1424:                         "game_state_update",
static/js/arena_app.js:1425:                         "match_state",
static/js/arena_app.js:1426:                         "match_state_v1",
static/js/arena_app.js:1430:                         "start_training_result"
static/js/arena_app.js:1445:             "game_state_update",
static/js/arena_app.js:1446:             "match_state",
static/js/arena_app.js:1447:             "match_state_v1",
static/js/arena_app.js:1451:             "start_training_result"
static/js/arena_app.js:1491:             "game_state_update",
static/js/arena_app.js:1492:             "match_state",
static/js/arena_app.js:1493:             "match_state_v1",
static/js/arena_app.js:1497:             "start_training_result",
static/js/arena_app.js:1510:         window.AmbitionzArenaV46 = {
```



## Legacy game.js Renderer Definitions


```text
static/js/game.js:7:     const el = DOM.byId(id);
static/js/game.js:53:     const status = DOM.byId("queue-status");
static/js/game.js:126:         if (effect === "Draw" && (me.hand || []).length <= 3) {
static/js/game.js:141:     const cards = state?.me?.hand || [];
static/js/game.js:175:     const readyButton = DOM.byId("ready-btn");
static/js/game.js:214:         DOM.setText("arena-action-hint", "Start a duel to draw your hand.");
static/js/game.js:256:     const modal = document.getElementById("post-match-modal");
static/js/game.js:284:     const modal = document.getElementById("post-match-modal");
static/js/game.js:295:     const playAgain = document.getElementById("post-match-play-again");
static/js/game.js:317:     byId: (id) => document.getElementById(id),
static/js/game.js:319:         const el = document.getElementById(id);
static/js/game.js:323:         const el = document.getElementById(id);
static/js/game.js:327:         const el = document.getElementById(id);
static/js/game.js:334:     onClick: (id, handler) => {
static/js/game.js:335:         const el = document.getElementById(id);
static/js/game.js:336:         if (el) el.addEventListener("click", handler);
static/js/game.js:345: function renderCard(card, options = {}) {
static/js/game.js:385:     DOM.setText("enemy-hand", enemy.hand_count ?? 0);
static/js/game.js:389: function renderField(state) {
static/js/game.js:405: function renderHand(state) {
static/js/game.js:406:     const hand = DOM.byId("hand");
static/js/game.js:408:     if (!hand) return;
static/js/game.js:410:     hand.innerHTML = "";
static/js/game.js:412:     const cards = state.me?.hand || [];
static/js/game.js:416:         hand.innerHTML = `<div class="empty-slot-v103">No cards in hand</div>`;
static/js/game.js:427:             "arena-hand-card",
static/js/game.js:450:             socket.emit("play_to_field", { index });
static/js/game.js:453:         hand.appendChild(wrapper);
static/js/game.js:457: function renderState(state) {
static/js/game.js:477:     const button = DOM.byId(id);
static/js/game.js:508:     const countdown = DOM.byId("matchmaking-countdown");
static/js/game.js:517:     const countdown = DOM.byId("matchmaking-countdown");
static/js/game.js:542:     const cancelButton = DOM.byId("cancel-queue-btn");
static/js/game.js:580:         socket.emit("toggle_unleash");
static/js/game.js:586:         socket.emit("set_intent", { intent: selectedIntent });
static/js/game.js:600:         const difficultySelect = DOM.byId("bot-difficulty");
static/js/game.js:607:             socket.emit("join_training", { difficulty });
static/js/game.js:611:             socket.emit("join_queue");
static/js/game.js:616:         socket.emit("declare_ready");
static/js/game.js:623:         const input = DOM.byId("private-room-code");
static/js/game.js:633:         socket.emit("join_private_room", { code });
static/js/game.js:639:         socket.emit("join_bot_match");
static/js/game.js:644:         socket.emit("cancel_queue");
static/js/game.js:654:     socket.emit("toggle_unleash");
static/js/game.js:658: socket.on("connect", () => {
static/js/game.js:663: socket.on("disconnect", () => {
static/js/game.js:672: socket.on("queue_status", (data) => {
static/js/game.js:676: socket.on("match_found", (data) => {
static/js/game.js:686: socket.on("matchmaking_status", (data) => {
static/js/game.js:703:         const countdown = DOM.byId("matchmaking-countdown");
static/js/game.js:731: socket.on("presence_update", (data) => {
static/js/game.js:735: socket.on("game_state_update", (state) => {
static/js/game.js:739: socket.on("battle_events", (events) => {
static/js/game.js:743: socket.on("battle_log", (data) => {
static/js/game.js:747: socket.on("game_over", (data) => {
static/js/game.js:756: socket.on("post_match_summary", (data) => {
static/js/game.js:762: socket.on("opponent_left", (data) => {
```



## Backend V1 Match Actions


```text
services/match_actions_v1.py:4: # Does not remove legacy handlers yet.
services/match_actions_v1.py:10: from game.deck import build_playable_deck, draw_starting_hand
services/match_actions_v1.py:19: def _card_id(card):
services/match_actions_v1.py:32: def _card_type(card):
services/match_actions_v1.py:36: def _card_cost(card):
services/match_actions_v1.py:43: def _card_power(card):
services/match_actions_v1.py:55: def ensure_field(player):
services/match_actions_v1.py:59:     field = player.get("field")
services/match_actions_v1.py:61:     if not isinstance(field, dict):
services/match_actions_v1.py:62:         field = {}
services/match_actions_v1.py:64:     field.setdefault("monster", None)
services/match_actions_v1.py:65:     field.setdefault("spell", None)
services/match_actions_v1.py:66:     field.setdefault("trap", None)
services/match_actions_v1.py:67:     field.setdefault("cards", [])
services/match_actions_v1.py:69:     player["field"] = field
services/match_actions_v1.py:71:     return field
services/match_actions_v1.py:74: def ensure_match_shape(match):
services/match_actions_v1.py:75:     match.setdefault("round", 1)
services/match_actions_v1.py:76:     match.setdefault("phase", "intent")
services/match_actions_v1.py:77:     match.setdefault("training", True)
services/match_actions_v1.py:78:     match.setdefault("is_bot_match", True)
services/match_actions_v1.py:86:         player.setdefault("hand", [])
services/match_actions_v1.py:87:         player.setdefault("deck", [])
services/match_actions_v1.py:88:         player.setdefault("graveyard", [])
services/match_actions_v1.py:89:         player.setdefault("energy", 2)
services/match_actions_v1.py:90:         player.setdefault("max_energy", player.get("energy", 2))
services/match_actions_v1.py:91:         player.setdefault("ambition", 0)
services/match_actions_v1.py:92:         player.setdefault("intent", None)
services/match_actions_v1.py:93:         player.setdefault("ready", False)
services/match_actions_v1.py:94:         ensure_field(player)
services/match_actions_v1.py:99: def card_catalog_by_id():
services/match_actions_v1.py:114: def hydrate_deck_card(card_id):
services/match_actions_v1.py:127: def build_default_training_deck():
services/match_actions_v1.py:131: def create_training_match_v1(user, sid, room_code):
services/match_actions_v1.py:132:     deck = build_default_training_deck()
services/match_actions_v1.py:133:     bot_deck = build_default_training_deck()
services/match_actions_v1.py:135:     hand = deck[:5]
services/match_actions_v1.py:136:     bot_hand = bot_deck[:5]
services/match_actions_v1.py:154:         "hand": hand,
services/match_actions_v1.py:157:         "field": {
services/match_actions_v1.py:175:         "hand": bot_hand,
services/match_actions_v1.py:178:         "field": {
services/match_actions_v1.py:196:         "events": [],
services/match_actions_v1.py:200: def find_card_in_hand(player, card_id):
services/match_actions_v1.py:201:     hand = player.get("hand") or []
services/match_actions_v1.py:203:     for index, card in enumerate(hand):
services/match_actions_v1.py:210: def zone_for_card(card):
services/match_actions_v1.py:222: def can_play_card(player, card):
services/match_actions_v1.py:224:         return False, "Card not found in hand."
services/match_actions_v1.py:236:     field = ensure_field(player)
services/match_actions_v1.py:238:     if field.get(zone):
services/match_actions_v1.py:244: def play_card(match, player_key, card_id):
services/match_actions_v1.py:252:     index, card = find_card_in_hand(player, card_id)
services/match_actions_v1.py:255:         return False, "Card not found in hand."
services/match_actions_v1.py:262:     hand = player.get("hand") or []
services/match_actions_v1.py:263:     hand.pop(index)
services/match_actions_v1.py:269:     field = ensure_field(player)
services/match_actions_v1.py:270:     field[zone] = card
services/match_actions_v1.py:271:     field.setdefault("cards", [])
services/match_actions_v1.py:283:     match.setdefault("events", []).append(event)
services/match_actions_v1.py:289: def set_intent(match, player_key, intent):
services/match_actions_v1.py:306:     match.setdefault("events", []).append({
services/match_actions_v1.py:315: def bot_prepare(match):
services/match_actions_v1.py:325:     for card in list(bot.get("hand") or []):
services/match_actions_v1.py:329:             index, found = find_card_in_hand(bot, _card_id(card))
services/match_actions_v1.py:332:                 bot["hand"].pop(index)
services/match_actions_v1.py:334:                 ensure_field(bot)[zone_for_card(found)] = found
services/match_actions_v1.py:335:                 match.setdefault("events", []).append({
services/match_actions_v1.py:346: def simple_damage_from_player(player):
services/match_actions_v1.py:347:     field = ensure_field(player)
services/match_actions_v1.py:348:     monster = field.get("monster")
services/match_actions_v1.py:356: def resolve_round_if_ready(match):
services/match_actions_v1.py:395:     match.setdefault("events", []).append({
services/match_actions_v1.py:414:             player.setdefault("hand", []).append(deck.pop(0))
services/match_actions_v1.py:432: def declare_ready(match, player_key):
services/match_actions_v1.py:444:     match.setdefault("events", []).append({
```



## Payload Contract


```text
services/match_state_v1.py:155:     hand = normalize_cards(player.get("hand") or [])
services/match_state_v1.py:167: def normalize_player(player, viewer=False):
services/match_state_v1.py:169:     hand_raw = player.get("hand") or []
services/match_state_v1.py:196:         "hand": hand,
services/match_state_v1.py:226:         "hand": me.get("hand") or [],
services/match_state_v1.py:234:         "playable_card_ids": playable,
services/match_state_v1.py:239:     if not me.get("hand"):
services/match_state_v1.py:259: def build_match_state_v1(match, viewer_key="p1", message=None):
services/match_state_v1.py:284:         "me": me,
services/match_state_v1.py:285:         "enemy": enemy,
services/match_state_v1.py:286:         "legal_actions": legal_actions,
services/match_state_v1.py:294: def build_match_state_payloads(match, message=None):
```



## CSS Arena Locks


```text
static/css/arena_app.css:502: body.az-arena-app-enabled .az-arena-player-head {
static/css/arena_app.css:506: body.az-arena-app-enabled .az-arena-player-head strong {
static/css/arena_app.css:510: body.az-arena-app-enabled .az-arena-stat {
static/css/arena_app.css:516: body.az-arena-app-enabled .az-arena-round {
static/css/arena_app.css:520: body.az-arena-app-enabled .az-arena-round strong {
static/css/arena_app.css:524: body.az-arena-app-enabled .az-arena-board {
static/css/arena_app.css:529:     overflow: hidden;
static/css/arena_app.css:533: body.az-arena-app-enabled .az-arena-field {
static/css/arena_app.css:540: body.az-arena-app-enabled .az-arena-slot {
static/css/arena_app.css:550: body.az-arena-app-enabled .az-arena-divider {
static/css/arena_app.css:559: body.az-arena-app-enabled .az-arena-hand {
static/css/arena_app.css:563:     overflow: hidden;
static/css/arena_app.css:566: body.az-arena-app-enabled .az-arena-hand-head {
static/css/arena_app.css:570: body.az-arena-app-enabled .az-arena-hand-head h2 {
static/css/arena_app.css:574: body.az-arena-app-enabled .az-arena-hand-head span {
static/css/arena_app.css:579: body.az-arena-app-enabled .az-arena-hand-row {
static/css/arena_app.css:582:     overflow-x: auto;
static/css/arena_app.css:583:     overflow-y: hidden;
static/css/arena_app.css:588: body.az-arena-app-enabled .az-arena-hand-row::-webkit-scrollbar {
static/css/arena_app.css:592: body.az-arena-app-enabled .az-arena-hand-row::-webkit-scrollbar-thumb {
static/css/arena_app.css:597: body.az-arena-app-enabled .az-arena-hand-row .az-arena-card {
static/css/arena_app.css:604: body.az-arena-app-enabled .az-arena-card {
static/css/arena_app.css:609:     overflow: hidden;
static/css/arena_app.css:622: body.az-arena-app-enabled .az-arena-card:hover:not(:disabled) {
static/css/arena_app.css:626: body.az-arena-app-enabled .az-card-frame-glow {
static/css/arena_app.css:629:     z-index: 1;
static/css/arena_app.css:635: body.az-arena-app-enabled .az-arena-card-cost {
static/css/arena_app.css:641:     z-index: 5;
static/css/arena_app.css:644: body.az-arena-app-enabled .az-arena-card-art {
static/css/arena_app.css:656:     z-index: 2;
static/css/arena_app.css:659: body.az-arena-app-enabled .az-arena-card::before {
static/css/arena_app.css:660:     display: none;
static/css/arena_app.css:663: body.az-arena-app-enabled .az-arena-card-body {
static/css/arena_app.css:668:     z-index: 4;
static/css/arena_app.css:671: body.az-arena-app-enabled .az-arena-card strong {
static/css/arena_app.css:677: body.az-arena-app-enabled .az-arena-card span {
static/css/arena_app.css:681:     overflow: hidden;
static/css/arena_app.css:682:     text-overflow: ellipsis;
static/css/arena_app.css:685: body.az-arena-app-enabled .az-arena-card-tags {
static/css/arena_app.css:689:     z-index: 5;
static/css/arena_app.css:693:     overflow: hidden;
static/css/arena_app.css:696: body.az-arena-app-enabled .az-arena-card-tags small {
static/css/arena_app.css:708: body.az-arena-app-enabled .az-arena-card-stats {
static/css/arena_app.css:713:     z-index: 5;
static/css/arena_app.css:719: body.az-arena-app-enabled .az-arena-card-stats div {
static/css/arena_app.css:730: body.az-arena-app-enabled .az-arena-card-stats b {
static/css/arena_app.css:736: body.az-arena-app-enabled .az-arena-card-stats small {
static/css/arena_app.css:744: body.az-arena-app-enabled .az-arena-card.type-monster {
static/css/arena_app.css:748: body.az-arena-app-enabled .az-arena-card.type-spell {
static/css/arena_app.css:752: body.az-arena-app-enabled .az-arena-card.type-trap {
static/css/arena_app.css:756: body.az-arena-app-enabled .az-arena-card.is-playable {
static/css/arena_app.css:763: body.az-arena-app-enabled .az-arena-card.is-unplayable {
static/css/arena_app.css:768: body.az-arena-app-enabled .az-arena-actions {
static/css/arena_app.css:776: body.az-arena-app-enabled .az-arena-actions button {
static/css/arena_app.css:783:     body.az-arena-app-enabled .az-arena-app {
static/css/arena_app.css:792:     body.az-arena-app-enabled .az-arena-app-top {
static/css/arena_app.css:797:     body.az-arena-app-enabled .az-arena-app-back {
static/css/arena_app.css:798:         display: none;
static/css/arena_app.css:801:     body.az-arena-app-enabled .az-arena-app-score {
static/css/arena_app.css:807:     body.az-arena-app-enabled .az-arena-stat-row {
static/css/arena_app.css:811:     body.az-arena-app-enabled .az-arena-stat {
static/css/arena_app.css:817:     body.az-arena-app-enabled .az-arena-board {
static/css/arena_app.css:822:     body.az-arena-app-enabled .az-arena-field {
static/css/arena_app.css:826:     body.az-arena-app-enabled .az-arena-hand {
static/css/arena_app.css:830:     body.az-arena-app-enabled .az-arena-hand-row {
static/css/arena_app.css:834:     body.az-arena-app-enabled .az-arena-hand-row .az-arena-card {
static/css/arena_app.css:840:     body.az-arena-app-enabled .az-arena-actions {
static/css/arena_app.css:845:     body.az-arena-app-enabled .az-arena-actions button {
static/css/arena_app.css:857: body.az-arena-app-enabled .az-arena-app {
static/css/arena_app.css:861: body.az-arena-app-enabled .az-arena-board {
static/css/arena_app.css:869:     overflow: hidden;
static/css/arena_app.css:872: body.az-arena-app-enabled .az-arena-board::before {
static/css/arena_app.css:885: body.az-arena-app-enabled .az-arena-board::after {
static/css/arena_app.css:897: body.az-arena-app-enabled .az-arena-field {
static/css/arena_app.css:899:     z-index: 2;
static/css/arena_app.css:903: body.az-arena-app-enabled #az-enemy-field {
static/css/arena_app.css:908: body.az-arena-app-enabled #az-me-field {
static/css/arena_app.css:913: body.az-arena-app-enabled .az-arena-slot {
static/css/arena_app.css:920: body.az-arena-app-enabled .az-arena-slot::before {
static/css/arena_app.css:929: body.az-arena-app-enabled .az-arena-card {
static/css/arena_app.css:933: body.az-arena-app-enabled #az-me-field .az-arena-card,
static/css/arena_app.css:934: body.az-arena-app-enabled #az-enemy-field .az-arena-card {
static/css/arena_app.css:939: body.az-arena-app-enabled #az-me-field .az-arena-card:hover:not(:disabled),
static/css/arena_app.css:940: body.az-arena-app-enabled #az-enemy-field .az-arena-card:hover:not(:disabled) {
static/css/arena_app.css:945:     position: fixed;
static/css/arena_app.css:952:     z-index: 1;
static/css/arena_app.css:960:     position: fixed;
static/css/arena_app.css:963:     z-index: 160;
static/css/arena_app.css:1081:     position: fixed;
static/css/arena_app.css:1083:     z-index: 300;
static/css/arena_app.css:1084:     display: none;
static/css/arena_app.css:1176:     position: fixed !important;
static/css/arena_app.css:1177:     z-index: 240 !important;
static/css/arena_app.css:1344: body.az-arena-app-enabled .az-arena-actions button.active {
static/css/arena_app.css:1346:     overflow: hidden;
static/css/arena_app.css:1349: body.az-arena-app-enabled .az-arena-actions button.active::after {
static/css/arena_app.css:1385:     position: fixed;
static/css/arena_app.css:1388:     z-index: 420;
static/css/arena_app.css:1407: body.az-arena-app-enabled .az-arena-card.element-fire .az-arena-card-art,
static/css/arena_app.css:1413: body.az-arena-app-enabled .az-arena-card.element-water .az-arena-card-art,
static/css/arena_app.css:1419: body.az-arena-app-enabled .az-arena-card.element-earth .az-arena-card-art,
static/css/arena_app.css:1425: body.az-arena-app-enabled .az-arena-card.element-plant .az-arena-card-art,
static/css/arena_app.css:1431: body.az-arena-app-enabled .az-arena-card.element-global .az-arena-card-art,
static/css/arena_app.css:1437: body.az-arena-app-enabled .az-arena-card.element-neutral .az-arena-card-art,
static/css/arena_app.css:1443: body.az-arena-app-enabled .az-arena-card-art {
static/css/arena_app.css:1450: body.az-arena-app-enabled .az-arena-card.element-fire {
static/css/arena_app.css:1454: body.az-arena-app-enabled .az-arena-card.element-water {
static/css/arena_app.css:1458: body.az-arena-app-enabled .az-arena-card.element-earth {
static/css/arena_app.css:1462: body.az-arena-app-enabled .az-arena-card.element-plant {
static/css/arena_app.css:1466: body.az-arena-app-enabled .az-arena-card.element-global {
static/css/arena_app.css:1471:     position: fixed;
static/css/arena_app.css:1472:     z-index: 260;
static/css/arena_app.css:1522: body.az-arena-app-enabled .az-arena-app {
static/css/arena_app.css:1527: body.az-arena-app-enabled .az-arena-app.az-compact-height {
static/css/arena_app.css:1532: body.az-arena-app-enabled .az-arena-app.az-compact-height .az-arena-hand {
static/css/arena_app.css:1536: body.az-arena-app-enabled .az-arena-app.az-compact-height .az-arena-hand-row {
static/css/arena_app.css:1540: body.az-arena-app-enabled .az-arena-app.az-compact-height .az-arena-hand-row .az-arena-card {
static/css/arena_app.css:1546: body.az-arena-app-enabled .az-card-rarity-line {
static/css/arena_app.css:1552:     z-index: 7;
static/css/arena_app.css:1558: body.az-arena-app-enabled .az-arena-card.rarity-common .az-card-rarity-line {
static/css/arena_app.css:1562: body.az-arena-app-enabled .az-arena-card.rarity-uncommon .az-card-rarity-line {
static/css/arena_app.css:1567: body.az-arena-app-enabled .az-arena-card.rarity-rare .az-card-rarity-line {
static/css/arena_app.css:1572: body.az-arena-app-enabled .az-arena-card.rarity-ultra-rare .az-card-rarity-line {
static/css/arena_app.css:1577: body.az-arena-app-enabled .az-arena-card.rarity-unique .az-card-rarity-line {
static/css/arena_app.css:1582: body.az-arena-app-enabled .az-arena-card-art {
static/css/arena_app.css:1583:     overflow: hidden;
static/css/arena_app.css:1589: body.az-arena-app-enabled .az-arena-card-art::before {
static/css/arena_app.css:1601: body.az-arena-app-enabled .az-arena-card-art::after {
static/css/arena_app.css:1621: body.az-arena-app-enabled .az-card-art-orb {
static/css/arena_app.css:1627:     z-index: 3;
static/css/arena_app.css:1639: body.az-arena-app-enabled .az-card-art-mark {
static/css/arena_app.css:1643:     z-index: 4;
static/css/arena_app.css:1651: body.az-arena-app-enabled .az-arena-hand-row .az-card-art-mark {
static/css/arena_app.css:1655: body.az-arena-app-enabled .az-arena-card-body {
static/css/arena_app.css:1661: body.az-arena-app-enabled .az-arena-card strong {
static/css/arena_app.css:1663:     overflow: hidden;
static/css/arena_app.css:1669: body.az-arena-app-enabled #az-me-field .az-arena-card strong,
static/css/arena_app.css:1670: body.az-arena-app-enabled #az-enemy-field .az-arena-card strong {
static/css/arena_app.css:1674: body.az-arena-app-enabled #az-me-field .az-arena-card span,
static/css/arena_app.css:1675: body.az-arena-app-enabled #az-enemy-field .az-arena-card span {
static/css/arena_app.css:1679: body.az-arena-app-enabled #az-me-field .az-arena-card-stats div,
static/css/arena_app.css:1680: body.az-arena-app-enabled #az-enemy-field .az-arena-card-stats div {
static/css/arena_app.css:1685: body.az-arena-app-enabled #az-me-field .az-arena-card-stats b,
static/css/arena_app.css:1686: body.az-arena-app-enabled #az-enemy-field .az-arena-card-stats b {
static/css/arena_app.css:1690: body.az-arena-app-enabled .az-arena-card-tags {
static/css/arena_app.css:1694: body.az-arena-app-enabled .az-arena-card-tags small {
static/css/arena_app.css:1696:     overflow: hidden;
static/css/arena_app.css:1697:     text-overflow: ellipsis;
static/css/arena_app.css:1700: body.az-arena-app-enabled .az-arena-app-shell,
static/css/arena_app.css:1701: body.az-arena-app-enabled .az-arena-card,
static/css/arena_app.css:1702: body.az-arena-app-enabled .az-arena-slot {
static/css/arena_app.css:1707:     body.az-arena-app-enabled .az-arena-field {
static/css/arena_app.css:1711:     body.az-arena-app-enabled .az-arena-card-tags small:nth-child(2) {
static/css/arena_app.css:1712:         display: none;
static/css/arena_app.css:1717:     body.az-arena-app-enabled .az-arena-app {
static/css/arena_app.css:1721:     body.az-arena-app-enabled .az-arena-app-title h1 {
static/css/arena_app.css:1725:     body.az-arena-app-enabled .az-arena-app-message {
static/css/arena_app.css:1729:     body.az-arena-app-enabled .az-arena-player {
static/css/arena_app.css:1733:     body.az-arena-app-enabled .az-arena-player-head {
static/css/arena_app.css:1737:     body.az-arena-app-enabled .az-arena-player-head span {
static/css/arena_app.css:1741:     body.az-arena-app-enabled .az-arena-player-head strong {
static/css/arena_app.css:1745:     body.az-arena-app-enabled .az-arena-field {
static/css/arena_app.css:1750:     body.az-arena-app-enabled .az-arena-card-cost {
static/css/arena_app.css:1756:     body.az-arena-app-enabled .az-arena-card-tags {
static/css/arena_app.css:1757:         display: none;
static/css/arena_app.css:1760:     body.az-arena-app-enabled .az-arena-card-body {
static/css/arena_app.css:1766:     body.az-arena-app-enabled .az-arena-card strong {
static/css/arena_app.css:1770:     body.az-arena-app-enabled .az-arena-card span {
static/css/arena_app.css:1774:     body.az-arena-app-enabled .az-arena-card-stats div {
static/css/arena_app.css:1779:     body.az-arena-app-enabled .az-arena-card-stats b {
static/css/arena_app.css:1783:     body.az-arena-app-enabled .az-arena-card-stats small {
static/css/arena_app.css:1794:     position: fixed;
static/css/arena_app.css:1796:     z-index: 360;
static/css/arena_app.css:1797:     display: none;
static/css/arena_app.css:1903:     overflow: hidden;
static/css/arena_app.css:1964: html:has(.az-arena-v40),
static/css/arena_app.css:1965: body:has(.az-arena-v40) {
static/css/arena_app.css:1968:     overflow: hidden !important;
static/css/arena_app.css:1972: body:has(.az-arena-v40) {
static/css/arena_app.css:1977: .az-arena-v40 {
static/css/arena_app.css:1978:     position: fixed;
static/css/arena_app.css:1981:     height: 100dvh;
static/css/arena_app.css:1982:     overflow: hidden;
static/css/arena_app.css:1999: .az-arena-v40 * {
static/css/arena_app.css:2003: .az-arena-v40 .arena-shell,
static/css/arena_app.css:2004: .az-arena-v40 .arena-board,
static/css/arena_app.css:2005: .az-arena-v40 .battlefield,
static/css/arena_app.css:2006: .az-arena-v40 .arena-main,
static/css/arena_app.css:2007: .az-arena-v40 .arena-stage {
static/css/arena_app.css:2009:     overflow: hidden;
static/css/arena_app.css:2012: .az-arena-v40 .az-arena-top,
static/css/arena_app.css:2013: .az-arena-v40 .arena-top,
static/css/arena_app.css:2014: .az-arena-v40 .top-bar {
static/css/arena_app.css:2017:     overflow: hidden;
static/css/arena_app.css:2020: .az-arena-v40 .az-board-v1,
static/css/arena_app.css:2021: .az-arena-v40 .arena-board-v1,
static/css/arena_app.css:2022: .az-arena-v40 .battle-board-v1 {
static/css/arena_app.css:2025:     overflow: hidden;
static/css/arena_app.css:2028: .az-arena-v40 .az-hand-v1,
static/css/arena_app.css:2029: .az-arena-v40 .player-hand,
static/css/arena_app.css:2030: .az-arena-v40 .hand-zone,
static/css/arena_app.css:2031: .az-arena-v40 #az-hand,
static/css/arena_app.css:2032: .az-arena-v40 #my-hand {
static/css/arena_app.css:2035:     overflow: hidden;
static/css/arena_app.css:2042: .az-arena-v40 .az-card,
static/css/arena_app.css:2043: .az-arena-v40 .arena-card,
static/css/arena_app.css:2044: .az-arena-v40 .card-shell,
static/css/arena_app.css:2045: .az-arena-v40 .hand-card,
static/css/arena_app.css:2046: .az-arena-v40 [data-card-id] {
static/css/arena_app.css:2051:     overflow: hidden;
static/css/arena_app.css:2056: .az-arena-v40 .az-card:hover,
static/css/arena_app.css:2057: .az-arena-v40 .arena-card:hover,
static/css/arena_app.css:2058: .az-arena-v40 .hand-card:hover,
static/css/arena_app.css:2059: .az-arena-v40 [data-card-id]:hover {
static/css/arena_app.css:2061:     z-index: 5;
static/css/arena_app.css:2068:     z-index: 8;
static/css/arena_app.css:2116: .az-arena-v40 .battle-log,
static/css/arena_app.css:2117: .az-arena-v40 .arena-log,
static/css/arena_app.css:2118: .az-arena-v40 #battle-log,
static/css/arena_app.css:2119: .az-arena-v40 #az-log {
static/css/arena_app.css:2121:     overflow: auto;
static/css/arena_app.css:2126:     .az-arena-v40 {
static/css/arena_app.css:2131:     .az-arena-v40 .az-card,
static/css/arena_app.css:2132:     .az-arena-v40 .arena-card,
static/css/arena_app.css:2133:     .az-arena-v40 .card-shell,
static/css/arena_app.css:2134:     .az-arena-v40 .hand-card,
static/css/arena_app.css:2135:     .az-arena-v40 [data-card-id] {
static/css/arena_app.css:2154: html:has(.az-arena-v45),
static/css/arena_app.css:2155: body.az-arena-v45 {
static/css/arena_app.css:2158:     overflow: hidden !important;
static/css/arena_app.css:2163: body.az-arena-v45 {
static/css/arena_app.css:2169: body.az-arena-v45 > main:not(#az-arena-v45-root),
static/css/arena_app.css:2170: body.az-arena-v45 > header,
static/css/arena_app.css:2171: body.az-arena-v45 > nav,
static/css/arena_app.css:2172: body.az-arena-v45 > footer {
static/css/arena_app.css:2173:     display: none !important;
static/css/arena_app.css:2176: .az-arena-v45-root {
static/css/arena_app.css:2177:     position: fixed;
static/css/arena_app.css:2179:     z-index: 999;
static/css/arena_app.css:2181:     height: 100dvh;
static/css/arena_app.css:2182:     overflow: hidden;
static/css/arena_app.css:2205:     overflow: hidden;
static/css/arena_app.css:2237:     overflow: hidden;
static/css/arena_app.css:2238:     text-overflow: ellipsis;
static/css/arena_app.css:2278:     overflow: hidden;
static/css/arena_app.css:2293:     overflow: hidden;
static/css/arena_app.css:2294:     text-overflow: ellipsis;
static/css/arena_app.css:2315:     overflow: hidden;
static/css/arena_app.css:2337:     overflow: hidden;
static/css/arena_app.css:2366:     overflow: hidden;
static/css/arena_app.css:2384:     z-index: 10;
static/css/arena_app.css:2412:     z-index: 4;
static/css/arena_app.css:2442:     overflow: hidden;
static/css/arena_app.css:2443:     text-overflow: ellipsis;
static/css/arena_app.css:2470:     overflow: hidden;
static/css/arena_app.css:2471:     text-overflow: ellipsis;
static/css/arena_app.css:2489:     overflow: hidden;
static/css/arena_app.css:2490:     text-overflow: ellipsis;
static/css/arena_app.css:2495:     display: none;
static/css/arena_app.css:2517:     .az-arena-v45-root {
```



## Potential Fatal Issues Detected


```text
- CSS hides all existing main elements except #az-arena-v45-root. If V45 root does not receive socket state, the arena appears dead.
- Multiple renderers likely active: game.js legacy renderer + arena_app.js V45 renderer. They may compete or listen to different payload contracts.
```
