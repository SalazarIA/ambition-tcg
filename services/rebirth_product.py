from collections import Counter
from copy import deepcopy
from random import Random

from services.rebirth_cards import (
    BASE_MONSTERS,
    EVOLVED_MONSTERS,
    PLAYER_DECK,
    SPELL_CARDS,
    TRAP_CARDS,
    catalog_payload,
    get_card,
    validate_deck_distribution,
)


PRODUCT_NAV = [
    {"key": "play", "label": "Arena", "href": "/rebirth"},
    {"key": "collection", "label": "Coleção", "href": "/rebirth/collection"},
    {"key": "shop", "label": "Loja", "href": "/rebirth/shop"},
    {"key": "progression", "label": "Recompensas", "href": "/rebirth/progression"},
    {"key": "profile", "label": "Perfil", "href": "/rebirth/profile"},
]

LAB_LINKS = [
    {"key": "history", "label": "Diário de Partidas", "href": "/rebirth/history"},
    {"key": "tutorial", "label": "Status do Tutorial", "href": "/rebirth/onboarding"},
    {"key": "support", "label": "Ferramentas de Suporte", "href": "/rebirth/support"},
    {"key": "desktop", "label": "Notas de Desktop", "href": "/rebirth/desktop"},
    {"key": "release", "label": "Controle de Lançamento", "href": "/rebirth/release"},
]

DEFAULT_LOADOUT = list(PLAYER_DECK)

AUTH_PLAN_STEPS = [
    {
        "title": "Criar",
        "status": "Etapa 1",
        "copy": "Crie seu nome Rebirth e salve cada clash, carta e recompensa nesta conta.",
    },
    {
        "title": "Aprender",
        "status": "Etapa 2",
        "copy": "A primeira partida abre com orientação ao vivo para explicar cada escolha de carta.",
    },
    {
        "title": "Conquistar",
        "status": "Etapa 3",
        "copy": "Conclua clashes, resgate XP diário e desbloqueie novos marcos de recompensa.",
    },
    {
        "title": "Montar",
        "status": "Etapa 4",
        "copy": "Abra pacotes, ajuste seu baralho de 30 cartas e leve-o ao próximo duelo.",
    },
]

TUTORIAL_STEPS = [
    {
        "step": 1,
        "title": "Escolha Um Monstro",
        "copy": "Sua mão está visível para você. Escolha o monstro que produz o clash mais limpo.",
    },
    {
        "step": 2,
        "title": "Leia A Resposta",
        "copy": "O bot responde com um monstro. O ataque decide a vitória; a guarda reduz dano.",
    },
    {
        "step": 3,
        "title": "Combine Duplicatas",
        "copy": "Dois monstros básicos iguais podem evoluir antes de você jogar uma carta.",
    },
    {
        "step": 4,
        "title": "Resgate Progresso",
        "copy": "Clashes, boosters e a conclusão do tutorial ficam salvos na sua conta Rebirth.",
    },
]

RELEASE_CHECKS = [
    {"name": "Produto Ativo", "state": "passed", "copy": "Ambitionz Rebirth é a superfície ativa do produto."},
    {"name": "Legado Desativado", "state": "passed", "copy": "Rotas antigas redirecionam e APIs aposentadas retornam 410."},
    {"name": "Persistência", "state": "passed", "copy": "Acesso, coleção, baralhos, progressão e boosters persistem no PostgreSQL autoritativo."},
    {"name": "Segurança da Conta", "state": "passed", "copy": "CSRF, limitação de autenticação e troca de senha estão ativos no Rebirth."},
    {"name": "Interface", "state": "passed", "copy": "As páginas Rebirth usam apenas os recursos atuais da Arena."},
    {"name": "Sensação das Cartas", "state": "passed", "copy": "Resultados de clash exibem habilidades, impacto e recompensas persistidas."},
    {"name": "Laboratório de Balanceamento", "state": "passed", "copy": "Simulações de personalidades do bot relatam impacto de cartas, habilidades e perfis."},
    {"name": "Histórico", "state": "passed", "copy": "Partidas autenticadas persistem comandos, eventos, hash de estado e retrato final."},
    {"name": "Extrato Econômico", "state": "passed", "copy": "XP, cartas iniciais, boosters, recompensas diárias e concessões escrevem um extrato auditável."},
    {"name": "Ferramentas de Suporte", "state": "passed", "copy": "Jogadores podem exportar/reiniciar a conta; concessões exigem token do servidor."},
    {"name": "Controle de QA", "state": "passed", "copy": "py_compile, pytest, verificação Node e teste do navegador passaram neste bloco."},
]

