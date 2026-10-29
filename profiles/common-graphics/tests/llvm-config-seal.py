#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Real accepted-tool integrity regression.
from pathlib import Path
import shutil
import re
import os
import subprocess
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'cross'))
import llvm_sdk as sdk


def test(args):
    host_baseline = len(args) == 6 and args[3] == '--host-baseline'
    if len(args) != 5 and not host_baseline:
        raise ValueError('usage: llvm-config-seal.py --sdk-source SDK ACCEPTED_WORK ORIGINAL_MANIFEST_SHA256 SEALED_WORK [TARGET_REFERENCE | --host-baseline BASELINE_HELPER] NEW_WORK')
    if host_baseline:
        old, anchor, sealed, _, reference, destination = args
    else:
        old, anchor, sealed, reference, destination = args
    for p in (old, sealed, reference):
        sdk.existing_directory(p)
    work = Path(sdk.new_destination(destination, [old, sealed, reference]))
    work.mkdir()
    cross = Path(__file__).resolve().parents[1] / 'cross'
    sealer = str(cross / 'seal-llvm-config.py')
    comparer = str(cross / 'compare-llvm-config.py')
    checks = []

    def check(name, condition):
        if not condition:
            raise ValueError('FAIL: ' + name)
        checks.append(name)
        print('PASS: ' + name, flush=True)

    def run(name, script, *argv):
        command = [sys.executable, script, '--sdk-source', sdk.sdk_source.load(), *map(str, argv)]
        out, err, status = sdk.query(*command)
        sdk.write_json(work / (name + '.json'), dict(command=command, stdout=out, stderr=err, exit=status))
        return out, err, status

    def refusal(name, fixture, expected, message):
        key = re.sub(r'[^a-z0-9_-]+', '-', name.lower()).strip('-')
        output = work / ('rejected-' + key)
        out, err, status = run(key, sealer, fixture, expected, output)
        check(name, status != 0 and message in err and not output.exists())

    check('caller anchor agrees with original manifest', sdk.digest(old + '/inputs.sha256') == anchor)
    r = sdk.read_json(old + '/receipt.json')
    native_files = [f['path'] for f in r['native_runtime']['files']] if r.get('native_runtime') else []
    darwin_file = r.get('native_darwin_runtime', {}).get('library') if r.get('native_darwin_runtime') else None
    pairs = {'bin/llvm-config.real': 'bin/llvm-config.real', 'receipt.json': 'receipt.json', 'provenance/receipt.json': 'receipt.json', 'provenance/inputs.sha256': 'inputs.sha256', 'provenance/original-launcher': 'bin/llvm-config'}
    check('unchanged compiled executable, historical receipt, manifest and launcher', all(Path(sealed, p).read_bytes() == Path(old, q).read_bytes() for p, q in pairs.items()))
    if darwin_file:
        check('Darwin sealer preserves selected C++ runtime byte for byte', Path(old, darwin_file).read_bytes() == Path(sealed, darwin_file).read_bytes())
        fake_bin = work / 'hostile-path'
        fake_bin.mkdir()
        fake_dirname = fake_bin / 'dirname'
        fake_dirname.write_text('#!/bin/sh\nexit 99\n')
        fake_dirname.chmod(0o755)
        hostile = os.environ.copy()
        hostile['PATH'] = str(fake_bin)
        hostile.update(DYLD_IMAGE_SUFFIX='_no_such_image', DYLD_VERSIONED_LIBRARY_PATH='/nonexistent', DYLD_PRINT_LIBRARIES='1')
        query = subprocess.run([str(Path(sealed) / 'bin/llvm-config'), '--version'], env=hostile, text=True, capture_output=True)
        check('Darwin launcher rejects PATH and DYLD injection', query.returncode == 0 and query.stdout.strip() == '23.1.4' and not query.stderr)
    if native_files:
        check('Linux sealer preserves every native loader/runtime file byte for byte', all(Path(old, p).read_bytes() == Path(sealed, p).read_bytes() for p in native_files))
    if host_baseline:
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location('llvm_compare', comparer)
        comparison = module_from_spec(spec)
        spec.loader.exec_module(comparison)
        comparison_rows = []
        for option in comparison.OPTIONS:
            expected = sdk.query(reference + '/bin/llvm-config', *comparison.arguments(option))
            actual = sdk.query(sealed + '/bin/llvm-config', *comparison.arguments(option))
            comparison_rows.append(dict(option=option, baseline=expected, actual=actual))
            check(option + ' agrees with actual host baseline executable', actual == expected and actual[2] == 0)
        sdk.write_json(work / 'host-baseline-comparison.json', comparison_rows)
    else:
        _, _, status = run('target-agreement', comparer, sealed, reference)
        check('16 real queries agree with supplied target capture', status == 0)
    out, err, status = sdk.query(sealed + '/bin/llvm-config', '--libs', 'ember_unknown_component')
    check('upstream still rejects unknown components', status != 0 and not out and 'unknown component' in err)
    rows = sdk.read_json(sealed + '/seal.json')['observed_inputs']
    check('all original inputs have explicit classes and observations', len(rows) == len(Path(old, 'inputs.sha256').read_text().splitlines()) and all(row['classification'] in ('accepted-local-artifact', 'target-report-metadata', 'installed-target-input', 'historical-build-input') for row in rows) and all(row['classification'] == 'historical-build-input' for row in rows if row['state'] != 'match'))
    paths = [line.split('  ', 1)[1] for line in Path(sealed, 'inputs.sha256').read_text().splitlines()]
    check('sealed runtime receipt has no temporary source/build dependency', all(p.startswith(r['target_prefix'] + '/') for p in paths if p.startswith('/')))
    for i, path in enumerate(['metadata/BuildVariables.inc', 'bin/llvm-config.real', 'receipt.json', *native_files, *([darwin_file] if darwin_file else [])]):
        fixture = work / ('original-drift-' + str(i))
        shutil.copytree(old, fixture)
        with (fixture / path).open('ab') as stream:
            stream.write(b'changed accepted artifact')
        _, err, status = run('original-drift-' + str(i), sealer, fixture, anchor, work / ('rejected-' + str(i)))
        check('sealing rejects original ' + path + ' drift', status != 0 and ('mismatch' in err or 'retained native runtime changed' in err))
        shutil.rmtree(fixture)
    fixture = work / 'manifest-fixture'
    shutil.copytree(old, fixture)
    with (fixture / 'inputs.sha256').open('a') as stream:
        stream.write('0' * 64 + '  /tmp/unknown-build-input\n')
    refusal('changed manifest cannot reuse acceptance anchor', fixture, anchor, 'original manifest hash mismatch')
    refusal('unknown paths cannot become disposable build inputs', fixture, sdk.digest(fixture / 'inputs.sha256'), 'unclassified original inputs')
    shutil.rmtree(fixture)
    shutil.copytree(old, fixture)
    removed = r['native_build'] + '/CMakeCache.txt'
    path = fixture / 'inputs.sha256'
    path.write_text(''.join(line for line in path.read_text().splitlines(keepends=True) if not line.endswith('  ' + removed + '\n')))
    refusal('missing required historical classifications cannot be dropped', fixture, sdk.digest(path), 'missing required original inputs')
    shutil.rmtree(fixture)
    for name, entry in {'report-metadata': r['target_build'] + '/tools/llvm-config/BuildVariables.inc', 'target-header': r['target_prefix'] + '/include/llvm/Config/llvm-config.h'}.items():
        shutil.copytree(old, fixture)
        path = fixture / 'inputs.sha256'
        lines = path.read_text().splitlines(keepends=True)
        if not any(line.endswith('  ' + entry + '\n') for line in lines):
            raise ValueError('fixture path not recorded')
        path.write_text(''.join('0' * 64 + '  ' + entry + '\n' if line.endswith('  ' + entry + '\n') else line for line in lines))
        refusal('required-' + name + '-hash-mismatch', fixture, sdk.digest(path), 'mismatch')
        shutil.rmtree(fixture)
    clone = work / 'sealed-historical-drift'
    shutil.copytree(sealed, clone)
    with (clone / 'inputs.sha256').open('a') as stream:
        stream.write('0' * 64 + '  /unrelated/sdk/module.py\n')
    out, _, status = sdk.query(str(clone / 'bin/llvm-config'), '--version')
    check('unrelated historical input does not block queries', status == 0 and out.strip() == '23.1.4')
    shutil.rmtree(clone)
    sdk.write_json(work / 'result.json', dict(checks=checks, scope=('Host migration equivalence against actual baseline executable; no fresh target capture or execution' if host_baseline else 'Host seal/query integrity against supplied real target capture; no target execution')))
    return 0


if __name__ == '__main__':
    sys.exit(sdk.main(test))
