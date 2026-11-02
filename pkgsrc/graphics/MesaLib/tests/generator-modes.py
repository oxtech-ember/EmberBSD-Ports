#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Parse the production native/cross selection with real bmake. Build nothing."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

RECIPE = Path(__file__).resolve().parents[1]
FIELDS = ('PKG_FAIL_REASON', 'MESON_ARGS', 'MESON_NATIVE_ARGS', 'DEPENDS',
          'BUILDLINK_DEPMETHOD.clang', 'BUILDLINK_DEPMETHOD.spirv-tools',
          'BUILDLINK_DEPMETHOD.spirv-llvm-translator',
          'BUILDLINK_API_DEPENDS.spirv-llvm-translator', 'TEST_INCLUDES',
          'BUILDLINK_API_DEPENDS.spirv-tools',
          'BUILDLINK_API_DEPENDS.googletest',
          'GCC_REQD', 'USE_LANGUAGES', 'PLIST.radeonsi')
BUILD_LINKS = {'../../lang/clang/buildlink3.mk', '../../parallel/spirv-tools/buildlink3.mk',
               '../../parallel/spirv-llvm-translator/buildlink3.mk'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def parse(make, work, source, arch, cross, sealed, tests=False):
    # External pkgsrc includes are outside this finite metadata boundary.
    # Keep local generator policy live. Record selected external interfaces.
    lines = []
    for line in source.splitlines():
        if line.startswith('.include '):
            name = line.split('"')[1]
            if name == 'mesa-generators.mk':
                line = '.include "' + str(RECIPE / name) + '"'
            else:
                line = 'TEST_INCLUDES+= ' + name
        lines.append(line)
    (work / 'recipe.mk').write_text('\n'.join(lines) + '\n')
    fixture = work / 'fixture.mk'
    fixture.write_text('''OPSYS=NetBSD
OS_VERSION=11.0
MACHINE_ARCH={arch}
USE_CROSS_COMPILE={cross}
EMBERBSD_COMMON_GRAPHICS=yes
WRKDIR={work}
CROSS_DESTDIR={work}
PREFIX=/usr/pkg
TOOLBASE=/usr/pkg
PYPKGPREFIX=py315
PYVERSSUFFIX=3.15
PKG_OPTIONS={pkg_options}
EMBERBSD_MESA_GENERATORS={sealed}
EMBERBSD_SDK_SOURCE={work}/selected-sdk
.include "{work}/recipe.mk"
show:
.for field in {fields}
\t@printf '%s\\n' ${{${{field}}:Q}}
.endfor
'''.format(arch=arch, cross=cross, work=work,
           pkg_options='llvm x11 wayland tests' if tests else 'llvm x11 wayland',
           sealed=sealed, fields=' '.join(FIELDS)))
    result = subprocess.run([str(make), '-r', '-m', '/', '-f', str(fixture), 'show'],
                            cwd=RECIPE, capture_output=True, text=True)
    require(result.returncode == 0, 'bmake failed: ' + result.stdout + result.stderr)
    output = result.stdout.splitlines()
    require(len(output) == len(FIELDS), 'Unexpected make metadata output')
    return dict(zip(FIELDS, output))


def oracle(values, arch, cross, sealed, tests=False):
    options = set(values['MESON_ARGS'].split())
    drivers = ('iris,radeonsi,virgl,softpipe,llvmpipe,zink' if arch == 'x86_64'
               else 'v3d,virgl,softpipe,llvmpipe,zink')
    require('-Dgallium-drivers=' + drivers in options, 'The selected drivers changed')
    test_flag = '-Dbuild-tests=true' if tests else '-Dbuild-tests=false'
    require(test_flag in options and ('-Dbuild-tests=false' if tests else '-Dbuild-tests=true') not in options,
            'The upstream test mode does not follow the tests package option')
    includes = set(values['TEST_INCLUDES'].split())
    gtest_include = '../../devel/googletest/buildlink3.mk'
    require((gtest_include in includes) == tests, 'GoogleTest buildlink does not follow the tests option')
    require(values['BUILDLINK_API_DEPENDS.googletest'] == ('googletest>=1.18.0' if tests else ''),
            'GoogleTest dependency is not scoped to the tests option')
    require(values['PLIST.radeonsi'] == ('yes' if arch == 'x86_64' else ''),
            'RadeonSI package files do not follow the selected architecture')
    require('-Dmicrosoft-clc=disabled' in options and '-Dgallium-rusticl=false' in options,
            'Unrelated CLC consumers changed')
    require('16.2' not in values['GCC_REQD'].split() and values['USE_LANGUAGES'].split() == ['c', 'c++'],
            'Compiler selection changed')
    if cross:
        require({'-Dmesa-clc=system', '-Dprecomp-compiler=system', '-Dspirv-tools=disabled'} <= options,
                'Cross builds did not select system generators')
        require(not (includes & BUILD_LINKS), 'Cross builds imported target CLC libraries')
        require('--native-file' in values['MESON_NATIVE_ARGS'], 'Cross native-file binding was lost')
        require(not sealed or '--native-file' in values['MESON_NATIVE_ARGS'],
                'Cross builds did not select the sealed native file')
    else:
        require(not values['PKG_FAIL_REASON'] and not values['MESON_NATIVE_ARGS'],
                'Native builds still require a sealed generator directory')
        require({'-Dmesa-clc=enabled', '-Dprecomp-compiler=enabled', '-Dspirv-tools=enabled',
                 '-Dinstall-mesa-clc=false', '-Dinstall-precomp-compiler=false'} <= options,
                'Native generators are absent or installable')
        require('-Dspirv-tools=disabled' not in options and '-Dmesa-clc=system' not in options,
                'Native selection contains conflicting options')
        require(BUILD_LINKS <= includes, 'Native CLC dependency interfaces are missing')
        for provider in ('clang', 'spirv-tools', 'spirv-llvm-translator'):
            require(values['BUILDLINK_DEPMETHOD.' + provider] == 'build', 'CLC library became a runtime dependency')
            require(not any(item.startswith(provider + '>') or item.startswith(provider + '-')
                            for item in values['DEPENDS'].split()), 'Explicit runtime CLC dependency')
        require(values['BUILDLINK_API_DEPENDS.spirv-llvm-translator'] == 'spirv-llvm-translator>=23.1.2<23.2',
                'Translator does not match LLVM 23.1')
        require(values['BUILDLINK_API_DEPENDS.spirv-tools'] == 'spirv-tools>=2026.4nb1',
                'SPIRV-Tools lacks the shared function-order repair')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bmake', type=Path, required=True)
    parser.add_argument('--work-parent', type=Path, required=True)
    args = parser.parse_args()
    require(args.bmake.is_absolute() and args.bmake.is_file(), 'Use an absolute bmake executable')
    require(args.work_parent.is_absolute() and args.work_parent.is_dir(), 'Use an existing absolute work parent')
    before = subprocess.check_output(['df', '-k', str(args.work_parent)], text=True)
    work = Path(tempfile.mkdtemp(prefix='mesa-generator-modes-', dir=args.work_parent))
    try:
        tools = work / 'sealed'
        tools.mkdir()
        (tools / 'installed.sha256').write_text('metadata fixture only; never executed\n')
        source = (RECIPE / 'Makefile').read_text()
        checks = 0
        for arch in ('x86_64', 'aarch64'):
            for cross, selected in ((False, False), (True, False), (True, True)):
                values = parse(args.bmake, work, source, arch, 'yes' if cross else 'no',
                               tools if selected else work / 'missing')
                oracle(values, arch, cross, selected)
                if cross and not selected:
                    result = subprocess.run([str(args.bmake), '-r', '-m', '/', '-f', str(work / 'fixture.mk'),
                                             'emberbsd-mesa-generators-check'],
                                            cwd=RECIPE, capture_output=True, text=True)
                    require(result.returncode != 0 and
                            'requires an absolute sealed EMBERBSD_MESA_GENERATORS directory' in result.stderr,
                            'The cross pre-configure target accepted a missing generator seal')
                checks += 1
        for arch in ('x86_64', 'aarch64'):
            for cross in (False, True):
                values = parse(args.bmake, work, source, arch, 'yes' if cross else 'no',
                               tools if cross else work / 'missing', tests=True)
                oracle(values, arch, cross, cross, tests=True)
                checks += 1
        mutations = [
            ('.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"\n# Cross builds', '.if 1\n# Cross builds'),
            ('BUILDLINK_DEPMETHOD.clang=\tbuild', 'BUILDLINK_DEPMETHOD.clang=\tfull'),
        ]
        for old, new in mutations:
            require(source.count(old) == 1, 'Causal control no longer matches the production recipe')
            values = parse(args.bmake, work, source.replace(old, new, 1), 'x86_64', 'no', work / 'missing')
            try:
                oracle(values, 'x86_64', False, False)
            except ValueError:
                checks += 1
            else:
                raise ValueError('The metadata oracle accepted a deliberate dependency/selection defect')
        print(f'PASS: {checks} native/cross metadata and causal checks; no configure/build/install')
    finally:
        cleanup_before = subprocess.check_output(['df', '-k', str(work)], text=True)
        shutil.rmtree(work)
        require(not work.exists(), 'Own metadata fixture remains')
        after = subprocess.check_output(['df', '-k', str(args.work_parent)], text=True)
        print(before + cleanup_before + after, end='')
        print('Removed owned fixture: ' + str(work))


if __name__ == '__main__':
    main()
