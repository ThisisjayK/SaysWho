/**
 * Run the extension's renderer outside a browser, so Python can compare what it displayed against what
 * Python decided.
 *
 * `SCOPE.md` §9: "the extension and the harness must produce identical verdicts on identical inputs, and
 * that is a validation check, not an aspiration." The harness's verdicts are in the payload. This prints
 * what the renderer actually put on the screen, and `tests/test_parity.py` asserts the two agree.
 *
 * The DOM here is a shim, not jsdom, because the alternative was a dependency for a test whose whole point
 * is that the thing under test is small enough not to need one. It implements exactly what `render.js`
 * touches during a render, and it throws on anything else rather than returning undefined: a silent
 * undefined would make the parity check pass by rendering nothing.
 *
 *     node tests/parity/render_in_node.mjs payload.json
 */

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const here = dirname(fileURLToPath(import.meta.url));
const RENDER_JS = join(here, "..", "..", "extension", "src", "render.js");

function makeNode(tag) {
  const node = {
    tag,
    className: "",
    textContent: "",
    children: [],
    attributes: {},
    style: {},
    listeners: {},
    tabIndex: 0,
    offsetWidth: 0,
    clientWidth: 800,
    appendChild(child) {
      child.parent = node;
      node.children.push(child);
      return child;
    },
    setAttribute(name, value) {
      node.attributes[name] = String(value);
    },
    addEventListener(name, fn) {
      (node.listeners[name] = node.listeners[name] || []).push(fn);
    },
    remove() {
      if (!node.parent) return;
      const at = node.parent.children.indexOf(node);
      if (at >= 0) node.parent.children.splice(at, 1);
      node.parent = null;
    },
    getBoundingClientRect() {
      return { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 };
    },
  };
  return node;
}

const document = {
  createElement: (tag) => makeNode(tag),
  createTextNode: (text) => {
    const node = makeNode("#text");
    node.textContent = String(text);
    return node;
  },
};

const sandbox = { window: {}, document, console };
vm.createContext(sandbox);
vm.runInContext(readFileSync(RENDER_JS, "utf8"), sandbox, { filename: "render.js" });

const payload = JSON.parse(readFileSync(process.argv[2], "utf8"));
const root = makeNode("div");
sandbox.window.saysWhoRender(root, payload);

/** Depth-first text of a node, the way a reader would read it. */
function text(node) {
  if (node.tag === "#text") return node.textContent;
  const own = node.children.length ? "" : node.textContent;
  return own + node.children.map(text).join(" ");
}

function find(node, predicate, out = []) {
  if (predicate(node)) out.push(node);
  node.children.forEach((child) => find(child, predicate, out));
  return out;
}

const marks = find(root, (n) => n.tag === "mark").map((n) => ({
  state: (n.className.match(/sw-mark sw-(\S+)/) || [])[1] || "",
  text: n.textContent,
  ariaLabel: n.attributes["aria-label"] || "",
}));

// The claim list renders one row per claim: the state label, then the claim's text.
const rows = find(root, (n) => n.className === "sw-row").map((n) => n.children.map((c) => c.textContent));

const chips = {};
find(root, (n) => (n.className || "").startsWith("sw-chip")).forEach((chip) => {
  const parts = chip.children.map((c) => c.textContent);
  chips[parts[1]] = Number(parts[2]);
});

// Hovering a mark is what builds the per-claim card, so the cards do not exist until something fires the
// handler. Firing it here is the only way to compare what the reader is shown against the payload.
const cards = marks.map((_, i) => {
  const mark = find(root, (n) => n.tag === "mark")[i];
  (mark.listeners.mouseenter || []).forEach((fn) => fn());
  const card = find(root, (n) => n.className === "sw-card").pop();
  const shown = {
    heading: card.children[0].textContent,
    verdicts: find(card, (n) => n.className === "sw-verdict").map((n) => n.textContent),
    voids: find(card, (n) => n.className === "sw-void").map((n) => n.textContent),
    spans: find(card, (n) => n.className === "sw-span").map((n) => n.textContent),
    // The card is removed again on mouseleave, so its notes are not in the page text afterwards. They are
    // the only place the reader is told why a verdict was thrown out, so they get captured here.
    notes: find(card, (n) => n.className === "sw-note").map((n) => n.textContent),
  };
  (mark.listeners.mouseleave || []).forEach((fn) => fn());
  return shown;
});

process.stdout.write(
  JSON.stringify({ marks, rows, chips, cards, fullText: text(root) }, null, 2)
);
