#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Ported from gdk-pixbuf-cross.rb.
"""Check patched Meson selection and installed GdkPixbuf build rules."""

import argparse
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def load_sdk(source):
    require(source and os.path.isabs(source), 'set an absolute --sdk-source or EMBERBSD_SDK_SOURCE')
    root = Path(source).resolve(strict=True)
    package = root / 'src/emberbsd_sdk'
    require((package / '__init__.py').is_file(), 'SDK source has no emberbsd_sdk API')
    sys.path.insert(0, str(root / 'src'))
    import emberbsd_sdk
    require(type(emberbsd_sdk.API_VERSION) is int and emberbsd_sdk.API_VERSION == 1 and
            Path(emberbsd_sdk.__file__).resolve().parent == package,
            'the selected SDK must provide API version 1')
    from emberbsd_sdk.errors import CommandError, SDKError
    from emberbsd_sdk.inventory import sha256_file
    from emberbsd_sdk.jsonio import read_json, write_json
    from emberbsd_sdk.paths import canonical_existing, canonical_new
    from emberbsd_sdk.process import capture
    return SimpleNamespace(root=str(root), CommandError=CommandError, SDKError=SDKError,
                           sha256_file=sha256_file, read_json=read_json, write_json=write_json,
                           canonical_existing=canonical_existing, canonical_new=canonical_new,
                           capture=capture)


def meson_string(value):
    return "'" + os.fspath(value).replace('\\', '\\\\').replace("'", "\\'") + "'"