PROGRESSION_TRACK = [
    {"level": 1, "name": "Primeira Centelha", "reward": "Pacote inicial pronto", "state": "claimed"},
    {"level": 2, "name": "Segundo Clash", "reward": "Bônus de 25 XP", "state": "ready"},
    {"level": 3, "name": "Vínculo Monstruoso", "reward": "Ajuste de baralho", "state": "locked"},
    {"level": 4, "name": "Prova Apex", "reward": "Moldura evoluída", "state": "locked"},
    {"level": 5, "name": "Corredor de Pacotes", "reward": "Bilhete de pacote", "state": "locked"},
    {"level": 6, "name": "Quebra-Guarda", "reward": "Centelha de melhoria", "state": "locked"},
    {"level": 7, "name": "Leitura Limpa", "reward": "Selo de orientação", "state": "locked"},
    {"level": 8, "name": "Linha de Pressão", "reward": "Chance de carta incomum", "state": "locked"},
    {"level": 9, "name": "Chama Gêmea", "reward": "Bônus de duplicata", "state": "locked"},
    {"level": 10, "name": "Nome de Arena", "reward": "Título de perfil", "state": "locked"},
    {"level": 11, "name": "Contra-Jogada", "reward": "Bilhete de pacote", "state": "locked"},
    {"level": 12, "name": "Vínculo Apex", "reward": "Chance de carta evoluída", "state": "locked"},
    {"level": 13, "name": "Mão Firme", "reward": "Estilo de slot do baralho", "state": "locked"},
    {"level": 14, "name": "Sequência Quente", "reward": "Bônus de XP", "state": "locked"},
    {"level": 15, "name": "Centelha do Cofre", "reward": "Moldura de coleção", "state": "locked"},
    {"level": 16, "name": "Instinto de Duelo", "reward": "Selo de orientação", "state": "locked"},
    {"level": 17, "name": "Mestre de Pacotes", "reward": "Bilhete de pacote", "state": "locked"},
    {"level": 18, "name": "Leitura da Ferida", "reward": "Chance de carta incomum", "state": "locked"},
    {"level": 19, "name": "Corrente Rebirth", "reward": "Bônus de duplicata", "state": "locked"},
    {"level": 20, "name": "Centelha da Temporada", "reward": "Selo da Temporada 0", "state": "locked"},
]


def nav(active):
    items = []
    for item in PRODUCT_NAV:
        copy = dict(item)
        copy["active"] = copy["key"] == active
        items.append(copy)
    return items


def page_payload(key, title, subtitle, primary_label="Entrar na Arena", primary_href="/rebirth"):
    return {
        "key": key,
        "title": title,
        "subtitle": subtitle,
        "primary_label": primary_label,
        "primary_href": primary_href,
        "nav": nav(key),
    }


def guest_account():
    return {"authenticated": False, "user": None}


def account_payload(user=None):
    return {"authenticated": bool(user), "user": deepcopy(user) if user else None}


