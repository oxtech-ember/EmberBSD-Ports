#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted), NSS host-tool cross-link regression.
"""Check NSS cross target routing and the native nsinstall host helper."""
import argparse
import hashlib
from pathlib import Path
import shutil
import stat
import sys
sys.dont_write_bytecode = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-source', required=True, type=Path)
    parser.add_argument('--ports-root', required=True, type=Path)
    parser.add_argument('--source-root', required=True, type=Path,
                        help='Extracted NSS source root; pkgsrc may or may not be patched.')
    parser.add_argument('--host-cc', required=True, type=Path)
    parser.add_argument('--bmake', required=True, type=Path)
    parser.add_argument('--gmake', required=True, type=Path)
    parser.add_argument('--target-release', required=True)
    parser.add_argument('--target-arch', choices=('amd64', 'aarch64eb'), required=True)
    parser.add_argument('--patch-tool', default='patch')
    parser.add_argument('--file-tool', default='file')
    parser.add_argument('--work', required=True, type=Path)
    args = parser.parse_args()
    if sys.implementation.name != 'cpython' or sys.version_info[:2] != (3, 15):
        parser.error('Use CPython 3.15.')
    if sys.platform != 'darwin':
        parser.error('This regression verifies Darwin ld rejecting NetBSD target flags; run it on macOS.')

    sdk_root = args.sdk_source.resolve(strict=True)
    sdk_src = sdk_root / 'src'
    package = (sdk_src / 'emberbsd_sdk').resolve(strict=True)
    sys.path.insert(0, str(sdk_src))
    import emberbsd_sdk
    from emberbsd_sdk import inventory, jsonio, paths, process
    from emberbsd_sdk.errors import CommandError
    if type(emberbsd_sdk.API_VERSION) is not int or emberbsd_sdk.API_VERSION != 1:
        parser.error('The selected SDK must provide API version 1.')
    if Path(emberbsd_sdk.__file__).resolve().parent != package:
        parser.error('emberbsd_sdk did not load from the explicitly selected SDK.')
    for module in (inventory, jsonio, paths, process):
        if not Path(module.__file__).resolve().is_relative_to(package):
            parser.error('An SDK module loaded from outside the selected SDK.')

    ports = args.ports_root.resolve(strict=True)
    source = args.source_root.resolve(strict=True)
    host_cc = args.host_cc.resolve(strict=True)
    bmake = args.bmake.resolve(strict=True)
    gmake = args.gmake.resolve(strict=True)
    pkgsrc = ports / 'upstream/pkgsrc'
    pkg = pkgsrc / 'devel/nss'
    source_coreconf = source / 'nss/coreconf'
    if not (pkg / 'Makefile').is_file() or not (source_coreconf / 'nsinstall/Makefile').is_file():
        parser.error('Expected pkgsrc devel/nss and source nss/coreconf/Makefile.')
    if not args.target_release or any(c.isspace() for c in args.target_release):
        parser.error('Use a nonempty target OS release without whitespace.')
    target_cpu = {'amd64': 'x86_64', 'aarch64eb': 'aarch64'}[args.target_arch]
    work = Path(paths.canonical_new(args.work))
    if work.exists() or work.is_symlink():
        parser.error('The output directory must be new.')
    for item in (ports, source, sdk_root, host_cc, bmake, gmake):
        paths.reject_overlap(str(work), str(item))
    if not (ports / 'scripts/prepare-pkgsrc.py').is_file():
        parser.error('The selected Ports root is missing scripts/prepare-pkgsrc.py.')

    work.mkdir(mode=0o700)
    temp = work / 'tmp'
    temp.mkdir()
    env = process.sanitized_environment()
    env.update(TMPDIR=str(temp), TMP=str(temp), TEMP=str(temp))
    commands = []
    receipt = {
        'test': 'nss-cross-host-tools',
        'sdk': {'root': str(sdk_root), 'api_version': 1},
        'ports_root': str(ports),
        'source_root': str(source),
        'target': {'os': 'NetBSD', 'release': args.target_release,
                   'machine_arch': args.target_arch, 'cpu_arch': target_cpu},
        'scope': 'NetBSD target OS_ARCH routing, the upstream Darwin-only link guard, and native nsinstall helper only. No target NSS library/package, shlibsign, or FIPS acceptance.',
        'commands': commands,
        'status': 'running',
    }

    def run(label, argv, *, cwd, input_data=None, expect=None):
        command = [str(item) for item in argv]
        try:
            result = process.capture(command, cwd=str(cwd), env=env, input=input_data)
            stdout, stderr, status = result.stdout, result.stderr, result.returncode
        except CommandError as error:
            stdout, stderr, status = error.stdout, error.stderr, error.returncode
        (work / (label + '.stdout')).write_bytes(stdout)
        (work / (label + '.stderr')).write_bytes(stderr)
        commands.append({'label': label, 'argv': command, 'cwd': str(cwd),
                         'status': status, 'expected': expect})
        jsonio.write_json(work / 'commands.json', commands, exclusive=False)
        if expect == 'success' and status != 0:
            raise RuntimeError(f'{label} failed with {status}; see {work}')
        if expect == 'failure' and status == 0:
            raise RuntimeError(f'{label} unexpectedly succeeded; see {work}')
        if type(expect) is int and status != expect:
            raise RuntimeError(f'{label} returned {status}, expected {expect}; see {work}')
        return status, stdout, stderr

    def ignore_coreconf(_directory, names):
        ignored = []
        for name in names:
            if name in ('dist', '.git') or name.endswith('.OBJ') or name.endswith(('.orig', '.rej', '.o', '.a', '.so', '.dylib', '.pyc')):
                ignored.append(name)
        return ignored

    try:
        delta = ports / 'profiles/common-build-tools/patches/pkgsrc-nss-cross-host-tools.patch'
        if not delta.is_file():
            raise RuntimeError('Missing pkgsrc-nss-cross-host-tools.patch in the selected Ports source.')
        initial_inputs = [
            ports / 'scripts/prepare-pkgsrc.py', delta,
            pkg / 'Makefile', pkg / 'PLIST', pkg / 'distinfo',
            pkg / 'patches/patch-nss_coreconf_nsinstall_Makefile',
            source_coreconf / 'nsinstall/Makefile', source_coreconf / 'rules.mk',
            source / 'nss/cmd/shlibsign/Makefile',
            source / 'nss/lib/freebl/config.mk',
            source / 'nss/coreconf/arch.mk',
        ]
        input_hashes = {str(path): inventory.sha256_file(path) for path in initial_inputs}
        compiler_version = run('host-compiler-version', [host_cc, '--version'], cwd=work, expect='success')[1].decode('utf-8', 'replace')
        compiler_target = run('host-compiler-target', [host_cc, '-dumpmachine'], cwd=work, expect='success')[1].decode('utf-8', 'replace').strip()
        if 'netbsd' in compiler_target.lower():
            raise RuntimeError('The selected host compiler is a NetBSD target compiler, not a native host compiler.')
        receipt['host_compiler'] = {'path': str(host_cc), 'sha256': inventory.sha256_file(host_cc),
                                   'version': compiler_version.strip(), 'target': compiler_target}
        receipt['bmake'] = {'path': str(bmake), 'sha256': inventory.sha256_file(bmake)}
        receipt['gmake'] = {'path': str(gmake), 'sha256': inventory.sha256_file(gmake)}
        receipt['patch_tool'] = args.patch_tool

        package_copy = work / 'pkgsrc'
        (package_copy / 'devel').mkdir(parents=True)
        shutil.copytree(pkg, package_copy / 'devel/nss', symlinks=True)
        recipe_delta = delta.read_bytes()
        run('check-pkgsrc-delta-format', ['git', 'apply', '--check', delta],
            cwd=package_copy, expect='success')
        run('apply-pkgsrc-delta', [args.patch_tool, '-f', '-N', '-F', '0', '-p1'],
            cwd=package_copy, input_data=recipe_delta, expect='success')
        modified_pkg = package_copy / 'devel/nss'
        recipe = (modified_pkg / 'Makefile').read_text(encoding='utf-8')
        for required in ('DISTNAME=\t\tnss-3.132', 'OS_TARGET=${OPSYS:Q}',
                         'OS_TARGET_RELEASE=${OS_VERSION:Q}', 'OS_TEST=${NSS_CPU_ARCH:Q}',
                         'NATIVE_FLAGS=${NATIVE_CPPFLAGS:Q}\\ ${NATIVE_CFLAGS:Q}',
                         'NATIVE_LDFLAGS=${NATIVE_LDFLAGS:Q}'):
            if required not in recipe:
                raise RuntimeError('The exported NSS recipe is missing: ' + required)
        if (pkg / 'PLIST').read_bytes() != (modified_pkg / 'PLIST').read_bytes():
            raise RuntimeError('The delta unexpectedly changed NSS PLIST.')
        if any('.chk' in line for line in (modified_pkg / 'PLIST').read_text(encoding='utf-8').splitlines()):
            raise RuntimeError('NSS PLIST unexpectedly lists signed-library .chk files.')
        shlib_make = (source / 'nss/cmd/shlibsign/Makefile').read_text(encoding='utf-8')
        if 'ifeq ($(CROSS_COMPILE),1)' not in shlib_make or '# do nothing' not in shlib_make:
            raise RuntimeError('The upstream cross shlibsign skip is not present; signing is outside this fix.')

        patch_dir = modified_pkg / 'patches'
        names = sorted(path.name for path in patch_dir.iterdir() if path.name.startswith('patch-nss_coreconf_'))
        nsinstall_patch = 'patch-nss_coreconf_nsinstall_zz_emberbsd_native_tools'
        rules_patch = 'patch-nss_coreconf_rules_mk_zz_emberbsd_native_program'
        baseline_patch = 'patch-nss_coreconf_nsinstall_Makefile'
        if not (patch_dir / nsinstall_patch).is_file() or not (patch_dir / rules_patch).is_file():
            raise RuntimeError('The exported NSS native-tool patches are incomplete.')
        if names.index(baseline_patch) >= names.index(nsinstall_patch) or names.index(nsinstall_patch) >= names.index(rules_patch):
            raise RuntimeError('The pkgsrc patch filename order is not valid.')
        for name in (nsinstall_patch, rules_patch):
            patch_path = patch_dir / name
            digest = hashlib.sha1(b''.join(line for line in patch_path.read_bytes().splitlines(keepends=True)
                                          if b'$NetBSD' not in line)).hexdigest()
            expected_line = f'SHA1 ({name}) = {digest}'
            if expected_line not in (modified_pkg / 'distinfo').read_text(encoding='utf-8'):
                raise RuntimeError('pkgsrc distinfo SHA1 mismatch for ' + name)
        block_start = recipe.find('.if ' + chr(36) + '{USE_CROSS_COMPILE:U:tl} == yes')
        block_end = recipe.find('\n.endif', block_start)
        if block_start < 0 or block_end < 0:
            raise RuntimeError('Cannot find the production pkgsrc cross stanza.')
        cross_block = recipe[block_start:block_end + len('\n.endif')] + '\n'
        target_metadata = {}
        for arch, cpu in (('amd64', 'x86_64'), ('aarch64eb', 'aarch64')):
            fixture = work / ('bmake-' + arch + '.mk')
            fixture.write_text(f'MACHINE_ARCH={arch}\nOPSYS=NetBSD\nOS_VERSION={args.target_release}\n'
                               'USE_CROSS_COMPILE=yes\n' + f'NATIVE_CC={host_cc}\nNATIVE_CFLAGS=\n' + cross_block,
                               encoding='utf-8')
            expanded = run('recipe-cross-' + arch,
                [bmake, '-f', fixture, '-v', 'MAKE_FLAGS'], cwd=work, expect='success')[1].decode('utf-8').split()
            values = dict(token.split('=', 1) for token in expanded)
            for key, value in {'CROSS_COMPILE': '1', 'OS_TARGET': 'NetBSD',
                               'OS_ARCH': 'NetBSD', 'OS_TARGET_RELEASE': args.target_release, 'OS_TEST': cpu,
                               'CPU_ARCH': cpu}.items():
                if values.get(key) != value:
                    raise RuntimeError(f'Production cross recipe maps {arch} {key} to {values.get(key)!r}, expected {value!r}.')
            target_metadata[arch] = values
        native_fixture = work / 'bmake-native.mk'
        native_fixture.write_text(f'MACHINE_ARCH={args.target_arch}\nOPSYS=Darwin\nOS_VERSION=27.0\n'
                                  'USE_CROSS_COMPILE=no\n' + f'NATIVE_CC={host_cc}\nNATIVE_CFLAGS=\n' + cross_block,
                                  encoding='utf-8')
        native_flags = run('recipe-native', [bmake, '-f', native_fixture, '-v', 'MAKE_FLAGS'],
                           cwd=work, expect='success')[1].decode('utf-8').strip()
        if native_flags:
            raise RuntimeError('The production cross stanza changed native MAKE_FLAGS.')
        receipt['recipe_target_metadata'] = target_metadata
        receipt['recipe_native_make_flags'] = native_flags

        freebl_config_path = source / 'nss/lib/freebl/config.mk'
        freebl_config = freebl_config_path.read_text(encoding='utf-8')
        arch_path = source / 'nss/coreconf/arch.mk'
        arch_lines = arch_path.read_text(encoding='utf-8').splitlines()
        arch_assignments = [line for line in arch_lines if line.startswith('OS_ARCH :=')]
        if len(arch_assignments) != 1 or 'uname -s' not in arch_assignments[0]:
            raise RuntimeError('Cannot identify the upstream host OS_ARCH assignment in coreconf/arch.mk.')
        host_arch_assignment = arch_assignments[0]
        guard_start = freebl_config.find('ifeq ($(OS_ARCH), Darwin)\n')
        guard_end = freebl_config.find('\nendif', guard_start)
        if guard_start < 0 or guard_end < 0:
            raise RuntimeError('Cannot find the upstream Darwin OS_ARCH guard in freebl/config.mk.')
        darwin_guard = freebl_config[guard_start:guard_end + len('\nendif')] + '\n'
        if '-dylib_file @executable_path/libplc4.dylib' not in darwin_guard or '-dylib_file @executable_path/libplds4.dylib' not in darwin_guard:
            raise RuntimeError('The upstream Darwin guard does not contain the expected libfreebl linker flags.')
        arch_values = target_metadata['amd64']
        guard_cases = (
            ('before-cross-netbsd', 'NetBSD', None, True),
            ('after-cross-netbsd', 'NetBSD', arch_values['OS_ARCH'], False),
            ('native-darwin', 'Darwin', None, True),
        )
        guard_results = {}
        for label, os_target, os_arch_override, expect_darwin_flags in guard_cases:
            fixture = work / ('freebl-' + label + '.mk')
            fixture.write_text(
                f'OS_TARGET={os_target}\nDIST=/target/dist\nEXTRA_SHARED_LIBS=\n'
                + host_arch_assignment + '\n'
                + darwin_guard
                + '\n.PHONY: print-flags\nprint-flags:\n'
                  '\t@printf \'%s|%s\\n\' "$(OS_ARCH)" "$(EXTRA_SHARED_LIBS)"\n',
                encoding='utf-8')
            make_argv = [gmake, '--no-print-directory', '-s', '-f', fixture, 'print-flags']
            if os_arch_override is not None:
                make_argv.append('OS_ARCH=' + os_arch_override)
            output = run('freebl-' + label, make_argv, cwd=work,
                         expect='success')[1].decode('utf-8', 'replace').strip()
            output_arch, link_flags = output.split('|', 1)
            has_darwin_flags = '-dylib_file' in link_flags
            if has_darwin_flags != expect_darwin_flags:
                raise RuntimeError(f'{label} produced unexpected Darwin linker flags: {link_flags!r}')
            guard_results[label] = {
                'OS_ARCH': output_arch,
                'OS_TARGET': os_target,
                'OS_ARCH_override_from_recipe': os_arch_override,
                'darwin_dylib_flags': has_darwin_flags,
                'link_flags': link_flags,
            }
        receipt['freebl_darwin_guard'] = {
            'source': str(freebl_config_path),
            'source_sha256': inventory.sha256_file(freebl_config_path),
            'host_arch_source': str(arch_path),
            'host_arch_source_sha256': inventory.sha256_file(arch_path),
            'cases': guard_results,
            'scope': 'Evaluates the exact upstream OS_ARCH guard. This does not build or accept target NSS libraries.',
        }

        state_probe = work / 'pkgsrc-state-probe'
        (state_probe / 'nss').mkdir(parents=True)
        shutil.copytree(source_coreconf, state_probe / 'nss/coreconf', symlinks=True, ignore=ignore_coreconf)
        baseline_patch_data = (modified_pkg / 'patches' / baseline_patch).read_bytes()
        reverse_status, _, _ = run('probe-existing-patch-reverse',
            [args.patch_tool, '--dry-run', '-R', '-f', '-F', '0', '-p0'],
            cwd=state_probe, input_data=baseline_patch_data)
        if reverse_status == 0:
            source_state = 'pkgsrc-patch-already-applied'
        else:
            forward_status, _, _ = run('probe-existing-patch-forward',
                [args.patch_tool, '--dry-run', '-f', '-F', '0', '-p0'],
                cwd=state_probe, input_data=baseline_patch_data)
            if forward_status != 0:
                raise RuntimeError('Source must be either raw NSS 3.132 or patched by the base pkgsrc nsinstall patch.')
            source_state = 'raw-source'
        receipt['source_state'] = source_state

        variants = {}
        for variant in ('before', 'after'):
            tree = work / variant
            tree.mkdir()
            (tree / 'nss').mkdir()
            shutil.copytree(source_coreconf, tree / 'nss/coreconf', symlinks=True, ignore=ignore_coreconf)
            if source_state == 'raw-source':
                run(variant + '-apply-pkgsrc-base-patch',
                    [args.patch_tool, '-f', '-F', '0', '-p0'], cwd=tree,
                    input_data=baseline_patch_data, expect='success')
            if variant == 'after':
                for name in (nsinstall_patch, rules_patch):
                    run('apply-' + name, [args.patch_tool, '-f', '-F', '0', '-p0'],
                        cwd=tree, input_data=(patch_dir / name).read_bytes(), expect='success')
            variants[variant] = tree

        target_only_ldflags = '-Wl,-rpath-link,/target/sysroot/usr/pkg/lib -Wl,-zrelro'
        target_only_shared = '-L/target/sysroot/usr/pkg/lib -Wl,-R/usr/pkg/lib'
        common = [
            f'OS_TARGET=NetBSD', f'OS_TARGET_RELEASE={args.target_release}',
            f'OS_TEST={target_cpu}', f'CPU_ARCH={target_cpu}', 'CROSS_COMPILE=1',
            'BUILD_OPT=1', f'CC={host_cc}', 'CC_IS_GCC=1', 'CC_IS_CLANG=',
            f'NATIVE_CC={host_cc}', 'NATIVE_FLAGS=', 'NATIVE_LDFLAGS=',
            'NATIVE_EXTRA_SHARED_LIBS=', f'LDFLAGS={target_only_ldflags}',
            f'EXTRA_SHARED_LIBS={target_only_shared}', 'OS_LIBS=-lrt',
        ]
        results = {}
        for variant in ('before', 'after'):
            obj = work / 'objects' / variant
            obj.mkdir(parents=True)
            cwd = variants[variant] / 'nss/coreconf/nsinstall'
            argv = [gmake, '--no-print-directory', '-B', '-j1', 'program', *common, f'OBJDIR={obj}']
            expected = 'failure' if variant == 'before' else 'success'
            status, stdout, stderr = run(variant + '-build', argv, cwd=cwd, expect=expected)
            if variant == 'before':
                diagnostic = (stdout + stderr).decode('utf-8', 'replace')
                if '-rpath-link' not in diagnostic or '-zrelro' not in diagnostic:
                    raise RuntimeError('The baseline failed for a different reason than target linker flag leakage.')
                results[variant] = {'status': status, 'failure': 'Darwin ld rejected target -rpath-link/-zrelro flags'}
            else:
                binary = obj / 'nsinstall'
                if not binary.is_file():
                    raise RuntimeError('The native nsinstall executable was not produced.')
                results[variant] = {'status': status, 'binary': str(binary),
                                    'sha256': inventory.sha256_file(binary)}
                file_result = run('host-binary-format', [args.file_tool, '-b', binary], cwd=work, expect='success')[1].decode('utf-8', 'replace').strip()
                if 'Mach-O' not in file_result:
                    raise RuntimeError('The selected native build helper is not a host Mach-O executable: ' + file_result)
                results[variant]['file'] = file_result
                run('host-binary-execution', [binary], cwd=work, expect=2)
                if variant == 'after':
                    copy_root = work / 'functional-copy'
                    source_dir = copy_root / 'source'
                    destination_dir = copy_root / 'destination'
                    source_dir.mkdir(parents=True)
                    destination_dir.mkdir()
                    payload = b'nsinstall binary copy regression\x00\xff\r\n'
                    source_file = source_dir / 'payload.bin'
                    source_file.write_bytes(payload)
                    source_file.chmod(0o600)
                    run('functional-copy',
                        [binary, '-m', '0640', source_file, destination_dir],
                        cwd=work, expect='success')
                    destination_file = destination_dir / source_file.name
                    destination_stat = destination_file.lstat()
                    copied_bytes = destination_file.read_bytes()
                    copied_mode = stat.S_IMODE(destination_stat.st_mode)
                    if not stat.S_ISREG(destination_stat.st_mode) or destination_file.is_symlink():
                        raise RuntimeError('nsinstall output is not a regular, non-symlink file.')
                    if copied_bytes != payload:
                        raise RuntimeError('nsinstall copied bytes do not match the independent binary payload.')
                    if copied_mode != 0o640:
                        raise RuntimeError(f'nsinstall copied mode {copied_mode:o}, expected 640.')
                    if source_file.read_bytes() != payload or stat.S_IMODE(source_file.stat().st_mode) != 0o600:
                        raise RuntimeError('nsinstall changed the source payload or mode.')
                    results[variant]['functional_copy'] = {
                        'argv': [str(binary), '-m', '0640', str(source_file), str(destination_dir)],
                        'source_sha256': inventory.sha256_file(source_file),
                        'destination_sha256': inventory.sha256_file(destination_file),
                        'payload_length': len(payload),
                        'source_mode': format(stat.S_IMODE(source_file.stat().st_mode), '04o'),
                        'destination_mode': format(copied_mode, '04o'),
                        'regular_file': True,
                        'symlink': False,
                    }
        receipt['builds'] = results

        # The rules.mk condition must leave ordinary/native program links on the
        # existing upstream path when NATIVE_CC is absent.
        native_obj = work / 'objects/native-control'
        native_obj.mkdir(parents=True)
        native_argv = [gmake, '--no-print-directory', '-B', '-j1', 'program',
                       f'OS_TARGET=NetBSD', f'OS_TARGET_RELEASE={args.target_release}',
                       f'OS_TEST={target_cpu}', f'CPU_ARCH={target_cpu}', 'CROSS_COMPILE=0',
                       'BUILD_OPT=1', f'CC={host_cc}', 'CC_IS_GCC=1', 'CC_IS_CLANG=',
                       'LDFLAGS=', 'EXTRA_SHARED_LIBS=', 'OS_LIBS=', f'OBJDIR={native_obj}']
        run('native-rule-control', native_argv, cwd=variants['after'] / 'nss/coreconf/nsinstall', expect='success')
        native_binary = native_obj / 'nsinstall'
        if not native_binary.is_file():
            raise RuntimeError('The ordinary program rule did not produce its native-control executable.')
        receipt['native_control'] = {'sha256': inventory.sha256_file(native_binary)}

        final_hashes = {str(path): inventory.sha256_file(path) for path in initial_inputs}
        if final_hashes != input_hashes:
            raise RuntimeError('A selected Ports, NSS source, or pkgsrc input changed during the regression.')
        receipt['input_sha256'] = input_hashes
        receipt['status'] = 'pass'
    except Exception as error:
        receipt['status'] = 'fail'
        receipt['error'] = str(error)
        jsonio.write_json(work / 'receipt.json', receipt, exclusive=False)
        raise
    jsonio.write_json(work / 'receipt.json', receipt, exclusive=False)
    print('PASS: target OS routing, Darwin link guard, native nsinstall copy/link, native-rule control; cross signing remains unverified')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
