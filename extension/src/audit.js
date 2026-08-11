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

  function panel() {
    let node = document.getElementById(PANEL_ID);
    if (node) return node;

    node = document.createElement("div");
    node.id = PANEL_ID;
    node.style.cssText = [
      "position:fixed",
      "top:0",
      "right:0",
      "bottom:0",
      "width:min(560px,46vw)",
      "z-index:2147483646",
      "overflow-y:auto",
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
    close.addEventListener("click", () => node.remove());
    node.appendChild(close);

    const body = document.createElement("div");
    body.id = `${PANEL_ID}-body`;
    node.appendChild(body);

    document.documentElement.appendChild(node);
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
      const note = document.createElement("p");
      note.style.cssText = "font:400 12px/1.5 system-ui,sans-serif;color:#6b6759;margin-top:14px";
      note.textContent =
        "The server is running without --judge, so this shows which sources could be read and nothing " +
        "about whether they support anything. Restart it with --judge for verdicts.";
      body.appendChild(note);
    }
    return payload;
  };
})();
