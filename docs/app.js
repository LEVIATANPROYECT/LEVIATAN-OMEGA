"use strict";
const REPO = "https://raw.githubusercontent.com/LEVIATANPROYECT/LEVIATAN-OMEGA/main/";
const PREFIX = "LEVIATAN-OMEGA/1\n";
const $ = id => document.getElementById(id);
const normal = text => text.replace(/\r\n?/g, "\n").normalize("NFC");
function canonical(value) {
  if (typeof value === "string") return normal(value);
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object") return Object.fromEntries(Object.keys(value).sort().map(k => [k, canonical(value[k])]));
  return value;
}
const bytes = text => new TextEncoder().encode(text);
const hex = data => [...new Uint8Array(data)].map(b => b.toString(16).padStart(2, "0")).join("");
const unhex = text => Uint8Array.from(text.match(/.{2}/g), x => parseInt(x, 16));
const random = length => hex(crypto.getRandomValues(new Uint8Array(length)));
const hash = async data => hex(await crypto.subtle.digest("SHA-256", data));
async function commitment(payload, salt) {
  const body = bytes(JSON.stringify(canonical(payload)));
  const joined = new Uint8Array(32 + body.length);
  joined.set(unhex(salt)); joined.set(body, 32);
  return hash(joined);
}
let config, state, saved;
const utc = text => new Date(text).toISOString().replace("T", " · ").replace(/\.\d{3}Z$/, " UTC");
function message(text, error = false) { $("form-message").textContent = text; $("form-message").classList.toggle("error", error); }
function inWindow() { const time = Date.now(); return config?.status === "ACTIVE" && time >= Date.parse(config.t0) && time < Date.parse(config.t0) + 168 * 3600000; }
async function refresh() {
  try {
    const [launchResponse, registryResponse] = await Promise.all([fetch(REPO + "launch.json", {cache: "no-store"}), fetch(REPO + "registry/live.json", {cache: "no-store"})]);
    if (!launchResponse.ok || !registryResponse.ok) throw Error("No se ha podido consultar el registro.");
    config = await launchResponse.json(); state = (await registryResponse.json()).state;
    const t0 = Date.parse(config.t0), deadline = t0 + 168 * 3600000, final = t0 + 216 * 3600000;
    $("status").textContent = config.status !== "ACTIVE" ? "Preparación · T0 no iniciado" : Date.now() < t0 ? "Inicio programado" : Date.now() < deadline ? "Abierto a contribuciones" : Date.now() < final ? "Moderación y apelaciones" : "Plazo finalizado";
    $("t0").textContent = Number.isFinite(t0) ? utc(config.t0) : "Pendiente";
    $("deadline").textContent = Number.isFinite(deadline) ? utc(deadline) : "Pendiente";
    const nodes = Object.values(state.nodes), accepted = nodes.filter(n => n.status === "ACEPTADA");
    $("accepted").textContent = accepted.length;
    $("pending").textContent = nodes.filter(n => ["PENDIENTE_MODERACIÓN", "APELACIÓN_PENDIENTE"].includes(n.status)).length;
    $("transforms").textContent = accepted.filter(n => n.derives_from || n.contribution_type === "Transformación de contribución anterior").length;
    $("generations").textContent = Math.max(0, ...accepted.map(n => n.generation));
    $("updated").textContent = "Actualización del registro: " + (state.updated_at ? utc(state.updated_at) : "pendiente de activación") + ". Los antecedentes PRE-T0 están excluidos.";
    $("genealogy").replaceChildren();
    for (const node of nodes.sort((a, b) => a.generation - b.generation || a.id.localeCompare(b.id))) {
      const card = document.createElement("div"); card.className = "node" + (node.generation === 0 ? " node-root" : "");
      const title = document.createElement("strong"); title.textContent = node.generation === 0 ? "Ω₀ · Génesis" : "G" + node.generation + " · " + node.id.slice(0, 16) + "…";
      const status = document.createElement("small"); status.textContent = node.status;
      const parent = document.createElement("small"); parent.textContent = node.parent ? "Padre: " + node.parent.slice(0, 16) + "…" : "Una persona · Una idea";
      card.id = "node-" + node.id;
      const permalink = document.createElement("a"); permalink.className = "node-link";
      permalink.href = "#" + card.id; permalink.textContent = "Enlace a este nodo ↗";
      card.append(title, status, parent, permalink); $("genealogy").append(card);
    }
    if (!nodes.length) $("genealogy").textContent = "El génesis se publicará al activar el experimento.";
    const requestedNode = document.getElementById(location.hash.slice(1));
    if (requestedNode?.classList.contains("node")) requestedNode.scrollIntoView({block: "center"});
    $("prepare-button").disabled = !inWindow();
    $("reveal-button").disabled = !inWindow() || !saved;
  } catch (error) { $("status").textContent = "Estado no disponible · consulta el repositorio"; message(error.message, true); }
}
function saveFile(value, filename) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2) + "\n"], {type: "application/json"}));
  const a = document.createElement("a"); a.href = url; a.download = filename; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function outgoing(data, title, explanation) {
  $("outgoing").value = PREFIX + JSON.stringify(data, null, 2);
  $("send-title").textContent = title; $("send-explanation").textContent = explanation;
  $("open-issue").href = "https://github.com/LEVIATANPROYECT/LEVIATAN-OMEGA/issues/new?title=" + encodeURIComponent("LEVIATÁN Ω · " + title);
  $("send-panel").hidden = false; $("send-panel").scrollIntoView({block: "nearest"});
}
$("prepare-form").addEventListener("submit", async event => {
  event.preventDefault(); message("");
  try {
    if (!inWindow()) throw Error("El plazo de aportaciones no está abierto.");
    const token = $("token").value.trim().toLowerCase();
    if (!/^[a-f0-9]{64}$/.test(token)) throw Error("Revisa el token de invitación.");
    const tokenCommitment = await hash(unhex(token));
    const parent = Object.values(state.nodes).find(n => ["GENESIS", "ACEPTADA", "RETIRADA"].includes(n.status) && n.child_commitments.includes(tokenCommitment));
    if (!parent || state.consumed.includes(tokenCommitment)) throw Error("La invitación todavía no está activa o ya está consumida. Actualiza y comprueba el nodo que te invitó.");
    const content = normal($("content").value.trim());
    if (bytes(content).length > 12000) throw Error("La aportación supera 12.000 bytes. Reduce el texto o enlaza tu archivo.");
    const count = Number($("children").value);
    if (!Number.isInteger(count) || count < 0 || count > 10) throw Error("Prepara entre 0 y 10 invitaciones.");
    const children = Array.from({length: count}, () => random(32));
    const payload = {content, contribution_type: $("contribution-type").value, derives_from: $("derives-from").value.trim() || null,
      ai_used: $("ai-used").checked, ai_details: $("ai-used").checked ? normal($("authorship").value) : "Sin uso de IA declarado",
      human_authorship: normal($("authorship").value), pseudonym: normal($("pseudonym").value.trim()),
      capabilities: normal($("capabilities").value), conditions_sha256: config.conditions_sha256,
      child_commitments: await Promise.all(children.map(t => hash(unhex(t)))),
      declarations: {adult: true, voluntary: true, unpaid: true, rights: true, privacy: true, conditions: true}};
    if (payload.derives_from && !state.nodes[payload.derives_from]) throw Error("El nodo del que deriva tu contribución no existe.");
    saved = {format: "LEVIATAN-OMEGA-PRIVATE/1", token, salt: random(32), payload, child_tokens: children};
    saveFile(saved, "LEVIATAN-OMEGA-PRIVADO.json");
    outgoing({kind: "commit", version: 1, token_commitment: tokenCommitment, contribution_commitment: await commitment(payload, saved.salt)},
      "Compromiso", "Se ha descargado tu archivo privado. Guárdalo: lo necesitarás para revelar y para entregar tus invitaciones después de la aceptación. Ahora copia este compromiso y publícalo en GitHub.");
    $("reveal-button").disabled = false;
    message("El compromiso no revela tu aportación ni el token. No publiques el archivo privado descargado.");
  } catch (error) { message(error.message, true); }
});
function tab(reveal) { $("prepare-form").hidden = reveal; $("reveal-panel").hidden = !reveal; $("new-tab").classList.toggle("active", !reveal); $("reveal-tab").classList.toggle("active", reveal); $("send-panel").hidden = true; message(""); }
$("new-tab").addEventListener("click", () => tab(false)); $("reveal-tab").addEventListener("click", () => tab(true));
$("restore").addEventListener("change", async () => {
  try { const file = $("restore").files[0]; if (!file || file.size > 60000) throw Error("Archivo no válido.");
    const value = JSON.parse(await file.text());
    if (value.format !== "LEVIATAN-OMEGA-PRIVATE/1" || !/^[a-f0-9]{64}$/.test(value.token) || !/^[a-f0-9]{64}$/.test(value.salt) || !value.payload) throw Error("El archivo no tiene el formato de participación.");
    saved = value; $("reveal-button").disabled = !inWindow(); message("Archivo cargado solo en este navegador.");
  } catch (error) { saved = null; $("reveal-button").disabled = true; message(error.message, true); }
});
$("reveal-button").addEventListener("click", () => {
  if (!inWindow() || !saved) return message("Carga tu archivo durante el plazo de participación.", true);
  const original = Number($("original-issue").value);
  if (!Number.isSafeInteger(original) || original < 1) return message("Indica el número del issue de compromiso.", true);
  outgoing({kind: "reveal", version: 1, original_issue: original, token: saved.token, salt: saved.salt, payload: saved.payload},
    "Revelación", "Este envío hace públicos tu aportación y el token que vas a consumir. Las futuras invitaciones privadas no están incluidas. Publícalo con la misma cuenta del compromiso.");
});
$("copy").addEventListener("click", async () => { try { await navigator.clipboard.writeText($("outgoing").value); message("Copiado. Abre GitHub y pégalo en el cuerpo del issue."); } catch { $("outgoing").focus(); $("outgoing").select(); message("Seleccionado: cópialo con el menú de tu dispositivo."); } });
const supplied = new URLSearchParams(location.hash.slice(1)).get("token");
if (supplied && /^[a-f0-9]{64}$/.test(supplied)) { $("token").value = supplied; history.replaceState(null, "", location.pathname + "#participar"); }
refresh();
