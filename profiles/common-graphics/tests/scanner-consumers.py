#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), real Meson consumers of host scanner metadata.
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('pkgsrc', 'makeconf', 'llvm-config', 'scanner', 'protocols-source',
                 'mesa-source', 'utility-path', 'work'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    for path in vars(args).values():
        if not path.is_absolute():
            parser.error('all paths must be absolute')
    if args.work.exists():
        parser.error('use a new work directory')
    args.work.mkdir()
    prefix = args.scanner.parent.parent
    if not Path(sys.executable).resolve().is_relative_to(prefix.resolve()):
        parser.error('run with the selected native prefix Python')
    config = args.work/'mk.conf'
    config.write_text('.include "'+str(args.makeconf)+'"\n.if defined(BSD_PKG_MK)\n'
        'WRKOBJDIR='+str(args.work/'objects')+'\nEMBERBSD_COMMON_GRAPHICS_CROSS=yes\n'
        'EMBERBSD_GRAPHICS_LLVM_CONFIG='+str(args.llvm_config)+'\n'
        'EMBERBSD_WAYLAND_SCANNER='+str(args.scanner)+'\n'
        '.include "'+str(args.pkgsrc/'EMBERBSD-COMMON-GRAPHICS-MK.CONF')+'"\n.endif\n')
    environment = dict(os.environ, PATH=str(args.utility_path), PYTHONDONTWRITEBYTECODE='1',
                       NINJA=str(prefix/'bin/ninja'))
    for name in ('PYTHONPATH', 'PYTHONHOME'):
        environment.pop(name, None)
    meson = [sys.executable, '-I', '-B', str(prefix/'bin/meson')]
    ninja = [str(prefix/'bin/ninja'), '-j1']
    checks = []

    def run(name, command, env=environment, success=True):
        result = subprocess.run([str(word) for word in command], env=env, capture_output=True, text=True)
        output = result.stdout+result.stderr
        (args.work/(name+'.log')).write_text(output)
        assert (result.returncode == 0) == success, name+'\n'+output
        return result.stdout

    def base(package):
        return [prefix/'bin/bmake', '-m', prefix/'share/mk', 'SHELL='+str(prefix/'bin/mksh'),
                '-C', args.pkgsrc/package, 'MAKECONF='+str(config)]

    def query(name, command, names, extra=()):
        output = run(name, [*command, *extra, *[item for var in names for item in ('-V', '${'+var+'}')]])
        values = output.splitlines()
        assert len(values) == len(names), output
        return dict(zip(names, values))

    protocols = base('devel/wayland-protocols')
    values = query('protocols-parse', protocols, ['PKG_FAIL_REASON', 'MESON_CROSS_FILE',
        '_EMBERBSD_SCANNER_NATIVE', 'TOOLBASE', 'CROSS_DESTDIR', 'MESON_ARGS'])
    assert not values['PKG_FAIL_REASON'], values
    Path(values['MESON_CROSS_FILE']).parent.mkdir(parents=True, exist_ok=True)
    run('production-guard', [*protocols, 'emberbsd-scanner-check'])
    run('machine-files', [*protocols, values['MESON_CROSS_FILE'], values['_EMBERBSD_SCANNER_NATIVE']])
    native = Path(values['_EMBERBSD_SCANNER_NATIVE']).read_text()
    cross = Path(values['MESON_CROSS_FILE']).read_text()
    assert 'PKG_CONFIG_SYSROOT_DIR=' in native and str(prefix/'lib/pkgconfig') in native
    assert "wayland-scanner = '"+str(args.scanner)+"'" in cross
    checks.append('real protocols recipe and isolated native/cross files')

    swaylock = base('wayland/swaylock')
    selected = query('swaylock-parse', swaylock, ['PKG_FAIL_REASON', 'MESON_BINARIES',
        'MESON_BINARY.wayland-scanner', 'MESON_NATIVE_ARGS'])
    assert not selected['PKG_FAIL_REASON'], selected
    assert 'wayland-scanner' in selected['MESON_BINARIES'].split()
    assert selected['MESON_BINARY.wayland-scanner'] == str(args.scanner)
    assert '--native-file' in selected['MESON_NATIVE_ARGS']
    run('swaylock-scanner-guard', [*swaylock, 'emberbsd-scanner-check'])
    selected = query('swaylock-native', swaylock, ['MESON_BINARIES', 'MESON_BINARY.wayland-scanner'],
                     ['USE_CROSS_COMPILE=no'])
    assert not any(selected.values()), selected
    checks.append('Swaylock cross scanner selection and unchanged native route')

    empty = args.work/'empty-pc';empty.mkdir()
    env = dict(environment, PKG_CONFIG=str(prefix/'bin/pkg-config'),
        PKG_CONFIG_FOR_BUILD=str(prefix/'bin/pkg-config'), PKG_CONFIG_PATH='',
        PKG_CONFIG_PATH_FOR_BUILD='', PKG_CONFIG_LIBDIR=str(empty),
        PKG_CONFIG_SYSROOT_DIR=values['CROSS_DESTDIR'], CMAKE='/usr/bin/false',
        CMAKE_FOR_BUILD='/usr/bin/false')
    common = ['--cross-file', values['MESON_CROSS_FILE'], '--prefix=/usr/pkg',
              '--wrap-mode=nodownload', *shlex.split(values['MESON_ARGS'])]
    run('red-no-native-metadata', [*meson, 'setup', args.work/'red', args.protocols_source, *common], env)
    red = json.loads(run('red-install', [*meson, 'introspect', '--installed', args.work/'red'], env))
    assert not any('/include/wayland-protocols/' in value for value in red.values())
    run('green-configure', [*meson, 'setup', args.work/'green', args.protocols_source,
        *common, '--native-file', values['_EMBERBSD_SCANNER_NATIVE']], env)
    run('green-generate', [*ninja, '-C', args.work/'green'], env)
    installed = json.loads(run('green-install', [*meson, 'introspect', '--installed', args.work/'green'], env))
    headers = {path:value for path,value in installed.items() if value.startswith('/usr/pkg/include/wayland-protocols/')}
    actual = sorted(value.removeprefix('/usr/pkg/') for value in headers.values())
    expected = sorted(line for line in (args.pkgsrc/'devel/wayland-protocols/PLIST').read_text().splitlines()
                      if line.startswith('include/wayland-protocols/'))
    assert expected and actual == expected and all(Path(path).is_file() for path in headers)
    checks.append('actual protocol generation equals complete enum-header PLIST; missing native metadata control omits headers')

    mesa = base('graphics/MesaLib')
    metadata = query('mesa-parse', mesa, ['PKG_FAIL_REASON', 'MESON_CROSS_FILE', '_EMBERBSD_SCANNER_NATIVE',
        'BUILDLINK_API_DEPENDS.wayland', 'BUILDLINK_API_DEPENDS.wayland-protocols'])
    assert not metadata['PKG_FAIL_REASON'], metadata
    assert 'wayland>=1.26.0nb1' in metadata['BUILDLINK_API_DEPENDS.wayland']
    assert 'wayland-protocols>=1.49' in metadata['BUILDLINK_API_DEPENDS.wayland-protocols']
    Path(metadata['MESON_CROSS_FILE']).parent.mkdir(parents=True, exist_ok=True)
    run('mesa-machine-files', [*mesa, metadata['MESON_CROSS_FILE'], metadata['_EMBERBSD_SCANNER_NATIVE'], 'emberbsd-scanner-check'])
    consumer = args.work/'mesa-consumer';consumer.mkdir()
    shutil.copyfile(args.mesa_source/'src/egl/wayland/wayland-drm/wayland-drm.xml', consumer/'wayland-drm.xml')
    import_line = next(line for line in (args.mesa_source/'meson.build').read_text().splitlines(True)
                       if "mod_wl = import('unstable-wayland')" in line)
    scan_line = next(line for line in (args.mesa_source/'src/egl/wayland/wayland-drm/meson.build').read_text().splitlines(True)
                     if line.startswith('_wl_drm = mod_wl.scan_xml('))
    # The language-less scanner fixture does not have target Wayland libraries.
    # Supply only the version consumed by Meson's module from the real recipe;
    # this declaration has no include directories, link flags or ABI claim.
    wayland = query('wayland-version', base('devel/wayland'), ['DISTNAME'])['DISTNAME']
    assert wayland.startswith('wayland-') and wayland.removeprefix('wayland-') == '1.26.0'
    def module_source(version):
        return ("project('mesa-scanner-contract')\n"
            + "meson.override_dependency('wayland-client', declare_dependency(version: '"+version+"'))\n"
            + import_line+scan_line)
    (consumer/'meson.build').write_text(module_source(wayland.removeprefix('wayland-')))
    target_env = dict(env, PKG_CONFIG_LIBDIR=str(Path(values['CROSS_DESTDIR'])/'usr/pkg/lib/pkgconfig'))
    run('mesa-module-configure', [*meson, 'setup', args.work/'mesa-build', consumer,
        '--cross-file', metadata['MESON_CROSS_FILE'], '--native-file', metadata['_EMBERBSD_SCANNER_NATIVE'],
        '--wrap-mode=nodownload'], target_env)
    run('mesa-module-generate', [*ninja, '-C', args.work/'mesa-build', 'wayland-drm-protocol.c',
        'wayland-drm-client-protocol.h', 'wayland-drm-server-protocol.h'], target_env)
    assert str(args.scanner) in (args.work/'mesa-build/build.ninja').read_text()
    assert 'wl_drm_interface' in (args.work/'mesa-build/wayland-drm-protocol.c').read_text()
    checks.append('actual Mesa scan_xml generates C/client/server outputs with recipe version metadata')

    # Only copy the selected generator-role inputs, not the entire compiler
    # prefix. Semantic failures replace the removed standalone hash receipt.
    negative = args.work/'negative-prefix'
    (negative/'bin').mkdir(parents=True);(negative/'lib/pkgconfig').mkdir(parents=True)
    for name in ('python3.15', 'pkg-config', 'wayland-scanner'):
        shutil.copy2(prefix/'bin'/name, negative/'bin'/name)
    pc = negative/'lib/pkgconfig/wayland-scanner.pc'
    original_pc = (prefix/'lib/pkgconfig/wayland-scanner.pc').read_text().replace(str(prefix),str(negative))
    pc.write_text(original_pc)
    override = ['TOOLBASE='+str(negative), 'TOOL_PYTHONBIN='+str(negative/'bin/python3.15'),
                'EMBERBSD_WAYLAND_SCANNER='+str(negative/'bin/wayland-scanner')]
    run('copied-inputs-positive', [*protocols, *override, 'emberbsd-scanner-check'])
    pc.write_text(original_pc.replace('Version: 1.26.0','Version: 1.25.0'))
    output = run('wrong-metadata', [*protocols, *override, 'emberbsd-scanner-check'], success=False)
    # Diagnostics go to the combined log; make stdout can exclude stderr.
    assert 'native metadata disagrees' in (args.work/'wrong-metadata.log').read_text()
    pc.write_text(original_pc)
    scanner = negative/'bin/wayland-scanner';scanner.chmod(scanner.stat().st_mode & ~0o111)
    run('nonexecutable-scanner', [*protocols, *override, 'emberbsd-scanner-check'], success=False)
    assert 'not executable' in (args.work/'nonexecutable-scanner.log').read_text()
    checks.append('actual consumer refuses nonexecutable scanner and inconsistent native metadata')
    summary = {'passed': checks, 'protocol_headers': len(expected),
               'scope': 'real native scanner/Meson generation; no target compilation or package installation'}
    (args.work/'result.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
