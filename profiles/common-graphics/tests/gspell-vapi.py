#!/usr/bin/env python3
"""Replay gspell's VAPI call without compiling C or executing target programs.

Origin: EmberBSD (AI-assisted). License: BSD-2-Clause.
Use a patched upstream source tree and its generated Gspell-1.gir input.
The SDK process API owns each host Meson, Ninja and vapigen session.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import time

sys.dont_write_bytecode = True


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('sdk-source', 'source-tree', 'recipe', 'gir', 'target-gir-dir', 'target-sysroot',
                 'bmake', 'meson', 'ninja', 'vapigen', 'work'):
        cli.add_argument('--' + name, type=Path, required=True)
    cli.add_argument('--target-localbase', default='/usr/pkg')
    a = cli.parse_args(argv)
    assert not os.path.lexists(a.work), 'Use a new work directory'
    a.work.mkdir()
    for name in ('tmp', 'home'):
        (a.work / name).mkdir()
    sys.path.insert(0, str(a.sdk_source / 'src'))
    import emberbsd_sdk
    from emberbsd_sdk.errors import CommandError
    from emberbsd_sdk.stream import capture_streamed
    assert emberbsd_sdk.API_VERSION == 1
    assert Path(emberbsd_sdk.__file__).resolve().parent == (a.sdk_source / 'src/emberbsd_sdk').resolve()
    env = dict(os.environ, TMPDIR=str(a.work / 'tmp'), TMP=str(a.work / 'tmp'),
               TEMP=str(a.work / 'tmp'), HOME=str(a.work / 'home'),
               PYTHONDONTWRITEBYTECODE='1')
    env['PATH'] = os.pathsep.join(dict.fromkeys([str(a.vapigen.parent), str(a.meson.parent), str(a.ninja.parent), env.get('PATH', '')]))
    commands = []
    deadline = time.monotonic() + 180

    def interrupted(number, frame):
        raise KeyboardInterrupt('signal ' + str(number))

    for number in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(number, interrupted)

    def run(args, expected=0):
        args = list(map(str, args))
        remaining = deadline - time.monotonic()
        assert remaining > 0, 'The control deadline expired'
        try:
            result = capture_streamed(args, cwd=str(a.work), env=env, timeout=min(60, remaining),
                                      stdout_limit=4 * 1024**2, stderr_limit=1024**2)
            code, out, err = 0, result.value, result.stderr
            assert not result.stderr_truncated
        except CommandError as error:
            code, out, err = error.returncode, error.stdout, error.stderr
            assert not error.stdout_truncated and not error.stderr_truncated
        number = len(commands)
        (a.work / ('command-%02d.stdout' % number)).write_bytes(out)
        (a.work / ('command-%02d.stderr' % number)).write_bytes(err)
        commands.append({'argv': args, 'exit': code,
                         'stdout_sha256': hashlib.sha256(out).hexdigest(),
                         'stderr_sha256': hashlib.sha256(err).hexdigest()})
        (a.work / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        assert code == expected, (args, code, out, err)
        return out + err

    text = (a.source_tree / 'gspell/meson.build').read_text()
    start = text.index('    GNOME.generate_vapi(')
    end = text.index('    )', start) + len('    )')
    call = text[start:end]
    line = "      gir_dirs: meson.get_external_property('gspell_gir_dirs', []),\n"
    assert call.count(line) == 1, 'The patched production VAPI call is required'
    recipe = a.recipe.read_text()
    start = recipe.index('.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"')
    end = recipe.index('.endif', start) + len('.endif')
    block = recipe[start:end]
    include = '.include "../../devel/gobject-introspection/cross.mk"\n'
    assert block.count(include) == 1
    # Only the common GI include is omitted from this standalone make fixture.
    makefile = a.work / 'recipe.mk'
    makefile.write_text(block.replace(include, '') + '\n')
    property_name = '${MESON_CROSS.gspell_gir_dirs:U[]}'
    assert Path(a.target_localbase).is_absolute()
    target_root = a.target_sysroot
    assert a.target_gir_dir == target_root / a.target_localbase.lstrip('/') / 'share/gir-1.0'
    values = {}
    for target, mode, root in (('native', 'no', target_root), ('amd64', 'yes', target_root),
                               ('aarch64', 'yes', a.work / 'aarch64 sysroot')):
        value = run([a.bmake, '-r', '-f', makefile,
                     'USE_CROSS_COMPILE=' + mode, '_CROSS_DESTDIR=' + str(root),
                     'MACHINE_ARCH=' + ('x86_64' if target == 'amd64' else target),
                     'CROSS_LOCALBASE=' + a.target_localbase, '-V', property_name])
        values[target] = ast.literal_eval(value.decode().strip())
        expected = root / a.target_localbase.lstrip('/') / 'share/gir-1.0'
        assert values[target] == ([] if mode == 'no' else [str(expected)])

    for tool in (a.meson, a.ninja, a.vapigen):
        run([tool, '--version'])
    empty = a.work / 'empty-gir'
    empty.mkdir()
    cases = []
    for name, body, dirs, cross, expected in (
            ('baseline', call.replace(line, ''), values['amd64'], True, 1),
            ('candidate', call, values['amd64'], True, 0),
            ('wrong-directory', call, [str(empty)], True, 1),
            ('native-default', call, [], False, None)):
        root = a.work / name
        source = root / 'source'
        source.mkdir(parents=True)
        shutil.copyfile(a.gir, source / 'Gspell-1.gir')
        for path in (a.source_tree / 'gspell').glob('*.metadata'):
            shutil.copyfile(path, source / path.name)
        (source / 'meson.build').write_text(
            "project('gspell', version: '1.14.5', meson_version: '>=1.12.0')\n"
            "GNOME = import('gnome')\nGSPELL_API_VERSION = '1'\n"
            "gspell_gir = [meson.current_source_dir() / 'Gspell-1.gir']\n" + body + '\n')
        machine = root / 'machine.ini'
        content = '[binaries]\nvapigen = ' + repr(str(a.vapigen)) + '\n'
        if cross:
            content += ("[host_machine]\nsystem = 'netbsd'\ncpu_family = 'x86_64'\n"
                        "cpu = 'x86_64'\nendian = 'little'\n[properties]\n"
                        'gspell_gir_dirs = ' + repr(dirs) + '\n')
        machine.write_text(content)
        build = root / 'build'
        run([a.meson, 'setup', build, source,
             '--cross-file' if cross else '--native-file', machine])
        ninja = (build / 'build.ninja').read_text()
        has_dir = '--girdir=' in ninja
        assert has_dir == (name in ('candidate', 'wrong-directory'))
        if expected is not None:
            output = run([a.ninja, '-C', build], expected)
            if expected:
                assert b"Package `Gtk-3.0' not found" in output
            else:
                assert (build / 'gspell-1.vapi').stat().st_size > 0
        cases.append({'case': name, 'expected_ninja_exit': expected,
                      'girdir_argument_present': has_dir})
    result = {'status': 'PASS', 'make_property_cases': values, 'cases': cases,
              'commands': len(commands), 'limits': 'Host VAPI generation only. No C compilation, target execution, complete package or native package acceptance.'}
    (a.work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
