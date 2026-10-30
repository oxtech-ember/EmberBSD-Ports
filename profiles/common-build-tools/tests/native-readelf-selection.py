#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the selected native readelf mapping in pkgsrc host recursion."""
import argparse
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types

sys.dont_write_bytecode = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-source', type=Path, required=True)
    parser.add_argument('--host-prefix', type=Path, required=True)
    parser.add_argument('--pkgsrc', type=Path, required=True)
    parser.add_argument('--bmake', type=Path, required=True)
    parser.add_argument('--compiler-family', choices=('clang', 'gcc'), default='clang')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(args.sdk_source / 'src'))
    spec = importlib.util.spec_from_file_location(
        'native_adapter', root / 'profiles/common-build-tools/cross/prepare-native-tools.py')
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    selection_args = types.SimpleNamespace(host_prefix=str(args.host_prefix),
                                           compiler_family=args.compiler_family, fetch_mode='manual')
    toolset = adapter.selection(selection_args)
    if 'readelf' not in toolset.tools:
        raise SystemExit('The selected SDK host prefix does not provide optional readelf')
    selected_readelf = str(Path(toolset.tool('readelf')).absolute())
    if not Path(selected_readelf).resolve(strict=True).is_relative_to(args.host_prefix.resolve(strict=True)):
        raise SystemExit('SDK readelf resolves outside the selected host prefix')

    with tempfile.TemporaryDirectory(prefix='ember-native-readelf-') as temporary:
        work = Path(temporary)
        mapping = work / 'native-tools.mk'
        mapping.write_bytes(adapter.render(toolset, fetch_mode='manual'))

        without_readelf = types.SimpleNamespace(
            compiler_family=toolset.compiler_family, path=toolset.path,
            abi_flags=toolset.abi_flags, host=toolset.host,
            tools={role: path for role, path in toolset.tools.items() if role != 'readelf'},
            tool=toolset.tool, command=toolset.command)
        assert b'TOOLS_PATH.readelf' not in adapter.render(without_readelf, fetch_mode='manual'), (
            'readelf must stay optional when the host prefix has no ELF reader')

        profile = work / 'profile'
        (profile / 'cross').mkdir(parents=True)
        shutil.copyfile(root / 'profiles/common-build-tools/mk.conf', profile / 'EMBERBSD-COMMON-TOOLS-MK.CONF')
        shutil.copyfile(root / 'profiles/common-build-tools/cross/native-tools.mk', profile / 'cross/native-tools.mk')
        (profile / 'cross/prepare-native-tools.py').symlink_to(
            root / 'profiles/common-build-tools/cross/prepare-native-tools.py')
        shutil.copyfile(root / 'pkgsrc/defaults.mk.conf', profile / 'EMBERBSD-DEFAULTS-MK.CONF')
        shutil.copyfile(root / 'pkgsrc/versions.mk', profile / 'EMBERBSD-VERSIONS.MK')
        system = work / 'sys'
        system.mkdir()
        (system / 'bsd.own.mk').write_text('.include "${MAKECONF}"\n')
        config = work / 'mk.conf'
        config.write_text(f'''PREFIX={args.host_prefix}
LOCALBASE={args.host_prefix}
EMBERBSD_SDK_SOURCE={args.sdk_source}
EMBERBSD_HOST_PREFIX={args.host_prefix}
EMBERBSD_HOST_PYTHON={toolset.tool('python')}
EMBERBSD_NATIVE_TOOLSET_MAKECONF={mapping}
EMBERBSD_HOST_COMPILER_FAMILY={args.compiler_family}
EMBERBSD_HOST_FETCH_MODE=manual
.include "{profile / 'EMBERBSD-COMMON-TOOLS-MK.CONF'}"
# pkgsrc's own metadata makefiles invoke base shell utilities by name; the
# tested mapping still pins the SDK tools before this test-only extension.
PATH:= ${{PATH}}:/usr/bin:/bin
.export PATH
''')
        bmake = str(args.bmake)
        package = args.pkgsrc / 'pkgtools/cwrappers'
        common = [bmake, '-r', '-m', str(system), '-C', str(package), 'MAKECONF=' + str(config),
                  'OPSYS=Linux', 'OS_VERSION=6.1', 'OPSYS_VERSION=601000',
                  'NATIVE_OPSYS=Linux', 'NATIVE_OS_VERSION=6.1', 'NATIVE_OPSYS_VERSION=601000',
                  'MACHINE_ARCH=x86_64', 'HOST_MACHINE_ARCH=x86_64', 'MACHINE_GNU_ARCH=x86_64',
                  'MACHINE_CPU=x86_64', 'LOWER_OPSYS=linux', 'OBJECT_FMT=ELF',
                  'TARGET_OPSYS=NetBSD', 'TARGET_MACHINE_ARCH=aarch64',
                  'PKG_INFO=/bin/true', 'PKG_ADMIN=/bin/true', 'SKIP_LICENSE_CHECK=yes',
                  'USE_CROSS_COMPILE=no', 'TOOLS_USE_CROSS_COMPILE=no',
                  'CHECK_SHLIBS_SUPPORTED=yes', 'USE_TOOLS+=readelf']
        environment = dict(os.environ, CONFIG_SHELL=toolset.tool('sh'), PATH=toolset.path)
        result = subprocess.run([*common, '-V', 'TOOLS_PATH.readelf',
                                 '-V', 'CHECK_SHLIBS_SUPPORTED', '-V', 'OBJECT_FMT'],
                                env=environment, capture_output=True, text=True)
        if result.returncode != 0:
            raise SystemExit(result.stdout + result.stderr)
        values = [line for line in result.stdout.splitlines() if line]
        assert values == [selected_readelf, 'yes', 'ELF'], result.stdout
        print('PASS: native cwrappers metadata selects SDK readelf for ELF checks')

        overridden = subprocess.run([*common, 'TOOLS_PATH.readelf=/tmp/override-readelf',
                                     '-V', 'TOOLS_PATH.readelf'],
                                    env=environment, capture_output=True, text=True)
        assert overridden.returncode != 0 and \
            'TOOLS_PATH.readelf differs from the selected Ports tool' in overridden.stdout + overridden.stderr, (
                overridden.stdout + overridden.stderr)
        print('PASS: native command-line readelf override is rejected')

        target_readelf = str(work / 'cross-tools/bin/aarch64--netbsd-readelf')
        cross_makefile = work / 'cross.mk'
        cross_makefile.write_text(f'USE_CROSS_COMPILE=yes\n.include "{mapping}"\n'
                                  f'TOOLS_PATH.readelf?={target_readelf}\n')
        cross = subprocess.run([bmake, '-r', '-f', str(cross_makefile), '-V', 'TOOLS_PATH.readelf'],
                               env=environment, capture_output=True, text=True)
        if cross.returncode != 0:
            raise SystemExit(cross.stdout + cross.stderr)
        assert cross.stdout.strip() == target_readelf, cross.stdout + cross.stderr
        print('PASS: native mapping preserves the selected cross-target readelf')


if __name__ == '__main__':
    main()
