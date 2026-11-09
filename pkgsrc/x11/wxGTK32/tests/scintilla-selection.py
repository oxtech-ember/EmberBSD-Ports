#!/usr/bin/env python3
"""Exercise wx configure's required Scintilla and Lexilla provider selection.

Origin: EmberBSD (AI-assisted). SPDX-License-Identifier: BSD-2-Clause
"""
import argparse
import os
from pathlib import Path
import re
import subprocess
import tempfile


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True,
                    help='prepared wx source containing generated configure')
parser.add_argument('--shell', required=True)
parser.add_argument('--pkg-config', required=True)
parser.add_argument('--work-parent', type=Path, required=True)
args = parser.parse_args()

configure = (args.source / 'configure').read_text()
marker = '# Use the common Ports providers; never fall back to bundled source.'
if marker not in configure:
    raise SystemExit('configure has no shared Scintilla/Lexilla provider selection')
start = configure.index(marker)
lines = configure[start:].splitlines()
depth = 0
selection_lines = []
for line in lines:
    selection_lines.append(line)
    if line.lstrip().startswith('if '):
        depth += 1
    elif line.strip() == 'fi':
        depth -= 1
        if depth == 0:
            break
else:
    raise SystemExit('configure provider selection has no matching fi')
selection = '\n'.join(selection_lines)
for required in (
        'if test "$wxUSE_STC" = "yes";',
        '$PKG_CONFIG --exists scintilla-core lexilla-access',
        '$PKG_CONFIG --cflags scintilla-core lexilla-access',
        '$PKG_CONFIG --libs scintilla-core lexilla-access'):
    if required not in selection:
        raise SystemExit(f'configure provider selection is incomplete: {required}')


def write_pc(directory, package, prefix, suffix, requires=None):
    directory.mkdir(parents=True, exist_ok=True)
    requires_line = f'Requires: {requires}\n' if requires else ''
    (directory / f'{package}.pc').write_text(f'''prefix={prefix}
includedir=${{prefix}}/include/{suffix}
libdir=${{prefix}}/lib
Name: {package}
Description: controlled wx STC provider selection test
Version: 1
{requires_line}Cflags: -I${{includedir}}
Libs: -L${{libdir}} -l{suffix}
''')


def run(work, name, pcdir, sysroot, enabled=True, pkg_config=None):
    driver = work / f'{name}.sh'
    driver.write_text('''as_fn_error() {
    printf '%s\\n' "$2" >&2
    exit 1
}
wxUSE_STC=$STC_ENABLED
PKG_CONFIG=$PKG_CONFIG_COMMAND
EXTRALIBS_STC=-lm
''' + selection + '''
printf 'STC_CFLAGS=%s\\n' "$STC_CFLAGS"
printf 'EXTRALIBS_STC=%s\\n' "$EXTRALIBS_STC"
printf 'WXCONFIG_LIBS_STC=%s\\n' "$WXCONFIG_LIBS_STC"
''')
    env = dict(os.environ)
    for key in ('PKG_CONFIG_PATH', 'PKG_CONFIG_LIBDIR',
                'PKG_CONFIG_SYSROOT_DIR', 'PKG_CONFIG_TOP_BUILD_DIR'):
        env.pop(key, None)
    env.update({
        'STC_ENABLED': 'yes' if enabled else 'no',
        'PKG_CONFIG_COMMAND': pkg_config or args.pkg_config,
        'PKG_CONFIG_PATH': '',
        'PKG_CONFIG_LIBDIR': str(pcdir),
        'PKG_CONFIG_SYSROOT_DIR': str(sysroot) if sysroot else '',
    })
    return subprocess.run([args.shell, str(driver)], cwd=work, env=env,
                          text=True, capture_output=True)


def check_installed_config(work, provider_result, cross):
    """Exercise the real wx-config template after configure substitution."""
    values = dict(line.split('=', 1) for line in provider_result.stdout.splitlines())
    values.update({
        'prefix': '/original-provider', 'exec_prefix': '${prefix}',
        'libdir': '${exec_prefix}/lib', 'includedir': '${prefix}/include',
        'bindir': '${exec_prefix}/bin', 'cross_compiling': 'yes' if cross else 'no',
        'host_alias': 'aarch64--netbsd', 'TOOLKIT_DIR': 'gtk', 'TOOLKIT_VERSION': '4',
        'WX_CHARTYPE': 'unicode', 'WX_RELEASE': '3.2', 'WX_VERSION': '3.2.12',
        'WX_LIBRARY_BASENAME_GUI': 'wx_gtk4u', 'WX_LIBRARY_BASENAME_NOGUI': 'wx_baseu',
        'STD_BASE_LIBS': 'base', 'STD_GUI_LIBS': 'core', 'BUILT_WX_LIBS': 'stc core base',
        'TOOLCHAIN_NAME': 'gtk4u-3.2',
    })
    template = (args.source / 'wx-config.in').read_text()
    relocated = work / 'relocated-provider'
    for shared in (0, 1):
        for monolithic in (0, 1):
            values.update(SHARED=str(shared), MONOLITHIC=str(monolithic))
            configured = re.sub(r'@([A-Za-z0-9_]+)@',
                                lambda match: values.get(match[1], ''), template)
            script = work / f'wx-config-{cross}-{shared}-{monolithic}'
            script.write_text(configured)
            result = subprocess.run([args.shell, str(script), f'--prefix={relocated}',
                                     '--libs', 'stc'], text=True, capture_output=True)
            assert result.returncode == 0, (result.stdout, result.stderr)
            assert f'-L{relocated}/lib' in result.stdout, result.stdout
            assert '/original-provider' not in result.stdout, result.stdout
            assert '-L' not in result.stdout.replace(f'-L{relocated}/lib', ''), result.stdout
            for provider in ('scintilla-core', 'lexilla-access', 'lexilla'):
                assert (f'-l{provider}' in result.stdout) == (not shared), result.stdout
    print(f"{'cross' if cross else 'native'} installed static/shared wx-config relocation PASS")


