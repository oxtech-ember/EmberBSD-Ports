#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise Mesa's actual language-selection fragments with Meson.

Usage: mesa-host-objc.py MESA_ARCHIVE MESON_SCRIPT PATCH_TOOL NEW_WORK
No C, C++ or Objective-C compiler is run. Objective-C consumers must fail
at the explicit absent compiler; other configurations must complete setup.
This checks configuration only, not a complete Mesa build.
"""
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile

sys.dont_write_bytecode = True
PORTS = Path(__file__).resolve().parents[3]
ARCHIVE_SHA256 = '794b3d1729075dae7ebd47c7283b7ca0cdb5dec668f7f11cc0a5d82f6138a0a5'


def section(source, begin, end):
    start = source.index(begin)
    return source[start:source.index(end, start)]


def fragment(source):
    """Use production statements, including the upstream platform defaults."""
    result = section(source, "if host_machine.system() == 'darwin'\n", "cc = meson.get_compiler('c')")
    result += re.search(r'^system_has_kms_drm = .*$', source, re.M).group() + '\n'
    result += section(source, "_vulkan_drivers = get_option('vulkan-drivers')", 'with_intel_vk = ')
    result += re.search(r'^with_kosmickrisp_vk = .*$', source, re.M).group() + '\n'
    result += section(source, "_platforms = get_option('platforms')", 'with_gfxstream_emulated_android = ')
    args = re.search(r"^if [^\n]+\n  add_project_arguments\(pre_args, language : \['objc'\]\)\nendif", source, re.M)
    if args is None:
        raise ValueError('Missing production Objective-C argument block')
    return result + "pre_args = ['-DMESA_OBJC_CONFIGURATION_TEST']\n" + args.group() + '\n'


def main():
    from mesonbuild import build
    if len(sys.argv) != 5:
        raise ValueError(__doc__)
    archive, meson, patch = [Path(value).resolve(strict=True) for value in sys.argv[1:4]]
    work = Path(sys.argv[4])
    if not work.is_absolute() or os.path.lexists(work):
        raise ValueError('Use a new absolute work directory')
    with archive.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != ARCHIVE_SHA256:
            raise ValueError('Unexpected Mesa archive')
    work.mkdir(parents=True)
    source = work / 'source'
    source.mkdir()
    with tarfile.open(archive) as bundle:
        upstream = bundle.extractfile('mesa-26.2.5/meson.build').read().decode()
    (source / 'meson.build').write_text(upstream)
    shared_patch = PORTS / 'pkgsrc/graphics/MesaLib/patches/patch-meson.build-host-objc'
    patch_data = b''.join(line for line in shared_patch.read_bytes().splitlines(keepends=True)
                          if b'$NetBSD' not in line)
    expected = f'SHA1 ({shared_patch.name}) = {hashlib.sha1(patch_data).hexdigest()}'
    if expected not in (shared_patch.parent.parent / 'distinfo').read_text().splitlines():
        raise ValueError('Shared patch differs from distinfo')
    subprocess.run([str(patch), '-f', '-F', '0', '-p0', '-d', str(source), '-i', str(shared_patch)], check=True)
    patched = (source / 'meson.build').read_text()
    missing = work / 'missing-objc-compiler'
    env = os.environ.copy()
    for key in ('PYTHONPATH', 'PYTHONHOME', 'OBJC', 'OBJC_FOR_BUILD'):
        env.pop(key, None)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['PATH'] = str(patch.parent)
    cases = [
        ('generators', patched, 'darwin', '[]', '[]', None),
        ('darwin-x11', patched, 'darwin', 'x11', '[]', None),
        ('darwin-default', patched, 'darwin', 'auto', 'auto', 'compiler'),
        ('metal-wsi', patched, 'darwin', 'macos', '[]', 'compiler'),
        ('kosmickrisp-offscreen', patched, 'darwin', '[]', 'kosmickrisp', 'compiler'),
        ('netbsd-default', patched, 'netbsd', 'auto', 'auto', None),
        ('netbsd-kosmickrisp-stubs', patched, 'netbsd', '[]', 'kosmickrisp', None),
        ('upstream-generators-causal', upstream, 'darwin', '[]', '[]', 'compiler'),
        ('old-argument-guard-causal', patched.replace('if with_objc\n  add_project_arguments',
            "if host_machine.system() == 'darwin'\n  add_project_arguments"), 'darwin', '[]', '[]', 'arguments'),
    ]
    for name, text, system, platforms, drivers, failure in cases:
        case = work / name
        case.mkdir()
        (case / 'meson.options').write_text(
            "option('platforms', type: 'array', value: ['auto'])\n"
            "option('vulkan-drivers', type: 'array', value: ['auto'])\n")
        (case / 'meson.build').write_text("project('mesa-objc-selection', meson_version: '>= 1.12.1')\n" + fragment(text))
        machine = case / 'cross.ini'
        machine.write_text(f"[binaries]\nobjc = '{missing}'\n[host_machine]\nsystem = '{system}'\n"
                           "cpu_family = 'aarch64'\ncpu = 'aarch64'\nendian = 'little'\n")
        command = [sys.executable, '-B', str(meson), 'setup', '--backend=none',
                   '--cross-file', str(machine), str(case / 'build'), str(case),
                   '-Dplatforms=' + platforms, '-Dvulkan-drivers=' + drivers]
        result = subprocess.run(command, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (case / 'result.log').write_text(result.stdout)
        objc_args = (build.load(str(case / 'build')).projects.host[''].project_args.host.get('objc', [])
                     if result.returncode == 0 else [])
        if failure is None:
            valid = result.returncode == 0 and not objc_args
        elif failure == 'compiler':
            valid = result.returncode != 0 and 'Unknown compiler(s)' in result.stdout and str(missing) in result.stdout
        else:
            valid = result.returncode == 0 and objc_args == ['-DMESA_OBJC_CONFIGURATION_TEST']
        if not valid:
            raise ValueError(f'{name}: unexpected Meson result\n{result.stdout}')
        print('PASS:', name)
    print(f'PASS: {len(cases)} actual Meson selection cases; no compiler execution')


if __name__ == '__main__':
    main()