def main():
    recipe = Path(__file__).resolve().parent.parent / '../../pkgsrc'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-source', default=os.environ.get('EMBERBSD_SDK_SOURCE'))
    parser.add_argument('--helper', default=str(recipe / 'graphics/gdk-pixbuf2/files/target-tools.py'))
    parser.add_argument('--elf-needed', default=str(recipe / 'devel/gobject-introspection/files/elf-needed.sh'))
    parser.add_argument('built_source', metavar='BUILT_SOURCE')
    parser.add_argument('host_prefix', metavar='HOST_PREFIX')
    parser.add_argument('cross_cc', metavar='CROSS_CC')
    parser.add_argument('new_work', metavar='NEW_WORK')
    options = parser.parse_args()
    require(sys.implementation.name == 'cpython' and sys.version_info[:2] == (3, 15),
            'select build-host CPython 3.15')
    require(os.path.isabs(sys.executable), 'sys.executable must be absolute')
    sdk = load_sdk(options.sdk_source)
    python = sdk.canonical_existing(sys.executable)
    require(os.access(python, os.X_OK), 'selected Python is not executable')
    source, host, cc, helper, needed = (sdk.canonical_existing(value) for value in
        (options.built_source, options.host_prefix, options.cross_cc, options.helper, options.elf_needed))
    require(os.path.isabs(options.new_work), 'new absolute work required')
    work = Path(sdk.canonical_new(options.new_work))
    require(not os.path.lexists(work), 'new absolute work required')
    (work / 'source/build-aux').mkdir(parents=True)
    root = Path(source + '/meson.build').read_text(encoding='utf-8')
    start = root.find("if meson.is_cross_build() and meson.get_external_property('emberbsd_gi_cross'")
    require(start != -1, 'missing native Python selection')
    finish = root.find('\nendif', start)
    require(finish != -1, 'missing Python selection end')
    root = root[start:finish + 7]
    selection = Path(source + '/gdk-pixbuf/meson.build').read_text(encoding='utf-8')
    start = selection.find('emberbsd_gi_cross =')
    require(start != -1, 'missing GI selection')
    finish = selection.find('  gdkpixbuf_gir =', start)
    require(finish != -1, 'missing GI selection end')
    selection = selection[start:finish] + 'endif\n'
    (work / 'source/meson.options').write_text(
        "option('introspection', type: 'feature', value: 'enabled')\n", encoding='utf-8')
    generator = work / 'source/build-aux/gen-thumbnailer.py'
    generator.write_text('#!/usr/bin/env python3\n', encoding='utf-8')
    generator.chmod(0o755)
    (work / 'source/meson.build').write_text(
        "project('pixbuf-tool-selection', 'c')\n" + root + selection + '''if emberbsd_gi_cross
  message('native scanner: ' + gir.full_path())
  message('native compiler: ' + gir_compiler.full_path())
  message('native python: ' + gen_thumbnailer[0].full_path())
else
  message('ordinary generator: ' + gen_thumbnailer.full_path())
endif
message('scanner arguments: ' + ' '.join(gir_args))
''', encoding='utf-8')
    properties = ('emberbsd_gi_cross = true\nemberbsd_pixbuf_python = ' + meson_string(python) +
                  '\nemberbsd_gi_ldd_wrapper = ' + meson_string(needed) +
                  '\nemberbsd_pixbuf_runner = [' + meson_string(python) + ", '-E', '-S', " +
                  meson_string(helper) + ']\n')
    binaries = '[binaries]\nc = ' + meson_string(cc) + "\ng-ir-scanner = '/usr/bin/false'\n"
    machine = "[host_machine]\nsystem = 'netbsd'\ncpu_family = 'aarch64'\ncpu = 'aarch64'\nendian = 'little'\n"
    (work / 'cross.ini').write_text(binaries + machine, encoding='utf-8')
    (work / 'enabled.ini').write_text(binaries + machine + '[properties]\n' + properties, encoding='utf-8')
    (work / 'native.ini').write_text(
        "[binaries]\nc = '/usr/bin/cc'\ng-ir-scanner = " + meson_string(host + '/bin/g-ir-scanner') +
        '\ng-ir-compiler = ' + meson_string(host + '/bin/g-ir-compiler') +
        '\n[properties]\n' + properties, encoding='utf-8')
    environment = dict(os.environ, PATH=host + '/bin:/usr/bin:/bin', EMBERBSD_SDK_SOURCE=sdk.root,
                       PYTHONDONTWRITEBYTECODE='1')
    for name in ('CC', 'CFLAGS', 'LDFLAGS', 'LD_LIBRARY_PATH', 'LD_PRELOAD', 'DYLD_LIBRARY_PATH'):
        environment.pop(name, None)

    def capture(name, command):
        try:
            result = sdk.capture(list(map(os.fspath, command)), cwd=str(work), env=environment)
        except sdk.CommandError as error:
            result = subprocess.CompletedProcess(error.argv, error.returncode, error.stdout, error.stderr)
        output = result.stdout + result.stderr
        (work / (name + '.log')).write_bytes(output)
        return result, output.decode('utf-8', 'replace')

    sdk.write_json(str(work / 'native-python-provider.json'), {
        'path': python, 'sha256': sdk.sha256_file(python), 'version': sys.version,
        'sdk_source': sdk.root, 'sdk_api': 1,
    })
    result, version = capture('cross-compiler-version', [cc, '-dumpfullversion'])
    require(result.returncode == 0 and version.strip().split('.')[0] == '16',
            'target fixtures require the common GCC16 cross compiler')
    for mode in ('native', 'default-cross', 'enabled-cross'):
        arguments = [host + '/bin/meson', 'setup', work / mode, work / 'source',
                     '--native-file', work / 'native.ini']
        if mode != 'native':
            arguments.extend(['--cross-file', work / ('cross.ini' if mode == 'default-cross' else 'enabled.ini')])
        result, output = capture(mode, arguments)
        require(result.returncode == 0, f'{mode} failed: {output}')
        if mode == 'enabled-cross':
            for tool in ('scanner', 'compiler'):
                require(f'native {tool}: {host}/bin/g-ir-{tool}' in output, f'wrong native {tool}')
            require('native python: ' + python in output, 'wrong native Python')
            require('--use-ldd-wrapper=' in output, 'ELF inspection missing')
        else:
            require('ordinary generator: ' + str(generator) in output, 'ordinary generator changed')
            require('--use-ldd-wrapper=' not in output, 'unexpected ELF inspection')
    # Fail closed when the explicitly selected native Python is absent.
    bad = (work / 'enabled.ini').read_text(encoding='utf-8').replace(
        meson_string(python), meson_string(work / 'missing-python'), 1)
    (work / 'missing.ini').write_text(bad, encoding='utf-8')
    result, output = capture('missing', [host + '/bin/meson', 'setup', work / 'missing', work / 'source',
                            '--native-file', work / 'native.ini', '--cross-file', work / 'missing.ini'])
    require(result.returncode != 0 and 'missing-python' in output, 'missing native Python was accepted')
    targets = sdk.read_json(source + '/output/meson-info/intro-targets.json')
    for namespace in ('GdkPixbuf-2.0', 'GdkPixdata-2.0'):
        for extension in ('gir', 'typelib'):
            target = next((item for item in targets if item['name'] == namespace + '.' + extension), None)
            require(target is not None, 'missing metadata target')
            command = [part for item in target['target_sources'] for part in item.get('compiler', [])]
            expected = host + '/bin/g-ir-' + ('scanner' if extension == 'gir' else 'compiler')
            require(any(os.path.exists(part) and sdk.canonical_existing(part) == sdk.canonical_existing(expected)
                        for part in command), 'wrong actual native generator')
            output = Path(source + '/output/gdk-pixbuf/' + namespace + '.' + extension)
            require(output.is_file() and output.stat().st_size > 0, 'empty metadata output')
    thumbnail = Path(source + '/output/thumbnailer/gdk-pixbuf-thumbnailer.thumbnailer').read_text(encoding='utf-8')
    for mimetype in ('image/png', 'image/jpeg', 'image/tiff', 'image/x-tga', 'image/x-icns'):
        require(mimetype + ';' in thumbnail, 'thumbnail MIME missing: ' + mimetype)
    inputs = [sdk.canonical_existing(__file__), source + '/meson.build',
              source + '/gdk-pixbuf/meson.build', source + '/output/build.ninja']
    (work / 'inputs.sha256').write_text(''.join(f'{sdk.sha256_file(path)}  {path}\n' for path in inputs),
                                       encoding='utf-8')
    print('PASS: native/default paths preserved, explicit native generators, missing Python rejected, '
          'all metadata and thumbnail outputs present')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        sdk_errors = sys.modules.get('emberbsd_sdk.errors')
        if not isinstance(error, (OSError, RuntimeError, ValueError, ImportError)) and not (
                sdk_errors is not None and isinstance(error, sdk_errors.SDKError)):
            raise
        print(f'error: {error}', file=sys.stderr)
        raise SystemExit(1)
