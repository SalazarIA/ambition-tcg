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
                    const error = body && body.error ? body.error.message : "Request failed.";
                    throw new Error(error);
                }
                return body;
            });
        });
    }

    function getJson(url) {
        return fetch(url).then(function (response) {
            return response.json().then(function (body) {
                if (!response.ok || !body.ok) {
                    const error = body && body.error ? body.error.message : "Request failed.";
                    throw new Error(error);
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

    function cardMarkup(card) {
        return [
            '<article class="rb-product-card rb-product-card-compact">',
            '<img src="' + escapeHtml(card.art) + '" alt="' + escapeHtml(card.name) + ' art">',
            "<div>",
            "<span>Tier " + escapeHtml(card.tier) + " - " + escapeHtml(card.element) + "</span>",
            "<h2>" + escapeHtml(card.name) + "</h2>",
            "<p>" + escapeHtml(card.role) + "</p>",
            "<strong>" + escapeHtml(card.attack) + " ATK / " + escapeHtml(card.guard) + " GRD</strong>",
            "</div>",
            "</article>"
        ].join("");
    }

    function bindBooster() {
        const button = document.querySelector("[data-rebirth-booster]");
        const result = document.getElementById("rebirth-booster-result");
        if (!button || !result || !endpoints.booster) {
            return;
        }

        button.addEventListener("click", function () {
            button.disabled = true;
            result.textContent = "Opening pack...";
            postJson(endpoints.booster, { seed: "booster-" + Date.now() })
                .then(function (payload) {
                    const booster = payload.booster;
                    const cards = booster.cards.map(cardMarkup).join("");
                    result.innerHTML = [
                        '<div class="rb-booster-summary">',
                        "<strong>" + escapeHtml(booster.summary.elevated_slot) + "</strong>",
                        "<span>" + escapeHtml(booster.summary.count) + " cards persisted</span>",
                        "</div>",
                        '<div class="rb-product-card-grid rb-product-card-grid-result">',
                        cards,
                        "</div>"
                    ].join("");
                })
                .catch(function (error) {
                    result.textContent = error.message;
                })
                .finally(function () {
                    button.disabled = false;
                });
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
        const maxSize = Number(form.getAttribute("data-loadout-size") || 8);
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
                    "<article><span>Selected</span><strong>" + escapeHtml(total) + "/" + escapeHtml(maxSize) + "</strong></article>",
                    "<article><span>Attack</span><strong>" + escapeHtml(attack) + "</strong></article>",
                    "<article><span>Guard</span><strong>" + escapeHtml(guard) + "</strong></article>",
                    "<article><span>Pairs</span><strong>" + escapeHtml(duplicatePairs(ids)) + "</strong></article>"
                ].join("");
                summary.classList.toggle("is-invalid", total !== maxSize);
            }
            button.disabled = total !== maxSize;
            if (!updateOptions.preserveResult) {
                result.textContent = total === maxSize ? "Loadout ready to save." : "Select exactly " + maxSize + " cards to save.";
            }
        }

        function save() {
            const cardIds = selectedIds();
            if (cardIds.length !== maxSize) {
                update();
                return;
            }
            button.disabled = true;
            result.textContent = "Saving loadout...";
            postJson(endpoints.loadout, { card_ids: cardIds })
                .then(function (payload) {
                    const saved = payload.loadout.summary;
                    result.innerHTML = [
                        "<strong>Loadout saved.</strong> ",
                        escapeHtml(saved.size) + " cards, ",
                        escapeHtml(saved.attack_total) + " total attack, ",
                        escapeHtml(saved.guard_total) + " total guard, ",
                        escapeHtml(saved.duplicate_pairs) + " duplicate pair."
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
                authResult.textContent = "Working...";
            }
            postJson(endpoint, formPayload(form))
                .then(function (payload) {
                    if (payload.csrf) {
                        window.REBIRTH_CSRF = payload.csrf;
                    }
                    if (authResult) {
                        authResult.textContent = "Signed in as " + payload.account.user.username + ".";
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
            result.textContent = "Updating password...";
            postJson(endpoints.changePassword, formPayload(form))
                .then(function (payload) {
                    result.textContent = payload.message || "Password updated.";
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
            result.textContent = "Claiming...";
            postJson(endpoints.claimDaily, {})
                .then(function (payload) {
                    result.textContent = "Claimed " + payload.claim.xp + " XP.";
                    button.textContent = "Claimed";
                    button.dataset.dailyState = "claimed";
                    button.disabled = true;
                })
                .catch(function (error) {
                    result.textContent = error.message;
                    if (/already claimed/i.test(error.message)) {
                        button.textContent = "Claimed";
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
            result.textContent = "Saving tutorial...";
            postJson(endpoints.completeTutorial, { step: 4 })
                .then(function (payload) {
                    const progress = payload.tutorial.progression;
                    result.textContent = "Tutorial complete. Level " + progress.level + ", " + progress.xp + " XP.";
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
                        ? row.matches + " matches / " + row.average_turns + " avg turns"
                        : row.plays + " plays / " + row.avg_damage + " avg damage";
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
                        "<article><span>Player</span><strong>" + escapeHtml(summary.player_win_rate) + "</strong></article>",
                        "<article><span>Bot</span><strong>" + escapeHtml(summary.bot_win_rate) + "</strong></article>",
                        "<article><span>Avg Turns</span><strong>" + escapeHtml(summary.average_turns) + "</strong></article>",
                        "<article><span>Matches</span><strong>" + escapeHtml(payload.balance.matches) + "</strong></article>"
                    ].join("");
                    if (details) {
                        details.innerHTML = [
                            labSection("Bot Profiles", payload.balance.profile_results || [], "name"),
                            labSection("Card Impact", payload.balance.card_stats || [], "name"),
                            labSection("Ability Impact", payload.balance.ability_stats || [], "name")
                        ].join("");
                    }
                    if (title) {
                        title.textContent = payload.balance.matches + " Matches";
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
                result.textContent = "Exporting...";
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
                const confirmed = window.confirm("Reset this Rebirth account back to starter state?");
                if (!confirmed) {
                    return;
                }
                resetButton.disabled = true;
                result.textContent = "Resetting...";
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

    document.addEventListener("DOMContentLoaded", function () {
        bindAuth();
        bindLogout();
        bindPasswordChange();
        bindBooster();
        bindLoadout();
        bindDailyReward();
        bindTutorial();
        bindBalance();
        bindSupport();
    });
}());
