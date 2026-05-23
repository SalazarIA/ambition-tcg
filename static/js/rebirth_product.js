(function () {
    "use strict";

    const endpoints = window.REBIRTH_PRODUCT_ENDPOINTS || {};

    function escapeHtml(value) {
        return String(value == null ? "" : value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function numberValue(value, fallback) {
        const parsed = Number(value);
        return Number.isFinite(parsed) ? parsed : Number(fallback || 0);
    }

    function clamp(value, min, max) {
        return Math.max(min, Math.min(max, value));
    }

    function levelProgress(profile) {
        const level = Math.max(1, numberValue(profile && profile.level, 1));
        const xp = Math.max(0, numberValue(profile && profile.xp, 0));
        const next = Math.max(1, numberValue(profile && profile.next_level_xp, level * 500));
        const floor = Math.max(0, (level - 1) * 500);
        const span = Math.max(1, next - floor);
        return {
            level: level,
            xp: xp,
            next: next,
            floor: floor,
            percent: Math.round(clamp(((xp - floor) / span) * 100, 0, 100))
        };
    }

    function postJson(url, payload) {
        return fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Rebirth-CSRF": window.REBIRTH_CSRF || ""
            },
            credentials: "same-origin",
            body: JSON.stringify(payload || {})
        }).then(function (response) {
            return response.json().then(function (body) {
                if (!response.ok || !body.ok) {
                    const serverError = body && body.error ? body.error : {};
                    const error = new Error(serverError.message || "A requisição falhou.");
                    error.code = serverError.code || "rebirth_error";
                    throw error;
                }
                return body;
            });
        });
    }

    function initiateMobilePurchase(productId) {
        const capacitor = window.Capacitor || null;
        const nativePlatform = capacitor && typeof capacitor.getPlatform === "function"
            ? capacitor.getPlatform()
            : "web";
        const platform = nativePlatform === "ios" ? "ios" : "google_play";
        const receipt = [
            "simulated",
            nativePlatform,
            String(productId || "coins_100"),
            Date.now(),
            Math.random().toString(16).slice(2)
        ].join("-");

        if (capacitor && capacitor.Plugins && capacitor.Plugins.Haptics && typeof capacitor.Plugins.Haptics.impact === "function") {
            capacitor.Plugins.Haptics.impact({ style: "medium" }).catch(function () {});
        }

        return postJson(endpoints.verifyReceipt || "/api/rebirth/shop/verify-receipt", {
            platform: platform,
            product_id: productId || "coins_100",
            receipt: receipt
        }).then(function (payload) {
            if (payload.wallet && window.RebirthGlobalAuth && typeof window.RebirthGlobalAuth.applyWallet === "function") {
                window.RebirthGlobalAuth.applyWallet(payload.wallet);
            }
            return payload;
        });
    }

    function getJson(url) {
        return fetch(url, { credentials: "same-origin" }).then(function (response) {
            return response.json().then(function (body) {
                if (!response.ok || !body.ok) {
                    const serverError = body && body.error ? body.error : {};
                    const error = new Error(serverError.message || "A requisição falhou.");
                    error.code = serverError.code || "rebirth_error";
                    throw error;
                }
                return body;
            });
        });
    }

    function formPayload(form) {
        const payload = {};
        Array.from(form.elements).forEach(function (element) {
            if (!element.name) {
                return;
            }
            payload[element.name] = element.value;
        });
        return payload;
    }

    const unsplashFallbacks = {
        fire: "https://images.unsplash.com/photo-1517976487492-5750f3195933?auto=format&fit=crop&w=900&q=80",
        water: "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=900&q=80",
        earth: "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=900&q=80",
        shadow: "https://images.unsplash.com/photo-1519608487953-e999c86e7455?auto=format&fit=crop&w=900&q=80",
        arcane: "https://images.unsplash.com/photo-1534796636912-3b95b3ab5986?auto=format&fit=crop&w=900&q=80",
        hidden: "https://images.unsplash.com/photo-1518709268805-4e9042af2176?auto=format&fit=crop&w=900&q=80",
        default: "https://images.unsplash.com/photo-1518709268805-4e9042af2176?auto=format&fit=crop&w=900&q=80"
    };

    function slug(value) {
        return String(value || "default").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "default";
    }

    function fallbackArt(card) {
        const element = slug(card && card.element);
        return unsplashFallbacks[element] || unsplashFallbacks.default;
    }

    function cardArtSource(card) {
        if (!card || card.art_status === "default_png_path") {
            return fallbackArt(card);
        }
        if (!card.art) {
            return fallbackArt(card);
        }
        return String(card.art).charAt(0) === "/" ? card.art : "/" + card.art;
    }

    function bindImageFallbacks(root) {
        Array.from((root || document).querySelectorAll("img[data-rebirth-unsplash-fallback]")).forEach(function (image) {
            image.addEventListener("error", function () {
                if (image.dataset.fallbackApplied === "true") return;
                image.dataset.fallbackApplied = "true";
                image.src = image.getAttribute("data-rebirth-unsplash-fallback");
            });
        });
    }

    function cardMarkup(card, index) {
        const rarity = slug(card.rarity || "common");
        const element = slug(card.element || "default");
        const source = cardArtSource(card);
        const rarityLabel = String(card.rarity || "").toUpperCase() === "UNCOMMON" ? "Incomum" : "Comum";
        return [
            '<article class="rb-product-card rb-product-card-compact rb-booster-card is-' + escapeHtml(rarity) + ' is-element-' + escapeHtml(element) + '">',
            '<img src="' + escapeHtml(source) + '" data-rebirth-unsplash-fallback="' + escapeHtml(fallbackArt(card)) + '" alt="Arte de ' + escapeHtml(card.name) + '">',
            "<div>",
            "<span>Slot " + escapeHtml(index + 1) + " - " + escapeHtml(rarityLabel) + " - " + escapeHtml(card.element) + "</span>",
            "<h2>" + escapeHtml(card.name) + "</h2>",
            "<p>" + escapeHtml(card.role) + "</p>",
            "<strong>" + escapeHtml(card.attack) + " ATK / " + escapeHtml(card.guard) + " GRD</strong>",
            "</div>",
            "</article>"
        ].join("");
    }

    function marketOfferMarkup(offer) {
        const card = offer.card || {};
        const currency = String(offer.currency_type || "COINZ").toUpperCase();
        const currencyLabel = currency === "COINZ" ? "Gemas" : "Ouro";
        const source = cardArtSource(card);
        return [
            '<article class="rb-product-card rb-market-offer is-currency-' + escapeHtml(slug(currency)) + '" data-market-offer-id="' + escapeHtml(offer.id) + '">',
            '<div class="rb-market-art">',
            '<img src="' + escapeHtml(source) + '" data-rebirth-unsplash-fallback="' + escapeHtml(fallbackArt(card)) + '" alt="Arte de ' + escapeHtml(card.name || offer.card_id) + '">',
            '<span>' + escapeHtml(currencyLabel) + " P2P</span>",
            "</div>",
            '<div class="rb-market-copy">',
            "<span>Oferta de " + escapeHtml(offer.seller_name || "Jogador") + "</span>",
            "<h2>" + escapeHtml(card.name || offer.card_id) + "</h2>",
            "<p>" + escapeHtml(card.role || "Carta do mercado") + "</p>",
            '<div class="rb-market-price"><span>Preco</span><strong>' + escapeHtml(offer.price) + " " + escapeHtml(currencyLabel) + "</strong></div>",
            '<button class="rb-button-secondary rb-secondary" type="button" data-rebirth-market-buy="' + escapeHtml(offer.id) + '">Comprar</button>',
            "</div>",
            "</article>"
        ].join("");
    }

    function ledgerEntryMarkup(entry) {
        const delta = numberValue(entry.delta, 0);
        const positive = delta >= 0;
        return [
            '<article class="rb-ledger-entry ' + (positive ? "is-credit" : "is-debit") + '">',
            "<span>" + escapeHtml(entry.resource || "extrato") + "</span>",
            "<strong>" + (positive ? "+" : "") + escapeHtml(delta) + "</strong>",
            "<p>" + escapeHtml(entry.reason || "movimento") + "</p>",
            "<small>" + escapeHtml(entry.reference_type || "sistema") + " " + escapeHtml(entry.reference_id || "") + "</small>",
            "</article>"
        ].join("");
    }

    function updateGlobalProgress(profile) {
        const progress = levelProgress(profile);
        const xpBox = document.querySelector(".rb-global-xp");
        if (!xpBox) return;
        const label = xpBox.querySelector("span");
        const value = xpBox.querySelector("strong");
        const fill = xpBox.querySelector("i b");
        if (label) label.textContent = "Nível " + progress.level;
        if (value) value.textContent = progress.xp + "/" + progress.next + " XP";
        if (fill) fill.style.width = progress.percent + "%";
    }

    function renderProgressDashboard(root, profile, ledger) {
        if (!root || !profile) return;
        const progress = levelProgress(profile);
        const level = root.querySelector("[data-rebirth-level]");
        const xp = root.querySelector("[data-rebirth-xp]");
        const next = root.querySelector("[data-rebirth-next-xp]");
        const percent = root.querySelector("[data-rebirth-xp-percent]");
        const fill = root.querySelector("[data-rebirth-xp-fill]");
        const wins = root.querySelector("[data-rebirth-wins]");
        const clashes = root.querySelector("[data-rebirth-clashes]");
        const boosters = root.querySelector("[data-rebirth-boosters]");
        const ledgerList = root.querySelector("[data-rebirth-ledger-list]");
        if (level) level.textContent = String(progress.level);
        if (xp) xp.textContent = String(progress.xp);
        if (next) next.textContent = String(progress.next);
        if (percent) percent.textContent = progress.percent + "%";
        if (fill) fill.style.width = progress.percent + "%";
        if (wins) wins.textContent = String(numberValue(profile.wins, 0));
        if (clashes) clashes.textContent = String(numberValue(profile.clashes, 0));
        if (boosters) boosters.textContent = String(numberValue(profile.boosters_opened, 0));
        if (ledgerList) {
            if (ledger && ledger.length) {
                ledgerList.innerHTML = ledger.slice(0, 6).map(ledgerEntryMarkup).join("");
            } else {
                ledgerList.innerHTML = '<article class="rb-ledger-entry"><span>Extrato</span><strong>0</strong><p>Nenhum movimento persistido ainda.</p><small>Jogue, compre ou abra booster para registrar.</small></article>';
            }
        }
        updateGlobalProgress(profile);
    }

    function bindBooster() {
        const buttons = document.querySelectorAll("[data-rebirth-booster]");
        const result = document.getElementById("rebirth-booster-result");
        if (!buttons.length || !result || !endpoints.booster) {
            return;
        }

        Array.from(buttons).forEach(function (button) {
            button.addEventListener("click", function () {
                button.disabled = true;
                // v55 Fase 3 — quebra teatral do selo de cera ANTES da
                // requisição. A classe é removida após 600ms (cobre a
                // animação rb-seal-shatter-left de 420ms + folga). Se o
                // request falha, o botão volta a clicável mas o selo
                // permanece quebrado visualmente (é o feedback de "abriu").
                const pack = button.closest(".rb-shop-pack");
                if (pack && !pack.classList.contains("is-seal-broken")) {
                    pack.classList.add("is-seal-broken");
                }
                result.textContent = "Abrindo booster...";
                postJson(endpoints.booster, { seed: "booster-" + Date.now() })
                    .then(function (payload) {
                        const booster = payload.booster;
                        const cards = booster.cards.map(cardMarkup).join("");
                        const raritySlots = booster.summary.rarity_slots || [];
                        result.innerHTML = [
                            '<div class="rb-booster-summary">',
                            "<strong>" + escapeHtml(booster.summary.elevated_slot) + "</strong>",
                            "<span>" + escapeHtml(booster.summary.count) + " cartas reveladas</span>",
                            "</div>",
                            raritySlots.length ? '<div class="rb-booster-rarity-line">' + raritySlots.map(function (slot) {
                                return "<span>" + escapeHtml(slot.replace("_", " ")) + "</span>";
                            }).join("") + "</div>" : "",
                            '<div class="rb-product-card-grid rb-product-card-grid-result">',
                            cards,
                            "</div>"
                        ].join("");
                        bindImageFallbacks(result);
                    })
                    .catch(function (error) {
                        result.textContent = error.message;
                        if (error.code === "auth_required" && window.RebirthGlobalAuth) {
                            window.RebirthGlobalAuth.open("Entre para guardar as cartas abertas no booster.");
                        }
                    })
                    .finally(function () {
                        button.disabled = false;
                    });
            });
        });
    }

    function bindMarket() {
        const list = document.querySelector("[data-rebirth-market-offers]");
        const result = document.querySelector("[data-rebirth-market-result]");
        if (!list || !endpoints.marketOffers) {
            return;
        }

        function renderOffers(offers) {
            if (!offers || !offers.length) {
                list.innerHTML = '<article class="rb-product-panel"><span>Mercado</span><h2>Nenhuma oferta ativa</h2><p>Ofertas ativas de jogadores aparecerão aqui.</p></article>';
                return;
            }
            list.innerHTML = offers.map(marketOfferMarkup).join("");
        }

        function refresh() {
            getJson(endpoints.marketOffers)
                .then(function (payload) {
                    renderOffers((payload.market && payload.market.offers) || []);
                    bindImageFallbacks(list);
                })
                .catch(function (error) {
                    if (result) result.textContent = error.message;
                });
        }

        list.addEventListener("click", function (event) {
            const button = event.target.closest("[data-rebirth-market-buy]");
            if (!button || !endpoints.marketBuy) {
                return;
            }
            button.disabled = true;
            if (result) result.textContent = "Comprando oferta do mercado...";
            postJson(endpoints.marketBuy, { offer_id: button.getAttribute("data-rebirth-market-buy") })
                .then(function (payload) {
                    const purchase = payload.market.purchase;
                    if (result) {
                        const wallet = payload.wallet || {};
                        const currency = purchase.currency_type === "COINZ" ? "Gemas" : "Ouro";
                        result.textContent = "Comprado: " + purchase.offer.card.name + " por " + purchase.price + " " + currency + ". Carteira: Ouro " + (wallet.GOLD == null ? "0" : wallet.GOLD) + " / Gemas " + (wallet.COINZ == null ? "0" : wallet.COINZ) + ".";
                    }
                    if (payload.wallet && window.RebirthGlobalAuth && typeof window.RebirthGlobalAuth.applyWallet === "function") {
                        window.RebirthGlobalAuth.applyWallet(payload.wallet);
                    }
                    renderOffers(payload.market.offers || []);
                    bindImageFallbacks(list);
                })
                .catch(function (error) {
                    if (result) result.textContent = error.message;
                    if (error.code === "auth_required" && window.RebirthGlobalAuth) {
                        window.RebirthGlobalAuth.open("Entre para comprar no Mercado de Jogadores.");
                    }
                })
                .finally(function () {
                    button.disabled = false;
                });
        });

        refresh();
    }

    function bindProgressionDashboard() {
        const roots = Array.from(document.querySelectorAll("[data-rebirth-progression-dashboard]"));
        if (!roots.length || !endpoints.progression) {
            return;
        }
        const result = document.querySelector("[data-rebirth-progression-result]");
        const progressionPromise = getJson(endpoints.progression).then(function (payload) {
            return payload.progression && payload.progression.profile ? payload.progression.profile : null;
        });
        const ledgerPromise = endpoints.ledger
            ? getJson(endpoints.ledger + "?limit=6").then(function (payload) {
                return payload.ledger || [];
            }).catch(function (error) {
                if (error.code === "auth_required") {
                    return [];
                }
                throw error;
            })
            : Promise.resolve([]);
        Promise.all([progressionPromise, ledgerPromise])
            .then(function (values) {
                roots.forEach(function (root) {
                    renderProgressDashboard(root, values[0], values[1]);
                });
            })
            .catch(function (error) {
                if (result) result.textContent = error.message;
            });
    }

    function bindLoadout() {
        const form = document.querySelector("[data-rebirth-loadout-form]");
        const button = document.querySelector("[data-rebirth-loadout-submit]");
        const result = document.querySelector("[data-rebirth-loadout-result]");
        const summary = document.querySelector("[data-rebirth-loadout-summary]");
        const hidden = document.querySelector("[data-rebirth-loadout-hidden]");
        if (!form || !button || !result || !endpoints.loadout) {
            return;
        }
        const maxSize = Number(form.getAttribute("data-loadout-size") || 30);
        const options = Array.from(form.querySelectorAll("[data-rebirth-card-option]"));

        function optionCount(option) {
            return Math.max(0, Number(option.getAttribute("data-selected-count") || 0));
        }

        function selectedIds() {
            const ids = [];
            options.forEach(function (option) {
                const cardId = option.getAttribute("data-card-id");
                const count = optionCount(option);
                for (let index = 0; index < count; index += 1) {
                    ids.push(cardId);
                }
            });
            return ids;
        }

        function selectedTotal() {
            return selectedIds().length;
        }

        function duplicatePairs(ids) {
            const counts = {};
            ids.forEach(function (id) {
                counts[id] = (counts[id] || 0) + 1;
            });
            return Object.keys(counts).filter(function (id) {
                return counts[id] >= 2;
            }).length;
        }

        function writeHidden(ids) {
            if (!hidden) return;
            hidden.innerHTML = ids.map(function (id) {
                return '<input type="hidden" name="card_ids" value="' + escapeHtml(id) + '">';
            }).join("");
        }

        function update(updateOptions) {
            updateOptions = updateOptions || {};
            const ids = selectedIds();
            const total = ids.length;
            let attack = 0;
            let guard = 0;
            options.forEach(function (option) {
                const count = optionCount(option);
                const owned = Number(option.getAttribute("data-owned-count") || 0);
                attack += count * Number(option.getAttribute("data-attack") || 0);
                guard += count * Number(option.getAttribute("data-guard") || 0);
                const label = option.querySelector("[data-loadout-count]");
                const increment = option.querySelector("[data-loadout-increment]");
                const decrement = option.querySelector("[data-loadout-decrement]");
                option.classList.toggle("is-selected", count > 0);
                option.classList.toggle("is-maxed", count >= owned);
                if (label) label.textContent = String(count);
                if (increment) increment.disabled = count >= owned || total >= maxSize;
                if (decrement) decrement.disabled = count <= 0;
            });
            writeHidden(ids);
            if (summary) {
                summary.innerHTML = [
                    "<article><span>Selecionadas</span><strong>" + escapeHtml(total) + "/" + escapeHtml(maxSize) + "</strong></article>",
                    "<article><span>Ataque</span><strong>" + escapeHtml(attack) + "</strong></article>",
                    "<article><span>Guarda</span><strong>" + escapeHtml(guard) + "</strong></article>",
                    "<article><span>Pares</span><strong>" + escapeHtml(duplicatePairs(ids)) + "</strong></article>"
                ].join("");
                summary.classList.toggle("is-invalid", total !== maxSize);
            }
            button.disabled = total !== maxSize;
            if (!updateOptions.preserveResult) {
                result.textContent = total === maxSize
                    ? "Baralho pronto para salvar."
                    : "Selecione exatamente " + maxSize + " cartas para salvar (atual: " + total + ").";
            }
        }

        function save() {
            const cardIds = selectedIds();
            if (cardIds.length !== maxSize) {
                update();
                return;
            }
            button.disabled = true;
            result.textContent = "Salvando baralho...";
            postJson(endpoints.loadout, { card_ids: cardIds })
                .then(function (payload) {
                    const saved = payload.loadout.summary;
                    result.innerHTML = [
                        "<strong>Baralho salvo.</strong> ",
                        escapeHtml(saved.size) + " cartas, ",
                        escapeHtml(saved.attack_total) + " de ataque, ",
                        escapeHtml(saved.guard_total) + " de guarda, ",
                        escapeHtml(saved.duplicate_pairs) + " par(es) duplicado(s)."
                    ].join("");
                })
                .catch(function (error) {
                    result.textContent = error.message;
                })
                .finally(function () {
                    update({ preserveResult: true });
                });
        }

        options.forEach(function (option) {
            option.addEventListener("click", function (event) {
                const increment = event.target.closest("[data-loadout-increment]");
                const decrement = event.target.closest("[data-loadout-decrement]");
                if (!increment && !decrement) return;
                const owned = Number(option.getAttribute("data-owned-count") || 0);
                const count = optionCount(option);
                if (increment && count < owned && selectedTotal() < maxSize) {
                    option.setAttribute("data-selected-count", String(count + 1));
                }
                if (decrement && count > 0) {
                    option.setAttribute("data-selected-count", String(count - 1));
                }
                update();
            });
        });

        button.addEventListener("click", save);
        form.addEventListener("submit", function (event) {
            event.preventDefault();
            save();
        });
        update();
    }

    function bindAuth() {
        const authResult = document.querySelector("[data-rebirth-auth-result]");
        const registerForm = document.querySelector("[data-rebirth-register]");
        const loginForm = document.querySelector("[data-rebirth-login]");

        function submitAuth(event, endpoint, redirectTo) {
            event.preventDefault();
            const form = event.currentTarget;
            const button = form.querySelector("button");
            if (button) {
                button.disabled = true;
            }
            if (authResult) {
                authResult.textContent = "Processando...";
            }
            postJson(endpoint, formPayload(form))
                .then(function (payload) {
                    if (payload.csrf) {
                        window.REBIRTH_CSRF = payload.csrf;
                    }
                    if (authResult) {
                        authResult.textContent = "Conectado como " + payload.account.user.username + ".";
                    }
                    window.location.href = redirectTo || "/rebirth";
                })
                .catch(function (error) {
                    if (authResult) {
                        authResult.textContent = error.message;
                    }
                })
                .finally(function () {
                    if (button) {
                        button.disabled = false;
                    }
                });
        }

        if (registerForm && endpoints.register) {
            registerForm.addEventListener("submit", function (event) {
                submitAuth(event, endpoints.register, "/rebirth?firstRun=1");
            });
        }
        if (loginForm && endpoints.login) {
            loginForm.addEventListener("submit", function (event) {
                submitAuth(event, endpoints.login, "/rebirth");
            });
        }
    }

    function bindLogout() {
        const buttons = document.querySelectorAll("[data-rebirth-logout]");
        if (!buttons.length || !endpoints.logout) {
            return;
        }
        Array.from(buttons).forEach(function (button) {
            button.addEventListener("click", function () {
                button.disabled = true;
                postJson(endpoints.logout, {})
                    .then(function () {
                        window.location.href = "/rebirth/account";
                    })
                    .catch(function () {
                        button.disabled = false;
                    });
            });
        });
    }

    function bindPasswordChange() {
        const form = document.querySelector("[data-rebirth-change-password]");
        const result = document.querySelector("[data-rebirth-password-result]");
        if (!form || !result || !endpoints.changePassword) {
            return;
        }
        form.addEventListener("submit", function (event) {
            event.preventDefault();
            const button = form.querySelector("button");
            if (button) {
                button.disabled = true;
            }
            result.textContent = "Atualizando senha...";
            postJson(endpoints.changePassword, formPayload(form))
                .then(function (payload) {
                    result.textContent = payload.message || "Senha atualizada.";
                    form.reset();
                })
                .catch(function (error) {
                    result.textContent = error.message;
                })
                .finally(function () {
                    if (button) {
                        button.disabled = false;
                    }
                });
        });
    }

    function bindDailyReward() {
        const button = document.querySelector("[data-rebirth-claim-daily]");
        const result = document.querySelector("[data-rebirth-progression-result]");
        if (!button || !result || !endpoints.claimDaily) {
            return;
        }
        button.addEventListener("click", function () {
            button.disabled = true;
            result.textContent = "Resgatando...";
            postJson(endpoints.claimDaily, {})
                .then(function (payload) {
                    result.textContent = payload.claim.xp + " XP resgatados.";
                    button.textContent = "Resgatado";
                    button.dataset.dailyState = "claimed";
                    button.disabled = true;
                    if (payload.claim && payload.claim.progression) {
                        Array.from(document.querySelectorAll("[data-rebirth-progression-dashboard]")).forEach(function (root) {
                            renderProgressDashboard(root, payload.claim.progression, null);
                        });
                    }
                    bindProgressionDashboard();
                })
                .catch(function (error) {
                    result.textContent = error.message;
                    if (/já foi resgatada|already claimed/i.test(error.message)) {
                        button.textContent = "Resgatado";
                        button.dataset.dailyState = "claimed";
                        button.disabled = true;
                    }
                })
                .finally(function () {
                    if (button.dataset.dailyState !== "claimed") {
                        button.disabled = false;
                    }
                });
        });
    }

    function bindTutorial() {
        const button = document.querySelector("[data-rebirth-tutorial-complete]");
        const result = document.querySelector("[data-rebirth-tutorial-result]");
        if (!button || !result || !endpoints.completeTutorial) {
            return;
        }
        button.addEventListener("click", function () {
            button.disabled = true;
            result.textContent = "Salvando tutorial...";
            postJson(endpoints.completeTutorial, { step: 4 })
                .then(function (payload) {
                    const progress = payload.tutorial.progression;
                    result.textContent = "Tutorial concluído. Nível " + progress.level + ", " + progress.xp + " XP.";
                })
                .catch(function (error) {
                    result.textContent = error.message;
                })
                .finally(function () {
                    button.disabled = false;
                });
        });
    }

    function bindBalance() {
        const button = document.querySelector("[data-rebirth-balance-run]");
        const result = document.querySelector("[data-rebirth-balance-result]");
        const details = document.querySelector("[data-rebirth-balance-details]");
        const title = document.querySelector("[data-rebirth-balance-title]");
        if (!button || !result || !endpoints.balance) {
            return;
        }
        function labSection(title, rows, labelKey) {
            return [
                "<section>",
                "<h3>" + escapeHtml(title) + "</h3>",
                rows.slice(0, 6).map(function (row) {
                    const label = row[labelKey] || row.name || row.card_id || row.ability_key || row.profile_id;
                    const rate = row.player_win_rate != null ? row.player_win_rate : row.win_rate;
                    const detail = row.matches != null
                        ? row.matches + " partidas / " + row.average_turns + " turnos médios"
                        : row.plays + " jogadas / " + row.avg_damage + " dano médio";
                    return "<article><span>" + escapeHtml(label) + "</span><strong>" + escapeHtml(rate) + "</strong><small>" + escapeHtml(detail) + "</small></article>";
                }).join(""),
                "</section>"
            ].join("");
        }

        button.addEventListener("click", function () {
            button.disabled = true;
            getJson(endpoints.balance + "?matches=40")
                .then(function (payload) {
                    const summary = payload.balance.summary;
                    result.innerHTML = [
                        "<article><span>Jogador</span><strong>" + escapeHtml(summary.player_win_rate) + "</strong></article>",
                        "<article><span>Bot</span><strong>" + escapeHtml(summary.bot_win_rate) + "</strong></article>",
                        "<article><span>Turnos Médios</span><strong>" + escapeHtml(summary.average_turns) + "</strong></article>",
                        "<article><span>Partidas</span><strong>" + escapeHtml(payload.balance.matches) + "</strong></article>"
                    ].join("");
                    if (details) {
                        details.innerHTML = [
                            labSection("Perfis do Bot", payload.balance.profile_results || [], "name"),
                            labSection("Impacto das Cartas", payload.balance.card_stats || [], "name"),
                            labSection("Impacto das Habilidades", payload.balance.ability_stats || [], "name")
                        ].join("");
                    }
                    if (title) {
                        title.textContent = payload.balance.matches + " Partidas";
                    }
                })
                .catch(function (error) {
                    result.textContent = error.message;
                })
                .finally(function () {
                    button.disabled = false;
                });
        });
    }

    function bindSupport() {
        const exportButton = document.querySelector("[data-rebirth-export]");
        const resetButton = document.querySelector("[data-rebirth-reset]");
        const result = document.querySelector("[data-rebirth-support-result]");
        if (!result) {
            return;
        }
        function write(payload) {
            result.textContent = JSON.stringify(payload, null, 2);
        }
        if (exportButton && endpoints.supportExport) {
            exportButton.addEventListener("click", function () {
                exportButton.disabled = true;
                result.textContent = "Exportando...";
                getJson(endpoints.supportExport)
                    .then(write)
                    .catch(function (error) {
                        result.textContent = error.message;
                    })
                    .finally(function () {
                        exportButton.disabled = false;
                    });
            });
        }
        if (resetButton && endpoints.supportReset) {
            resetButton.addEventListener("click", function () {
                const confirmed = window.confirm("Reiniciar esta conta Rebirth para o estado inicial?");
                if (!confirmed) {
                    return;
                }
                resetButton.disabled = true;
                result.textContent = "Reiniciando...";
                postJson(endpoints.supportReset, { confirm: "RESET REBIRTH" })
                    .then(write)
                    .catch(function (error) {
                        result.textContent = error.message;
                    })
                    .finally(function () {
                        resetButton.disabled = false;
                    });
            });
        }
    }

    window.initiateMobilePurchase = initiateMobilePurchase;

    document.addEventListener("DOMContentLoaded", function () {
        bindImageFallbacks(document);
        bindPasswordChange();
        bindBooster();
        bindMarket();
        bindProgressionDashboard();
        bindLoadout();
        bindDailyReward();
        bindTutorial();
        bindBalance();
        bindSupport();
    });
}());
