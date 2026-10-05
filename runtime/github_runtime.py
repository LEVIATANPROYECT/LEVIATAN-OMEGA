"""GitHub event capture and durable validation queue. Never log event bodies.

Only default-branch workflows call this module. Untrusted submissions are JSON
data, never Python, shell, workflow expressions, filenames or repository names.
"""
import base64
import copy
import hashlib
import json
import os
import re
import secrets
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from runtime import domain as d

PUBLIC = "LEVIATANPROYECT/LEVIATAN-OMEGA"
CONTENT = "LEVIATANPROYECT/leviatan-omega-private-content"
KEYS = "LEVIATANPROYECT/leviatan-omega-private-keys"
OWNER = "LEVIATANPROYECT"
PREFIX = "LEVIATAN-OMEGA/1\n"


def pack(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("utf-8")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class ApiError(Exception):
    def __init__(self, status):
        self.status = status
        super().__init__(f"GitHub HTTP {status}")


class GitHub:
    def __init__(self, repo, token):
        self.repo, self.token = repo, token

    def request(self, suffix, method="GET", value=None):
        url = "https://api.github.com/repos/" + self.repo + "/" + suffix
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "Leviatan-Omega",
                   "Authorization": "Bearer " + self.token,
                   "X-GitHub-Api-Version": "2022-11-28"}
        req = Request(url, data=pack(value) if value is not None else None,
                      headers=headers, method=method)
        for attempt in range(4):
            try:
                with urlopen(req, timeout=40) as response:
                    raw = response.read()
                return json.loads(raw) if raw else None
            except HTTPError as exc:
                status = exc.code
                exc.close()
                if status >= 500 and attempt < 3:
                    time.sleep(2 ** attempt)
                    continue
                raise ApiError(status) from None

    def read(self, path):
        try:
            result = self.request("contents/" + path + "?ref=main")
        except ApiError as exc:
            if exc.status == 404:
                return None, None
            raise
        return base64.b64decode(result["content"]), result["sha"]

    def json(self, path):
        data, sha = self.read(path)
        return (json.loads(data) if data is not None else None), sha

    def put(self, path, data, sha=None, message="Update operational record"):
        value = {"message": message, "content": base64.b64encode(data).decode("ascii"),
                 "branch": "main"}
        if sha:
            value["sha"] = sha
        return self.request("contents/" + path, "PUT", value)

    def once(self, path, value):
        """Create once; retrieve winner after a racing creation."""
        existing, _ = self.json(path)
        if existing is not None:
            return existing
        try:
            self.put(path, pack(value))
            return value
        except ApiError as exc:
            if exc.status not in (409, 422):
                raise
            existing, _ = self.json(path)
            if existing is None:
                raise
            return existing


def parse_body(body):
    d.require(isinstance(body, str) and body.startswith(PREFIX), "INVALID_FORMAT")
    d.require(len(body.encode("utf-8")) <= 55000, "EVENT_TOO_LARGE")
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            d.require(key not in obj, "DUPLICATE_JSON_KEY")
            obj[key] = value
        return obj
    try:
        data = json.loads(body[len(PREFIX):], object_pairs_hook=unique,
                          parse_constant=lambda _: d.require(False, "INVALID_NUMBER"))
    except (ValueError, RecursionError):
        raise d.InvalidEntry("INVALID_JSON") from None
    d.require(isinstance(data, dict), "INVALID_FORMAT")
    return data


def minimal_event(event, event_name):
    issue = event.get("issue", {})
    if "pull_request" in issue or event.get("action") not in {"opened", "created"}:
        return None
    if event.get("repository", {}).get("full_name") != PUBLIC:
        return None
    item = event.get("comment") if event_name == "issue_comment" else issue
    if not item or not str(item.get("body", "")).startswith(PREFIX):
        return None
    if item.get("user", {}).get("type") == "Bot":
        return None
    identifier = ("comment-" if event_name == "issue_comment" else "issue-") + str(item["id"])
    return {"capture_id": identifier, "issue": issue["number"],
            "issue_id": issue["id"], "actor": item["user"]["login"],
            "received_at": item["created_at"], "event_type": event_name,
            "body": item["body"]}


