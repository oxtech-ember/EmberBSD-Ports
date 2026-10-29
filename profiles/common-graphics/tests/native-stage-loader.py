#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check actual GLib/GI make environments for a selected native runtime view."""
import argparse
import subprocess
import tempfile
from pathlib import Path
p = argparse.ArgumentParser()
for name in ('pkgsrc', 'bmake', 'makeconf', 'view', 'sdk-source'):
    p.add_argument('--' + name, type=Path, required=True)
a = p.parse_args()
def environment(recipe, *options):
    result = subprocess.run([str(a.bmake), '-C', str(a.pkgsrc/'devel'/recipe),
        f'MAKECONF={a.makeconf}', 'EMBERBSD_DARWIN_BOOTSTRAP=yes',
        'EMBERBSD_DARWIN_TOOLCHAIN_ONLY=yes', f'EMBERBSD_SDK_SOURCE={a.sdk_source}', *options, '-v', 'MAKE_ENV'],
        capture_output=True, text=True, check=True)
    return next(word.split('=',1)[1] for word in result.stdout.split()
                if word.startswith('DYLD_LIBRARY_PATH='))
for recipe in ('glib2', 'glib2-introspection', 'gobject-introspection'):
    baseline = environment(recipe, 'EMBERBSD_NATIVE_RUNTIME_VIEW=')
    selected = environment(recipe, f'EMBERBSD_NATIVE_RUNTIME_VIEW={a.view}')
    assert not baseline.endswith(':')
    assert selected == baseline + ':' + str(a.view)
    outside = environment(recipe, f'EMBERBSD_NATIVE_RUNTIME_VIEW={a.view}',
                          'EMBERBSD_NATIVE_STAGE_ROOT=')
    assert outside == baseline
def harfbuzz(*options):
    return subprocess.run([str(a.bmake), '-C', str(a.pkgsrc/'fonts/harfbuzz'),
        f'MAKECONF={a.makeconf}', 'EMBERBSD_DARWIN_BOOTSTRAP=yes',
        'EMBERBSD_DARWIN_TOOLCHAIN_ONLY=yes', f'EMBERBSD_SDK_SOURCE={a.sdk_source}', *options, '-v', 'MAKE_ENV'],
        capture_output=True, text=True, check=True).stdout
selected = harfbuzz(f'EMBERBSD_NATIVE_RUNTIME_VIEW={a.view}')
assert 'EMBERBSD_NATIVE_RUNTIME_VIEW=' + str(a.view) in selected
stage_root = subprocess.run([str(a.bmake), '-C', str(a.pkgsrc/'fonts/harfbuzz'),
    f'MAKECONF={a.makeconf}', 'EMBERBSD_DARWIN_BOOTSTRAP=yes',
    'EMBERBSD_DARWIN_TOOLCHAIN_ONLY=yes', '-v', 'EMBERBSD_NATIVE_STAGE_ROOT'],
    text=True, capture_output=True, check=True).stdout.strip()
prefix = subprocess.run([str(a.bmake), '-C', str(a.pkgsrc/'fonts/harfbuzz'),
    f'MAKECONF={a.makeconf}', 'EMBERBSD_DARWIN_BOOTSTRAP=yes',
    'EMBERBSD_DARWIN_TOOLCHAIN_ONLY=yes', '-v', 'PREFIX'],
    text=True, capture_output=True, check=True).stdout.strip()
assert 'XDG_DATA_DIRS=' + stage_root + prefix + '/share:' + prefix + '/share' in selected
chosen = harfbuzz(f'EMBERBSD_NATIVE_RUNTIME_VIEW={a.view}', 'XDG_DATA_DIRS=/one:/two')
assert 'XDG_DATA_DIRS=' + stage_root + prefix + '/share:/one:/two' in chosen
def meson_args(*options):
    return subprocess.run([str(a.bmake), '-C', str(a.pkgsrc/'fonts/harfbuzz'),
        f'MAKECONF={a.makeconf}', 'EMBERBSD_DARWIN_BOOTSTRAP=yes',
        'EMBERBSD_DARWIN_TOOLCHAIN_ONLY=yes', f'EMBERBSD_SDK_SOURCE={a.sdk_source}',
        *options, '-v', 'MESON_NATIVE_ARGS'], check=True, capture_output=True, text=True).stdout
assert '.meson-native-stage-pkgconf' in meson_args(f'EMBERBSD_NATIVE_RUNTIME_VIEW={a.view}')
assert '.meson-emberbsd-native-gi' in meson_args(f'EMBERBSD_NATIVE_RUNTIME_VIEW={a.view}')
assert '.meson-native-stage-pkgconf' not in meson_args('EMBERBSD_NATIVE_STAGE_ROOT=')
assert '.meson-emberbsd-native-gi' not in meson_args('EMBERBSD_NATIVE_RUNTIME_VIEW=')
assert 'EMBERBSD_NATIVE_RUNTIME_VIEW=' not in harfbuzz('EMBERBSD_NATIVE_RUNTIME_VIEW=')
assert 'EMBERBSD_NATIVE_RUNTIME_VIEW=' not in harfbuzz(
    f'EMBERBSD_NATIVE_RUNTIME_VIEW={a.view}', 'EMBERBSD_NATIVE_STAGE_ROOT=')
