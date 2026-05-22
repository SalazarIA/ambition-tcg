(function () {
    "use strict";

    const endpoints = Object.assign(
        {},
        window.REBIRTH_PRODUCT_ENDPOINTS || {},
        window.REBIRTH_ENDPOINTS || {},
        window.REBIRTH_AUTH_ENDPOINTS || {}
    );

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
                    const error = new Error(serverError.message || "Request failed.");
                    error.code = serverError.code || "rebirth_error";
                    throw error;
                }
                return body;
            });
        });
    }

    function getJson(url) {
        return fetch(url, { credentials: "same-origin" }).then(function (response) {
            return response.json().then(function (body) {
                if (!response.ok || !body.ok) {
                    const serverError = body && body.error ? body.error : {};
                    const error = new Error(serverError.message || "Request failed.");
                    error.code = serverError.code || "rebirth_error";
                    throw error;
                }
                return body;
            });
        });
    }

    function modal() {
        return document.querySelector("[data-rebirth-auth-modal]");
    }

    function authResult() {
        return document.querySelector("[data-rebirth-auth-result]");
    }

    function openAuth(message) {
        const host = modal();
        if (!host) return;
        host.hidden = false;
        document.documentElement.classList.add("rb-auth-is-open");
        const result = authResult();
        if (result && message) {
            result.textContent = message;
        }
        const firstInput = host.querySelector("input");
        if (firstInput) {
            window.setTimeout(function () {
                firstInput.focus();
            }, 40);
        }
    }

    function closeAuth() {
        const host = modal();
        if (!host) return;
        host.hidden = true;
        document.documentElement.classList.remove("rb-auth-is-open");
    }

    function formPayload(form) {
        const payload = {};
        Array.from(form.elements).forEach(function (element) {
            if (element.name) {
                payload[element.name] = element.value;
            }
        });
        return payload;
    }

    function bindAuthTriggers() {
        document.addEventListener("click", function (event) {
            const openButton = event.target.closest("[data-rebirth-auth-open]");
            if (openButton) {
                event.preventDefault();
                openAuth(openButton.getAttribute("data-auth-message") || "Entre para guardar sua jornada Rebirth.");
                return;
            }
            if (event.target.closest("[data-rebirth-auth-close]")) {
                event.preventDefault();
                closeAuth();
            }
        });
        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape") {
                closeAuth();
            }
        });
    }

    function bindAuthForms() {
        const forms = document.querySelectorAll("[data-rebirth-register], [data-rebirth-login]");
        const result = authResult();
        Array.from(forms).forEach(function (form) {
            const isRegister = form.hasAttribute("data-rebirth-register");
            const endpoint = isRegister ? endpoints.register : endpoints.login;
            if (!endpoint) return;
            form.addEventListener("submit", function (event) {
                event.preventDefault();
                const button = form.querySelector("button");
                if (button) button.disabled = true;
                if (result) result.textContent = isRegister ? "Criando conta..." : "Entrando...";
                postJson(endpoint, formPayload(form))
                    .then(function (payload) {
                        if (payload.csrf) {
                            window.REBIRTH_CSRF = payload.csrf;
                        }
                        if (result && payload.account && payload.account.user) {
                            result.textContent = "Bem-vindo, " + payload.account.user.username + ".";
                        }
                        window.location.href = form.getAttribute("data-auth-redirect") || "/rebirth";
                    })
                    .catch(function (error) {
                        if (result) result.textContent = error.message;
                    })
                    .finally(function () {
                        if (button) button.disabled = false;
                    });
            });
        });
    }

    function bindLogout() {
        const buttons = document.querySelectorAll("[data-rebirth-logout]");
        if (!buttons.length || !endpoints.logout) return;
        Array.from(buttons).forEach(function (button) {
            button.addEventListener("click", function () {
                button.disabled = true;
                postJson(endpoints.logout, {})
                    .then(function () {
                        window.location.href = "/";
                    })
                    .catch(function () {
                        button.disabled = false;
                    });
            });
        });
    }

    function applyWallet(wallet) {
        if (!wallet) return;
        ["GOLD", "COINZ"].forEach(function (currency) {
            const value = wallet[currency];
            Array.from(document.querySelectorAll('[data-rebirth-wallet-value="' + currency + '"]')).forEach(function (node) {
                node.textContent = String(value == null ? 0 : value);
            });
        });
    }

    function refreshWallet() {
        if (!endpoints.wallet) {
            return Promise.resolve(null);
        }
        return getJson(endpoints.wallet)
            .then(function (payload) {
                applyWallet(payload.wallet);
                return payload.wallet;
            })
            .catch(function (error) {
                if (error.code !== "auth_required") {
                    throw error;
                }
                return null;
            });
    }

    window.RebirthGlobalAuth = {
        open: openAuth,
        close: closeAuth,
        applyWallet: applyWallet,
        refreshWallet: refreshWallet
    };

    document.addEventListener("DOMContentLoaded", function () {
        bindAuthTriggers();
        bindAuthForms();
        bindLogout();
        refreshWallet().catch(function () {});
    });
}());