def capture(event, event_name, content, keys):
    value = minimal_event(event, event_name)
    if value is None:
        return
    body = pack(value)
    capture_id = value["capture_id"]
    secret = keys.once("live/captures/" + capture_id + ".json", {
        "node_id": "omega-" + uuid.uuid4().hex,
        "key": secrets.token_hex(32), "nonce": secrets.token_hex(12),
        "salt": secrets.token_hex(32), "event_sha256": hashlib.sha256(body).hexdigest()})
    d.require(secret["event_sha256"] == hashlib.sha256(body).hexdigest(), "CAPTURE_CONFLICT")
    aad = capture_id.encode("ascii")
    encrypted = AESGCM(bytes.fromhex(secret["key"])).encrypt(bytes.fromhex(secret["nonce"]), body, aad)
    content.once("live/captures/" + secret["node_id"] + ".json", {
        "ciphertext": base64.b64encode(encrypted).decode("ascii")})
    print("Original event captured in separate private stores.")


def load_capture(capture_id, content, keys):
    d.require(re.fullmatch(r"(?:issue|comment)-[0-9]+", capture_id), "INVALID_CAPTURE_ID")
    secret, _ = keys.json("live/captures/" + capture_id + ".json")
    if secret is None:
        return None
    encrypted, _ = content.json("live/captures/" + secret["node_id"] + ".json")
    if encrypted is None:
        return None
    raw = AESGCM(bytes.fromhex(secret["key"])).decrypt(bytes.fromhex(secret["nonce"]),
          base64.b64decode(encrypted["ciphertext"]), capture_id.encode("ascii"))
    d.require(hashlib.sha256(raw).hexdigest() == secret["event_sha256"], "CAPTURE_CONFLICT")
    value = json.loads(raw)
    value["secret"] = secret
    return value


def sign_state(state, signing_key):
    payload = pack(state)
    return {"state": state, "signature": {
        "algorithm": "Ed25519", "encoding": "base64",
        "signature": base64.b64encode(signing_key.sign(payload)).decode("ascii"),
        "sha256": hashlib.sha256(payload).hexdigest()}}


def read_registry(public, signing_key):
    envelope, sha = public.json("registry/live.json")
    d.require(envelope is not None, "REGISTRY_MISSING")
    state = envelope["state"]
    signing_key.public_key().verify(base64.b64decode(envelope["signature"]["signature"]), pack(state))
    return state, sha


def transition(public, signing_key, change):
    """A whole signed registry is a single compare-and-swap transaction."""
    for attempt in range(8):
        state, sha = read_registry(public, signing_key)
        updated = change(state)
        if updated == state:
            return state
        updated["updated_at"] = now()
        updated["revision"] = state.get("revision", 0) + 1
        try:
            public.put("registry/live.json", pack(sign_state(updated, signing_key)), sha,
                       "Record signed canonical batch [skip ci]")
            return updated
        except ApiError as exc:
            if exc.status != 409:
                raise
            time.sleep(min(attempt + 1, 5))
    raise ApiError(409)


def original_for(number, public, content, keys):
    d.require(isinstance(number, int) and not isinstance(number, bool) and number > 0,
              "INVALID_ORIGINAL_NUMBER")
    # Only the stable GitHub ID is read here; NEVER the mutable body.
    issue = public.request("issues/" + str(number))
    d.require("pull_request" not in issue, "INVALID_ORIGINAL")
    captured = load_capture("issue-" + str(issue["id"]), content, keys)
    return captured


