#!/usr/bin/env python3
"""Fail closed: reports are evidence, never inferred from CI/package success."""
import hashlib
import json
from pathlib import Path
import sys

TARGETS=('pc-intel','pc-amd','pi5','arm64-uefi')
APPS=('7zip','notepadpp','sumatrapdf','putty')
SCENARIOS=('boot','network','display','audio','storage','update','tutorials')
def validate(root):
    errors=[]
    for target in TARGETS:
        f=root/f'{target}.json'
        if not f.exists(): errors.append(f'Missing evidence: {target}'); continue
        data=json.loads(f.read_text())
        for key in ['hardware','image_sha256','source_commit','tester','tested_at']:
            if not data.get(key): errors.append(f'{target}: missing {key}')
        expected=list(SCENARIOS)+list(APPS)
        if target.startswith('pc-'): expected+=['install-erase','install-alongside','boot-recovery','bitlocker-refusal']
        for scenario in expected:
            result=data.get('results',{}).get(scenario,{})
            if result.get('status')!='passed': errors.append(f'{target}: {scenario} not passed')
            evidence=result.get('evidence','')
            path=(root/evidence).resolve()
            if not evidence or not path.is_relative_to(root.resolve()) or not path.is_file():
                errors.append(f'{target}: {scenario} missing evidence file')
            elif hashlib.sha256(path.read_bytes()).hexdigest()!=result.get('sha256'):
                errors.append(f'{target}: {scenario} evidence checksum mismatch')
    return errors
if __name__=='__main__':
    errors=validate(Path(sys.argv[1] if len(sys.argv)>1 else 'reports'))
    print('\n'.join(errors) if errors else 'All release gates passed')
    sys.exit(bool(errors))
