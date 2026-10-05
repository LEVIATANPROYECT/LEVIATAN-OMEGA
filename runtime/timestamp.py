"""Free OpenTimestamps calendar submission; pending is never called confirmed."""
import hashlib
import json
import secrets
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from opentimestamps.calendar import RemoteCalendar
from opentimestamps.core.op import OpAppend, OpSHA256
from opentimestamps.core.serialize import BytesDeserializationContext, BytesSerializationContext
from opentimestamps.core.timestamp import DetachedTimestampFile


def stamp(path):
    path = Path(path)
    output = path.with_name(path.name + '.ots')
    if output.exists():
        proof = DetachedTimestampFile.deserialize(BytesDeserializationContext(output.read_bytes()))
        if proof.file_digest == hashlib.sha256(path.read_bytes()).digest():
            return output
        raise ValueError('Existing proof belongs to different content')
    with path.open('rb') as stream:
        detached = DetachedTimestampFile.from_fd(OpSHA256(), stream)
    blinded = detached.timestamp.ops.add(OpAppend(secrets.token_bytes(16))).ops.add(OpSHA256())
    calendars = ['https://a.pool.opentimestamps.org', 'https://b.pool.opentimestamps.org', 'https://a.pool.eternitywall.com']
    successful = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(RemoteCalendar(url).submit, blinded.msg, timeout=20): url for url in calendars}
        for future in as_completed(futures):
            try:
                result = future.result()
                blinded.merge(result)
                successful.append(futures[future])
            except Exception as exc:
                print('Calendar unavailable:', futures[future], type(exc).__name__)
    if not successful:
        raise RuntimeError('No free calendar accepted the commitment')
    context = BytesSerializationContext()
    detached.serialize(context)
    proof = context.getbytes()
    checked = DetachedTimestampFile.deserialize(BytesDeserializationContext(proof))
    assert checked.file_digest == hashlib.sha256(path.read_bytes()).digest()
    output.write_bytes(proof)
    print(json.dumps({'file': str(path), 'proof_bytes': len(proof), 'calendars': successful,
                      'status': 'PENDING_BITCOIN_CONFIRMATION'}))
    return output


if __name__ == '__main__':
    stamp(sys.argv[1])