def decide(config, state, captured, data, public, content, keys):
    kind = data.get("kind")
    d.require(not state.get("closed_at") or kind == "withdraw", "REGISTRY_CLOSED")
    when, actor = captured["received_at"], captured["actor"]
    if captured["event_type"] == "issues":
        if kind == "commit":
            d.validate_commit(config, state, data, when)
            return state, "COMMIT_CAPTURED"
        d.require(kind == "reveal", "INVALID_FORMAT")
        original = original_for(data.get("original_issue"), public, content, keys)
        if original is None:
            return None, "WAITING_FOR_COMMIT_CAPTURE"
        original_data = parse_body(original["body"])
        secret = captured["secret"]
        content_hash = d.payload_commitment(data.get("payload"), secret["salt"])
        result = d.apply_reveal(config, state, data=data, received_at=when, actor=actor,
            original={"actor": original["actor"], "received_at": original["received_at"],
                      "data": original_data}, node_id=secret["node_id"], content_hash=content_hash)
        return result, "PENDIENTE_MODERACIÓN"
    d.require(captured["event_type"] == "issue_comment", "INVALID_EVENT")
    target = load_capture("issue-" + str(captured["issue_id"]), content, keys)
    if target is None:
        return None, "WAITING_FOR_REVEAL_CAPTURE"
    target_data = parse_body(target["body"])
    d.require(target_data.get("kind") == "reveal", "REVEAL_REQUIRED")
    node_id = target["secret"]["node_id"]
    if node_id not in state["nodes"]:
        return None, "WAITING_FOR_REVEAL_VALIDATION"
    node = state["nodes"][node_id]
    if kind in {"accept", "reject"}:
        d.require(actor.casefold() == OWNER.casefold(), "MODERATOR_REQUIRED")
        d.require(data.get("reason") in {"VALID", "IRRELEVANT", "SPAM", "RIGHTS", "PRIVACY", "ILLEGAL", "MANIPULATION", "CONDITIONS"}, "INVALID_REASON")
        if node.get("moderation_at") == when:
            return state, node["status"]
        result = d.moderate(config, state, node_id=node_id, accepted=kind == "accept",
                           reason=data["reason"], at=when,
                           children=target_data["payload"]["child_commitments"])
        return result, result["nodes"][node_id]["status"]
    d.require(actor == target["actor"], "ENTRY_OWNER_REQUIRED")
    if kind == "appeal":
        if node.get("appeal_at") == when:
            return state, node["status"]
        result = d.appeal(config, state, node_id=node_id, at=when)
        result["nodes"][node_id]["appeal_at"] = when
        return result, "APELACIÓN_PENDIENTE"
    d.require(kind == "withdraw", "INVALID_COMMAND")
    result = copy.deepcopy(state)
    result["nodes"][node_id].update(status="RETIRADA", withdrawn_at=when)
    return result, "RETIRADA_PRIVACY_REVIEW_REQUIRED"


def respond(public, captured, code):
    marker = "<!-- omega-result:" + hashlib.sha256(captured["capture_id"].encode()).hexdigest()[:20] + " -->"
    suffix = "issues/" + str(captured["issue"]) + "/comments"
    page = 1
    while True:
        items = public.request(suffix + "?per_page=100&page=" + str(page))
        if any(marker in (item.get("body") or "") for item in items):
            return
        if len(items) < 100:
            break
        page += 1
    text = marker + "\nLEVIATÁN Ω · " + code + "\n\n"
    if code == "COMMIT_CAPTURED":
        text += "Compromiso original capturado. Publica la revelación desde la herramienta, en menos de 24 horas y antes del cierre de aportaciones."
    elif code in {"PENDIENTE_MODERACIÓN", "ACEPTADA", "RECHAZADA", "APELACIÓN_PENDIENTE", "RETIRADA_PRIVACY_REVIEW_REQUIRED"}:
        text += "Consulta el estado y las reglas en [la web oficial](https://leviatanproyect.github.io/LEVIATAN-OMEGA/). La moderación es independiente de la validación técnica."
    else:
        text += "El evento no cumple una comprobación técnica. Las ediciones no sustituyen el envío original. Contacto: leviathan.omega.contact@gmail.com."
    public.request(suffix, "POST", {"body": text})