def product_shell_payload(account=None):
    account = account or guest_account()
    payload = page_payload(
        "home",
        "Ambitionz Rebirth",
        "Uma plataforma TCG de fantasia sombria para duelar, colecionar e abrir pacotes.",
    )
    payload.update(
        {
            "account": account,
            "status": [
                {"label": "Modo", "value": "Clash TCG"},
                {"label": "Cartas", "value": "100 no catálogo"},
                {"label": "Economia", "value": "Ouro + Gemas"},
            ],
            "blocks": [
                {
                    "title": "Entrar na Arena",
                    "copy": "Comece um duelo contra o bot e leia a mesa viva em tempo real.",
                    "href": "/rebirth",
                },
                {
                    "title": "Minha Coleção",
                    "copy": "Monte um deck de 30 cartas com monstros, magias, armadilhas e evoluções.",
                    "href": "/rebirth/collection",
                },
                {
                    "title": "Loja & Mercado",
                    "copy": "Abra boosters de 5 cartas e veja ofertas ativas de outros jogadores.",
                    "href": "/rebirth/shop",
                },
                {
                    "title": "Recompensas",
                    "copy": "Suba de nível com XP, missões diárias e marcos de temporada.",
                    "href": "/rebirth/progression",
                },
                {
                    "title": "Perfil",
                    "copy": "Acompanhe nível, selos, carteira e controles da conta.",
                    "href": "/rebirth/profile",
                },
            ],
        }
    )
    return payload


def auth_plan_payload(account=None):
    account = account or guest_account()
    payload = page_payload(
        "account",
        "Login / Cadastro",
        "Entre para guardar coleção, recompensas, Ouro e Gemas.",
        primary_label="Entrar na Arena",
        primary_href="/rebirth?firstRun=1",
    )
    payload["account"] = account
    payload["steps"] = deepcopy(AUTH_PLAN_STEPS)
    payload["constraints"] = [
        "Cada clash concede XP à conta.",
        "A primeira partida começa com orientação sobre monstros, magias e armadilhas.",
        "Recompensas diárias são liberadas após um clash.",
        "Pacotes e alterações de baralho ficam salvos para este jogador.",
        "Os controles de senha ficam na tela Perfil.",
    ]
    return payload


def owned_counts(collection_counts=None):
    if collection_counts is not None:
        return Counter(collection_counts)
    return Counter(PLAYER_DECK)


def card_collection(collection_counts=None, loadout_card_ids=None):
    counts = owned_counts(collection_counts)
    loadout_counts = Counter(loadout_card_ids or DEFAULT_LOADOUT)
    cards = []
    for card in catalog_payload():
        card_copy = deepcopy(card)
        card_copy["owned_count"] = counts.get(card["id"], 0)
        card_copy["in_loadout_count"] = loadout_counts.get(card["id"], 0)
        card_copy["unlock_state"] = "Possuída" if card_copy["owned_count"] else "Prévia"
        card_copy["is_evolved"] = int(card_copy.get("tier", 1)) > 1
        cards.append(card_copy)
    return cards


def collection_payload(account=None, collection_counts=None, loadout_card_ids=None):
    account = account or guest_account()
    loadout_ids = loadout_card_ids or DEFAULT_LOADOUT
    cards = card_collection(collection_counts=collection_counts, loadout_card_ids=loadout_ids)
    base_owned = [card for card in cards if card["owned_count"]]
    payload = page_payload(
        "collection",
        "Minha Coleção",
        "Ajuste seu deck de 30 cartas entre monstros, magias, armadilhas e pares de evolução.",
        primary_label="Entrar na Arena",
        primary_href="/rebirth",
    )
    payload.update(
        {
            "account": account,
            "is_persisted": bool(account.get("authenticated")),
            "cards": cards,
            "loadout": [get_card(card_id) for card_id in loadout_ids],
            "summary": {
                "owned_cards": sum(card["owned_count"] for card in cards),
                "unique_owned": len(base_owned),
                "loadout_size": len(loadout_ids),
                "preview_evolutions": len(EVOLVED_MONSTERS),
            },
        }
    )
    return payload