with tempfile.TemporaryDirectory(prefix='wx-scintilla-selection-',
                                 dir=args.work_parent) as tmp:
    work = Path(tmp)
    native_pc = work / 'native-pc'
    target_pc = work / 'target-pc'
    target_sysroot = work / 'target-sysroot'
    host_prefix = work / 'selected-host'
    for directory in (native_pc, target_pc):
        write_pc(directory, 'scintilla-core', str(host_prefix), 'scintilla-core')
        write_pc(directory, 'lexilla', str(host_prefix), 'lexilla')
        write_pc(directory, 'lexilla-access', str(host_prefix), 'lexilla-access',
                 requires='lexilla')
    write_pc(target_pc, 'scintilla-core', '/usr/pkg', 'scintilla-core')
    write_pc(target_pc, 'lexilla', '/usr/pkg', 'lexilla')
    write_pc(target_pc, 'lexilla-access', '/usr/pkg', 'lexilla-access',
             requires='lexilla')

    native = run(work, 'native', native_pc, None)
    assert native.returncode == 0, (native.stdout, native.stderr)
    assert f'-I{host_prefix}/include/scintilla-core' in native.stdout
    assert f'-I{host_prefix}/include/lexilla-access' in native.stdout
    assert f'-I{host_prefix}/include/lexilla' in native.stdout
    assert f'-L{host_prefix}/lib' in native.stdout
    assert '-lscintilla-core' in native.stdout
    assert '-llexilla-access' in native.stdout
    assert '-llexilla' in native.stdout
    installed_native = dict(line.split('=', 1) for line in native.stdout.splitlines())['WXCONFIG_LIBS_STC']
    assert '-L' not in installed_native and str(host_prefix) not in installed_native
    assert all(f'-l{p}' in installed_native for p in ('scintilla-core', 'lexilla-access', 'lexilla'))
    print('native provider metadata selected PASS')

    cross = run(work, 'cross', target_pc, target_sysroot)
    assert cross.returncode == 0, (cross.stdout, cross.stderr)
    for provider in ('scintilla-core', 'lexilla-access', 'lexilla'):
        assert f'-I{target_sysroot}/usr/pkg/include/{provider}' in cross.stdout
        assert f'-l{provider}' in cross.stdout
    assert f'-L{target_sysroot}/usr/pkg/lib' in cross.stdout
    installed_cross = dict(line.split('=', 1) for line in cross.stdout.splitlines())['WXCONFIG_LIBS_STC']
    assert installed_cross == installed_native
    assert str(target_sysroot) not in installed_cross
    print('cross target provider metadata selected PASS')
    check_installed_config(work, native, False)
    check_installed_config(work, cross, True)

    for missing in ('scintilla-core', 'lexilla-access', 'lexilla'):
        partial_pc = work / f'missing-{missing}'
        if missing == 'scintilla-core':
            write_pc(partial_pc, 'lexilla', str(host_prefix), 'lexilla')
            write_pc(partial_pc, 'lexilla-access', str(host_prefix), 'lexilla-access',
                     requires='lexilla')
        elif missing == 'lexilla-access':
            write_pc(partial_pc, 'scintilla-core', str(host_prefix), 'scintilla-core')
            write_pc(partial_pc, 'lexilla', str(host_prefix), 'lexilla')
        else:
            write_pc(partial_pc, 'scintilla-core', str(host_prefix), 'scintilla-core')
            write_pc(partial_pc, 'lexilla-access', str(host_prefix), 'lexilla-access',
                     requires='lexilla')
        result = run(work, f'missing-{missing}', partial_pc, None)
        assert result.returncode != 0, (missing, result.stdout, result.stderr)
        assert 'requires the shared Scintilla core and Lexilla providers' in result.stderr
        print(f'missing {missing} refused PASS')

    no_stc = run(work, 'disabled', work / 'no-providers', None,
                 enabled=False, pkg_config=str(work / 'does-not-exist'))
    assert no_stc.returncode == 0, (no_stc.stdout, no_stc.stderr)
    assert 'STC_CFLAGS=' in no_stc.stdout
    assert 'EXTRALIBS_STC=-lm' in no_stc.stdout
    print('disabled STC does not require providers PASS')
