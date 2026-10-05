"""Verify the frozen documents and Ed25519 canonical envelopes."""
import base64
import hashlib
import json
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from runtime.github_runtime import pack


def main():
    public = serialization.load_pem_public_key(Path('identity/creator-public-key.pem').read_bytes())
    manifest = json.loads(Path('manifest.json').read_text('utf-8'))
    public.verify(base64.b64decode(manifest['signature']), pack(manifest['signed']))
    for filename, digest in manifest['signed']['sha256'].items():
        assert hashlib.sha256(Path(filename).read_bytes()).hexdigest() == digest, filename
    envelope = json.loads(Path('registry/live.json').read_text('utf-8'))
    public.verify(base64.b64decode(envelope['signature']['signature']), pack(envelope['state']))
    config = json.loads(Path('launch.json').read_text('utf-8'))
    assert config['conditions_sha256'] == manifest['signed']['sha256']['CONDITIONS.md']
    if config['status'] == 'ACTIVE':
        from runtime.domain import deadlines
        deadlines(config)
        genesis = envelope['state']['nodes']['omega-0']
        assert genesis['status'] == 'GENESIS' and len(genesis['child_commitments']) == 10
        signature = json.loads(Path('launch-signature.json').read_text('utf-8'))
        public.verify(base64.b64decode(signature['signature']), Path('launch.json').read_bytes())
    forbidden = {'login', 'email', 'actor', 'issue', 'token', 'salt', 'key', 'child_tokens', 'ciphertext'}
    for node in envelope['state']['nodes'].values():
        assert not forbidden.intersection(node)
    assert Path('private').exists() is False
    print('Frozen document hashes, registry signature, launch state and public data separation: PASS')


if __name__ == '__main__':
    main()
