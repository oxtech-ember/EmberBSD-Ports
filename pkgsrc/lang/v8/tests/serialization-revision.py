#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check old Node snapshot/cache rejection and new serialization roundtrips."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--node', type=Path, required=True)
    parser.add_argument('--old-snapshot', type=Path, required=True)
    parser.add_argument('--old-cache', type=Path, required=True)
    parser.add_argument('--darwin-runtime-view', type=Path)
    args = parser.parse_args()
    node = str(args.node.resolve(strict=True))
    env = os.environ.copy()
    env.pop('DYLD_LIBRARY_PATH', None)
    if args.darwin_runtime_view:
        env['DYLD_LIBRARY_PATH'] = str(args.darwin_runtime_view.resolve(strict=True))
    def run(*argv, check=True):
        return subprocess.run([node, *map(str, argv)], env=env, check=check,
                              text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    old = run('--snapshot-blob', args.old_snapshot.resolve(strict=True), check=False)
    assert old.returncode != 0 and 'version mismatch' in old.stderr.lower(), old.stderr
    run('-e', "const fs=require('fs'),vm=require('vm');"
        "const s=new vm.Script('21*2',{cachedData:fs.readFileSync(process.argv[1])});"
        "if(!s.cachedDataRejected||s.runInThisContext()!==42)throw Error('old cache accepted')",
        args.old_cache.resolve(strict=True))
    with tempfile.TemporaryDirectory(prefix='v8-serialization-') as directory:
        root = Path(directory)
        entry, snapshot = root / 'entry.js', root / 'snapshot.blob'
        entry.write_text("require('node:v8').startupSnapshot.setDeserializeMainFunction("
                         "() => console.log('new snapshot restored'));\n")
        run('--snapshot-blob', snapshot, '--build-snapshot', entry)
        assert 'new snapshot restored' in run('--snapshot-blob', snapshot).stdout
    run('-e', "const vm=require('vm');const a=new vm.Script('21*2');"
        "const b=new vm.Script('21*2',{cachedData:a.createCachedData()});"
        "if(b.cachedDataRejected||b.runInThisContext()!==42)throw Error('new cache invalid');"
        "if(!process.versions.v8.includes('-emberbsd.s1'))throw Error('missing revision')")
    print('V8 old snapshot/cache rejected; new snapshot/cache roundtrips PASS')


if __name__ == '__main__':
    main()
