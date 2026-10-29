#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Synthetic runtime fixture; not ABI acceptance.
"""Exercise the selected Clang cross route with the installed host toolchain."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--sdk-source', type=Path, required=True)
parser.add_argument('--host-prefix', type=Path, required=True)
parser.add_argument('--pkgsrc', type=Path, required=True,
                    help='complete pkgsrc export produced by scripts/prepare-pkgsrc.py')
parser.add_argument('--bmake', type=Path, required=True)
parser.add_argument('--runtime-only', action='store_true',
                    help='check runtime routing without the pkgsrc metadata fixture')
parser.add_argument('new_work', type=Path)
args = parser.parse_args()
sdk, prefix, work = args.sdk_source, args.host_prefix, args.new_work
sdk, prefix = sdk.resolve(strict=True), prefix.resolve(strict=True)
work.mkdir(parents=True)
work = work.resolve(strict=True)
# The OS TOOLDIR is test-owned. Never write into a user's installed tools.
os_tools = work / 'os-tools'
os_tools.mkdir()
sdk_tests = sdk / 'tests'
sys.path.insert(0, str(sdk / 'src'))
sys.path.insert(0, str(sdk_tests))
import test_llvm_builder as llvm_builder
from test_llvm_builder import LLVMBuilderTests

cross = Path(__file__).resolve().parents[1]
helper = cross / 'cross/prepare-tools.py'
ports = cross.parents[1]
python = Path(sys.executable).resolve(strict=True)
pkgsrc = args.pkgsrc.resolve(strict=True)
bmake = args.bmake.resolve(strict=True)
env = dict(os.environ)
env['EMBERBSD_HOST_PREFIX'] = str(prefix)
env['EMBERBSD_HOST_COMPILER_FAMILY'] = 'clang'
env['EMBERBSD_SDK_SOURCE'] = str(sdk)
env['PATH'] = str(prefix / 'bin')


def profile_setup():
    profile = work / 'profile'
    profile.mkdir()
    for name in ('mk.conf', 'native-tools.mk', 'prepare-native-tools.py', 'fortran.mk', 'compiler-policy.mk',
                 'gcc16-external-runtime.sh'):
        shutil.copy2(cross / 'cross' / name, profile / name)
    shutil.copy2(ports / 'pkgsrc/defaults.mk.conf', profile / 'EMBERBSD-DEFAULTS-MK.CONF')
    shutil.copy2(ports / 'pkgsrc/versions.mk', profile / 'EMBERBSD-VERSIONS.MK')
    loader = profile / 'lang/llvm/files/sdk_source.py'
    loader.parent.mkdir(parents=True)
    shutil.copy2(ports / 'pkgsrc/lang/llvm/files/sdk_source.py', loader)
    mapping = work / 'native-tools.mk.conf'
    result = subprocess.run([str(python), str(cross / 'cross/prepare-native-tools.py'),
        '--sdk-source', str(sdk), 'write', '--host-prefix', str(prefix),
        '--output', str(mapping)], env=env, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    pkg_admin = work / 'pkg_admin'
    pkg_admin.write_text('#!' + str(prefix / 'bin/mksh') + '\n'
        'case "$*" in *config-var*) echo /dev/null;; esac\nexit 0\n')
    pkg_admin.chmod(0o755)
    return profile, mapping, pkg_admin


profile, native_mapping, pkg_admin = profile_setup()


def pkgsrc_route(target, triple, tools, sysroot, *, cxx, runtime_root=None):
    config = work / ('makeconf-' + target)
    config.write_text(''.join(f'{key}= {value}\n' for key, value in {
        'BSD_PKG_MK': 'yes', 'BATCH': 'yes', 'USE_CROSS_COMPILE': 'yes',
        'EMBERBSD_SDK_SOURCE': sdk, 'EMBERBSD_HOST_PREFIX': prefix,
        'EMBERBSD_HOST_COMPILER_FAMILY': 'clang',
        'EMBERBSD_NATIVE_TOOLSET_MAKECONF': native_mapping,
        'EMBERBSD_CROSS_TOOLS': tools, 'EMBERBSD_CROSS_SYSROOT': sysroot,
        'EMBERBSD_CROSS_HOST_PREFIX': prefix, 'EMBERBSD_CROSS_TARGET': target,
        'EMBERBSD_CROSS_COMPILER_FAMILY': 'clang'} .items()) +
        f'.include "{profile / "mk.conf"}"\n')
    package = 'textproc/icu' if cxx else 'devel/zlib'
    keys = ('PKGSRC_COMPILER', 'CC', 'CXX', 'PKG_CC', 'PKG_CXX', 'PKG_FAIL_REASON',
            'DEPENDS', 'BUILD_DEPENDS', 'TOOL_DEPENDS', '.MAKE.MAKEFILES',
            'BUILDLINK_PASSTHRU_RPATHDIRS', '_CWRAPPERS_TRANSFORM')
    command = [str(bmake), '-C', str(pkgsrc / package), 'MAKECONF=' + str(config),
        'OPSYS=NetBSD', 'OS_VERSION=11.0', 'OPSYS_VERSION=110000',
        'NATIVE_OPSYS=Darwin', 'NATIVE_OS_VERSION=27.0', 'NATIVE_OPSYS_VERSION=270001',
        'MACHINE_ARCH=' + ('x86_64' if target == 'amd64' else 'aarch64'),
        'HOST_MACHINE_ARCH=arm64', 'MACHINE_GNU_ARCH=' + ('x86_64' if target == 'amd64' else 'aarch64'),
        'MACHINE_CPU=' + ('x86_64' if target == 'amd64' else 'aarch64'),
        'LOWER_OPSYS=netbsd', 'OBJECT_FMT=ELF',
        'PKG_INFO=' + str(prefix / 'bin/pkg_info'), 'PKG_ADMIN=' + str(pkg_admin),
        'SKIP_LICENSE_CHECK=yes', 'WRKOBJDIR=' + str(work / 'objects')]
    for key in keys:
        command += ['-V', '${' + key + '}']
    package_env = dict(env, PATH=str(prefix / 'bin') + os.pathsep + '/usr/bin' + os.pathsep + '/bin',
                       CONFIG_SHELL=str(prefix / 'bin/mksh'))
    result = subprocess.run(command, env=package_env,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    values = result.stdout.splitlines()
    assert len(values) == len(keys), result.stdout + result.stderr
    data = dict(zip(keys, values))
    assert data['PKGSRC_COMPILER'] == 'clang', data
    assert triple + '-clang' in data['CC'] and triple + '-clang++' in data['CXX'], data
    assert data['PKG_CC'] == str(tools / 'bin/clang'), data
    assert (tools / 'bin/clang').resolve(strict=True) == (tools / 'commands/cc').resolve(strict=True)
    if cxx:
        assert data['PKG_CXX'] == str(tools / 'bin/clang++'), data
        assert (tools / 'bin/clang++').resolve(strict=True) == (tools / 'commands/cxx').resolve(strict=True)
    assert not data['PKG_FAIL_REASON'], data['PKG_FAIL_REASON']
    if runtime_root is not None:
        assert str(runtime_root) not in data['BUILDLINK_PASSTHRU_RPATHDIRS']
        assert '/usr/pkg/llvm/lib' in data['BUILDLINK_PASSTHRU_RPATHDIRS']
        assert ('R:' + str(runtime_root) + '/usr/pkg/llvm:/usr/pkg/llvm') in data['_CWRAPPERS_TRANSFORM']
    makefiles = [Path(name) if Path(name).is_absolute() else pkgsrc / package / name
                 for name in data['.MAKE.MAKEFILES'].split()]
    assert any(path.resolve() == pkgsrc / 'mk/tools/cross.NetBSD.mk' for path in makefiles), data['.MAKE.MAKEFILES']
    dependencies = ' '.join(data[key] for key in ('DEPENDS', 'BUILD_DEPENDS', 'TOOL_DEPENDS'))
    assert 'gcc16' not in dependencies and 'gcc16-libs' not in dependencies, dependencies

    def rejected(*assignments, diagnostic):
        result = subprocess.run(command + list(assignments), env=package_env,
                                capture_output=True, text=True)
        output = result.stdout + result.stderr
        assert result.returncode != 0 and diagnostic in output, output

    rejected('EMBERBSD_CROSS_COMPILER_FAMILY=invalid',
             diagnostic='Select clang or gcc as the cross compiler family')
    if not cxx and target == 'aarch64':
        language_command = command[:command.index('-V')]
        language_command += ['USE_LANGUAGES=c fortran', '-V', '${PKGSRC_COMPILER}',
                             '-V', '${FC}', '-V', '${PKG_FAIL_REASON}']
        result = subprocess.run(language_command, env=package_env,
                                capture_output=True, text=True)
        values = result.stdout.splitlines()
        assert result.returncode == 0 and len(values) == 3, result.stdout + result.stderr
        assert values[0] == 'clang' and not values[1], values
        assert 'Select the GCC cross profile and its common Fortran provider' in values[2], values
    target_mk = tools / 'target.mk'
    original = target_mk.read_text()
    target_mk.write_text(original.replace(
        '_EMBER_TARGET_TARGET:= ' + target + '\n',
        '_EMBER_TARGET_TARGET:= ' + ('amd64' if target == 'aarch64' else 'aarch64') + '\n'))
    try:
        rejected(diagnostic='Prepared Clang tools do not match the selected target and sysroot')
    finally:
        target_mk.write_text(original)


def retarget_runtime(fixture, target):
    if target == 'amd64':
        record = fixture.record
        record.update(target='amd64', triplet='x86_64--netbsd', machine_arch='x86_64', elf_machine=62)
        old_path = fixture.stage / record['artifacts']['builtins']
        new_path = fixture.stage / record['artifacts']['builtins'].replace('aarch64', 'x86_64')
        new_path.parent.mkdir(parents=True, exist_ok=True)
        old_path.rename(new_path)
        record['artifacts']['builtins'] = record['artifacts']['builtins'].replace('aarch64', 'x86_64')
        for path in fixture.stage.rglob('*'):
            if not path.is_file() or path.is_symlink():
                continue
            data = path.read_bytes()
            # Change ELF e_machine in raw fixture objects and ELF members of ar files.
            offset = 0
            while True:
                offset = data.find(b'\x7fELF', offset)
                if offset < 0:
                    break
                data = data[:offset + 18] + (62).to_bytes(2, 'little') + data[offset + 20:]
                offset += 20
            path.write_bytes(data)
        fixture.save()


def completed_sysroot(target):
    case = LLVMBuilderTests()
    case.setUp()
    # Reuse the SDK producer fixture; this synthetic result exercises routing,
    # not the target ABI or runtime payload acceptance.
    from test_builder import fixture as builder_fixture
    options = builder_fixture(case.root, target=target)
    builder, runtime = case.builder(options=options,
                                    retarget=lambda fixture: retarget_runtime(fixture, target))

    def compiler_for_selected_target(self):
        triplet = {'aarch64': 'aarch64--netbsd', 'amd64': 'x86_64--netbsd'}[self.options['target']]
        names = {'cc': 'clang', 'cxx': 'clang++', 'cpp': 'clang', 'as': 'clang', 'ld': 'ld.lld'}
        binaries, commands = {}, {}
        for role in llvm_builder.CLANG_BINARIES:
            path = self.paths['compiler'] + '/bin/' + names.get(role, 'llvm-' + role)
            binaries[role] = dict(path=path, selected_path=path, sha256='f' * 64)
            commands[role] = [path]
        for role in ('cc', 'cxx'):
            commands[role] += ['--target=' + triplet, '--ld-path=' + binaries['ld']['path']]
        commands['cpp'] += ['-E', '--target=' + triplet]
        commands['as'] += ['--target=' + triplet, '-c', '-x', 'assembler']
        return dict(family='clang', version='23.1.4', triplet=triplet,
                    reported_triplet=triplet.replace('--', '-unknown-', 1),
                    resource_dir=self.paths['compiler'] + '/lib/clang/23',
                    binaries=binaries, commands=commands)

    llvm_builder.ClangBuilder.compiler = compiler_for_selected_target
    builder.run()
    sysroot = Path(builder.paths['destination'])
    base_header = sysroot / 'usr/include/stdint.h'
    base_header.parent.mkdir(parents=True, exist_ok=True)
    base_header.write_text('/* selected runtime base fixture */\n')
    runtime.record['base']['files'] = {
        'usr/include/stdint.h': hashlib.sha256(base_header.read_bytes()).hexdigest(),
        'usr/lib/libc.so': hashlib.sha256((sysroot / 'usr/lib/libc.so').read_bytes()).hexdigest()}
    runtime.save()
    return case, sysroot, runtime.stage


def invoke(target, sysroot, output, *, accept, extra=()):
    args = [python, helper, '--target', target, '--host-prefix', prefix,
            '--sysroot', sysroot, '--sdk-source', sdk,
            prefix, os_tools, output, *extra]
    result = subprocess.run([str(x) for x in args], env=env, text=True,
                            capture_output=True)
    text = result.stdout + result.stderr
    (work / (Path(output).name + '.log')).write_text(text)
    assert (result.returncode == 0) == accept, text
    return text


def require_default_clang(target, output):
    result = subprocess.run([str(python), str(helper), '--target', target,
        '--sdk-source', str(sdk), str(prefix), str(os_tools), str(output)],
        env=env, text=True, capture_output=True)
    text = result.stdout + result.stderr
    assert result.returncode != 0 and 'Clang applications require --sysroot and --host-prefix' in text, text
    assert not Path(output).exists()


for triple in ('aarch64--netbsd', 'x86_64--netbsd'):
    install = os_tools / ('bin/' + triple + '-install')
    install.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(prefix / 'bin/bsdinstall', install)

for target, triple, machine, instruction in (
        ('aarch64', 'aarch64--netbsd', 183, 'ret'),
        ('amd64', 'x86_64--netbsd', 62, 'retq')):
    case, sysroot, stage = completed_sysroot(target)
    try:
        output = work / ('tools-' + target)
        require_default_clang(target, work / ('default-' + target))
        result = invoke(target, sysroot, output, accept=True)
        assert 'Prepared Clang application tools' in result
        # pkgsrc's cross-root completeness probe is unrelated to runtime ABI;
        # supply its one required marker in this synthetic fixture.
        header = sysroot / 'usr/include/stddef.h'
        header.parent.mkdir(parents=True, exist_ok=True)
        header.write_text('/* cross-root routing fixture */\n')
        for role in ('as', 'ld'):
            alias = output / 'bin' / (triple + '-' + role)
            assert alias.is_symlink(), str(alias)
            assert alias.resolve(strict=True).is_relative_to(output / 'commands')
        source = work / (target + '.s')
        source.write_text('.text\n.globl fixture_entry\nfixture_entry:\n  ' + instruction + '\n')
        obj, linked = work / (target + '.o'), work / (target + '-linked.o')
        subprocess.run([output / 'bin' / (triple + '-as'), '-c', source, '-o', obj],
                       env=env, check=True, capture_output=True)
        subprocess.run([output / 'bin' / (triple + '-ld'), '-r', '-o', linked, obj],
                       env=env, check=True, capture_output=True)
        data = linked.read_bytes()
        assert data[:4] == b'\x7fELF' and int.from_bytes(data[18:20], 'little') == machine
        target_mk = (output / 'target.mk').read_text()
        assert '_EMBER_TARGET_FAMILY:= clang\n' in target_mk
        assert '_EMBER_TARGET_SYSROOT:= ' + str(sysroot) in target_mk
        assert '_EMBER_TARGET_RUNTIME_ROOT:= ' + str(sysroot) in target_mk
        assert 'gcc' not in target_mk.lower() and 'g++' not in target_mk.lower()
        staged = work / ('tools-staged-' + target)
        invoke(target, sysroot, staged, accept=True, extra=('--runtime-stage', stage))
        staged_mk = (staged / 'target.mk').read_text()
        assert '_EMBER_TARGET_RUNTIME_ROOT:= ' + str(stage) in staged_mk
        final_root = work / ('final-sysroot-' + target)
        shutil.copytree(sysroot, final_root, symlinks=True)
        (final_root / 'usr/include/stdint.h').write_text('/* final userland header */\n')
        libc = final_root / 'usr/lib/libc.so'
        libc.write_bytes(libc.read_bytes() + b'final-libc')
        ready = work / ('tools-ready-distinct-base-' + target)
        invoke(target, final_root, ready, accept=True)
        assert '_EMBER_TARGET_SYSROOT:= ' + str(final_root) in (ready / 'target.mk').read_text()
        library = final_root / 'usr/pkg/llvm/lib/libc++.so.1'
        saved_library = library.read_bytes()
        library.write_bytes(saved_library + b'damaged')
        damaged = work / ('tools-damaged-runtime-' + target)
        invoke(target, final_root, damaged, accept=False)
        assert not damaged.exists()
        library.write_bytes(saved_library)
        alternate = work / ('tools-distinct-base-' + target)
        invoke(target, final_root, alternate, accept=True,
               extra=('--runtime-stage', stage, '--runtime-base', sysroot))
        alternate_mk = (alternate / 'target.mk').read_text()
        assert '_EMBER_TARGET_SYSROOT:= ' + str(final_root) in alternate_mk
        assert '_EMBER_TARGET_RUNTIME_ROOT:= ' + str(stage) in alternate_mk
        bad_base = work / ('tools-wrong-base-' + target)
        invoke(target, final_root, bad_base, accept=False, extra=('--runtime-stage', stage))
        assert not bad_base.exists()
        without_stage = work / ('tools-base-without-stage-' + target)
        invoke(target, final_root, without_stage, accept=False, extra=('--runtime-base', sysroot))
        assert not without_stage.exists()
        commands = json.loads((staged / 'commands/commands.json').read_text())
        assert any(str(stage) in word for word in commands['commands']['cxx'])
        assert any(str(stage) in word for word in commands['link_flags']['cxx'])
        base_header = sysroot / 'usr/include/stdint.h'
        original = base_header.read_text()
        base_header.write_text('/* changed base */\n')
        invalid = work / ('tools-staged-wrong-base-' + target)
        text = invoke(target, sysroot, invalid, accept=False, extra=('--runtime-stage', stage))
        assert 'base inputs changed' in text and not invalid.exists(), text
        base_header.write_text(original)
        if not args.runtime_only:
            pkgsrc_route(target, triple, output, sysroot, cxx=(target == 'aarch64'))
            pkgsrc_route(target, triple, staged, sysroot, cxx=(target == 'aarch64'), runtime_root=stage)
    finally:
        case.doCleanups()

# The adapter must refuse absent runtime inputs before creating its output.
case, sysroot, stage = completed_sysroot('aarch64')
try:
    missing = work / 'missing-sysroot'
    text = invoke('aarch64', work / 'no-such-sysroot', missing, accept=False)
    assert 'sysroot' in text.lower() and not missing.exists(), text
    mismatch = work / 'mismatched-runtime'
    text = invoke('amd64', sysroot, mismatch, accept=False)
    assert 'completed matching SDK sysroot' in text and not mismatch.exists(), text
finally:
    case.doCleanups()

print('PASS: selected Clang assembler/linker for AArch64 and amd64; input refusals; synthetic runtime only')