def validate_loadout(card_ids, collection_counts=None):
    if not isinstance(card_ids, list):
        raise ValueError("card_ids deve ser uma lista.")
    selected = [str(card_id) for card_id in card_ids if str(card_id or "").strip()]
    validate_deck_distribution(selected)

    owned = owned_counts(collection_counts)
    selected_counts = Counter(selected)
    for card_id, amount in selected_counts.items():
        if card_id not in owned:
            raise ValueError(f"{card_id} não pertence à coleção Rebirth.")
        if amount > owned[card_id]:
            raise ValueError(f"{card_id} excede as cópias possuídas.")

    loadout = [get_card(card_id) for card_id in selected]
    families = sorted({card["family"] for card in loadout})
    return {
        "loadout": loadout,
        "summary": {
            "size": len(loadout),
            "families": families,
            "attack_total": sum(int(card["attack"]) for card in loadout),
            "guard_total": sum(int(card["guard"]) for card in loadout),
            "duplicate_pairs": sum(1 for count in selected_counts.values() if count >= 2),
        },
    }


def shop_payload(account=None, booster_history=None, market_offers=None):
    account = account or guest_account()
    payload = page_payload(
        "shop",
        "Loja & Mercado",
        "Abra boosters, revele cartas por raridade e acompanhe ofertas do mercado.",
        primary_label="Abrir Booster",
        primary_href="/rebirth/shop",
    )
    payload.update(
        {
            "offers": [
                {
                    "id": "starter_booster_demo",
                    "name": "Booster Rebirth",
                    "price": "Grátis na beta",
                    "contents": "5 cartas: 3 comuns e 2 incomuns",
                    "state": "available",
                }
            ],
            "market": {
                "offers": market_offers or [],
                "fee_rate": "5%",
                "currencies": ["GOLD"],
            },
            "account": account,
            "history": booster_history or [],
            "disclaimer": "Boosters são grátis durante a beta Rebirth. O mercado opera apenas em Ouro e bloqueia cartas listadas até a venda ou o cancelamento.",
        }
    )
    return payload


def open_booster(seed=None):
    rng = Random(str(seed or "rebirth-booster-demo"))
    common_pool = [card["id"] for card in BASE_MONSTERS if card.get("rarity") == "COMMON"]
    uncommon_pool = [card["id"] for card in EVOLVED_MONSTERS + SPELL_CARDS + TRAP_CARDS if card.get("rarity") == "UNCOMMON"]
    card_ids = [
        rng.choice(common_pool),
        rng.choice(common_pool),
        rng.choice(common_pool),
        rng.choice(uncommon_pool),
        rng.choice(uncommon_pool),
    ]
    cards = [get_card(card_id) for card_id in card_ids]
    rarity_counts = Counter(card["rarity"] for card in cards)
    return {
        "booster_id": "starter_booster_demo",
        "cards": cards,
        "summary": {
            "count": len(cards),
            "highest_attack": max(card["attack"] for card in cards),
            "elevated_slot": cards[-1]["name"],
            "rarity_counts": dict(rarity_counts),
            "rarity_slots": ["COMMON", "COMMON", "COMMON", "UNCOMMON", "UNCOMMON"],
        },
    }


def progression_payload(account=None, progression=None):
    account = account or guest_account()
    profile = progression or {
        "level": 1,
        "xp": 0,
        "next_level_xp": 500,
        "wins": 0,
        "losses": 0,
        "clashes": 0,
        "boosters_opened": 0,
        "tutorial_step": 0,
        "tutorial_complete": False,
        "daily_claimed": False,
    }
    payload = page_payload(
        "progression",
        "Recompensas",
        "Ganhe XP, colete o progresso diário e persiga a trilha de recompensas da Temporada 0.",
        primary_label="Jogar por XP",
        primary_href="/rebirth",
    )
    daily_claimed = bool(profile.get("daily_claimed", False))
    daily_ready = int(profile.get("clashes", 0)) >= 1
    payload.update(
        {
            "account": account,
            "profile": profile,
            "track": progression_track(profile),
            "daily": {
                "name": "Jogue um clash",
                "progress": min(1, int(profile.get("clashes", 0))),
                "goal": 1,
                "reward": "25 XP",
                "state": "claimed" if daily_claimed else "ready" if daily_ready else "locked",
            },
        }
    )
    return payload


