#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); Fortran option and capability refusal controls.
"""Exercise source guards. This check does not build or qualify a compiler."""
import argparse
from pathlib import Path
import os
import sys

sys.dont_write_bytecode = True
PROFILE = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(PROFILE / 'runtime/recipe/files'), str(PROFILE), str(PROFILE / 'cross')]
import sdk_source


def main(argv):
    sdk_source.install_signal_handlers()
    args = sdk_source.arguments(argv)
    from emberbsd_sdk import inventory, jsonio
    from emberbsd_sdk.errors import CommandError, SDKError
    from host import new_path, require
    import fortran_support as policy
    from target_options import parse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('new_output')
    parser.add_argument('--native-gfortran', help='Optional real host GCC16 Fortran driver for wrong-target control')
    parser.add_argument('--existing-cxx-prefix', help='Optional C/C++-only target prefix for missing-frontend control')
    options = parser.parse_args(args)
    work = new_path(options.new_output)
    work.mkdir()
    results = []

    def passed(name, facts=None):
        results.append({'case': name, 'status': 'PASS', **({'facts': facts} if facts else {})})

    def refused(name, invoke):
        try:
            invoke()
        except (SDKError, OSError) as error:
            passed(name, {'refusal': str(error)})
        else:
            raise SDKError('Required refusal did not occur: ' + name)

    allowed = {'kernel_allowed': True, 'bootstrap_allowed': True, 'fortran_allowed': True}
    for name, args, expected in (
        ('default-unchanged', [], ('aarch64', 'applications', [])),
        ('amd64-unchanged', ['--target', 'amd64'], ('amd64', 'applications', [])),
        ('kernel-unchanged', ['--kernel', '--target', 'amd64'], ('amd64', 'kernel', [])),
        ('kernel-bootstrap-unchanged', ['--kernel', '--bootstrap-libgcc'], ('aarch64', 'kernel-bootstrap', [])),
        ('fortran-aarch64', ['--with-fortran'], ('aarch64', 'applications-fortran', [])),
        ('fortran-amd64', ['--target', 'amd64', '--with-fortran', '/input'], ('amd64', 'applications-fortran', ['/input'])),
        ('fortran-before-target', ['--with-fortran', '--target', 'amd64'], ('amd64', 'applications-fortran', []))):
        require(parse(args, **allowed) == expected, 'Wrong option result: ' + name)
        passed(name)
    for name, args in (
        ('duplicate-fortran', ['--with-fortran', '--with-fortran']),
        ('kernel-before-fortran', ['--kernel', '--with-fortran']),
        ('fortran-before-kernel', ['--with-fortran', '--kernel']),
        ('bootstrap-before-fortran', ['--bootstrap-libgcc', '--with-fortran']),
        ('fortran-before-bootstrap', ['--with-fortran', '--bootstrap-libgcc']),
        ('unknown-option', ['--languages=c,c++,fortran']),
        ('duplicate-target', ['--target', 'amd64', '--target', 'amd64']),
        ('empty-target', ['--target', '']),
        ('missing-target', ['--target']),
        ('unsupported-target', ['--target', 'arm-none-eabi'])):
        refused(name, lambda args=args: parse(args, **allowed))
    refused('other-entry-points-refuse-fortran', lambda: parse(['--with-fortran']))
    for target, triplet in (('amd64', 'x86_64--netbsd'), ('aarch64', 'aarch64--netbsd')):
        policy.reports(target, '16.2.0\n', triplet + '\n', 'Target: ' + triplet + '\nThread model: posix\n')
        passed('reports-' + target)
    for name, target, version, triplet, threads in (
        ('legacy-version', 'amd64', '15.2.0', 'x86_64--netbsd', 'Thread model: posix'),
        ('different-release', 'amd64', '16.2.1', 'x86_64--netbsd', 'Thread model: posix'),
        ('host-triplet', 'amd64', '16.2.0', 'aarch64-apple-darwin27', 'Thread model: posix'),
        ('other-target', 'amd64', '16.2.0', 'aarch64--netbsd', 'Thread model: posix'),
        ('wrong-threads', 'amd64', '16.2.0', 'x86_64--netbsd', 'Target: x86_64--netbsd\nThread model: single'),
        ('duplicate-threads', 'amd64', '16.2.0', 'x86_64--netbsd', 'Target: x86_64--netbsd\nThread model: posix\nThread model: single'),
        ('contradictory-verbose-target', 'amd64', '16.2.0', 'x86_64--netbsd', 'Target: aarch64--netbsd\nThread model: posix'),
        ('duplicate-verbose-target', 'amd64', '16.2.0', 'x86_64--netbsd', 'Target: x86_64--netbsd\nTarget: x86_64--netbsd\nThread model: posix'),
        ('missing-threads', 'amd64', '16.2.0', 'x86_64--netbsd', 'Target: x86_64--netbsd'),
        ('invalid-policy-target', 'amd65', '16.2.0', 'x86_64--netbsd', 'Thread model: posix')):
        refused(name, lambda target=target, version=version, triplet=triplet, threads=threads:
                policy.reports(target, version, triplet, threads))
    policy.symbol_report('0000000000000000 0000000000000005 T emberbsd_fortran_add_\n', 'emberbsd_fortran_add_')
    passed('nonempty-probe-symbol')
    for name, text in (
        ('empty-probe-object', ''),
        ('zero-sized-probe-routine', '0000 0000 T emberbsd_fortran_add_\n'),
        ('wrong-probe-routine', '0000 0005 T another_routine\n'),
        ('undefined-probe-routine', ' U emberbsd_fortran_add_\n'),
        ('duplicate-probe-routine', '0000 0005 T emberbsd_fortran_add_\n0005 0005 T emberbsd_fortran_add_\n')):
        refused(name, lambda text=text: policy.symbol_report(text, 'emberbsd_fortran_add_'))
    prefix = work / 'prefix'
    prefix.mkdir()
    backend = prefix / 'f951'
    backend.write_text('path-only fixture; this file is never executed\n')
    backend.chmod(0o755)
    require(policy.executable(backend, prefix) == backend, 'In-prefix path rejected')
    passed('in-prefix-executable-path')
    outside = work / 'outside'
    outside.write_text('outside the prefix; never executed\n')
    outside.chmod(0o755)
    escape = prefix / 'escape'
    escape.symlink_to('../outside')
    nonexec = prefix / 'nonexec'
    nonexec.write_text('not executable\n')
    nonexec.chmod(0o644)
    refused('escaping-executable', lambda: policy.executable(escape, prefix))
    refused('relative-executable', lambda: policy.executable(Path('f951'), prefix))
    refused('missing-executable', lambda: policy.executable(prefix / 'absent', prefix))
    refused('directory-executable', lambda: policy.executable(prefix, prefix))
    refused('nonexecutable-frontend', lambda: policy.executable(nonexec, prefix))
    before = inventory.snapshot_tree(work)
    refused('repeat-output', lambda: policy.qualify(prefix, 'amd64', prefix, {}, work, work, quarantine=work))
    refused('overlapping-output', lambda: policy.qualify(prefix, 'amd64', prefix / 'new', {}, work, work, quarantine=work))
    require(inventory.snapshot_tree(work) == before, 'An early refusal mutated existing fixtures')
    passed('early-refusals-preserve-bytes-modes-links')
    out, err = policy.query([sys.executable, '-B', '-c', 'import sys; print("stdout"); print("stderr",file=sys.stderr)'])
    require((out, err) == ('stdout\n', 'stderr\n'), 'Query stream mismatch')
    passed('query-preserves-streams')
    try:
        policy.query([sys.executable, '-B', '-c', 'import sys; print("out"); print("err",file=sys.stderr); sys.exit(7)'])
    except CommandError as error:
        require(error.returncode == 7 and error.stdout == b'out\n' and error.stderr == b'err\n', 'Failed query status or streams changed')
        passed('query-preserves-failure')
    else:
        raise SDKError('Failed query was accepted')
    refused('query-refuses-stdout-truncation', lambda: policy.query([sys.executable, '-B', '-c', 'import sys; sys.stdout.write("x"*(1024*1024+1))']))
    refused('query-refuses-stderr-truncation', lambda: policy.query([sys.executable, '-B', '-c', 'import sys; sys.stderr.write("x"*(1024*1024+1))']))
    if options.native_gfortran:
        native = Path(options.native_gfortran).resolve(strict=True)
        require(native.is_absolute(), 'Native control driver must be absolute')
        image = policy.host_image(native)
        version, _ = policy.query([native, '-dumpfullversion'])
        triplet, _ = policy.query([native, '-dumpmachine'])
        out, err = policy.query([native, '-v'])
        require(version.strip() == '16.2.0', 'Native control must use GCC16.2.0')
        require(triplet.strip() not in ('x86_64--netbsd', 'aarch64--netbsd'), 'Control is not a native compiler')
        refused('real-native-fortran-refused-as-target', lambda: policy.reports('amd64', version, triplet, out + err))
        passed('real-native-image', {'path': str(native.resolve(strict=True)), 'sha256': inventory.sha256_file(native.resolve(strict=True)), 'image': image, 'triplet': triplet.strip()})
    if options.existing_cxx_prefix:
        before = inventory.snapshot_tree(work)
        refused('real-cxx-prefix-missing-fortran', lambda: policy.inspect(options.existing_cxx_prefix, 'amd64'))
        require(inventory.snapshot_tree(work) == before, 'Missing compiler control changed fixtures')
    # Execute the real build preamble with a typed failure at its first
    # producer boundary. No configure, compiler, archive extractor or make runs.
    from unittest import mock
    from emberbsd_sdk.errors import ProcessOwnershipError
    import pipeline
    fixture = work / 'lifecycle'
    fixture.mkdir()
    seed, tools, math, prepared = [fixture / name for name in ('seed', 'tools', 'math', 'prepared')]
    for directory in (seed / 'usr/include', seed / 'usr/pkg/gcc16/include/c++/x86_64--netbsd',
                      seed / 'usr/pkg/gcc16/lib/gcc/x86_64--netbsd/16.2.0', tools / 'bin', math, prepared):
        directory.mkdir(parents=True, exist_ok=True)
    (seed / 'usr/include/stddef.h').write_text('never compiled\n')
    (seed / 'usr/pkg/gcc16/lib/gcc/x86_64--netbsd/16.2.0/crtbegin.o').write_text('not an object; never linked\n')
    (tools / 'bin/nbgmake').write_text('never executed\n')
    (tools / 'bin/nbgmake').chmod(0o755)
    archive = fixture / 'source.tar.xz'
    archive.write_text('not an archive; never extracted\n')
    for kind in ('old-guard-removed', 'mode-quarantine', 'existing-marker', 'ordinary-failure',
                 'replaced-work', 'early-failure', 'default-policy-unchanged'):
        destination = fixture / kind
        marker = destination / policy.QUARANTINE
        original_marker = b'preserve this existing marker\n'
        values = list(map(str, (prepared, archive, seed, tools, math, destination)))

        def injected(*args, **kwargs):
            if kind == 'existing-marker':
                marker.write_bytes(original_marker)
            if kind == 'replaced-work':
                destination.rename(fixture / (kind + '-original'))
                destination.mkdir()
                (destination / 'sentinel').write_text('replacement directory stays unchanged\n')
            if kind == 'ordinary-failure':
                raise CommandError(9, ['injected-bounded-producer'])
            raise ProcessOwnershipError(424242, 'injected before Fortran qualification')

        source_options = ({'side_effect': ProcessOwnershipError(424242, 'injected before work creation')}
                          if kind == 'early-failure' else {'return_value': {'source': 'controlled fixture'}})
        with mock.patch.object(pipeline, 'check_math', return_value=math), \
             mock.patch.object(pipeline, 'audit_source'), \
             mock.patch.object(pipeline, 'host_compilers', return_value=('fixture-cc', 'fixture-cxx')), \
             mock.patch.object(policy, 'source_state', **source_options), \
             mock.patch.object(policy, 'qualify', side_effect=AssertionError('qualification must not run')), \
             mock.patch.object(pipeline, 'logged', side_effect=AssertionError('no producer may run')), \
             mock.patch.object(pipeline, 'binutils_main', side_effect=injected):
            try:
                if kind == 'old-guard-removed':
                    pipeline._build_compiler('amd64', 'applications-fortran', values, owned={})
                else:
                    flags = ['--target', 'amd64'] + ([] if kind == 'default-policy-unchanged' else ['--with-fortran'])
                    pipeline.build_main(flags + values)
            except ProcessOwnershipError as error:
                require(kind != 'ordinary-failure' and error.sid == 424242, 'Typed ownership failure changed')
                if kind == 'replaced-work':
                    require('cannot persist the Fortran quarantine' in str(error), 'Changed directory identity was accepted')
            except CommandError as error:
                require(kind == 'ordinary-failure' and error.returncode == 9, 'Ordinary failure changed')
            else:
                raise SDKError('Injected build failure was accepted')
        if kind == 'mode-quarantine':
            marked = jsonio.read_json(marker)
            info = destination.stat()
            require(marked['state'] == 'producer-ownership-unproven' and marked['session'] == 424242
                    and (marked['device'], marked['inode']) == (info.st_dev, info.st_ino), 'Missing owned generation quarantine')
        elif kind == 'existing-marker':
            require(marker.read_bytes() == original_marker, 'Existing quarantine was replaced')
        else:
            require(not marker.exists(), 'Quarantine crossed its declared lifecycle boundary')
        if kind == 'early-failure':
            require(not destination.exists(), 'Early ownership failure created work')
        if kind == 'replaced-work':
            require(sorted(p.name for p in destination.iterdir()) == ['sentinel'], 'Replacement directory was modified')
        passed('lifecycle-' + kind)
    jsonio.write_json(work / 'result.json', {'status': 'PASS', 'checks': len(results), 'cases': results,
                      'scope': 'Source guard controls only; no compiler build, target object, runtime or installation.'}, exclusive=True)
    print('PASS: ' + str(len(results)) + ' Fortran source guard controls')


if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(getattr(error, 'returncode', None) or 2)
