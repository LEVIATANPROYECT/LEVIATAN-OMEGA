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

    def test_captured_commit_reveal_and_authorized_moderation_flow(self):
        from test_domain import ParticipationRules
        from runtime.github_runtime import decide, OWNER
        rules = ParticipationRules(); rules.setUp()
        public, content, keys = MemoryRepository(), MemoryRepository(), MemoryRepository()
        commit = self.event()
        commit['issue']['body'] = PREFIX + json.dumps(rules.original['data'])
        commit['issue']['created_at'] = rules.original['received_at']
        capture(commit, 'issues', content, keys)
        # Mutable GitHub body is hostile and must never replace captured data.
        public.request = lambda path: {'id':123, 'body':'edited after commitment'}
        reveal = copy.deepcopy(commit)
        reveal['issue'].update(id=124,number=9,created_at='2026-10-01T02:00:00Z',
          body=PREFIX+json.dumps(dict(rules.data,original_issue=8)))
        capture(reveal,'issues',content,keys)
        captured=load_capture('issue-124',content,keys)
        pending,code=decide(rules.config,rules.state,captured,parse_body(captured['body']),public,content,keys)
        self.assertEqual(code,'PENDIENTE_MODERACIÓN')
        command={'kind':'accept','version':1,'reason':'VALID'}
        event={'event_type':'issue_comment','issue_id':124,'actor':'attacker','received_at':'2026-10-01T03:00:00Z'}
        with self.assertRaisesRegex(d.InvalidEntry,'MODERATOR_REQUIRED'):
            decide(rules.config,pending,event,command,public,content,keys)
        event['actor']=OWNER
        accepted,code=decide(rules.config,pending,event,command,public,content,keys)
        self.assertEqual(code,'ACEPTADA')
        self.assertEqual(len(accepted['consumed']),1)
        replay,_=decide(rules.config,accepted,event,command,public,content,keys)
        self.assertEqual(accepted,replay)


if __name__ == "__main__":
    unittest.main()