def progression_track(profile):
    level = int(profile.get("level", 1))
    track = deepcopy(PROGRESSION_TRACK)
    for item in track:
        if item["level"] < level:
            item["state"] = "claimed"
        elif item["level"] == level:
            item["state"] = "ready"
        else:
            item["state"] = "locked"
    return track


def guest_profile():
    return {
        "user": None,
        "progression": {
            "level": 1,
            "xp": 0,
            "next_level_xp": 500,
            "wins": 0,
            "losses": 0,
            "clashes": 0,
            "boosters_opened": 0,
            "tutorial_step": 0,
            "tutorial_complete": False,
            "daily_claimed": False,
        },
        "collection": {"owned_cards": len(PLAYER_DECK), "unique_owned": len(set(PLAYER_DECK)), "loadout_size": len(PLAYER_DECK)},
        "achievements": [
            {
                "key": key,
                "name": name,
                "copy": copy,
                "unlocked": False,
                "unlocked_at": None,
            }
            for key, name, copy in [
                ("founder", "Fundador Rebirth", "Crie uma conta Rebirth."),
                ("first_clash", "Primeiro Clash", "Resolva um clash Rebirth persistido."),
                ("first_win", "Primeira Vitória", "Vença uma partida Rebirth persistida."),
                ("first_booster", "Booster Aberto", "Abra um booster Rebirth sem pagamento."),
                ("daily_claimed", "Centelha Diária", "Resgate a recompensa diária do primeiro clash."),
                ("tutorial_complete", "Desperto", "Conclua a introdução do Rebirth."),
                ("first_campaign_clear", "Coroa Cinzenta", "Derrote o Rei Cinzento e conclua a campanha."),
                ("no_damage_win", "Intocavel", "Venca um encontro de campanha sem perder PV."),
                ("evolve_master", "Mestre da Evolucao", "Venca um encontro apos evoluir uma unidade."),
                ("shadow_slayer", "Cacador do Eclipse", "Derrote o Parasita do Eclipse."),
                ("3_win_streak", "Marcha Imparavel", "Venca tres encontros de campanha em sequencia."),
            ]
        ],
        "unlocked_achievements": 0,
        "recent_boosters": [],
    }


def profile_payload(account=None, profile=None):
    account = account or guest_account()
    profile = profile or guest_profile()
    progress = profile.get("progression") or guest_profile()["progression"]
    collection = profile.get("collection") or guest_profile()["collection"]
    payload = page_payload(
        "profile",
        "Perfil do Jogador",
        "Identidade persistida, conquistas e controles da conta do jogador ativo.",
        primary_label="Abrir Coleção",
        primary_href="/rebirth/collection",
    )
    payload.update(
        {
            "account": account,
            "profile": profile,
            "stats": [
                {"label": "Nível", "value": progress.get("level", 1)},
                {"label": "XP", "value": f"{progress.get('xp', 0)}/{progress.get('next_level_xp', 500)}"},
                {"label": "Ouro", "value": progress.get("gold", 0)},
                {"label": "Gemas", "value": progress.get("coinz", progress.get("premium", 0))},
                {"label": "Cartas", "value": collection.get("owned_cards", 0)},
                {"label": "Selos", "value": profile.get("unlocked_achievements", 0)},
            ],
        }
    )
    return payload


def history_payload(account=None, matches=None, ledger=None):
    account = account or guest_account()
    matches = matches or []
    ledger = ledger or []
    payload = page_payload(
        "history",
        "Histórico de Partidas + Extrato Econômico",
        "Partidas Rebirth persistidas salvam comandos, eventos, hashes de estado e movimentos de recompensa.",
        primary_label="Jogar pelo Histórico",
        primary_href="/rebirth",
    )
    payload.update(
        {
            "account": account,
            "matches": matches,
            "ledger": ledger,
            "summary": {
                "matches": len(matches),
                "ledger_entries": len(ledger),
                "finished": len([match for match in matches if match.get("status") == "finished"]),
            },
        }
    )
    return payload


