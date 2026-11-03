#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check runtime/devel dependency separation with real pkgsrc and bmake."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[4]
COMPONENTS = ('libcxx', 'libcxxabi', 'libunwind')


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def framework_view(export, destination):
    destination.mkdir()
    for item in export.iterdir():
        if item.name not in ('lang', 'runtime-fixture', '.git'):
            (destination / item.name).symlink_to(item, target_is_directory=item.is_dir())
    lang = destination / 'lang'
    lang.mkdir()
    selected = {name for component in COMPONENTS for name in (component, component + '-devel')}
    for item in (export / 'lang').iterdir():
        if item.name in selected:
            shutil.copytree(item, lang / item.name, symlinks=True)
        else:
            (lang / item.name).symlink_to(item, target_is_directory=item.is_dir())
    for name in selected:
        shutil.copyfile(ROOT / 'pkgsrc/lang' / name / 'buildlink3.mk',
                        lang / name / 'buildlink3.mk')
    package = destination / 'runtime-fixture/consumer'
    package.mkdir(parents=True)
    includes = ''.join(f'.include "../../lang/{name}/buildlink3.mk"\n' for name in COMPONENTS)
    (package / 'Makefile').write_text(
        'DISTNAME= split-runtime-fixture-1\n'
        'CATEGORIES= runtime-fixture\n'
        'COMMENT= metadata fixture\n'
        'LICENSE= 2-clause-bsd\n'
        'USE_LANGUAGES= c c++\n' + includes + '.include "../../mk/bsd.pkg.mk"\n')
    return package


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('pkgsrc', 'bmake', 'make-mk', 'shell', 'makeconf', 'env-json', 'work'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--make-arg', action='append', default=[])
    args = parser.parse_args()
    for name, value in vars(args).items():
        if isinstance(value, Path):
            require(value.is_absolute(), f'{name} must be absolute')
    require((args.pkgsrc / 'mk/bsd.pkg.mk').is_file(), 'actual pkgsrc export required')
    require(not os.path.lexists(args.work), 'work directory must be new')
    args.work.mkdir(parents=True)
    (args.work / 'tmp').mkdir()
    package = framework_view(args.pkgsrc, args.work / 'pkgsrc')
    env = json.loads(args.env_json.read_text())
    env = env.get('environment', env)
    require(isinstance(env, dict) and all(isinstance(k, str) and isinstance(v, str)
                                         for k, v in env.items()), 'invalid environment')
    env['TMPDIR'] = str(args.work / 'tmp')
    base = [str(args.bmake), '-m', str(args.make_mk), 'SHELL=' + str(args.shell),
            'MAKECONF=' + str(args.makeconf), *args.make_arg,
            'BUILD_DIR=' + str(args.work / 'objects'),
            'WRKDIR=' + str(args.work / 'objects/work'),
            'PACKAGES=' + str(args.work / 'packages')]

    def query(label, options, variables):
        command = base + options
        for variable in variables:
            command.extend(('-V', '${' + variable + '}'))
        result = subprocess.run(command, cwd=package, env=env, capture_output=True,
                                text=True, timeout=120)
        (args.work / (label + '.stdout')).write_text(result.stdout)
        (args.work / (label + '.stderr')).write_text(result.stderr)
        require(result.returncode == 0, f'{label} failed: {result.stderr}')
        lines = result.stdout.splitlines()
        require(len(lines) == len(variables), f'{label}: unexpected bmake output')
        return dict(zip(variables, lines))

    variables = ['DEPENDS', 'BUILD_DEPENDS']
    for component in COMPONENTS:
        variables += [f'BUILDLINK_PKGSRCDIR.{component}',
                      f'BUILDLINK_PKGSRCDIR.{component}-devel',
                      f'BUILDLINK_INCDIRS.{component}-devel',
                      f'BUILDLINK_LIBDIRS.{component}',
                      f'BUILDLINK_LIBDIRS.{component}-devel',
                      f'BUILDLINK_DEPMETHOD.{component}-devel']
    selected = query('netbsd-cross', ['OPSYS=NetBSD', 'MACHINE_ARCH=x86_64',
        'USE_CROSS_COMPILE=yes', 'EMBER_LLVM_CXX_SYSROOT=' + str(args.work / 'sysroot')], variables)
    for component in COMPONENTS:
        runtime = component + '>='
        development = component + '-devel>='
        require(any(x.startswith(runtime) for x in selected['DEPENDS'].split()),
                f'{component}: runtime dependency missing')
        require(not any(x.startswith(development) for x in selected['DEPENDS'].split()),
                f'{component}: devel leaked into runtime dependencies')
        require(any(x.startswith(development) for x in selected['BUILD_DEPENDS'].split()),
                f'{component}: build-only devel dependency missing')
        require(selected[f'BUILDLINK_PKGSRCDIR.{component}'].endswith('/lang/' + component),
                f'{component}: incorrect runtime owner')
        require(selected[f'BUILDLINK_PKGSRCDIR.{component}-devel'].endswith('/lang/' + component + '-devel'),
                f'{component}: incorrect devel owner')
        require('llvm/include' in selected[f'BUILDLINK_INCDIRS.{component}-devel'],
                f'{component}: missing devel headers')
        require('llvm/lib' in selected[f'BUILDLINK_LIBDIRS.{component}'].split() and
                'llvm/lib' in selected[f'BUILDLINK_LIBDIRS.{component}-devel'].split(),
                f'{component}: missing library search directory')
        require(selected[f'BUILDLINK_DEPMETHOD.{component}-devel'] == 'build',
                f'{component}: devel method not build-only')

    native_vars = ['DEPENDS'] + [f'BUILDLINK_PKGSRCDIR.{name}' for name in COMPONENTS]
    native = query('darwin-native', ['OPSYS=Darwin', 'USE_CROSS_COMPILE=no',
        'EMBER_LLVM_CXX_SYSROOT=', 'EMBER_LLVM_CXX_STAGE='], native_vars)
    for component in COMPONENTS:
        require(native[f'BUILDLINK_PKGSRCDIR.{component}'].endswith('/lang/' + component),
                f'{component}: native owner changed')
        require(not any(x.startswith(component + '-devel') for x in native['DEPENDS'].split()),
                f'{component}: native devel dependency introduced')
    print('PASS: real pkgsrc metadata distinguishes target runtime and build-only headers')


if __name__ == '__main__':
    main()
