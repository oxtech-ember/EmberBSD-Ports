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
FIELDS = ('PKG_FAIL_REASON', 'MESON_ARGS', 'MESON_NATIVE_ARGS', 'DEPENDS', 'TOOL_DEPENDS',
          'TOOLS_PATH.mesa_clc', 'TOOLS_PATH.vtn_bindgen2', 'TOOLS_PATH.pco_clc',
          '_EMBERBSD_MESA_NATIVE', '_EMBERBSD_MESA_GENERATOR_NAMES',
          'BUILDLINK_DEPMETHOD.clang', 'BUILDLINK_DEPMETHOD.spirv-tools',
          'BUILDLINK_DEPMETHOD.spirv-llvm-translator',
          'BUILDLINK_API_DEPENDS.spirv-llvm-translator', 'TEST_INCLUDES',
          'BUILDLINK_API_DEPENDS.spirv-tools',
          'BUILDLINK_API_DEPENDS.googletest',
          'GCC_REQD', 'USE_LANGUAGES', 'PLIST.radeonsi', 'PLIST.radv',
          'PLIST.full_drivers', 'PLIST.powervr')
BUILD_LINKS = {'../../lang/clang/buildlink3.mk', '../../parallel/spirv-tools/buildlink3.mk',
               '../../parallel/spirv-llvm-translator/buildlink3.mk'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def parse(make, work, source, arch, cross, sealed, tests=False, minimal=False, powervr=False):
    # External pkgsrc includes are outside this finite metadata boundary.
    # Keep local generator policy live. Record selected external interfaces.
    lines = []
    for line in source.splitlines():
        if line.startswith('.include '):
            name = line.split('"')[1]
            if name in ('mesa-generators.mk', 'mesa-source.mk'):
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
ECHO=echo
MV=mv
RM=rm
CMP=cmp
TEST=test
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
           pkg_options=('softpipe-only x11 powervr' if powervr else
                        'softpipe-only x11' if minimal else
                        ('llvm x11 wayland tests' if tests else 'llvm x11 wayland')),
           sealed=sealed, fields=' '.join(FIELDS)))
    result = subprocess.run([str(make), '-r', '-m', '/', '-f', str(fixture), 'show'],
                            cwd=RECIPE, capture_output=True, text=True)
    require(result.returncode == 0, 'bmake failed: ' + result.stdout + result.stderr)
    output = result.stdout.splitlines()
    require(len(output) == len(FIELDS), 'Unexpected make metadata output')
    return dict(zip(FIELDS, output))


