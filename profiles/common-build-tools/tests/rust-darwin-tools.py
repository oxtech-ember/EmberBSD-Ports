#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Real Mach-O routing/signature controls for the Rust Darwin package helper."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

HELPER = Path(__file__).resolve().parents[3] / 'pkgsrc/lang/rust-bin/files/darwin-llvm.py'


def state(root):
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_file():
            result[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
        elif path.is_dir():
            result[str(path.relative_to(root))] = 'directory'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', required=True, help='complete explicitly selected native C compiler command')
    parser.add_argument('--work', type=Path, required=True)
    for name in ('lipo', 'otool', 'install-name-tool', 'codesign'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    if not args.work.is_absolute() or args.work.exists():
        parser.error('use a new absolute work directory')
    args.work.mkdir()
    cc = shlex.split(args.cc)
    if not cc or not Path(cc[0]).is_absolute():
        parser.error('select the native compiler by absolute path')
    tools = {role: getattr(args, role) for role in ('lipo', 'otool', 'install_name_tool', 'codesign')}
    for tool in tools.values():
        assert tool.is_absolute() and tool.is_file() and os.access(tool, os.X_OK), tool
    root = args.work / 'original'
    for relative in ('bin', 'lib', 'lib/rustlib/fixture/lib'):
        (root / relative).mkdir(parents=True, exist_ok=True)
    library = args.work / 'library.c'
    library.write_text('int answer(void) { return 42; }\n')
    source = args.work / 'main.c'
    source.write_text('extern int answer(void); int main(void) { return answer()!=42; }\n')
    commands = [
        [*cc, '-dynamiclib', str(library), '-Wl,-install_name,@rpath/libLLVM.dylib', '-o', str(root/'lib/libLLVM.dylib')],
        [*cc, str(source), '-L'+str(root/'lib'), '-lLLVM', '-Wl,-rpath,@loader_path/../lib', '-o', str(root/'bin/rustc')],
        [*cc, '-dynamiclib', str(source), '-L'+str(root/'lib'), '-lLLVM', '-Wl,-rpath,@loader_path',
         '-Wl,-install_name,@rpath/librustc_driver-fixture.dylib', '-o', str(root/'lib/librustc_driver-fixture.dylib')],
    ]
    for command in commands:
        subprocess.run(command, check=True, capture_output=True)
    shutil.copy2(root/'lib/libLLVM.dylib', root/'lib/rustlib/fixture/lib/libLLVM.dylib')
    records = args.work/'selected-tools.jsonl'
    wrappers = args.work/'selected tools'; wrappers.mkdir()
    selected = {}
    for role, path in tools.items():
        wrapper = wrappers/role
        wrapper.write_text('#!'+sys.executable+'\nimport json,os,sys\n'
            +'with open('+repr(str(records))+',"a") as stream: stream.write(json.dumps(['+repr(role)+',sys.argv[1:]])+"\\n")\n'
            +'os.execv('+repr(str(path))+',['+repr(str(path))+',*sys.argv[1:]])\n')
        wrapper.chmod(0o755);selected[role]=wrapper
    def invoke(prefix, receipt, toolset=selected):
        command=[sys.executable, '-B', '-I', '-S', str(HELPER), str(prefix), str(receipt)]
        for role, path in toolset.items():command.extend(('--'+role.replace('_','-'),str(path)))
        return subprocess.run(command, capture_output=True, text=True, env=dict(os.environ,PATH='/no-ambient-tools'))
    good = args.work/'good';shutil.copytree(root,good)
    result = invoke(good,args.work/'good.json')
    assert result.returncode == 0, result.stderr
    inventory = json.loads((args.work/'good.json').read_text())
    assert len(inventory['providers'])==2 and len(inventory['consumers'])==2
    assert len(inventory['commands'])==8
    assert all('--force' not in item['argv'] for item in inventory['commands'])
    calls=[json.loads(line) for line in records.read_text().splitlines()]
    assert set(item[0] for item in calls)==set(tools),calls
    assert all(call[1][0] in ('--display','--verify') for call in calls if call[0]=='codesign')
    subprocess.run([str(good/'bin/rustc')],check=True)
    # Entitlements and hardened runtime are outside the pinned plain signature
    # contract. Refusal must precede even the first rename or mutator invocation.
    signed = args.work/'signed';shutil.copytree(root,signed)
    entitlements=args.work/'entitlements.plist'
    entitlements.write_text('<?xml version="1.0"?><plist version="1.0"><dict><key>com.apple.security.cs.allow-jit</key><true/></dict></plist>')
    subprocess.run([str(tools['codesign']),'--force','--sign','-','--identifier','original.custom',
                    '--options','runtime','--entitlements',str(entitlements),str(signed/'bin/rustc')],check=True,capture_output=True)
    before=state(signed);records.write_text('')
    result=invoke(signed,args.work/'signed.json')
    assert result.returncode and 'Unsupported Rust signing metadata' in result.stderr,result.stderr
    assert state(signed)==before and not (args.work/'signed.json').exists()
    calls=[json.loads(line) for line in records.read_text().splitlines()]
    assert not any(call[0]=='install_name_tool' for call in calls)
    missing=args.work/'missing';shutil.copytree(root,missing);before=state(missing)
    result=invoke(missing,args.work/'missing.json',dict(selected,lipo=Path('llvm-lipo')))
    assert result.returncode and 'absolute executable' in result.stderr
    assert state(missing)==before and not (args.work/'missing.json').exists()
    failed=args.work/'failed';shutil.copytree(root,failed)
    verifier=wrappers/'failing-verifier'
    verifier.write_text('#!'+sys.executable+'\nimport os,sys\n'
        +'if "--verify" in sys.argv: raise SystemExit(19)\n'
        +'os.execv('+repr(str(tools['codesign']))+',['+repr(str(tools['codesign']))+',*sys.argv[1:]])\n')
    verifier.chmod(0o755)
    result=invoke(failed,args.work/'failed.json',dict(selected,codesign=verifier))
    assert result.returncode and 'failed' in result.stderr and not (args.work/'failed.json').exists()
    print('PASS: real selected Mach-O tools, automatic LLVM signatures, loader consumer, entitled/runtime refusal before mutation, missing selection and required verification failure.')


if __name__ == '__main__':
    main()
