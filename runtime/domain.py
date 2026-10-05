"""Pure validation and registry transitions; no network, credentials or I/O."""

import copy
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timedelta, timezone

HEX = re.compile(r"^[0-9a-f]{64}$")
NODE_ID = re.compile(r"^omega-[0-9a-f]{32}$")
TYPES = {"Análisis", "Crítica", "Investigación", "Código", "Texto", "Imagen",
         "Transformación de contribución anterior", "Otro"}
DECLARATIONS = {"adult", "voluntary", "unpaid", "rights", "privacy", "conditions"}
PENDING = {"PENDIENTE_MODERACIÓN", "APELACIÓN_PENDIENTE"}


class InvalidEntry(ValueError):
    """A stable public rejection code without submitted content or secrets."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def require(condition, code):
    if not condition:
        raise InvalidEntry(code)


def normalize(value):
    require(isinstance(value, str), "INVALID_TEXT")
    return unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))


def digest(value):
    return hashlib.sha256(normalize(value).encode("utf-8")).hexdigest()


def canonical_json(value):
    # The browser uses the same sorted keys, compact separators and NFC strings.
    if isinstance(value, str):
        return normalize(value)
    if isinstance(value, list):
        return [canonical_json(item) for item in value]
    if isinstance(value, dict):
        return {key: canonical_json(value[key]) for key in sorted(value)}
    require(value is None or isinstance(value, (bool, int)), "INVALID_JSON_VALUE")
    return value


def payload_commitment(payload, salt):
    require(isinstance(salt, str) and HEX.fullmatch(salt), "INVALID_BLINDING_SALT")
    data = json.dumps(canonical_json(payload), ensure_ascii=False,
                      sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(bytes.fromhex(salt) + data).hexdigest()


def instant(value):
    require(isinstance(value, str), "INVALID_TIMESTAMP")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise InvalidEntry("INVALID_TIMESTAMP") from None
    require(result.tzinfo is not None, "TIMEZONE_REQUIRED")
    return result.astimezone(timezone.utc)


def deadlines(config):
    require(config.get("status") == "ACTIVE", "NOT_ACTIVE")
    start = instant(config.get("t0"))
    return start, start + timedelta(hours=168), start + timedelta(hours=216)


def contribution_window(config, received_at):
    start, end, _ = deadlines(config)
    timestamp = instant(received_at)
    require(start <= timestamp < end, "OUTSIDE_CONTRIBUTION_WINDOW")
    return timestamp


def token_hash(token):
    require(isinstance(token, str) and HEX.fullmatch(token), "INVALID_TOKEN")
    return hashlib.sha256(bytes.fromhex(token)).hexdigest()


def parents_for(state, commitment):
    return [node for node in state["nodes"].values()
            if node["status"] in {"GENESIS", "ACEPTADA", "RETIRADA"}
            and commitment in node.get("child_commitments", [])]


def validate_commit(config, state, data, received_at):
    contribution_window(config, received_at)
    require(data.get("kind") == "commit" and data.get("version") == 1, "INVALID_FORMAT")
    for field in ("token_commitment", "contribution_commitment"):
        require(isinstance(data.get(field), str) and HEX.fullmatch(data[field]), "INVALID_COMMITMENT")
    require(len(parents_for(state, data["token_commitment"])) == 1, "TOKEN_NOT_ISSUED")
    require(data["token_commitment"] not in state["consumed"], "TOKEN_USED")


def validate_payload(config, state, payload):
    require(isinstance(payload, dict), "INVALID_PAYLOAD")
    expected = {"content", "contribution_type", "derives_from", "ai_used", "ai_details",
                "human_authorship", "pseudonym", "conditions_sha256", "child_commitments",
                "declarations", "capabilities"}
    require(set(payload) == expected, "INVALID_PAYLOAD_FIELDS")
    content = normalize(payload["content"])
    require(0 < len(content.strip()) and len(content.encode("utf-8")) <= 12000, "INVALID_CONTENT_SIZE")
    require(isinstance(payload["contribution_type"], str) and
            payload["contribution_type"] in TYPES, "INVALID_CONTRIBUTION_TYPE")
    require(isinstance(payload["ai_used"], bool), "INVALID_AI_DECLARATION")
    for field in ("ai_details", "human_authorship", "pseudonym", "capabilities"):
        text = normalize(payload[field])
        require(0 < len(text.strip()) <= 1000, "INVALID_DESCRIPTION")
    require(payload["conditions_sha256"] == config.get("conditions_sha256"), "CONDITIONS_CHANGED")
    require(isinstance(payload["declarations"], dict) and
            set(payload["declarations"]) == DECLARATIONS and
            all(value is True for value in payload["declarations"].values()), "DECLARATIONS_REQUIRED")
    derives_from = payload["derives_from"]
    require(derives_from is None or (isinstance(derives_from, str) and
            derives_from in state["nodes"] and
            state["nodes"][derives_from]["status"] in {"GENESIS", "ACEPTADA", "RETIRADA"}),
            "INVALID_DERIVATION")
    children = payload["child_commitments"]
    require(isinstance(children, list) and len(children) <= 10, "TOO_MANY_CHILDREN")
    require(all(isinstance(h, str) and HEX.fullmatch(h) for h in children), "INVALID_CHILD_COMMITMENT")
    require(len(set(children)) == len(children), "DUPLICATE_CHILD_COMMITMENT")
    issued = {h for n in state["nodes"].values() for h in n.get("child_commitments", [])}
    require(not issued.intersection(children), "CHILD_COMMITMENT_ALREADY_ISSUED")
    return payload


def apply_reveal(config, state, *, data, received_at, actor, original,
                 node_id, content_hash):
    """Caller must persist the returned whole registry with compare-and-swap.

    `original` is the immutable privately captured first issue, never its edited
    body. Re-read registry and revalidate after every concurrent-write conflict.
    """
    received = contribution_window(config, received_at)
    require(NODE_ID.fullmatch(node_id), "INVALID_NODE_ID")
    require(isinstance(content_hash, str) and HEX.fullmatch(content_hash), "INVALID_CONTENT_HASH")
    require(data.get("kind") == "reveal" and data.get("version") == 1, "INVALID_FORMAT")
    require(actor == original["actor"], "COMMIT_OWNER_MISMATCH")
    committed_at = contribution_window(config, original["received_at"])
    require(committed_at <= received < committed_at + timedelta(hours=24), "REVEAL_DEADLINE")
    committed = original["data"]
    commitment = token_hash(data.get("token"))
    require(committed.get("kind") == "commit" and committed.get("version") == 1, "INVALID_ORIGINAL")
    require(commitment == committed.get("token_commitment"), "TOKEN_MISMATCH")
    payload = data.get("payload")
    require(isinstance(payload, dict), "INVALID_PAYLOAD")
    require(payload_commitment(payload, data.get("salt")) == committed.get("contribution_commitment"),
            "CONTRIBUTION_CHANGED")
    parents = parents_for(state, commitment)
    require(len(parents) == 1, "TOKEN_NOT_ISSUED")
    # Replaying this exact captured event is an idempotent operation. The
    # caller binds node_id to the immutable private capture, not user input.
    if node_id in state["nodes"]:
        require(state["nodes"][node_id]["content_hash"] == content_hash, "NODE_COLLISION")
        return copy.deepcopy(state)
    validate_payload(config, state, payload)
    require(commitment not in state["consumed"], "TOKEN_USED")
    result = copy.deepcopy(state)
    result["consumed"].append(commitment)
    result["nodes"][node_id] = {
        "id": node_id, "parent": parents[0]["id"],
        "generation": parents[0]["generation"] + 1,
        "status": "PENDIENTE_MODERACIÓN", "received_at": received_at,
        "content_hash": content_hash, "conditions_sha256": payload["conditions_sha256"],
        "contribution_type": payload["contribution_type"],
        "ai_used": payload["ai_used"], "derives_from": payload["derives_from"],
        "child_commitments": [], "appeal_used": False,
    }
    return result


def moderate(config, state, *, node_id, accepted, reason, at, children):
    _, _, final_deadline = deadlines(config)
    require(instant(at) < final_deadline, "MODERATION_CLOSED")
    require(node_id in state["nodes"], "NODE_NOT_FOUND")
    node = state["nodes"][node_id]
    require(instant(at) >= instant(node["received_at"]), "MODERATION_BEFORE_RECEIPT")
    require(node["status"] in PENDING, "NOT_PENDING")
    require(isinstance(reason, str) and re.fullmatch(r"[A-Z_]{2,50}", reason), "INVALID_REASON")
    result = copy.deepcopy(state)
    target = result["nodes"][node_id]
    if accepted:
        require(isinstance(children, list) and len(children) <= 10 and
                all(isinstance(h, str) and HEX.fullmatch(h) for h in children), "INVALID_CHILD_COMMITMENT")
        issued = {h for n in state["nodes"].values() for h in n.get("child_commitments", [])}
        require(len(set(children)) == len(children) and not issued.intersection(children),
                "DUPLICATE_CHILD_COMMITMENT")
        target["child_commitments"] = list(children)
    target.update(status="ACEPTADA" if accepted else "RECHAZADA",
                  moderation_at=at, moderation_reason=reason)
    return result


def appeal(config, state, *, node_id, at):
    _, _, end = deadlines(config)
    node = state["nodes"].get(node_id)
    require(node is not None, "NODE_NOT_FOUND")
    require(node["status"] == "RECHAZADA" and not node["appeal_used"], "APPEAL_UNAVAILABLE")
    require(instant(node["moderation_at"]) <= instant(at) <
            min(end, instant(node["moderation_at"]) + timedelta(hours=24)), "APPEAL_DEADLINE")
    result = copy.deepcopy(state)
    result["nodes"][node_id].update(status="APELACIÓN_PENDIENTE", appeal_used=True)
    return result


def close_pending(config, state, *, at):
    _, _, end = deadlines(config)
    require(instant(at) >= end, "CLOSURE_TOO_EARLY")
    result = copy.deepcopy(state)
    for node in result["nodes"].values():
        if node["status"] in PENDING:
            node.update(status="EXCLUIDA", exclusion_reason="DEADLINE_2")
    return result
