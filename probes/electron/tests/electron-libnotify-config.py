#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check Electron's libnotify GN config using real pkg-config metadata."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for key in ('source', 'work', 'git', 'gn', 'pkg-config', 'utility-path'):
        ap.add_argument('--' + key, required=True)
    o = ap.parse_args()
    source, work = Path(o.source), Path(o.work)
    assert source.is_absolute() and work.is_absolute() and not work.exists()
    work.mkdir(parents=True)
    env = dict(PATH=o.utility_path, LC_ALL='C', PYTHONDONTWRITEBYTECODE='1')
    def run(*args):
        return subprocess.run(list(map(str, args)), cwd=work, env=env, text=True,
                              capture_output=True, check=True).stdout
    for name in ('electron/BUILD.gn', 'build/config/linux/pkg_config.gni',
                 'build/config/linux/pkg-config.py'):
        dst = work / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, dst)
    # Apply only Electron GN hunk from the same versioned patch.
    patch = Path(__file__).resolve().parents[1] / 'patches/electron-logging-singleton-libnotify.patch'
    run(o.git, 'apply', '--include=electron/BUILD.gn', patch)
    text = (work / 'electron/BUILD.gn').read_text()
    start = text.index('  pkg_config("libnotify_dependencies") {')
    end = text.index('  generate_library_loader("libnotify_loader") {', start)
    block = text[start:end]
    (work / 'electron/BUILD.gn').write_text('import("//build/config/linux/pkg_config.gni")\n' + block)
    for name in ('compute_inputs_for_analyze', 'gclient_args', 'sysroot'):
        (work / ('build/config/' + name + '.gni')).write_text('')
    (work / 'build/toolchain').mkdir(parents=True, exist_ok=True)
    (work / 'build/toolchain/rbe.gni').write_text('')
    sysroot = work / 'sysroot'
    pcdir = sysroot / 'usr/pkg/lib/pkgconfig'
    pcdir.mkdir(parents=True)
    for name, lib in (('libnotify', 'notify'), ('glib-2.0', 'glibfixture'), ('gdk-pixbuf-2.0', 'gdkfixture')):
        (pcdir / (name + '.pc')).write_text('prefix=/usr/pkg\nincludedir=${prefix}/include\nlibdir=${prefix}/lib\nName: '+name+'\nDescription: fixture\nVersion: 1\nLibs: -L${libdir} -l'+lib+'\nCflags: -I${includedir}/'+name+'\n')
    (work / '.gn').write_text('buildconfig="//BUILDCONFIG.gn"\nscript_executable=' + json.dumps(sys.executable) + '\n')
    settings = dict(host_os='mac', current_os='netbsd', current_cpu='x64', host_toolchain='//:host',
                    sysroot=str(sysroot), target_sysroot=str(sysroot), emberbsd_target_sysroot=str(sysroot),
                    use_sysroot=True, use_remoteexec=False, build_with_chromium=False,
                    compute_inputs_for_analyze=False)
    def value(v): return str(v).lower() if isinstance(v, bool) else json.dumps(v)
    (work / 'BUILDCONFIG.gn').write_text(''.join(k+'='+value(v)+'\n' for k,v in settings.items())+'set_default_toolchain("//:target")\n')
    (work / 'BUILD.gn').write_text('source_set("all") { configs=["//electron:libnotify_config"] }\ntoolchain("target") { tool("stamp") { command="touch {{output}}" } }\n')
    run(o.gn, 'gen', work / 'out', '--args=pkg_config=' + json.dumps(o.pkg_config) + ' system_libdir="pkg/lib"')
    result = json.loads(run(o.gn, 'desc', work / 'out', '//:all', '--format=json'))['//:all']
    libs = result.get('libs', [])
    includes = ' '.join(result.get('cflags_c', []) + result.get('include_dirs', []))
    assert 'notify' not in libs and 'glibfixture' in libs and 'gdkfixture' in libs, result
    assert 'libnotify' in includes, result
    print('PASS: libnotify headers and dependency libraries without direct -lnotify')

if __name__ == '__main__':
    main()
