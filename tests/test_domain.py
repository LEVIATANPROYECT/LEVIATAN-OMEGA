import copy
import unittest
from runtime.domain import (InvalidEntry, token_hash, payload_commitment,
                            apply_reveal, moderate, appeal, close_pending,
                            validate_commit, validate_payload)


class ParticipationRules(unittest.TestCase):
    def setUp(self):
        self.config = {"status": "ACTIVE", "t0": "2026-10-01T00:00:00Z",
                       "conditions_sha256": "a" * 64}
        self.token = "1" * 64
        self.state = {"nodes": {"omega-0": {"id": "omega-0", "status": "GENESIS",
                      "generation": 0, "child_commitments": [token_hash(self.token)]}},
                      "consumed": []}
        self.payload = {"content": "Una contribución", "contribution_type": "Texto",
                        "derives_from": None, "ai_used": False, "ai_details": "NO APLICA",
                        "human_authorship": "Texto propio", "pseudonym": "ANÓNIMO",
                        "conditions_sha256": "a" * 64, "child_commitments": [],
                        "declarations": {k: True for k in ("adult", "voluntary", "unpaid",
                                         "rights", "privacy", "conditions")},
                        "capabilities": "RED: sí; ESCRITURA EXTERNA: no"}
        self.original = {"actor": "author", "received_at": "2026-10-01T01:00:00Z",
                         "data": {"kind": "commit", "version": 1,
                                  "token_commitment": token_hash(self.token),
                                  "contribution_commitment": payload_commitment(self.payload, "2" * 64)}}
        self.data = {"kind": "reveal", "version": 1, "token": self.token,
                     "salt": "2" * 64, "payload": self.payload}
        self.node_id = "omega-" + "3" * 32

    def reveal(self, **changes):
        values = dict(data=self.data, received_at="2026-10-01T02:00:00Z",
                      actor="author", original=self.original, node_id=self.node_id,
                      content_hash="4" * 64)
        state = changes.pop("state", self.state)
        config = changes.pop("config", self.config)
        values.update(changes)
        return apply_reveal(config, state, **values)

    def rejects(self, code, callback):
        with self.assertRaises(InvalidEntry) as error:
            callback()
        self.assertEqual(error.exception.code, code)

    def test_pre_t0_blocks_real_entries(self):
        self.rejects("NOT_ACTIVE", lambda: self.reveal(config={"status": "PRE-T0"}))

    def test_unissued_token_is_rejected(self):
        self.state["nodes"]["omega-0"]["child_commitments"] = []
        self.rejects("TOKEN_NOT_ISSUED", self.reveal)

    def test_other_account_cannot_steal_public_reveal(self):
        self.rejects("COMMIT_OWNER_MISMATCH", lambda: self.reveal(actor="attacker"))

    def test_reveal_expires_at_24_hours(self):
        self.rejects("REVEAL_DEADLINE", lambda: self.reveal(received_at="2026-10-02T01:00:00Z"))

    def test_global_deadline_takes_precedence(self):
        self.original["received_at"] = "2026-10-07T23:00:00Z"
        self.rejects("OUTSIDE_CONTRIBUTION_WINDOW", lambda: self.reveal(received_at="2026-10-08T00:00:00Z"))

    def test_changed_content_cannot_replace_committed_content(self):
        self.data["payload"]["content"] = "Contenido sustituido"
        self.rejects("CONTRIBUTION_CHANGED", self.reveal)

    def test_conditions_version_is_bound(self):
        self.payload["conditions_sha256"] = "b" * 64
        self.original["data"]["contribution_commitment"] = payload_commitment(self.payload, "2" * 64)
        self.rejects("CONDITIONS_CHANGED", self.reveal)

    def test_same_event_retry_is_idempotent(self):
        first = self.reveal()
        self.assertEqual(first, self.reveal(state=first))

    def test_same_token_cannot_create_two_nodes(self):
        first = self.reveal()
        self.rejects("TOKEN_USED", lambda: self.reveal(state=first, node_id="omega-" + "5" * 32))

    def test_public_registry_excludes_content_and_identity(self):
        result = self.reveal()
        public = result["nodes"][self.node_id]
        self.assertFalse({"token", "salt", "key", "actor", "login", "issue", "content", "pseudonym"}.intersection(public))
        self.assertEqual(public["generation"], 1)
        self.assertEqual(self.state["consumed"], [])

    def test_no_children_is_valid(self):
        self.assertEqual(self.reveal()["nodes"][self.node_id]["child_commitments"], [])

    def test_children_only_become_available_after_acceptance(self):
        self.payload["child_commitments"] = ["6" * 64]
        self.original["data"]["contribution_commitment"] = payload_commitment(self.payload, "2" * 64)
        pending = self.reveal()
        self.assertEqual(pending["nodes"][self.node_id]["child_commitments"], [])
        result = moderate(self.config, pending, node_id=self.node_id, accepted=True,
                          reason="VALID", at="2026-10-01T03:00:00Z", children=["6" * 64])
        self.assertEqual(result["nodes"][self.node_id]["child_commitments"], ["6" * 64])
        self.assertEqual(result, self.reveal(state=result))

    def test_retired_parent_keeps_issued_invitations_valid(self):
        self.state["nodes"]["omega-0"]["status"] = "RETIRADA"
        self.assertEqual(self.reveal()["nodes"][self.node_id]["parent"], "omega-0")

    def test_single_appeal_and_final_exclusion(self):
        rejected = moderate(self.config, self.reveal(), node_id=self.node_id, accepted=False,
                            reason="IRRELEVANT", at="2026-10-01T03:00:00Z", children=[])
        appealed = appeal(self.config, rejected, node_id=self.node_id, at="2026-10-01T04:00:00Z")
        self.rejects("APPEAL_UNAVAILABLE", lambda: appeal(self.config, appealed, node_id=self.node_id, at="2026-10-01T05:00:00Z"))
        closed = close_pending(self.config, appealed, at="2026-10-10T00:00:00Z")
        self.assertEqual(closed["nodes"][self.node_id]["status"], "EXCLUIDA")

    def test_duplicate_child_hashes_and_oversize_content_rejected(self):
        self.payload["child_commitments"] = ["6" * 64, "6" * 64]
        self.original["data"]["contribution_commitment"] = payload_commitment(self.payload, "2" * 64)
        self.rejects("DUPLICATE_CHILD_COMMITMENT", self.reveal)
        self.payload["child_commitments"] = []
        self.payload["content"] = "x" * 12001
        self.original["data"]["contribution_commitment"] = payload_commitment(self.payload, "2" * 64)
        self.rejects("INVALID_CONTENT_SIZE", self.reveal)

    def test_malformed_declarations_are_rejected(self):
        self.payload["declarations"] = None
        self.original["data"]["contribution_commitment"] = payload_commitment(self.payload, "2" * 64)
        self.rejects("DECLARATIONS_REQUIRED", self.reveal)

    def test_moderation_cannot_predate_submission(self):
        self.rejects("MODERATION_BEFORE_RECEIPT", lambda: moderate(
            self.config, self.reveal(), node_id=self.node_id, accepted=True,
            reason="VALID", at="2026-10-01T01:00:00Z", children=[]))


if __name__ == "__main__":
    unittest.main()
