"""Timestamp one signed registry snapshot per six-hour experiment interval."""
import os
import tempfile
from pathlib import Path
from runtime.domain import instant, deadlines
from runtime.github_runtime import GitHub, PUBLIC, pack, now
from runtime.timestamp import stamp


def main():
    public=GitHub(PUBLIC,os.environ['GITHUB_TOKEN'])
    config,_=public.json('launch.json')
    if config.get('status')!='ACTIVE':
        print('No active experiment.'); return
    start,_,end=deadlines(config)
    elapsed=(instant(now())-start).total_seconds()
    if elapsed<21600 or instant(now())>end:
        print('No periodic snapshot due.'); return
    slot=int(elapsed//21600)
    name=f'timestamps/interval-{slot:02d}.json'
    proof,_=public.read(name+'.ots')
    if proof is not None:
        print('This interval already has a calendar receipt.'); return
    registry,_=public.json('registry/live.json')
    snapshot=public.once(name,registry)
    with tempfile.TemporaryDirectory() as folder:
        path=Path(folder)/'snapshot.json'; path.write_bytes(pack(snapshot))
        proof=stamp(path).read_bytes()
        public.put(name+'.ots',proof,message='Timestamp signed canonical state [skip ci]')
    print('Free calendar receipt published; Bitcoin confirmation remains unverified.')


if __name__=='__main__':
    main()
