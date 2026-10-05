import copy
import json
import unittest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from runtime import domain as d
from runtime.github_runtime import (PREFIX, capture, load_capture, minimal_event,
    parse_body, sign_state, transition, pack, ApiError, PUBLIC)


class MemoryRepository:
    def __init__(self):
        self.files = {}
        self.revision = 0
        self.conflict_once = False

    def read(self, path):
        return self.files.get(path, (None, None))

    def json(self, path):
        data, sha = self.read(path)
        return (json.loads(data) if data else None), sha

    def put(self, path, data, sha=None, message=""):
        if self.conflict_once:
            self.conflict_once = False
            raise ApiError(409)
        if self.read(path)[1] != sha:
            raise ApiError(409)
        self.revision += 1
        self.files[path] = (data, str(self.revision))

    def once(self, path, value):
        existing, _ = self.json(path)
        if existing is not None:
            return existing
        self.put(path, pack(value))
        return value


class AdapterTests(unittest.TestCase):
    def event(self):
        return {"action": "opened", "repository": {"full_name": PUBLIC},
                "issue": {"id": 123, "number": 8, "body": PREFIX + '{"kind":"commit"}',
                          "created_at": "2026-10-05T01:00:00Z",
                          "user": {"login": "test-person", "type": "User"}}}

    def test_capture_is_encrypted_split_and_immutable(self):
        content, keys = MemoryRepository(), MemoryRepository()
        event = self.event()
        capture(event, "issues", content, keys)
        first = copy.deepcopy((content.files, keys.files))
        capture(event, "issues", content, keys)
        self.assertEqual(first, (content.files, keys.files))
        encoded = b"".join(value[0] for value in content.files.values())
        self.assertNotIn(b"test-person", encoded)
        self.assertNotIn(b'"key"', encoded)
        original = load_capture("issue-123", content, keys)
        self.assertEqual(original["body"], event["issue"]["body"])
        event["issue"]["body"] = PREFIX + '{"kind":"reveal"}'
        with self.assertRaises(d.InvalidEntry):
            capture(event, "issues", content, keys)
        self.assertEqual(first, (content.files, keys.files))

    def test_capture_recovers_after_content_write_failure(self):
        content, keys = MemoryRepository(), MemoryRepository()
        content.conflict_once = True
        with self.assertRaises(ApiError):
            capture(self.event(), "issues", content, keys)
        self.assertIsNone(load_capture("issue-123", content, keys))
        capture(self.event(), "issues", content, keys)
        self.assertIsNotNone(load_capture("issue-123", content, keys))
        self.assertEqual(len(keys.files), 1)

    def test_parser_rejects_duplicate_keys_and_arbitrary_markdown(self):
        for value in [PREFIX + '{"kind":"commit","kind":"reveal"}',
                      '```json\n{"kind":"commit"}\n```', PREFIX + '[1,2]']:
            with self.assertRaises(d.InvalidEntry):
                parse_body(value)

    def test_pull_requests_and_edits_never_capture(self):
        event = self.event()
        event["issue"]["pull_request"] = {}
        self.assertIsNone(minimal_event(event, "issues"))
        event = self.event()
        event["action"] = "edited"
        self.assertIsNone(minimal_event(event, "issues"))

    def test_atomic_registry_revalidates_after_conflict(self):
        public, signer = MemoryRepository(), Ed25519PrivateKey.generate()
        public.put("registry/live.json", pack(sign_state({"nodes": {}, "consumed": [], "revision": 0}, signer)))
        calls = []
        def change(state):
            calls.append(state["revision"])
            result = copy.deepcopy(state)
            result["consumed"].append("token-hash")
            return result
        public.conflict_once = True
        result = transition(public, signer, change)
        self.assertEqual(result["consumed"], ["token-hash"])
        self.assertEqual(calls, [0, 0])
        envelope, _ = public.json("registry/live.json")
        import base64
        signer.public_key().verify(base64.b64decode(envelope["signature"]["signature"]), pack(envelope["state"]))


if __name__ == "__main__":
    unittest.main()
