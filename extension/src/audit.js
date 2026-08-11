/**
 * Audit without leaving the page.
 *
 * Posts a capture to the local server (`python3 -m sayswho.server`) and renders the payload it returns, in a
 * panel over the product page, using the same `render.js` the standalone report uses.
 *
 * **Nothing here decides anything.** The gates, the span guard and the denominators are Python and stay
 * Python. This file posts JSON and draws what comes back. A JavaScript reimplementation of the pipeline
 * would be the second implementation the `SCOPE.md` §9 parity check exists to compare, and the two would
 * drift apart under maintenance until the interface was telling users something the audited pipeline never
 * said.
 *
 * **What it does not do.** It does not mark the product's own sentences in place. The payload carries
 * character offsets into the answer text, and mapping those onto a live DOM that re-renders as you scroll
 * is a separate piece of work with its own failure modes, and getting it subtly wrong would put a verdict
 * next to the wrong sentence. The panel shows the marked answer beside the page instead.
 *
 * If the server is not running, that is reported as the server not running. It is not reported as an audit
 * that found nothing, because those are different facts and only one of them is about the answer.
 */

(() => {
  const ENDPOINT = "http://127.0.0.1:8765";
  const PANEL_ID = "sayswho-panel";

  async function serverIsUp() {
    try {
      const response = await fetch(`${ENDPOINT}/health`, { method: "GET" });
      if (!response.ok) return null;
      return await response.json();
    } catch (err) {
      return null;
    }
  }

  const PANEL_WIDTH = "min(560px,46vw)";

  /** Step the buttons aside so the panel does not open on top of them. */
  function moveDock(open) {
    const dock = document.getElementById("sayswho-dock");
    if (dock) dock.style.right = open ? `calc(${PANEL_WIDTH} + 16px)` : "16px";
  }

  function panel() {
    // The capture toast is superseded the moment a panel opens, and it was outliving its usefulness by
    // sitting there until the page was reloaded.
    window.saysWhoHideToast?.();

    let node = document.getElementById(PANEL_ID);
    if (node) return node;

    node = document.createElement("div");
    node.id = PANEL_ID;
    node.className = "sw-panel";
    // Structure only. Colour, border and the close control are in render.css, which is the only place a
    // dark-mode variant can live, and this panel sits on products that are usually dark.
    node.style.cssText = [
      "position:fixed",
      "top:0",
      "right:0",
      "bottom:0",
      `width:${PANEL_WIDTH}`,
      "z-index:2147483646",
      "overflow-y:auto",
      // A hard stop. The renderer wraps long strings itself, and this is the backstop that keeps a missed
      // one from giving the whole page a horizontal scrollbar.
      "overflow-x:hidden",
      // Thin. The panel's own padding sits between its background and the rendered content's, so anything
      // generous here reads as a wide frame around the audit rather than as breathing room.
      "padding:8px 10px 28px",
    ].join(";");

    function dismiss() {
      node.remove();
      moveDock(false);
      document.removeEventListener("keydown", onKey);
    }

    function onKey(event) {
      if (event.key === "Escape") dismiss();
    }

    // An icon, not the word "close": the word was a light pill inheriting the host page's white text, so on
    // claude.ai it was white on near-white. Escape works too, which is what a panel is expected to do.
    const close = document.createElement("button");
    close.type = "button";
    close.className = "sw-panel-close";
    close.title = "Close the audit panel (Esc)";
    close.setAttribute("aria-label", "Close the audit panel");

    const NS = "http://www.w3.org/2000/svg";
    const cross = document.createElementNS(NS, "svg");
    cross.setAttribute("viewBox", "0 0 24 24");
    cross.setAttribute("width", "14");
    cross.setAttribute("height", "14");
    cross.setAttribute("fill", "none");
    cross.setAttribute("stroke", "currentColor");
    cross.setAttribute("stroke-width", "2");
    cross.setAttribute("stroke-linecap", "round");
    cross.setAttribute("aria-hidden", "true");
    ["M6 6 18 18", "M18 6 6 18"].forEach((d) => {
      const line = document.createElementNS(NS, "path");
      line.setAttribute("d", d);
      cross.appendChild(line);
    });
    close.appendChild(cross);

    close.addEventListener("click", dismiss);
    document.addEventListener("keydown", onKey);
    node.appendChild(close);

    const body = document.createElement("div");
    body.id = `${PANEL_ID}-body`;
    // The renderer's own padding assumes a full page. In here the panel supplies it.
    body.className = "sw-in-panel";
    node.appendChild(body);

    document.documentElement.appendChild(node);
    moveDock(true);
    return node;
  }

  function message(text) {
    panel();
    const body = document.getElementById(`${PANEL_ID}-body`);
    body.textContent = "";
    const p = document.createElement("pre");
    // Class, not an inline style. An inline colour cannot have a dark variant, and this panel spends most
    // of its life on a dark product.
    p.className = "sw-panel-message";
    p.textContent = text;
    body.appendChild(p);
  }

  window.saysWhoAudit = async function (record, onStatus) {
    const health = await serverIsUp();
    if (health === null) {
      message(
        "The local audit server is not running.\n\n" +
          "Start it in a terminal:\n\n" +
          "    python3 -m sayswho.server --judge\n\n" +
          "This is the server being unreachable, not an audit that found nothing. The capture was still\n" +
          "downloaded, so nothing has been lost."
      );
      return null;
    }

    onStatus?.(health.judge ? "auditing (fetching every cited page)..." : "checking sources...");

    let payload;
    try {
      const response = await fetch(`${ENDPOINT}/audit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(record),
      });
      payload = await response.json();
      if (!response.ok) {
        message(`The audit failed.\n\n${payload.error}\n${payload.detail || ""}`);
        return null;
      }
    } catch (err) {
      message(`The audit could not be sent.\n\n${err}`);
      return null;
    }

    if (payload.error) {
      message(`${payload.error}\n\n${payload.detail || ""}\n\n${payload.note || ""}`.trim());
      return payload;
    }

    panel();
    const body = document.getElementById(`${PANEL_ID}-body`);
    window.saysWhoRender(body, payload);

    if (!health.judge) {
      // First, not last. Underneath this sit five counters reading zero, and a reader who meets those
      // before the explanation reads them as "nothing checked out" rather than "nothing was checked".
      const note = document.createElement("p");
      note.className = "sw-panel-warn";
      note.textContent =
        "No verdicts in this run. The server is running without --judge, so the counts below are zero " +
        "because nothing was judged, not because nothing checked out. Restart it with --judge.";
      body.insertBefore(note, body.firstChild);
    }

    if (payload.saved_to) {
      const where = document.createElement("p");
      where.className = "sw-panel-note";
      where.textContent = `capture saved to ${payload.saved_to}`;
      body.appendChild(where);
    }
    return payload;
  };
})();
