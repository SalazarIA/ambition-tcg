window.AmbitionzDOM = (() => {
    function byId(id) {
        return document.getElementById(id);
    }

    function setText(id, value, fallback = "") {
        const element = byId(id);

        if (!element) {
            console.warn(`[AmbitionzDOM] Missing element #${id}`);
            return false;
        }

        element.textContent = value ?? fallback;
        return true;
    }

    function setHtml(id, html) {
        const element = byId(id);

        if (!element) {
            console.warn(`[AmbitionzDOM] Missing element #${id}`);
            return false;
        }

        element.innerHTML = html;
        return true;
    }

    function appendLog(id, message, options = {}) {
        const element = byId(id);

        if (!element) {
            console.warn(`[AmbitionzDOM] Missing log #${id}`);
            return false;
        }

        const line = document.createElement("div");
        line.className = options.className || "log-line";
        line.textContent = message || "Battle event.";

        if (options.prepend !== false) {
            element.prepend(line);
        } else {
            element.appendChild(line);
        }

        return true;
    }

    function onClick(id, handler) {
        const element = byId(id);

        if (!element) {
            console.warn(`[AmbitionzDOM] Missing clickable #${id}`);
            return false;
        }

        element.addEventListener("click", handler);
        return true;
    }

    function qsa(selector) {
        return Array.from(document.querySelectorAll(selector));
    }

    function safeJson(value, fallback = {}) {
        try {
            return JSON.parse(value);
        } catch {
            return fallback;
        }
    }

    return {
        byId,
        setText,
        setHtml,
        appendLog,
        onClick,
        qsa,
        safeJson,
    };
})();
