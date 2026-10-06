"use strict";

// Local synthetic fixtures only: no network, GitHub issues or real invitations.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { webcrypto, createHash } = require("node:crypto");

const source = fs.readFileSync(path.join(__dirname, "../docs/app.js"), "utf8");
const html = fs.readFileSync(path.join(__dirname, "../docs/index.html"), "utf8");
const fixtureToken = "1".repeat(64);
const tokenHash = createHash("sha256").update(Buffer.from(fixtureToken, "hex")).digest("hex");
const prefix = "LEVIATAN-OMEGA/1\n";

class Element {
  constructor(id = "") {
    this.id = id; this.value = ""; this.textContent = ""; this.hidden = false;
    this.disabled = false; this.checked = false; this.files = []; this.children = [];
    this.events = new Map(); this.classes = new Set();
    this.classList = {
      toggle: (name, on) => on ? this.classes.add(name) : this.classes.delete(name),
      contains: name => this.classes.has(name),
    };
  }
  addEventListener(name, callback) { this.events.set(name, callback); }
  fire(name) { return this.events.get(name)?.({ preventDefault() {} }); }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  scrollIntoView() {}
  focus() {}
  select() {}
}

async function app() {
  const elements = new Map([...html.matchAll(/\bid="([^"]+)"/g)].map(m => [m[1], new Element(m[1])]));
  const downloads = [], blobs = new Map(), network = [], intervals = [];
  const now = { value: Date.parse("2026-10-06T01:00:00Z") };
  class ClockDate extends Date {
    constructor(...args) { super(...(args.length ? args : [now.value])); }
    static now() { return now.value; }
  }
  const config = { status: "ACTIVE", t0: "2026-10-05T02:32:00Z", conditions_sha256: "a".repeat(64) };
  const registry = { version: 1, revision: 1, updated_at: config.t0, consumed: [], nodes: {
    "omega-0": { id: "omega-0", status: "GENESIS", generation: 0, parent: null, child_commitments: [tokenHash] },
  } };
  let unavailable = false;
  const document = {
    hidden: false,
    getElementById: id => elements.get(id) || null,
    createElement: tag => {
      const el = new Element();
      el.click = () => { if (tag === "a" && el.download) downloads.push({ filename: el.download, blob: blobs.get(el.href) }); };
      return el;
    },
  };
  const context = vm.createContext({
    document, crypto: webcrypto, TextEncoder, Uint8Array, Blob, URLSearchParams, Date: ClockDate,
    URL: { createObjectURL: blob => { const id = `blob:local-${blobs.size}`; blobs.set(id, blob); return id; }, revokeObjectURL() {} },
    location: { hash: "", pathname: "/LEVIATAN-OMEGA/" }, history: { replaceState() {} },
    navigator: { clipboard: { writeText: async () => {} } },
    setTimeout() {}, setInterval(callback, delay) { intervals.push({ callback, delay }); },
    fetch: async url => {
      network.push(url);
      if (unavailable) throw new Error("Offline fixture");
      assert.ok(url.startsWith("https://raw.githubusercontent.com/LEVIATANPROYECT/LEVIATAN-OMEGA/main/"));
      const value = url.endsWith("launch.json") ? config : { state: registry };
      return { ok: true, json: async () => structuredClone(value) };
    },
  });
  vm.runInContext(source, context, { filename: "docs/app.js" });
  await vm.runInContext("refresh()", context);
  for (const [id, value] of Object.entries({ token: fixtureToken, content: "Aportación sintética local", children: "2", authorship: "Texto de prueba", pseudonym: "TEST", capabilities: "RED: no", "contribution-type": "Texto" })) elements.get(id).value = value;
  elements.get("declarations").checked = true;
  const run = text => vm.runInContext(text, context);
  return { elements, downloads, network, intervals, now, registry, config, run, setUnavailable(value) { unavailable = value; } };
}

test("the invitation count is an explicit choice, including voluntary zero", async () => {
  assert.match(html, /<select id="children" required><option value="" selected disabled>/);
  const a = await app();
  a.elements.get("children").value = "";
  await a.elements.get("prepare-form").fire("submit");
  assert.equal(a.downloads.length, 0);
  assert.match(a.elements.get("form-message").textContent, /Elige cuántas/);
  a.elements.get("children").value = "0";
  await a.elements.get("prepare-form").fire("submit");
  const saved = JSON.parse(await a.downloads[0].blob.text());
  assert.equal(saved.child_tokens.length, 0);
  assert.equal(saved.payload.child_commitments.length, 0);
});

test("commit and reveal exclude future tokens; backup re-download preserves the same secrets", async () => {
  const a = await app();
  await a.elements.get("prepare-form").fire("submit");
  const savedText = await a.downloads[0].blob.text();
  const saved = JSON.parse(savedText);
  const commitText = a.elements.get("outgoing").value;
  const commit = JSON.parse(commitText.slice(prefix.length));
  assert.equal(commit.kind, "commit");
  assert.equal(commit.token_commitment, tokenHash);
  assert.equal(commit.token, undefined);
  assert.equal(commit.payload, undefined);
  assert.equal(saved.child_tokens.length, 2);
  for (const child of saved.child_tokens) assert.ok(!commitText.includes(child));
  assert.equal(a.elements.get("private-backup").hidden, false);
  a.elements.get("download-private").fire("click");
  assert.equal(await a.downloads[1].blob.text(), savedText);
  a.elements.get("original-issue").value = "https://github.com/LEVIATANPROYECT/LEVIATAN-OMEGA/issues/42#issuecomment-1";
  a.elements.get("reveal-button").fire("click");
  const revealText = a.elements.get("outgoing").value;
  const reveal = JSON.parse(revealText.slice(prefix.length));
  assert.equal(reveal.kind, "reveal");
  assert.equal(reveal.original_issue, 42);
  assert.equal(reveal.token, fixtureToken);
  assert.equal(reveal.child_tokens, undefined);
  for (const child of saved.child_tokens) assert.ok(!revealText.includes(child));
  assert.ok(a.network.every(url => url.endsWith(".json")));
});

test("rapid double submission generates only one commitment and backup", async () => {
  const a = await app();
  await Promise.all([a.elements.get("prepare-form").fire("submit"), a.elements.get("prepare-form").fire("submit")]);
  assert.equal(a.downloads.length, 1);
  assert.equal(a.elements.get("prepare-button").disabled, false);
});

test("a refreshed consumed invitation cannot prepare another contribution", async () => {
  const a = await app();
  a.registry.consumed.push(tokenHash);
  await a.elements.get("prepare-form").fire("submit");
  assert.equal(a.downloads.length, 0);
  assert.match(a.elements.get("form-message").textContent, /consumida/);
});

test("registry failure blocks preparation until a successful refresh", async () => {
  const a = await app();
  a.setUnavailable(true);
  await a.elements.get("prepare-form").fire("submit");
  assert.equal(a.downloads.length, 0);
  assert.equal(a.elements.get("prepare-button").disabled, true);
  a.run("updateWindow()");
  assert.equal(a.elements.get("prepare-button").disabled, true);
  a.setUnavailable(false);
  await a.run("refresh()");
  assert.equal(a.elements.get("prepare-button").disabled, false);
});

test("issue links must point to this repository and contain a positive safe issue number", async () => {
  const a = await app();
  for (const value of ["42", "https://github.com/LEVIATANPROYECT/LEVIATAN-OMEGA/issues/42", "https://github.com/leviatanproyect/leviatan-omega/issues/42/"]) {
    assert.equal(a.run(`issueNumber(${JSON.stringify(value)})`), 42);
  }
  for (const value of ["0", "-1", "1.5", "1e3", "9007199254740992", "https://example.com/issues/42", "https://github.com/other/repo/issues/42", "https://github.com/LEVIATANPROYECT/LEVIATAN-OMEGA/pull/42"]) {
    assert.throws(() => a.run(`issueNumber(${JSON.stringify(value)})`));
  }
});

test("countdown and both submission buttons close at the fixed deadline", async () => {
  const a = await app();
  await a.elements.get("prepare-form").fire("submit");
  assert.match(a.elements.get("countdown").textContent, /6 días/);
  a.now.value = Date.parse("2026-10-12T02:32:00Z");
  a.run("updateWindow()");
  assert.equal(a.elements.get("countdown").textContent, "Aportaciones cerradas");
  assert.equal(a.elements.get("prepare-button").disabled, true);
  assert.equal(a.elements.get("reveal-button").disabled, true);
});

test("blank contributions and unchecked declarations do not generate a private file", async () => {
  const a = await app();
  a.elements.get("content").value = " \n ";
  await a.elements.get("prepare-form").fire("submit");
  assert.equal(a.downloads.length, 0);
  a.elements.get("content").value = "Aportación sintética";
  a.elements.get("declarations").checked = false;
  await a.elements.get("prepare-form").fire("submit");
  assert.equal(a.downloads.length, 0);
});
