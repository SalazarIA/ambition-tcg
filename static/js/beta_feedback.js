/* Ambitionz public beta feedback widget. Defensive, local, no external service. */
(function () {
    if (window.__ambitionzBetaFeedbackV1) return;
    window.__ambitionzBetaFeedbackV1 = true;

    var eligiblePaths = {
        "/arena": true,
        "/training": true,
        "/profile": true,
        "/progression": true,
        "/roadmap": true
    };

    function shouldMount() {
        return eligiblePaths[window.location.pathname || ""] || Boolean(document.querySelector("[data-beta-feedback-widget]"));
    }

    function setStatus(panel, text, kind) {
        var status = panel.querySelector("[data-beta-feedback-status]");
        if (!status) return;
        status.textContent = text || "";
        status.dataset.status = kind || "";
    }

    function closePanel(panel) {
        panel.hidden = true;
        document.body.classList.remove("az-beta-feedback-open-v1");
    }

    function openPanel(panel) {
        panel.hidden = false;
        document.body.classList.add("az-beta-feedback-open-v1");
        var textarea = panel.querySelector("textarea");
        if (textarea) textarea.focus();
    }

    function mountWidget() {
        if (!shouldMount() || document.getElementById("az-beta-feedback-widget-v1")) return;

        var wrapper = document.createElement("aside");
        wrapper.id = "az-beta-feedback-widget-v1";
        wrapper.className = "az-beta-feedback-widget-v1";
        wrapper.setAttribute("aria-label", "Beta feedback widget");
        wrapper.innerHTML = [
            '<button type="button" class="az-beta-feedback-trigger-v1" data-beta-feedback-open>Feedback beta</button>',
            '<section class="az-beta-feedback-panel-v1" data-beta-feedback-panel hidden>',
            '  <header>',
            '    <span>Public beta</span>',
            '    <strong>Enviar feedback</strong>',
            '    <button type="button" aria-label="Close feedback" data-beta-feedback-close>&times;</button>',
            '  </header>',
            '  <form data-beta-feedback-form>',
            '    <label>Tipo',
            '      <select name="type">',
            '        <option value="bug">Bug</option>',
            '        <option value="balance">Balanceamento</option>',
            '        <option value="suggestion">Sugestao</option>',
            '        <option value="praise">Elogio</option>',
            '        <option value="other">Outro</option>',
            '      </select>',
            '    </label>',
            '    <label>Mensagem',
            '      <textarea name="message" rows="4" maxlength="2000" required placeholder="Conte o que aconteceu, em qual tela, e o que voce esperava."></textarea>',
            '    </label>',
            '    <div class="az-beta-feedback-actions-v1">',
            '      <button type="submit" class="btn small-btn">Enviar</button>',
            '      <button type="button" class="btn btn-secondary small-btn" data-beta-feedback-close>Cancelar</button>',
            '    </div>',
            '    <p class="az-beta-feedback-status-v1" data-beta-feedback-status aria-live="polite"></p>',
            '  </form>',
            '</section>'
        ].join("");

        document.body.appendChild(wrapper);

        var panel = wrapper.querySelector("[data-beta-feedback-panel]");
        var trigger = wrapper.querySelector("[data-beta-feedback-open]");
        var form = wrapper.querySelector("[data-beta-feedback-form]");

        trigger.addEventListener("click", function () {
            openPanel(panel);
        });

        wrapper.querySelectorAll("[data-beta-feedback-close]").forEach(function (button) {
            button.addEventListener("click", function () {
                closePanel(panel);
            });
        });

        form.addEventListener("submit", function (event) {
            event.preventDefault();

            var submitButton = form.querySelector("button[type='submit']");
            var message = (form.elements.message.value || "").trim();
            var type = form.elements.type.value || "other";

            if (message.length < 8) {
                setStatus(panel, "Escreva um pouco mais para o time conseguir agir.", "error");
                return;
            }

            if (submitButton) submitButton.disabled = true;
            setStatus(panel, "Enviando feedback...", "pending");

            fetch("/api/beta/feedback", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin",
                body: JSON.stringify({
                    type: type,
                    message: message,
                    page: window.location.pathname || "/"
                })
            })
                .then(function (response) {
                    return response.json().catch(function () {
                        return { ok: false, message: "Feedback unavailable right now." };
                    }).then(function (payload) {
                        if (!response.ok || !payload.ok) {
                            throw new Error(payload.message || "Feedback unavailable right now.");
                        }
                        return payload;
                    });
                })
                .then(function () {
                    form.reset();
                    setStatus(panel, "Feedback recebido. Obrigado por testar a beta.", "success");
                    window.setTimeout(function () {
                        closePanel(panel);
                    }, 1000);
                })
                .catch(function (error) {
                    setStatus(panel, error.message || "Nao foi possivel enviar agora.", "error");
                })
                .finally(function () {
                    if (submitButton) submitButton.disabled = false;
                });
        });
    }

    document.addEventListener("DOMContentLoaded", mountWidget);
})();
