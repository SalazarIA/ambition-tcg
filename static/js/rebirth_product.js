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
            result.textContent = "Opening booster...";
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
        if (!form || !button || !result || !endpoints.loadout) {
            return;
        }

        function validate() {
            const cardIds = Array.from(form.querySelectorAll('input[name="card_ids"]:checked')).map(function (input) {
                return input.value;
            });
            button.disabled = true;
            result.textContent = "Validating loadout...";
            postJson(endpoints.loadout, { card_ids: cardIds })
                .then(function (payload) {
                    const summary = payload.loadout.summary;
                    result.innerHTML = [
                        "<strong>Loadout valid.</strong> ",
                        escapeHtml(summary.size) + " cards, ",
                        escapeHtml(summary.attack_total) + " total attack, ",
                        escapeHtml(summary.guard_total) + " total guard, ",
                        escapeHtml(summary.duplicate_pairs) + " duplicate pair."
                    ].join("");
                })
                .catch(function (error) {
                    result.textContent = error.message;
                })
                .finally(function () {
                    button.disabled = false;
                });
        }

        button.addEventListener("click", validate);
        form.addEventListener("submit", function (event) {
            event.preventDefault();
            validate();
        });
    }

    function bindAuth() {
        const authResult = document.querySelector("[data-rebirth-auth-result]");
        const registerForm = document.querySelector("[data-rebirth-register]");
        const loginForm = document.querySelector("[data-rebirth-login]");

        function submitAuth(event, endpoint) {
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
                    window.location.reload();
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
                submitAuth(event, endpoints.register);
            });
        }
        if (loginForm && endpoints.login) {
            loginForm.addEventListener("submit", function (event) {
                submitAuth(event, endpoints.login);
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
                })
                .catch(function (error) {
                    result.textContent = error.message;
                })
                .finally(function () {
                    button.disabled = false;
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
        if (!button || !result || !endpoints.balance) {
            return;
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
                })
                .catch(function (error) {
                    result.textContent = error.message;
                })
                .finally(function () {
                    button.disabled = false;
                });
        });
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
    });
}());