def oracle(values, arch, cross, sealed, provider_version, tests=False):
    require(values['PLIST.full_drivers'] == 'yes', 'Default full-driver PLIST was lost')
    options = set(values['MESON_ARGS'].split())
    drivers = ('iris,radeonsi,virgl,softpipe,llvmpipe,zink' if arch == 'x86_64'
               else 'v3d,virgl,softpipe,llvmpipe,zink')
    require('-Dgallium-drivers=' + drivers in options, 'The selected drivers changed')
    if arch == 'x86_64':
        require('-Dvulkan-drivers=amd' in options and
                '-Dvulkan-manifest-per-architecture=false' in options,
                'amd64 must ship the RADV ICD')
        require('-Dvulkan-drivers=' not in options, 'amd64 kept an empty Vulkan list')
    else:
        require('-Dvulkan-drivers=imagination,broadcom' in options,
                'AArch64 Vulkan ICD selection changed')
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
    require(values['PLIST.radv'] == ('yes' if arch == 'x86_64' else ''),
            'RADV package files do not follow the selected architecture')
    require('-Dmicrosoft-clc=disabled' in options and '-Dgallium-rusticl=false' in options,
            'Unrelated CLC consumers changed')
    require('16.2' not in values['GCC_REQD'].split() and values['USE_LANGUAGES'].split() == ['c', 'c++'],
            'Compiler selection changed')
    if cross:
        require({'-Dmesa-clc=system', '-Dprecomp-compiler=system', '-Dspirv-tools=disabled'} <= options,
                'Cross builds did not select system generators')
        require(not (includes & BUILD_LINKS), 'Cross builds imported target CLC libraries')
        require('--native-file' in values['MESON_NATIVE_ARGS'], 'Cross native-file binding was lost')
        if sealed:
            require(not any(item.startswith('mesa-generators-') for item in values['TOOL_DEPENDS'].split()),
                    'Explicit external tools unexpectedly add a package dependency')
        else:
            require(('mesa-generators-' + provider_version + ':../mesa-generators') in
                    values['TOOL_DEPENDS'].split(),
                    'The normal cross path does not depend on the matching native generator package')
            for name in (('mesa_clc', 'vtn_bindgen2', 'pco_clc') if arch == 'aarch64'
                         else ('mesa_clc', 'vtn_bindgen2')):
                require(values['TOOLS_PATH.' + name] == '/usr/pkg/bin/' + name,
                        'The normal cross path did not select the native package tool: ' + name)
    else:
        require(not values['PKG_FAIL_REASON'] and not values['MESON_NATIVE_ARGS'],
                'Native builds still require a sealed generator directory')
        require(not any(item.startswith('mesa-generators-') for item in values['TOOL_DEPENDS'].split()),
                'Native builds unexpectedly depend on the cross generator package')
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
        source_vars = work / 'source-vars.mk'
        source_vars.write_text('''
.include "{source}"
show:
	@printf '%s\\n' ${{DISTNAME}} ${{MESA_SOURCE_VERSION}} ${{MESA_PORT_REVISION}} \\
	    ${{MESA_GENERATORS_VERSION}} ${{PATCHDIR}} ${{DISTINFO_FILE}}
'''.format(source=RECIPE / 'mesa-source.mk'))
        source_values = subprocess.check_output([str(args.bmake), '-r', '-m', '/', '-f',
                                                  str(source_vars), 'show'], cwd=RECIPE, text=True).splitlines()
        distname, mesa_version, revision, generator_version, patchdir, distinfo = source_values
        require(distname == 'mesa-' + mesa_version and
                generator_version == mesa_version + 'nb' + revision,
                'Mesa source and generator package versions are not shared')
        require(patchdir.endswith('/MesaLib/patches') and distinfo.endswith('/MesaLib/distinfo'),
                'The generator package does not share the Mesa source patch set and archive digest')
        provider_path = RECIPE.parent / 'mesa-generators'
        provider_make = (provider_path / 'Makefile').read_text()
        provider_make_lines = provider_make.splitlines()
        prefs_index = provider_make_lines.index('.include "../../mk/bsd.prefs.mk"')
        bison_index = provider_make_lines.index('TOOLS_PLATFORM.bison= ${TOOLBASE}/bin/bison')
        flex_index = provider_make_lines.index('TOOLS_PLATFORM.flex= ${TOOLBASE}/bin/flex')
        clang_index = provider_make_lines.index('.include "../../lang/clang/buildlink3.mk"')
        require(prefs_index < bison_index < clang_index and prefs_index < flex_index < clang_index,
                'The provider must initialize TOOLBASE before selecting host Bison/Flex paths')
        provider_lines = []
        for line in provider_make.splitlines():
            if line.startswith('.include '):
                include = line.split('"')[1]
                if include == '../MesaLib/mesa-source.mk':
                    provider_lines.append('.include "' + str(RECIPE / 'mesa-source.mk') + '"')
                continue
            provider_lines.append(line)
        provider_query = work / 'provider-query.mk'
        provider_query.write_text('PKGVERSION_NOREV= ${PKGNAME:C/^mesa-generators-//}\n' +
                                  'TOOL_PYTHONBIN= /selected/python3.15\n' +
                                  'TOOLBASE= /selected/host-prefix\n' +
                                  'TOOLS_PLATFORM.bison?= /selected/host-prefix/bin/bison\n' +
                                  'TOOLS_PLATFORM.flex?= /selected/host-prefix/bin/flex\n' +
                                  '\n'.join(provider_lines) + '''
show:
	@printf '%s\\n' ${PKGNAME:Q}
	@printf '%s\\n' ${PKGREVISION:Q}
	@printf '%s\\n' ${PKGVERSION_NOREV:Q}
	@printf '%s\\n' ${MESA_GENERATORS_VERSION:Q}
	@printf '%s\\n' ${DISTNAME:Q}
	@printf '%s\\n' ${PATCHDIR:Q}
	@printf '%s\\n' ${DISTINFO_FILE:Q}
	@printf '%s\\n' ${TOOL_DEPENDS:Q}
	@printf '%s\\n' ${SUBST_CLASSES:Q}
	@printf '%s\\n' ${SUBST_STAGE.python:Q}
	@printf '%s\\n' ${SUBST_FILES.python:Q}
	@printf '%s\\n' ${SUBST_SED.python:Q}
	@printf '%s\\n' ${MESON_ARGS:Q}
	@printf '%s\\n' ${USE_TOOLS:Q}
	@printf '%s\\n' ${TOOLS_PLATFORM.bison:Q}
	@printf '%s\\n' ${TOOLS_PLATFORM.flex:Q}
''')
        provider_values = subprocess.check_output([str(args.bmake), '-r', '-m', '/', '-f',
                                                   str(provider_query), 'show'],
                                                  cwd=provider_path, text=True).splitlines()
        expected_name = 'mesa-generators-' + mesa_version
        expected_pkgver = mesa_version + 'nb' + revision
        require(provider_values[0:4] == [expected_name, revision, mesa_version, expected_pkgver],
                'The provider package name/version metadata is cyclic or does not match Mesa')
        require(provider_values[4] == distname and provider_values[5].endswith('/MesaLib/patches') and
                provider_values[6].endswith('/MesaLib/distinfo'),
                'The provider package does not use the shared source identity and complete patch set')
        require(provider_values[8:11] == ['python', 'pre-configure', 'meson.build'] and
                '/selected/python3.15' in provider_values[11],
                'The provider does not substitute the selected host Python before configure')
        require('-Dcpp_rtti=true' in provider_values[12].split(),
                'The provider passed an invalid Meson boolean for C++ RTTI')
        require({'bison', 'flex', 'cmake', 'pkg-config'} <= set(provider_values[13].split()) and
                'ninja' not in provider_values[13].split(),
                'The provider tool declaration does not match the Meson input tools')
        require('bison-' in provider_values[7] and 'flex>=' in provider_values[7],
                'The provider does not declare its selected Bison/Flex packages')
        require(provider_values[14:16] == ['/selected/host-prefix/bin/bison',
                                            '/selected/host-prefix/bin/flex'],
                'The provider fell back to a platform Bison/Flex tool')
        provider_plist = (RECIPE.parent / 'mesa-generators/PLIST').read_text().splitlines()
        require({'bin/mesa_clc', 'bin/vtn_bindgen2', 'bin/pco_clc'} ==
                {line for line in provider_plist if line.startswith('bin/')},
                'The native package installed generator interface is incomplete')
        require(not any(name in provider_make for name in ('py-lxml', 'py-rnc2rng', 'py-rply', 'py-appdirs')),
                'Optional schema/test modules became mandatory native package dependencies')
        tools = work / 'sealed'
        tools.mkdir()
        (tools / 'installed.sha256').write_text('metadata fixture only; never executed\n')
        source = (RECIPE / 'Makefile').read_text()
        checks = 0
        for arch in ('x86_64', 'aarch64'):
            for cross, selected in ((False, False), (True, None), (True, True)):
                values = parse(args.bmake, work, source, arch, 'yes' if cross else 'no',
                               tools if selected is True else '' if selected is None else work / 'missing')
                oracle(values, arch, cross, selected, expected_pkgver)
                if cross and selected is None:
                    for name in ('mesa_clc', 'vtn_bindgen2', 'pco_clc'):
                        path = work / 'native-prefix/bin' / name
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_text('#!/bin/sh\nexit 0\n')
                        path.chmod(0o755)
                    prefix_fixture = work / 'fixture.mk'
                    prefix_fixture.write_text(prefix_fixture.read_text().replace('TOOLBASE=/usr/pkg',
                                                                                 'TOOLBASE=' + str(work / 'native-prefix')))
                    result = subprocess.run([str(args.bmake), '-r', '-m', '/', '-f', str(prefix_fixture),
                                             'emberbsd-mesa-generators-check'],
                                            cwd=RECIPE, capture_output=True, text=True)
                    require(result.returncode == 0, 'The normal package provider check failed: ' + result.stderr)
                    native_path = Path(values['_EMBERBSD_MESA_NATIVE'])
                    native_path.unlink(missing_ok=True)
                    generated = subprocess.run([str(args.bmake), '-r', '-m', '/', '-f', str(prefix_fixture),
                                                str(native_path)], cwd=RECIPE, capture_output=True, text=True)
                    require(generated.returncode == 0, 'The normal Meson native file was not regenerated: ' +
                            generated.stdout + generated.stderr)
                    native_text = native_path.read_text()
                    required_tools = values['_EMBERBSD_MESA_GENERATOR_NAMES'].split()
                    require(all(name + " = '" + str(work / 'native-prefix/bin' / name) + "'" in native_text
                                for name in required_tools),
                            'The normal native file does not bind the selected package executables ' +
                            arch + ' ' + repr(required_tools) + ': ' + native_text)
                    # A retained work directory must follow selection changes,
                    # while identical contents must keep Meson's input mtime.
                    command = [str(args.bmake), '-r', '-m', '/', '-f', str(prefix_fixture)]
                    switched = subprocess.run(command + ['EMBERBSD_MESA_GENERATORS=' + str(tools),
                                                          str(native_path)],
                                              cwd=RECIPE, capture_output=True, text=True)
                    require(switched.returncode == 0 and all(
                        name + " = '" + str(tools / 'bin' / name) + "'" in native_path.read_text()
                        for name in required_tools),
                        'The retained native file ignored the selected external generator paths')
                    restored = subprocess.run(command + [str(native_path)], cwd=RECIPE,
                                              capture_output=True, text=True)
                    require(restored.returncode == 0 and native_path.read_text() == native_text,
                            'The retained native file ignored the return to packaged generators')
                    before_mtime = native_path.stat().st_mtime_ns
                    repeated = subprocess.run(command + [str(native_path)], cwd=RECIPE,
                                              capture_output=True, text=True)
                    require(repeated.returncode == 0 and
                            native_path.stat().st_mtime_ns == before_mtime,
                            'Unchanged native generator selection touched the Meson input')
                if cross and selected is True:
                    result = subprocess.run([str(args.bmake), '-r', '-m', '/', '-f', str(work / 'fixture.mk'),
                                             'EMBERBSD_MESA_GENERATORS=' + str(work / 'missing'),
                                             'emberbsd-mesa-generators-check'],
                                            cwd=RECIPE, capture_output=True, text=True)
                    require(result.returncode != 0 and
                            'installed.sha256 seal' in result.stderr,
                            'The external path accepted a missing generator seal')
                checks += 1
        for arch in ('x86_64', 'aarch64'):
            for cross in (False, True):
                values = parse(args.bmake, work, source, arch, 'yes' if cross else 'no',
                               '' if cross else work / 'missing', tests=True)
                oracle(values, arch, cross, None, expected_pkgver, tests=True)
                checks += 1
        for arch in ('x86_64', 'aarch64'):
            for cross in (False, True):
                values = parse(args.bmake, work, source, arch, 'yes' if cross else 'no',
                               work / 'missing', minimal=True)
                options = set(values['MESON_ARGS'].split())
                require({'-Dgallium-drivers=softpipe', '-Dvulkan-drivers=',
                         '-Dllvm=disabled', '-Dplatforms=x11', '-Degl=enabled',
                         '-Dgles2=enabled', '-Dbuild-tests=false'} <= options,
                        'Softpipe selection does not keep the required APIs')
                require(not any(x.startswith(('-Dmesa-clc=system', '-Dmesa-clc=enabled',
                                              '-Dprecomp-compiler=system', '-Dprecomp-compiler=enabled'))
                                for x in options), 'Softpipe imported CLC generators')
                require('vulkan-loader' not in values['DEPENDS'], 'Softpipe imported Vulkan loader')
                require(not any(item.startswith('mesa-generators-') for item in values['TOOL_DEPENDS'].split()),
                        'Softpipe imported the native shader tools package')
                require(not (set(values['TEST_INCLUDES'].split()) & BUILD_LINKS),
                        'Softpipe imported native CLC dependencies')
                require('../../lang/llvm/buildlink3.mk' not in values['TEST_INCLUDES'].split(),
                        'Softpipe imported target LLVM dependency')
                require(not values['PLIST.full_drivers'] and not values['PLIST.radeonsi'],
                        'Softpipe retained full-driver PLIST')
                checks += 1
        # The small PowerVR set keeps softpipe and adds only the Vulkan ICD.
        for arch in ('aarch64',):
            for cross, selected in ((True, True), (False, False)):
                values = parse(args.bmake, work, source, arch, 'yes' if cross else 'no',
                               tools if selected else work / 'missing', powervr=True)
                options = set(values['MESON_ARGS'].split())
                if not cross:
                    require('cross build' in values['PKG_FAIL_REASON'],
                            'The PowerVR set accepted a native build without generators')
                    checks += 1
                    continue
                require({'-Dgallium-drivers=softpipe', '-Dvulkan-drivers=imagination',
                         '-Dimagination-srv=false', '-Dllvm=disabled',
                         '-Dmesa-clc=system', '-Dprecomp-compiler=system'} <= options,
                        'The PowerVR set lost its driver or generator selection')
                require('-Dvulkan-drivers=' not in options, 'The PowerVR set kept an empty Vulkan list')
                require('vulkan-loader' in values['DEPENDS'], 'The PowerVR ICD lacks the Vulkan loader')
                require(values['PLIST.powervr'] == 'yes' and not values['PLIST.full_drivers'],
                        'The PowerVR set has the wrong package files')
                require('../../lang/llvm/buildlink3.mk' not in values['TEST_INCLUDES'].split(),
                        'The PowerVR set imported target LLVM')
                checks += 1
        # Exercise the real options policy with a stub for pkgsrc's option resolver.
        option_source = (RECIPE / 'options.mk').read_text().replace(
            '.include "../../mk/bsd.options.mk"', '')
        option_file = work / 'options.mk'
        for selected, arch, accepted in (
            ('llvm x11 wayland', 'aarch64', True), ('softpipe-only x11', 'aarch64', True),
            ('softpipe-only x11 llvm', 'aarch64', False),
            ('softpipe-only x11 wayland', 'aarch64', False),
            ('softpipe-only', 'aarch64', False), ('x11 wayland', 'aarch64', False),
            ('softpipe-only x11 powervr', 'aarch64', True),
            ('softpipe-only x11 powervr', 'x86_64', False),
            ('llvm x11 wayland powervr', 'aarch64', False),
        ):
            option_file.write_text('PKG_OPTIONS= ' + selected + '\n' + option_source +
                                   '\nshow:\n\t@printf "%s\\n" ${PKG_FAIL_REASON:Q}\n')
            result = subprocess.run([str(args.bmake), '-r', '-m', '/', '-f', str(option_file),
                                     'MACHINE_ARCH=' + arch, 'show'], capture_output=True, text=True)
            require(result.returncode == 0 and bool(result.stdout.strip()) != accepted,
                    'Unexpected options policy for ' + selected + ' on ' + arch + ': ' +
                    result.stdout + result.stderr)
            checks += 1
        mutations = [
            ('.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"\n# Cross builds', '.if 1\n# Cross builds'),
            ('BUILDLINK_DEPMETHOD.clang=\tbuild', 'BUILDLINK_DEPMETHOD.clang=\tfull'),
        ]
        for old, new in mutations:
            require(source.count(old) == 1, 'Causal control no longer matches the production recipe')
            values = parse(args.bmake, work, source.replace(old, new, 1), 'x86_64', 'no', work / 'missing')
            try:
                oracle(values, 'x86_64', False, False, expected_pkgver)
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
