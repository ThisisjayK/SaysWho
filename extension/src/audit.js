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
      "background:#faf9f6",
      "border-left:1px solid #111",
      "box-shadow:-6px 0 24px rgba(0,0,0,0.12)",
      "padding:16px 18px 40px",
    ].join(";");

    const close = document.createElement("button");
    close.type = "button";
    close.textContent = "close";
    close.style.cssText =
      "position:sticky;top:0;float:right;font:500 12px system-ui,sans-serif;cursor:pointer;" +
      "background:#f5f3ee;border:1px solid #111;border-radius:6px;padding:4px 8px";
    close.addEventListener("click", () => {
      node.remove();
      moveDock(false);
    });
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
    p.style.cssText =
      "font:400 12px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap;color:#111";
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
      message(`${payload.error}\n\n${payload.detail || ""}\n\n${payload.note || ""}`);
      return payload;
    }

    panel();
    const body = document.getElementById(`${PANEL_ID}-body`);
    window.saysWhoRender(body, payload);

    if (!health.judge) {
      // First, not last. Underneath this sit five counters reading zero, and a reader who meets those
      // before the explanation reads them as "nothing checked out" rather than "nothing was checked".
      const note = document.createElement("p");
      note.style.cssText =
        "font:600 12.5px/1.5 system-ui,sans-serif;color:#8a5a00;margin:0 0 12px;padding:9px 11px;" +
        "background:#fdf1dc;border:1px solid #e5cf9d;border-radius:5px";
      note.textContent =
        "No verdicts in this run. The server is running without --judge, so the counts below are zero " +
        "because nothing was judged, not because nothing checked out. Restart it with --judge.";
      body.insertBefore(note, body.firstChild);
    }

    if (payload.saved_to) {
      const where = document.createElement("p");
      where.style.cssText = "font:400 11.5px/1.5 ui-monospace,Menlo,monospace;color:#6b6759;margin-top:14px";
      where.textContent = `capture saved to ${payload.saved_to}`;
      body.appendChild(where);
    }
    return payload;
  };
})();