def support_payload(account=None, export=None):
    account = account or guest_account()
    payload = page_payload(
        "support",
        "Suporte + Segurança Administrativa",
        "Exportação, reinício de conta e concessões protegidas por token para o MVP Rebirth.",
        primary_label="Abrir Perfil",
        primary_href="/rebirth/profile",
    )
    payload.update(
        {
            "account": account,
            "export": export,
            "checks": [
                "A exportação é autônoma e limitada à conta conectada.",
                "O reinício exige confirmação explícita.",
                "A concessão administrativa fica desativada sem REBIRTH_ADMIN_TOKEN.",
                "Toda concessão registra entradas em admin_audit_log e economy_ledger.",
            ],
        }
    )
    return payload


def lab_payload():
    payload = page_payload(
        "lab",
        "Laboratório Rebirth",
        "Ferramentas internas de QA, suporte e lançamento para a equipe Rebirth.",
        primary_label="Voltar ao Jogo",
        primary_href="/rebirth",
    )
    payload.update({"links": deepcopy(LAB_LINKS)})
    return payload


def desktop_payload():
    payload = page_payload(
        "desktop",
        "Polimento da Arena Desktop",
        "A moldura desktop enquadra o tabuleiro vertical com status úteis sem esticar o jogo.",
        primary_label="Abrir Arena",
        primary_href="/rebirth",
    )
    payload.update(
        {
            "checks": [
                "O tabuleiro vertical permanece fixo e centralizado.",
                "As laterais desktop adicionam status sem mudar as regras.",
                "A arena jogável não cria rolagem da página.",
                "O celular mantém a composição em uma única tela.",
            ]
        }
    )
    return payload


def onboarding_payload(account=None, progression=None):
    account = account or guest_account()
    progress = progression or {}
    payload = page_payload(
        "tutorial",
        "Introdução/Tutorial Rebirth",
        "Um percurso jogável curto para aprender o ciclo persistido do Rebirth.",
        primary_label="Jogar Clash Tutorial",
        primary_href="/rebirth",
    )
    payload.update(
        {
            "account": account,
            "steps": deepcopy(TUTORIAL_STEPS),
            "current_step": int(progress.get("tutorial_step", 0) or 0),
            "complete": bool(progress.get("tutorial_complete", False)),
        }
    )
    return payload


def balance_payload(simulation=None):
    payload = page_payload(
        "balance",
        "Balanceamento + Ajuste do Bot",
        "Simulações determinísticas medem cartas, habilidades e personalidades do bot sem reativar sistemas antigos.",
        primary_label="Abrir Arena",
        primary_href="/rebirth",
    )
    payload.update(
        {
            "simulation": simulation,
            "notes": [
                "O bot defensivo prioriza vitórias protegidas e linhas de absorção.",
                "O bot agressivo força ataque alto e pressão rápida.",
                "O bot oportunista busca viradas por habilidade, finalizações e janelas de pressão.",
                "A simulação é determinística, limitada e relata impacto por carta e habilidade.",
                "O simulador do jogador evolui duplicatas disponíveis antes de escolher uma linha de clash.",
            ],
        }
    )
    return payload


def release_payload():
    payload = page_payload(
        "release",
        "Higiene da Versão Candidata",
        "O controle final de deploy, cache offline, testes e contenção do legado do Rebirth.",
        primary_label="Saúde",
        primary_href="/health",
    )
    payload.update(
        {
            "checks": deepcopy(RELEASE_CHECKS),
            "commands": [
                "python3 -m py_compile app.py services/rebirth_engine.py services/rebirth_cards.py services/rebirth_bot.py services/rebirth_state.py services/rebirth_match_store.py services/rebirth_product.py services/rebirth_persistence.py services/rebirth_balance.py",
                "python3 -m pytest -q",
                "python3 tools/rebirth_balance_report.py --matches 120 --output docs/REBIRTH_BALANCE_REPORT.md",
                "node --check static/js/rebirth.js",
                "node --check static/js/service-worker.js",
                "node --check static/js/pwa.js",
                "node --check static/js/rebirth_product.js",
            ],
        }
    )
    return payload
