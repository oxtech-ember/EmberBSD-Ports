#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Exercise the Chromium snapshot PaX action using real GN, without building."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys


def block(text, anchor):
    start = text.index(anchor)
    brace = text.index('{', start)
    depth = 0
    for i in range(brace, len(text)):
        if text[i] == '{': depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0: return text[start:i + 1]
    raise ValueError('unterminated GN block')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'v8-source', 'work', 'gn', 'git'):
        ap.add_argument('--' + name, required=True)
    o = ap.parse_args()
    source, work = Path(o.source), Path(o.work)
    assert source.is_absolute() and work.is_absolute() and not work.exists()
    work.mkdir(parents=True)
    path = work / 'tools/v8_context_snapshot/BUILD.gn'
    path.parent.mkdir(parents=True)
    shutil.copyfile(source / 'tools/v8_context_snapshot/BUILD.gn', path)
    patch = Path(__file__).resolve().parents[1] / 'patches/chromium-snapshot-host-paxctl.patch'
    subprocess.run([o.git, 'apply', '--check', str(patch)], cwd=work, check=True)
    subprocess.run([o.git, 'apply', str(patch)], cwd=work, check=True)
    text = path.read_text()
    action = block(text, 'if (host_os == "netbsd") {')
    # Keep the real action and dependency conditional, with unrelated targets as stubs.
    generate = block(text, 'action("generate_v8_context_snapshot") {')
    conditional = block(generate, 'if (host_os == "netbsd") {')
    (work / '.gn').write_text('buildconfig="//BUILDCONFIG.gn"\nscript_executable=' + json.dumps(sys.executable) + '\n')
    (work / 'BUILDCONFIG.gn').write_text('set_default_toolchain("//:default")\n')
    (work / 'BUILD.gn').write_text('group("all") { deps=["//tools/v8_context_snapshot:consumer", "//v8:consumer"] }\ntoolchain("default") { tool("stamp") { command="touch {{output}}" } tool("link") { command="true" outputs=["{{root_out_dir}}/{{target_output_name}}"] } }\ntoolchain("snapshot") { tool("stamp") { command="touch {{output}}" } tool("link") { command="true" outputs=["{{root_out_dir}}/{{target_output_name}}"] } }\n')
    (work / 'v8/tools').mkdir(parents=True)
    (work / 'v8/gni').mkdir(parents=True)
    declaration = block((Path(o.v8_source) / 'gni/snapshot_toolchain.gni').read_text(), 'declare_args() {')
    (work / 'v8/gni/snapshot_toolchain.gni').write_text(declaration + '\n')
    (work / 'v8/BUILD.gn').write_text('import("//v8/gni/snapshot_toolchain.gni")\nnot_needed([ "v8_host_paxctl", "v8_snapshot_toolchain" ])\ngroup("consumer") {}\n')
    (work / 'v8/tools/run-paxctl.py').write_text('# fixture action script is not executed\n')
    path.write_text('import("//v8/gni/snapshot_toolchain.gni")\nv8_snapshot_toolchain="//:snapshot"\nnot_needed([ "v8_snapshot_toolchain" ])\n'+action+'\nexecutable("v8_context_snapshot_generator") {}\ngroup("consumer") { deps=[]\n'+conditional+'\n}\n')
    def run(host, utility):
        out = work / ('out-' + host + ('-selected' if utility else '-missing'))
        (work / 'BUILDCONFIG.gn').write_text('host_os=' + json.dumps(host) + '\ntarget_os=' + json.dumps('linux' if host == 'netbsd' else 'netbsd') + '\nset_default_toolchain("//:default")\n')
        args = 'v8_host_paxctl=' + json.dumps(utility)
        return out, subprocess.run([o.gn, 'gen', str(out), '--args='+args], cwd=work, text=True, capture_output=True)
    for host in ('mac', 'linux'):
        out, r = run(host, '')
        assert r.returncode == 0, r.stdout+r.stderr
        result = subprocess.run([o.gn, 'ls', str(out), '//tools/v8_context_snapshot:run_paxctl_v8_context_snapshot_generator'], cwd=work, text=True, capture_output=True)
        assert not result.stdout.strip(), result.stdout
    _, missing = run('netbsd', '')
    assert missing.returncode and 'explicit paxctl path' in missing.stdout+missing.stderr
    selected = str(work / 'selected-paxctl')
    Path(selected).write_text('fixture utility not executed\n')
    out, result = run('netbsd', selected)
    assert result.returncode == 0, result.stdout+result.stderr
    data = json.loads(subprocess.check_output([o.gn, 'desc', str(out), '//tools/v8_context_snapshot:run_paxctl_v8_context_snapshot_generator', '--format=json'], cwd=work, text=True))
    row = data['//tools/v8_context_snapshot:run_paxctl_v8_context_snapshot_generator']
    assert selected in row['args'] and row['inputs'] == ['//selected-paxctl'], row
    assert any('snapshot/v8_context_snapshot_generator' in x for x in row['args']), row
    assert '/usr/sbin/paxctl' not in row['args'], row
    print('PASS: mac/Linux cross skip; NetBSD host requires selected path and uses snapshot toolchain')

if __name__ == '__main__': main()
