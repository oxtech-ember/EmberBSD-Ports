#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Read real pkgsrc metadata with SDK-selection/compiler-query doubles; build nothing."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types

sys.dont_write_bytecode = True


def selected(data):
    return types.SimpleNamespace(
        compiler_family=data['family'], path=data['path'], abi_flags=data['flags'],
        tool=lambda role: data['tools'][role],
        command=lambda role: (data['tools'][role],))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-source', type=Path, required=True)
    parser.add_argument('--pkgsrc', type=Path, required=True)
    parser.add_argument('--bmake', type=Path, required=True)
    parser.add_argument('--darwin-sdk', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(args.sdk_source / 'src'))
    source = root / 'profiles/common-build-tools'
    spec = importlib.util.spec_from_file_location('native_adapter', source / 'cross/prepare-native-tools.py')
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    with tempfile.TemporaryDirectory(prefix='ember-native-profile-') as temporary:
        work = Path(temporary)
        profile = work / 'profile'
        profile.mkdir()
        for original, name in (
                (source / 'mk.conf', 'EMBERBSD-COMMON-TOOLS-MK.CONF'),
                (source / 'cross/native-tools.mk', 'EMBERBSD-NATIVE-TOOLS.MK'),
                (source / 'cross/prepare-native-tools.py', 'prepare-native-tools.py'),
                (root / 'pkgsrc/defaults.mk.conf', 'EMBERBSD-DEFAULTS-MK.CONF')):
            shutil.copyfile(original, profile / name)
        loader = profile / 'lang/llvm/files/sdk_source.py'
        loader.parent.mkdir(parents=True)
        shutil.copyfile(root / 'pkgsrc/lang/llvm/files/sdk_source.py', loader)
        system = work / 'sys'
        system.mkdir()
        (system / 'bsd.own.mk').write_text('.include "${MAKECONF}"\n')
        calls = work / 'compiler-calls.jsonl'
        compiler = f'''#!{sys.executable}
import json, pathlib, sys
with open({str(calls)!r}, 'a') as out: out.write(json.dumps(sys.argv) + '\\n')
args = sys.argv[1:]
assert '-o' not in args, 'Metadata must not compile a fixture'
if '-print-libgcc-file-name' in args: print(str(pathlib.Path(sys.argv[0]).parents[1] / 'lib/libgcc.a'))
elif '-v' in args: print('gcc version 16.2.0', file=sys.stderr)
elif '-dumpmachine' in args: print('aarch64--netbsd')
elif '-dumpversion' in args or '-dumpfullversion' in args: print('23.1.4' if 'clang' in sys.argv[0] else '16.2.0')
elif '-###' in args: pass
else: raise SystemExit('Unexpected compiler query: ' + repr(args))
'''
        for family in ('clang', 'gcc'):
            prefix = work / family
            (prefix / 'bin').mkdir(parents=True)
            (prefix / 'gcc16/bin').mkdir(parents=True)
            names = {'cc': 'bin/clang', 'cxx': 'bin/clang++', 'cpp': 'bin/clang-cpp'} if family == 'clang' else {
                'cc': 'gcc16/bin/gcc', 'cxx': 'gcc16/bin/g++', 'cpp': 'gcc16/bin/cpp'}
            tools = {}
            for role in adapter.ROLE_VARIABLES:
                if role in names or role in ('as', 'ld', 'ar', 'ranlib', 'nm', 'strip'):
                    path = prefix / names.get(role, 'bin/' + ({'as': 'clang-as', 'ld': 'ld.lld'}.get(role, 'llvm-' + role) if family == 'clang' else role))
                    path.write_text(compiler)
                    path.chmod(0o755)
                    tools[role] = str(path)
                else:
                    tools[role] = str(args.bmake) if role in ('make', 'bmake') else (
                        sys.executable if role == 'python' else shutil.which({'sh': 'mksh', 'install': 'bsdinstall'}.get(role, role)))
                    if not tools[role]:
                        path = prefix / 'bin' / role
                        path.write_text(f'#!{sys.executable}\nraise SystemExit(\"Unexpected generator execution in metadata test\")\n')
                        path.chmod(0o755)
                        tools[role] = str(path)
            data = dict(family=family, tools=tools, path=str(prefix / 'bin') + ':' + os.environ['PATH'],
                        flags={key: [] for key in ('cppflags', 'cflags', 'cxxflags', 'ldflags')})
            mapping = work / (family + '-tools.mk')
            mapping.write_bytes(adapter.render(selected(data)))
            # Keep the actual adapter and SDK import contract. Double only the
            # loader result: no claim that these fixture drivers are native tools.
            python = work / (family + '-python')
            python.write_text(f'''#!{sys.executable}
import runpy, sys, types
sys.path.insert(0, {str(args.sdk_source / 'src')!r})
from emberbsd_sdk import native_toolset
data = {data!r}
def load(prefix, *, required_roles, compiler_family):
    assert prefix == {str(prefix)!r} and compiler_family == data['family']
    assert set(required_roles) == set(data['tools'])
    return types.SimpleNamespace(compiler_family=data['family'], path=data['path'], abi_flags=data['flags'],
        tool=lambda role: data['tools'][role], command=lambda role: (data['tools'][role],))
native_toolset.load_host_prefix = load
index = next(i for i, item in enumerate(sys.argv) if item.endswith('prepare-native-tools.py'))
sys.argv = sys.argv[index:]
runpy.run_path(sys.argv[0], run_name='__main__')
''')
            python.chmod(0o755)
            pkginfo = work / (family + '-pkg-info')
            pkginfo.write_text(f'#!{tools["sh"]}\ncase "$*" in "-qe gcc16") exit 0;; "-f gcc16") echo "File: gcc16/bin/gcc"; exit 0;; esac\nexit 1\n')
            pkginfo.chmod(0o755)
            config = work / (family + '.conf')
            config.write_text(f'''PREFIX={prefix}
LOCALBASE={prefix}
EMBERBSD_SDK_SOURCE={args.sdk_source}
EMBERBSD_HOST_PREFIX={prefix}
EMBERBSD_HOST_PYTHON={python}
EMBERBSD_NATIVE_TOOLSET_MAKECONF={mapping}
''' + ('EMBERBSD_HOST_COMPILER_FAMILY=gcc\n' if family == 'gcc' else '') +
                f'.include "{profile}/EMBERBSD-COMMON-TOOLS-MK.CONF"\n')
            keys = ('PKGSRC_COMPILER', 'CCPATH', 'CXXPATH', 'PKG_CC', 'PKG_CXX', 'PKG_AR', 'PKG_LD',
                    'DEPENDS', 'BUILD_DEPENDS', 'TOOL_DEPENDS', 'PKG_FAIL_REASON', 'MAKE_JOBS',
                    'USE_PKGSRC_GCC_RUNTIME', 'BUILDLINK_DEPMETHOD.gcc16', 'NATIVE_CC')

            def query(platform, recipe='devel/zlib', *extra, reject=None):
                opsys, arch = platform
                version, number = ('11.0', '110000') if opsys == 'NetBSD' else ('26.0', '260000')
                command = [str(args.bmake), '-r', '-m', str(system), '-C', str(args.pkgsrc / recipe),
                           'MAKECONF=' + str(config), 'OPSYS=' + opsys, 'OS_VERSION=' + version,
                           'OPSYS_VERSION=' + number, 'NATIVE_OPSYS=' + opsys,
                           'NATIVE_OS_VERSION=' + version, 'NATIVE_OPSYS_VERSION=' + number,
                           'MACHINE_ARCH=' + arch, 'HOST_MACHINE_ARCH=' + arch, 'MACHINE_GNU_ARCH=' + arch,
                           'MACHINE_CPU=' + arch, 'LOWER_OPSYS=' + opsys.lower(),
                           'OBJECT_FMT=' + ('ELF' if opsys == 'NetBSD' else 'Mach-O'),
                           'OSX_VERSION=27.0', 'OSX_SDK_PATH=' + str(args.darwin_sdk),
                           'PKG_INFO=' + str(pkginfo), 'PKG_ADMIN=' + shutil.which('pkg_admin'), 'PKG_BUILD_OPTIONS.gcc16=c++ always-libgcc',
                           'PKG_BUILD_OPTIONS.llvm=tests', 'WRKOBJDIR=' + str(work / 'objects'),
                           'USE_BUILTIN.dl=yes', 'USE_BUILTIN.pthread=yes', 'H_PTHREAD=/usr/include/pthread.h',
                           '_GCC_VERSION=16.2.0', *extra,
                           *[word for key in keys for word in ('-V', '${' + key + '}')]]
                environment = dict(os.environ, CONFIG_SHELL=tools['sh'])
                result = subprocess.run(command, env=environment, capture_output=True, text=True)
                if reject:
                    assert result.returncode and reject in result.stdout + result.stderr, result.stdout + result.stderr
                    return
                assert result.returncode == 0, result.stdout + result.stderr
                values = result.stdout.splitlines()
                assert len(values) == len(keys), result.stdout + result.stderr
                return dict(zip(keys, values))

            for platform in (('NetBSD', 'aarch64'), ('NetBSD', 'x86_64'), ('Darwin', 'aarch64')):
                for recipe in ('devel/zlib', 'textproc/icu'):
                    result = query(platform, recipe, 'MAKE_JOBS=18')
                    assert result['PKGSRC_COMPILER'] == family, result
                    assert result['CCPATH'] == tools['cc'] and result['CXXPATH'] == tools['cxx'], result
                    assert result['PKG_AR'] == tools['ar'] and result['PKG_LD'] == tools['ld'], result
                    expected_cc = tools['cc'] if family == 'clang' else str(work / 'objects' / recipe / 'work/.gcc/bin/gcc')
                    assert result['PKG_CC'] == expected_cc, result
                    if recipe == 'textproc/icu':
                        expected_cxx = tools['cxx'] if family == 'clang' else str(work / 'objects' / recipe / 'work/.gcc/bin/g++')
                        assert result['PKG_CXX'] == expected_cxx, result
                    assert result['MAKE_JOBS'] == '18' and result['NATIVE_CC'] == tools['cc'], result
                    assert not result['PKG_FAIL_REASON'], result
                    deps = ' '.join(result[key] for key in ('DEPENDS', 'BUILD_DEPENDS', 'TOOL_DEPENDS'))
                    assert ('gcc16>=' in deps) == (family == 'gcc'), result
                    assert 'gcc16-libs' not in deps, result
                    if family == 'gcc':
                        assert result['USE_PKGSRC_GCC_RUNTIME'] == 'no' and result['BUILDLINK_DEPMETHOD.gcc16'] == 'full', result
                    print('PASS:', family, *platform, recipe, 'metadata/compiler route')
            platform = ('NetBSD', 'aarch64')
            if family == 'clang':
                unsupported = query(platform, 'devel/zlib', 'USE_LANGUAGES=ada')
                assert unsupported['PKGSRC_COMPILER'] == 'clang', unsupported
                assert 'gcc16>=' not in unsupported['DEPENDS'] + unsupported['TOOL_DEPENDS'], unsupported
            query(platform, 'devel/zlib', 'PKGSRC_COMPILER=' + ('gcc' if family == 'clang' else 'clang'), reject='differs from the selected native prefix family')
            query(platform, 'devel/zlib', 'CC=/usr/bin/cc', reject='differs from the selected native Ports tool')
            query(platform, 'devel/zlib', 'PKG_CC=/usr/bin/cc', reject='differs from the selected native Ports tool')
            query(platform, 'devel/zlib', 'EMBERBSD_HOST_PREFIX=', reject='Set EMBERBSD_HOST_PREFIX')
            if family == 'gcc':
                for override, message in (('USE_PKGSRC_GCC_RUNTIME=yes', 'complete gcc16 runtime'), ('BUILDLINK_DEPMETHOD.gcc16=build', 'full dependency'), ('GCC_REQD=12', 'requires GCC_REQD=16.2')):
                    assert message in query(platform, 'devel/zlib', override)['PKG_FAIL_REASON']
            query(platform, 'devel/zlib', 'PREFIX=/other', reject='PREFIX and LOCALBASE')
            query(platform, 'devel/zlib', 'USE_CROSS_COMPILE=yes', reject='requires native package builds')
            query(platform, 'devel/zlib', '_EMBER_SDK_CC=/usr/bin/cc', reject='reserved SDK native selection')
            if family == 'clang':
                native_inputs = work / 'cross-native-inputs.mk'
                native_inputs.write_text(config.read_text().split('.include', 1)[0])
                subprocess.run([sys.executable, '-B', str(source / 'tests/cross-targets.py'), '--sdk-source', str(args.sdk_source), str(args.bmake), str(native_inputs)], env=dict(os.environ, CONFIG_SHELL=tools['sh']), check=True)
            mapping.write_bytes(mapping.read_bytes() + b'# stale mapping\n')
            query(platform, reject='native include is invalid')
        assert not (work / 'objects').exists(), 'Metadata created package work'
    print('PASS: family/override/cross/stale-mapping refusals; no package build or prefix writes')


if __name__ == '__main__':
    main()