for options in (
    (f'EMBERBSD_SDK_SOURCE={a.sdk_source}', 'EMBERBSD_NATIVE_STAGE_PYTHON='),
    ('EMBERBSD_SDK_SOURCE=', f'EMBERBSD_NATIVE_STAGE_PYTHON={a.bmake.parent}/python3.15'),
    (f'EMBERBSD_SDK_SOURCE={a.sdk_source}', f'EMBERBSD_NATIVE_STAGE_PYTHON={a.bmake.parent}/python3.15',
     'EMBERBSD_NATIVE_STAGE_PREFIX='),
):
    result = subprocess.run([str(a.bmake), '-C', str(a.pkgsrc/'fonts/harfbuzz'),
        f'MAKECONF={a.makeconf}', 'EMBERBSD_DARWIN_BOOTSTRAP=yes',
        'EMBERBSD_DARWIN_TOOLCHAIN_ONLY=yes', f'EMBERBSD_NATIVE_RUNTIME_VIEW={a.view}',
        *options, 'emberbsd-native-gi-meson'], text=True, capture_output=True)
    assert result.returncode and 'Missing native Python, SDK source or stage prefix' in result.stderr
helper = a.pkgsrc/'devel/gobject-introspection/native-stage-loader.mk'
with tempfile.TemporaryDirectory() as tmp:
    fixture = Path(tmp)/'scope.mk'
    fixture.write_text('.include "' + str(helper) + '"\n')
    def suffix(*opts):
        return subprocess.run([str(a.bmake), '-f', str(fixture), *opts, '-v',
                               '_EMBERBSD_NATIVE_RUNTIME_SUFFIX'], text=True,
                              capture_output=True, check=True).stdout.strip()
    opts = ('OPSYS=Darwin', 'EMBERBSD_NATIVE_STAGE_ROOT=/stage',
            'EMBERBSD_NATIVE_RUNTIME_VIEW=' + str(a.view))
    assert suffix(*opts, 'USE_CROSS_COMPILE=yes') == ''
    assert suffix(*opts, 'USE_CROSS_COMPILE=no') == ':' + str(a.view)
    hostile = [Path(tmp)/name for name in ("quote'path", 'back`tick', 'dollar$path', 'double"quote')]
    for directory in hostile: directory.mkdir()
    for bad in ('relative', str(Path(tmp)/'missing'), str(fixture), str(a.view)+':bad',
                *(str(directory) for directory in hostile)):
        result = subprocess.run([str(a.bmake), '-f', str(fixture), 'OPSYS=Darwin',
            'EMBERBSD_NATIVE_STAGE_ROOT=/stage', 'EMBERBSD_NATIVE_RUNTIME_VIEW='+bad,
            '-v', 'MAKE_ENV'], text=True, capture_output=True)
        assert result.returncode != 0 and 'must be an absolute existing directory without colon' in result.stderr
with tempfile.TemporaryDirectory() as tmp:
    directory = a.pkgsrc/'devel/gobject-introspection'
    def fixture(contents, variable):
        path = Path(tmp)/'fixture.mk'
        path.write_text('DISTNAME= fixture-1\nCATEGORIES= devel\nCOMMENT= fixture\n'
            'LICENSE= modified-bsd\n' + contents + '.include "../../mk/bsd.pkg.mk"\n')
        return subprocess.run([str(a.bmake), '-C', str(directory), '-f', str(path),
            f'MAKECONF={a.makeconf}', 'EMBERBSD_DARWIN_BOOTSTRAP=yes',
            'EMBERBSD_DARWIN_TOOLCHAIN_ONLY=yes', f'EMBERBSD_NATIVE_RUNTIME_VIEW={a.view}',
            '-v', variable], text=True, capture_output=True, check=True).stdout
    minimal = fixture('.include "../../devel/meson/build.mk"\n', 'MESON_NATIVE_ARGS')
    assert '.meson-native-stage-pkgconf' not in minimal
    subprocess.run([str(a.bmake), '-C', str(directory), '-f', str(Path(tmp)/'fixture.mk'),
        f'MAKECONF={a.makeconf}', 'EMBERBSD_DARWIN_BOOTSTRAP=yes',
        'EMBERBSD_DARWIN_TOOLCHAIN_ONLY=yes', f'WRKOBJDIR={tmp}/objects',
        'emberbsd-native-stage-pkgconf'], check=True, capture_output=True, text=True)
    assert not list(Path(tmp).rglob('.meson-native-stage-pkgconf'))
    late = fixture('USE_TOOLS+= pkg-config\n.include "../../devel/meson/build.mk"\n'
        '.include "../../devel/gobject-introspection/buildlink3.mk"\n', 'MESON_NATIVE_ARGS')
    assert '.meson-native-stage-pkgconf' in late and '.meson-emberbsd-native-gi' in late
    nonmeson = fixture('.include "../../mk/bsd.prefs.mk"\n'
        '.include "../../devel/gobject-introspection/buildlink3.mk"\n', 'MESON_NATIVE_ARGS')
    assert '.meson-emberbsd-native-gi' not in nonmeson
print('Native GLib stage loader environment PASS')
