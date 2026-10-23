#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted). Port of the Ruby verifier test.
"""Exercise production byte/interface checks; never execute fixture tools."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
PORTS = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PORTS / 'pkgsrc/lang/llvm/files'))
import sdk_source


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def test(arguments):
    from emberbsd_sdk.errors import CommandError
    from emberbsd_sdk.process import capture
    if len(arguments) != 3:
        raise ValueError('Use mesa-generators.py --sdk-source SDK DIGEST SEALED_TOOLS NEW_WORK')
    hash_tool, sealed = [Path(value).resolve(strict=True) for value in arguments[:2]]
    work = Path(os.path.abspath(arguments[2]))
    if not arguments[2].startswith('/') or os.path.lexists(work):
        raise ValueError('Use a new absolute work directory')
    work.mkdir(parents=True)
    verifier = PORTS / 'pkgsrc/graphics/MesaLib/verify-mesa-generators.sh'
    source = work / 'source'
    source.mkdir()
    (source / 'VERSION').write_text('26.2.5\n')
    origin = Path(json.loads((sealed / 'receipt.json').read_text())['source'])
    for line in (sealed / 'interface.sha256').read_text().splitlines():
        _, name = line.split()
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origin / name, target)
    patch = PORTS / 'pkgsrc/graphics/MesaLib/patches/patch-src_imagination_common_pvr__iface.h'
    if (source / 'src/imagination/common/pvr_iface.h').is_file():
        capture(['patch', '--no-backup-if-mismatch', '-f', '-N', '-F', '0', '-p0', '-d', str(source), '-i', str(patch)])
    checks = 0

    def run(name, tools, valid, selected='powervr', script=verifier):
        nonlocal checks
        try:
            result = capture(['sh', str(script), str(hash_tool), str(tools), str(source), selected])
            output, status = result.stdout + result.stderr, 0
        except CommandError as error:
            output, status = error.stdout + error.stderr, error.returncode
        (work / (name + '.log')).write_bytes(output)
        if (status == 0) != valid:
            raise ValueError('Unexpected verifier result: ' + name)
        checks += 1

    selected = (sealed / 'PROFILES').read_text().strip() if (sealed / 'PROFILES').is_file() else 'powervr'
    run('real-tools', sealed, True, selected)
    fixture = work / 'fixture'
    (fixture / 'bin').mkdir(parents=True)
    (fixture / 'FORMAT').write_text('ember-mesa-generators-1\n')
    (fixture / 'receipt.json').write_text('{}\n')
    shutil.copy2(sealed / 'interface.sha256', fixture / 'interface.sha256')
    for name in ('mesa_clc', 'vtn_bindgen2', 'pco_clc'):
        binary = fixture / 'bin' / name
        binary.write_text('never executed\n')
        binary.chmod(0o755)
    manifest = ''.join(f'{digest(path)}  {path.relative_to(fixture)}\n'
                       for path in sorted(fixture.rglob('*')) if path.is_file())
    receipt = fixture / 'installed.sha256'
    receipt.write_text(manifest)
    run('model-positive', fixture, True)
    names = ('missing-tool', 'changed-tool', 'missing-manifest-entry', 'duplicate-tool', 'bad-hash',
             'traversal', 'changed-abi', 'changed-last-tool-no-lf', 'changed-last-interface-no-lf', 'wrong-version')
    for name in names:
        backup, source_backup = work / 'save', work / 'save-source'
        shutil.copytree(fixture, backup)
        shutil.copytree(source, source_backup)
        binary = fixture / 'bin/pco_clc'
        row = next(line for line in manifest.splitlines(keepends=True) if line.endswith('bin/pco_clc\n'))
        if name == 'missing-tool':
            binary.unlink()
        elif name == 'changed-tool':
            binary.write_text('changed')
        elif name == 'missing-manifest-entry':
            receipt.write_text(manifest.replace(row, ''))
        elif name == 'duplicate-tool':
            receipt.write_text(manifest + row)
        elif name == 'bad-hash':
            receipt.write_text('x' + manifest[1:])
        elif name == 'traversal':
            receipt.write_text(manifest + '0' * 64 + '  ../secret\n')
        elif name == 'changed-abi':
            (source / 'src/compiler/nir/nir.h').write_text('changed')
        elif name == 'changed-last-tool-no-lf':
            receipt.write_text((manifest.replace(row, '') + row).removesuffix('\n'))
            binary.write_text('changed')
        elif name == 'changed-last-interface-no-lf':
            interface = fixture / 'interface.sha256'
            content = interface.read_text().removesuffix('\n')
            interface.write_text(content)
            receipt.write_text(''.join(f'{digest(interface)}  interface.sha256\n'
                if line.endswith('interface.sha256\n') else line for line in manifest.splitlines(keepends=True)))
            (source / content.splitlines()[-1].split()[-1]).write_text('changed')
        elif name == 'wrong-version':
            (source / 'VERSION').write_text('26.2.4\n')
        run(name, fixture, False)
        if name.endswith('no-lf'):
            old = work / 'verifier-old-final-line.sh'
            old.write_text(verifier.read_text().replace(' || [ -n "$expected$file$extra" ]', ''))
            run(name + '-causal', fixture, True, script=old)
        shutil.rmtree(fixture)
        backup.rename(fixture)
        shutil.rmtree(source)
        source_backup.rename(source)
    mutant = work / 'verifier-without-hash.sh'
    guard = '[ "${actual##* }" = "$expected" ] || fail "changed file: $file"'
    if guard not in verifier.read_text():
        raise ValueError('Causal hash guard is absent from the real verifier')
    mutant.write_text(verifier.read_text().replace(guard, ':'))
    (fixture / 'bin/pco_clc').write_text('changed')
    run('causal-missing-hash', fixture, True, script=mutant)
    print(f'PASS: {checks} production receipt/interface checks, including causal controls')


if __name__ == '__main__':
    sdk_source.install_signal_handlers()
    try:
        if sys.version_info[:2] != (3, 15):
            raise ValueError('Host Python 3.15 is required')
        _, arguments = sdk_source.load_sdk()
        test(arguments)
    except Exception as error:
        sdk_source.exit_error(error)
