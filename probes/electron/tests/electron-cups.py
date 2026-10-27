#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Exercise Chromium's CUPS configuration with real GN and pkg-config."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def cups_block(text):
    start = text.index('if (use_cups) {\n  if (is_chromeos_device) {') if 'if (use_cups) {\n  if (is_chromeos_device) {' in text else text.index('if (use_cups) {\n  # NetBSD CUPS')
    finish = text.index('\nif (is_android) {', start)
    return text[start:finish]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'work', 'git', 'gn', 'pkg-config', 'utility-path'):
        parser.add_argument('--' + name, required=True)
    options = parser.parse_args()
    source, work = Path(options.source), Path(options.work)
    assert source.is_absolute() and work.is_absolute() and not work.exists()
    assert not work.is_relative_to(source)
    work.mkdir(parents=True)
    env = dict(PATH=options.utility_path, LC_ALL='C', PYTHONDONTWRITEBYTECODE='1')
    commands = []
    def run(label, argv, cwd, error=None):
        result = subprocess.run(list(map(str, argv)), cwd=cwd, env=env, text=True, capture_output=True)
        output = result.stdout + result.stderr
        (work / (label + '.log')).write_text(output)
        commands.append(dict(label=label, argv=list(map(str, argv)), status=result.returncode))
        assert (result.returncode == 0 if error is None else result.returncode != 0 and error in output), label + ': ' + output
        return result.stdout
    baseline = work / 'baseline'
    names = ('printing/BUILD.gn', 'printing/cups_config_helper.py',
             'build/config/linux/pkg_config.gni', 'build/config/linux/pkg-config.py')
    before = {}
    for name in names:
        path = baseline / name; path.parent.mkdir(parents=True, exist_ok=True)
        data = (source / name).read_bytes(); path.write_bytes(data)
        before[name] = hashlib.sha256(data).hexdigest()
    patched = work / 'patched'; shutil.copytree(baseline, patched)
    patch = Path(__file__).resolve().parents[1] / 'patches/gn-netbsd-cups-pkgconfig.patch'
    run('patch-check', [options.git, 'apply', '--check', patch], patched)
    run('patch', [options.git, 'apply', patch], patched)
    # This is deliberately metadata-only test data, not a target package or ABI.
    metadata = '''prefix=/usr/pkg
exec_prefix=${prefix}
libdir=${prefix}/lib
includedir=${prefix}/include
Name: cups
Description: CUPS metadata fixture
Version: 2.4.20
Libs: -L${libdir} -lcups
Cflags: -I${includedir} -DCUPS_METADATA_FIXTURE=1
'''
    def fixture(label, *, old=False, platform='netbsd', present=True, printing=True):
        root = work / label; shutil.copytree(baseline if old else patched, root)
        for name in ('compute_inputs_for_analyze', 'gclient_args', 'sysroot'):
            (root / ('build/config/' + name + '.gni')).write_text('')
        (root / 'build/toolchain').mkdir(); (root / 'build/toolchain/rbe.gni').write_text('')
        sysroot = root / 'sysroot'; (sysroot / 'usr/pkg/lib/pkgconfig').mkdir(parents=True)
        if present:
            (sysroot / 'usr/pkg/lib/pkgconfig/cups.pc').write_text(metadata)
        # If the old helper executes this target script, the marker proves it.
        marker = root / 'target-script-executed'
        target_bin = sysroot / 'usr/bin'; target_bin.mkdir()
        script = target_bin / 'cups-config'
        script.write_text('#!' + sys.executable + '\nfrom pathlib import Path\nPath(' + repr(str(marker)) + ').write_text("executed")\nprint("-lwrong_target_script")\n')
        script.chmod(0o755)
        (root / '.gn').write_text('buildconfig="//BUILDCONFIG.gn"\nscript_executable=' + json.dumps(sys.executable) + '\n')
        buildconfig = dict(host_os='mac', current_os=platform, current_cpu='x64',
            host_toolchain='//:host', sysroot=str(sysroot), target_sysroot=str(sysroot),
            emberbsd_target_sysroot=str(sysroot), use_sysroot=True, use_remoteexec=False,
            build_with_chromium=False, compute_inputs_for_analyze=False,
            is_chromeos_device=platform=='chromeos', is_netbsd=platform=='netbsd',
            is_mac=platform=='mac', use_cups=printing, mac_sdk_path='/declared/macos-sdk')
        def value(v): return str(v).lower() if isinstance(v, bool) else json.dumps(v)
        (root / 'BUILDCONFIG.gn').write_text(''.join(k+'='+value(v)+'\n' for k,v in buildconfig.items())+'set_default_toolchain("//:target")\n')
        selected = cups_block((root / 'printing/BUILD.gn').read_text())
        (root / 'printing/BUILD.gn').write_text('import("//build/config/linux/pkg_config.gni")\n' + selected + '\n' + ('group("selected") { public_configs=[":cups"] }\n' if printing else 'group("selected") {}\n'))
        (root / 'BUILD.gn').write_text('group("all") { deps=["//printing:selected"] }\ntoolchain("target") { tool("stamp") { command="touch {{output}}" } }\n')
        argv = [options.gn, 'gen', root / 'out', '--args=pkg_config=' + json.dumps(options.pkg_config) + ' system_libdir="pkg/lib"']
        error = 'cups' if not present and printing and platform!='mac' and not old else None
        run(label + '-gen', argv, root, error)
        if error is not None: return root, None
        if not printing: return root, {}
        result = json.loads(run(label + '-desc', [options.gn, 'desc', root / 'out', '//printing:cups', '--format=json'], root))['//printing:cups']
        return root, result

    old, output = fixture('old-target-execution', old=True)
    assert (old / 'target-script-executed').is_file() and output['libs']==['wrong_target_script'], output
    selected, output = fixture('netbsd')
    assert not (selected / 'target-script-executed').exists()
    assert output['libs']==['cups'] and output['cflags']==['-DCUPS_METADATA_FIXTURE=1'], output
    assert output['lib_dirs']==['//sysroot/usr/pkg/lib/'], output
    assert 'sysroot/usr/pkg/include' in output['cflags_c'][0], output
    missing, _ = fixture('missing-target-pc', present=False)
    assert not (missing / 'target-script-executed').exists()
    mac, output = fixture('mac', platform='mac')
    assert output['libs']==['cups'] and output['lib_dirs']==['/declared/macos-sdk/usr/lib/'], output
    assert not (mac / 'target-script-executed').exists()
    chromeos, output = fixture('chromeos', platform='chromeos')
    # Chromium's platform emulation guard intentionally makes this empty on Darwin;
    # the original pkg_config branch is preserved, not a target-script invocation.
    assert not (chromeos / 'target-script-executed').exists()
    disabled, _ = fixture('printing-disabled', printing=False, present=False)
    assert not (disabled / 'target-script-executed').exists()
    assert before == {name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in names}
    (work / 'result.json').write_text(json.dumps(dict(scope='real GN and pkg-config on explicit metadata fixtures; no CUPS library compile or target ABI claim', commands=commands),indent=2)+'\n')
    print('PASS: actual CUPS GN configuration, target metadata, baseline target-script execution, missing input refusal and other platform selections')


if __name__ == '__main__':
    main()
