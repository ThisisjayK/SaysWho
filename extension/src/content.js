/**
 * The content script: the two controls, and the capture they both start from.
 *
 * "Capture" downloads the record for the harness, which is the path that has always worked and needs
 * nothing running. "Audit" posts the same record to the local server and draws the result in a panel over
 * the page, which removes the terminal step from the loop.
 *
 * Producing a verdict still needs the fetch layer, the gates and the span guard, all of which are Python and
 * stay Python: a JavaScript reimplementation would be a second implementation of the thing the parity check
 * in `SCOPE.md` §9 exists to compare. The second control moves where the audit is *triggered*, not where it
 * is decided.
 *
 * What is still not here is marking the product's own sentences in place. See `audit.js`.
 *
 * **Why the icons are built rather than written.** `innerHTML` with an SVG string is the shorter way and it
 * throws on any page enforcing Trusted Types, which claude.ai does. Every node here is created through the
 * DOM API for that reason, and the same rule applies to anything added later.
 */

(() => {
  const DOCK_ID = "sayswho-dock";
  if (document.getElementById(DOCK_ID)) return;

  const adapter = saysWhoAdapterFor(location.hostname);

  const SVG_NS = "http://www.w3.org/2000/svg";

  function icon(shapes) {
    const svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("width", "17");
    svg.setAttribute("height", "17");
    svg.setAttribute("fill", "none");
    svg.setAttribute("stroke", "currentColor");
    svg.setAttribute("stroke-width", "1.8");
    svg.setAttribute("stroke-linecap", "round");
    svg.setAttribute("stroke-linejoin", "round");
    svg.setAttribute("aria-hidden", "true");
    shapes.forEach((shape) => {
      const node = document.createElementNS(SVG_NS, shape.tag);
      Object.keys(shape.attrs).forEach((name) => node.setAttribute(name, shape.attrs[name]));
      svg.appendChild(node);
    });
    return svg;
  }

  const path = (d) => ({ tag: "path", attrs: { d } });
  const circle = (cx, cy, r) => ({ tag: "circle", attrs: { cx, cy, r } });

  /** A viewfinder: four corners and a centre. This control frames the answer and takes a copy of it. */
  const CAPTURE_ICON = [
    path("M4 8.5V5.5A1.5 1.5 0 0 1 5.5 4h3"),
    path("M15.5 4h3A1.5 1.5 0 0 1 20 5.5v3"),
    path("M20 15.5v3a1.5 1.5 0 0 1-1.5 1.5h-3"),
    path("M8.5 20h-3A1.5 1.5 0 0 1 4 18.5v-3"),
    circle(12, 12, 2.6),
  ];

  /** A magnifier with a tick in it: look at the sources, and report what checked out. */
  const AUDIT_ICON = [
    circle(10.5, 10.5, 6.5),
    path("M15.5 15.5 20.5 20.5"),
    path("M7.8 10.6l2 2 3.5-3.6"),
  ];

  // ---------------------------------------------------------------- the dock

  const dock = document.createElement("div");
  dock.id = DOCK_ID;
  dock.style.cssText = [
    "position:fixed",
    "right:16px",
    "bottom:16px",
    "z-index:2147483647",
    "display:flex",
    "flex-direction:row",
    "align-items:center",
    "gap:8px",
    // The panel slides in from the right, so the dock steps aside rather than sitting on top of it.
    "transition:right 120ms ease",
  ].join(";");

  /** One label, immediately left of the dock.
   *
   * A child of the dock rather than a fixed element of its own, for two reasons. Positioned against the
   * viewport it overlapped the button it was labelling by 28 pixels, and it stayed put when the dock steps
   * aside for the panel. Anchored here it can do neither.
   */
  const tip = document.createElement("div");
  tip.style.cssText = [
    "position:absolute",
    "right:100%",
    "top:50%",
    "transform:translateY(-50%)",
    "margin-right:10px",
    "padding:5px 9px",
    "font:500 12px/1.2 system-ui,-apple-system,sans-serif",
    "color:#faf9f5",
    "background:#14140f",
    "border-radius:5px",
    "white-space:nowrap",
    "pointer-events:none",
    "opacity:0",
    "transition:opacity 90ms ease",
  ].join(";");

  function showTip(text) {
    tip.textContent = text;
    tip.style.opacity = "1";
  }

  function hideTip() {
    tip.style.opacity = "0";
  }

  function roundButton(id, label, shapes) {
    const button = document.createElement("button");
    button.id = id;
    button.type = "button";
    // Both an accessible name and a native tooltip, because the custom label below is a visual affordance
    // and neither a screen reader nor a keyboard user should depend on hovering to find out what this does.
    button.setAttribute("aria-label", label);
    button.title = label;
    button.style.cssText = [
      "width:34px",
      "height:34px",
      "padding:0",
      "display:flex",
      "align-items:center",
      "justify-content:center",
      "color:#14140f",
      "background:#f5f3ee",
      "border:1px solid #14140f",
      "border-radius:50%",
      "box-shadow:0 1px 4px rgba(0,0,0,0.18)",
      "cursor:pointer",
      "transition:background 90ms ease",
    ].join(";");
    button.appendChild(icon(shapes));

    const enter = () => {
      if (button.disabled) return;
      button.style.background = "#fff";
      showTip(button.dataset.status || label);
    };
    const leave = () => {
      button.style.background = "#f5f3ee";
      if (!button.dataset.status) hideTip();
    };
    button.addEventListener("mouseenter", enter);
    button.addEventListener("focus", enter);
    button.addEventListener("mouseleave", leave);
    button.addEventListener("blur", leave);
    return button;
  }

  const captureButton = roundButton("sayswho-capture-button", "SaysWho: capture", CAPTURE_ICON);
  const auditButton = roundButton("sayswho-audit-button", "SaysWho: audit", AUDIT_ICON);

  /** Show progress where the label goes, since an icon has nowhere to put a word. */
  function working(button, status) {
    if (status) {
      button.dataset.status = status;
      button.style.opacity = "0.55";
      button.disabled = true;
      showTip(status);
    } else {
      delete button.dataset.status;
      button.style.opacity = "1";
      button.disabled = false;
      hideTip();
    }
  }

  const TOAST_SECONDS = 14;
  let toastTimer = null;

  const toast = document.createElement("div");
  toast.id = "sayswho-toast";
  toast.title = "click to dismiss";
  toast.style.cssText = [
    "position:fixed",
    "right:16px",
    "bottom:60px",
    "z-index:2147483647",
    "max-width:340px",
    "padding:10px 12px",
    "font:400 12px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace",
    "color:#111",
    "background:#fff",
    "border:1px solid #111",
    "border-radius:6px",
    "white-space:pre-wrap",
    "cursor:pointer",
    "display:none",
  ].join(";");

  /** Dismissable and self-dismissing.
   *
   * It used to sit there until the page was reloaded, which on a product you keep working in means it is
   * still there an hour later covering something. Three ways out: click it, start another action, or wait.
   */
  function hideToast() {
    toast.style.display = "none";
    clearTimeout(toastTimer);
  }

  function say(message) {
    toast.textContent = message + "\n\n(click to dismiss)";
    toast.style.display = "block";
    clearTimeout(toastTimer);
    toastTimer = setTimeout(hideToast, TOAST_SECONDS * 1000);
  }

  toast.addEventListener("click", hideToast);
  // audit.js hides it when a panel opens, since the panel supersedes anything the toast was saying.
  window.saysWhoHideToast = hideToast;

  // ---------------------------------------------------------------- the work

  async function capture({ download = true } = {}) {
    hideToast();
    working(captureButton, "SaysWho: reading the answer...");
    const found = saysWhoFindAnswer(adapter);

    if (!found) {
      // No container matched. Reporting that plainly beats capturing the whole page and calling it an answer.
      working(captureButton, null);
      say(
        `No answer found on this page.\n\n` +
          `adapter: ${adapter.id}\n` +
          `selectors tried: ${adapter.answerSelectors.join(", ")}\n\n` +
          `The selectors need updating for this product.`
      );
      return;
    }

    const record = await saysWhoBuildCapture({ adapter, found, product: adapter.id });

    console.log(`SaysWho ${record.extension_version} captured ${record.citations.length} citations`);

    if (record.citations.length === 0) {
      say(
        `Captured, but this answer has no citations.\n\n` +
          `G0 will return NO_CITATIONS and refuse to score it.\n` +
          `An uncited answer is not a zero percent answer, it is a different object.\n\n` +
          `adapter: ${record.adapter}\nverified: ${record.adapter_verified}`
      );
    } else {
      say(
        `Captured.  (SaysWho ${record.extension_version})\n\n` +
          `citations: ${record.citations.length}\n` +
          `chars: ${record.rendered_chars} of ${record.dom_chars} in the DOM\n` +
          `chrome links dropped: ${record.chrome_links_excluded}\n` +
          (record.dom_chars > record.rendered_chars * 1.05
            ? `\nINCOMPLETE: ${record.dom_chars - record.rendered_chars} characters are in the page but ` +
              `were never laid out, so they are missing from this capture.\n`
            : "") +
          (record.citations_possibly_hidden
            ? `\nINCOMPLETE: ${record.expanders_seen} "+N" controls hide at least ` +
              `${record.citations_possibly_hidden} more citations.\n` +
              `Expand them and capture again, or this answer is audited over a subset of its sources.\n`
            : "") +
          `sha256: ${record.answer_sha256.slice(0, 16)}...\n` +
          `adapter: ${record.adapter}\n` +
          `verified: ${record.adapter_verified}` +
          (record.adapter_verified
            ? ""
            : `\n\nThis adapter has not been checked against the real page. Compare the capture against\n` +
              `what is on screen before trusting anything computed from it.`)
      );
    }

    working(captureButton, null);
    chrome.runtime.sendMessage({ type: "sayswho:capture", capture: record, download });
    return record;
  }

  async function auditHere() {
    // No download yet. A successful audit means the server wrote the capture to the repo's captures
    // directory, which is where the harness reads them from, so downloading a second copy to ~/Downloads
    // is clutter rather than safety.
    const record = await capture({ download: false });
    if (!record) return;

    working(auditButton, "SaysWho: auditing...");
    let payload = null;
    try {
      payload = await window.saysWhoAudit(record, (status) => working(auditButton, `SaysWho: ${status}`));
    } finally {
      working(auditButton, null);
    }

    // Download only when nothing else has stored this capture, which is a different question from whether
    // the audit succeeded. An audit can fail after the server has already written the capture to disk, and
    // that was downloading a second copy: the server saves before it fetches anything, so a judge that
    // could not be built still leaves the file. `saved_to` is the server saying where it put it.
    if (!payload || !payload.saved_to) {
      chrome.runtime.sendMessage({ type: "sayswho:capture", capture: record, download: true });
    }
  }

  captureButton.addEventListener("click", capture);
  auditButton.addEventListener("click", auditHere);

  // The popup drives the same two paths, so hiding the dock costs a person nothing but the shortcut.
  chrome.runtime.onMessage.addListener((message) => {
    if (message?.type === "sayswho:capture-now") capture();
    if (message?.type === "sayswho:audit-now") auditHere();
  });

  // ---------------------------------------------------------------- mounting

  // Shared with popup.js and background.js. A test compares the three files, because a typo in one of them
  // silently breaks the toggle rather than raising anything.
  const SHOW_DOCK_KEY = "sayswho.showDock";

  dock.appendChild(captureButton);
  dock.appendChild(auditButton);
  dock.appendChild(tip);

  // The toast is mounted whatever the setting says. It is the only feedback a person gets when the buttons
  // are hidden and they trigger a capture from the popup, and a capture that reports nothing looks failed.
  document.documentElement.appendChild(toast);

  function mountDock(show) {
    if (show) {
      if (!dock.isConnected) document.documentElement.appendChild(dock);
    } else {
      dock.remove();
    }
  }

  // Absent means shown. A fresh profile that has never opened the popup should still see the buttons.
  chrome.storage.local.get(SHOW_DOCK_KEY, (stored) => mountDock(stored?.[SHOW_DOCK_KEY] !== false));

  // Live, so the toggle in the popup takes effect on the open tab rather than on the next page load.
  chrome.storage.onChanged.addListener((changes, area) => {
    if (area === "local" && SHOW_DOCK_KEY in changes) {
      mountDock(changes[SHOW_DOCK_KEY].newValue !== false);
    }
  });
})();