def drain(public, content, keys):
    config, _ = public.json("launch.json")
    if not config or config.get("status") != "ACTIVE":
        print("Launch inactive; capture remains separate from official participation.")
        return
    signing, _ = keys.read("live/signing/ed25519.pem")
    d.require(signing is not None, "SIGNING_KEY_MISSING")
    signer = serialization.load_pem_private_key(signing, password=None)
    tree = keys.request("git/trees/main?recursive=1")
    d.require(not tree.get("truncated"), "QUEUE_INDEX_TRUNCATED")
    queue = []
    for item in tree.get("tree", []):
        match = re.fullmatch(r"live/captures/((?:issue|comment)-[0-9]+)\.json", item["path"])
        if not match:
            continue
        receipt, _ = keys.json("live/receipts/" + match[1] + ".json")
        if receipt and receipt.get("responded"):
            continue
        captured = load_capture(match[1], content, keys)
        if captured is not None:
            queue.append(captured)
    queue.sort(key=lambda entry: (entry["received_at"], int(entry["capture_id"].split("-")[1])))
    for captured in queue[:250]:
        receipt_path = "live/receipts/" + captured["capture_id"] + ".json"
        receipt, receipt_sha = keys.json(receipt_path)
        if receipt is None:
            try:
                data = parse_body(captured["body"])
                code_box = []
                def change(state):
                    result, code = decide(config, state, captured, data, public, content, keys)
                    code_box[:] = [code]
                    return state if result is None else result
                transition(public, signer, change)
                code = code_box[0]
                if code.startswith("WAITING_FOR_"):
                    # A later independent capture/drain or scheduled drain retries.
                    continue
            except d.InvalidEntry as exc:
                code = exc.code
            except (TypeError, KeyError, RecursionError, UnicodeError):
                # Malformed hostile input must not block unrelated queued work.
                code = "INVALID_FORMAT"
            receipt = keys.once(receipt_path, {"code": code, "processed_at": now(), "responded": False})
            receipt, receipt_sha = keys.json(receipt_path)
        respond(public, captured, receipt["code"])
        receipt["responded"] = True
        keys.put(receipt_path, pack(receipt), receipt_sha)
    _, _, end = d.deadlines(config)
    if d.instant(now()) >= end:
        def close(state):
            if state.get("closed_at"):
                return state
            result = d.close_pending(config, state, at=now())
            result["closed_at"] = now()
            result["deadline_2"] = end.isoformat().replace("+00:00", "Z")
            return result
        final_state = transition(public, signer, close)
        final_archive = public.once("final/archive.json", sign_state(final_state, signer))
        certificate = {"version": 1, "creator": "Peter", "responsible_operator": "Pedro Rivilla",
            "work": "LEVIATÁN Ω", "deadline_2": end.isoformat().replace("+00:00", "Z"),
            "archive_sha256": hashlib.sha256(pack(final_archive)).hexdigest(),
            "conditions_sha256": config["conditions_sha256"],
            "statement": "Este archivo identifica el registro canónico final del acontecimiento. No transfiere derechos ni acredita una venta.",
            "timestamp_reference": "final/archive.json.ots"}
        public.once("final/certificate.json", {"signed": certificate,
            "signature": base64.b64encode(signer.sign(pack(certificate))).decode("ascii")})
    print("Durable queue processed; no submission content or secret material logged.")


def healthcheck(public, content, keys):
    """Infrastructure check only: no issue, invitation or participant is created."""
    signing, _ = keys.read("live/signing/ed25519.pem")
    signer = serialization.load_pem_private_key(signing, password=None)
    read_registry(public, signer)
    name = "health/storage-v1.json"
    secret = keys.once(name, {"key": secrets.token_hex(32), "nonce": secrets.token_hex(12)})
    plaintext = b"LEVIATAN OMEGA infrastructure verification; NOT A CONTRIBUTION"
    ciphertext = AESGCM(bytes.fromhex(secret["key"])).encrypt(bytes.fromhex(secret["nonce"]), plaintext, None)
    content.once(name, {"ciphertext": base64.b64encode(ciphertext).decode("ascii")})
    stored, _ = content.json(name)
    decoded = AESGCM(bytes.fromhex(secret["key"])).decrypt(bytes.fromhex(secret["nonce"]), base64.b64decode(stored["ciphertext"]), None)
    d.require(decoded == plaintext, "STORAGE_ROUNDTRIP_FAILED")
    print("Private storage round-trip and operational signing key: PASS. No participant created.")


def main():
    public = GitHub(PUBLIC, os.environ["GITHUB_TOKEN"])
    content = GitHub(CONTENT, os.environ["PRIVATE_CONTENT_TOKEN"])
    keys = GitHub(KEYS, os.environ["PRIVATE_KEYS_TOKEN"])
    try:
        if sys.argv[1] == "capture":
            capture(json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text("utf-8")),
                    os.environ["GITHUB_EVENT_NAME"], content, keys)
        elif sys.argv[1] == "drain":
            drain(public, content, keys)
        elif sys.argv[1] == "healthcheck":
            healthcheck(public, content, keys)
        else:
            raise ValueError("Unknown mode")
    except (ApiError, d.InvalidEntry) as exc:
        print("Operational error:", str(exc))
        raise SystemExit(1) from None
    except Exception as exc:
        # Tracebacks can disclose submitted content through exception strings.
        print("Operational error type:", type(exc).__name__)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
