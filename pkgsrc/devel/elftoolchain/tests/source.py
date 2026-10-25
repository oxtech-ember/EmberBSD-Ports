#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted source ownership regression.
"""Check the source receiver. Do not build or qualify a target library."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import sys
import subprocess
import tarfile
import tempfile


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def relative(name):
    parts = PurePosixPath(name).parts
    require(name and not name.startswith('/') and '\\' not in name and
            all(p not in ('', '.', '..') for p in name.split('/')) and
            not any(ord(c) < 32 or ord(c) == 127 for c in name),
            f'unsafe relative path: {name!r}')
    require(parts[0] in ('common', 'libelf'), f'outside the shared subset: {name}')


def facts(data, mode=0o644):
    return dict(size=len(data), mode=mode, sha256=digest(data))


def expected_source(manifest):
    require(manifest['format'] == 'emberbsd-elftoolchain-base-source' and
            manifest['version'] == 1, 'unsupported base source manifest')
    result = dict(manifest['files'])
    for name, override in manifest['packaging_overrides'].items():
        require(override['base_sha256'] == result[name]['sha256'],
                f'packaging override has a different base: {name}')
        result[name] = {k: override[k] for k in ('size', 'mode', 'sha256')}
    for name in result:
        relative(name)
    return result


def check_subset(root, expected):
    found = {}
    for component in ('common', 'libelf'):
        require((root / component).is_dir(), f'missing component: {component}')
        for path in (root / component).rglob('*'):
            require(not path.is_symlink(), f'subset contains a link: {path}')
            if path.is_dir():
                continue
            require(path.is_file(), f'subset contains a special node: {path}')
            found[str(path.relative_to(root))] = facts(path.read_bytes(), path.stat().st_mode & 0o777)
    require(set(found) == set(expected),
            f'subset path mismatch: extra={sorted(set(found) - set(expected))}, '
            f'missing={sorted(set(expected) - set(found))}')
    require(found == expected, 'subset file bytes or modes differ from the base manifest')
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--os-source', type=Path, required=True)
    parser.add_argument('--os-revision', required=True)
    parser.add_argument('--git', type=Path, required=True)
    parser.add_argument('--patch-tool', type=Path, required=True)
    parser.add_argument('--bmake', type=Path, required=True)
    parser.add_argument('--m4', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True,
                        help='new test directory; only logs and result.json remain')
    args = parser.parse_args()
    recipe = Path(__file__).resolve().parents[1]
    for name in ('archive', 'os_source', 'git', 'patch_tool', 'bmake', 'm4', 'work'):
        require(getattr(args, name).is_absolute(), f'--{name.replace("_", "-")} must be absolute')
    require(re.fullmatch('[0-9a-f]{40}', args.os_revision), 'use an exact OS commit')
    require(not os.path.lexists(args.work), 'test work already exists')
    require(args.work.parent.is_dir(), 'test work parent is missing')
    require(not args.work.is_relative_to(recipe) and not recipe.is_relative_to(args.work),
            'test work overlaps the recipe')
    args.work.mkdir()
    logs = args.work / 'logs'
    logs.mkdir()
    commands = []
    checks = []
    env = dict(os.environ, LC_ALL='C', GIT_NO_LAZY_FETCH='1')

    def run(argv, *, cwd=None, data=None, actual_exit=0):
        result = subprocess.run([str(v) for v in argv], cwd=cwd, input=data,
                                capture_output=True, env=env, timeout=30)
        index = len(commands)
        for suffix, value in (('stdout', result.stdout), ('stderr', result.stderr)):
            (logs / f'{index:04d}.{suffix}').write_bytes(value)
        commands.append(dict(argv=[str(v) for v in argv], cwd=str(cwd) if cwd else None,
                             exit=result.returncode, stdout_sha256=digest(result.stdout),
                             stderr_sha256=digest(result.stderr)))
        require(result.returncode == actual_exit,
                f'command {index} exited {result.returncode}, expected {actual_exit}')
        return result.stdout

    def git(*arguments):
        return run([args.git, '--no-optional-locks', '-c', 'protocol.allow=never',
                    '-c', 'tar.umask=0022',
                    '-C', args.os_source, *arguments])

    def refusal(label, action):
        try:
            action()
        except RuntimeError:
            checks.append(label)
        else:
            raise RuntimeError(f'{label}: the invalid control was accepted')

    def recipe_identity():
        return {str(p.relative_to(recipe)): facts(p.read_bytes(), p.stat().st_mode & 0o777)
                for p in sorted(recipe.rglob('*')) if p.is_file()}

    inputs = recipe_identity()
    tools = {name: dict(path=str(getattr(args, name)),
                       sha256=digest(getattr(args, name).read_bytes()))
             for name in ('git', 'patch_tool', 'bmake', 'm4')}
    report = dict(scope='source-receiver-generated-header-and-metadata-only', status='FAIL')
    try:
        manifest_bytes = (recipe / 'files/base-source.json').read_bytes()
        manifest = json.loads(manifest_bytes)
        expected = expected_source(manifest)
        for component, tree in manifest['base']['trees'].items():
            actual = git('rev-parse', args.os_revision + ':' + manifest['base']['prefix'] + '/' + component)
            require(actual.decode().strip() == tree, f'OS {component} tree differs from the public base pin')
        snapshot = git('archive', '--format=tar', args.os_revision,
                       *[manifest['base']['prefix'] + '/' + c for c in ('common', 'libelf')])
        base_files = {}
        with tarfile.open(fileobj=io.BytesIO(snapshot)) as packed:
            for member in packed:
                if member.isdir():
                    continue
                require(member.isfile(), 'OS snapshot contains a link or special file')
                name = member.name.removeprefix(manifest['base']['prefix'] + '/')
                relative(name)
                require(name not in base_files, 'duplicate OS snapshot file')
                base_files[name] = facts(packed.extractfile(member).read(), member.mode & 0o777)
        require(base_files == manifest['files'], 'manifest differs from the independent OS snapshot')
        checks.append('complete-independent-os-snapshot')

        data = args.archive.read_bytes()
        observed = dict(size=len(data), sha256=digest(data),
                        sha512=hashlib.sha512(data).hexdigest(), blake2s=hashlib.blake2s(data).hexdigest())
        require(observed == manifest['upstream']['archive'], 'pristine archive differs from upstream pin')
        distinfo = (recipe / 'distinfo').read_text()
        entries = {}
        for line in distinfo.splitlines():
            if not line or line.startswith('$NetBSD'):
                continue
            match = re.fullmatch(r'(BLAKE2s|SHA512|Size|SHA1) \(([^/()]+)\) = ([0-9a-f]+)( bytes)?', line)
            require(match is not None, 'unknown distinfo entry')
            kind, name, value, suffix = match.groups()
            require((kind == 'Size') == (suffix == ' bytes') and (kind, name) not in entries,
                    'invalid or duplicate distinfo entry')
            entries[kind, name] = value
        archive_name = manifest['upstream']['distname'] + '.tar.bz2'
        for kind, value in (('BLAKE2s', observed['blake2s']), ('SHA512', observed['sha512']),
                            ('Size', str(observed['size']))):
            require(entries[kind, archive_name] == value, f'{kind} differs from recipe distinfo')
        patches = sorted((recipe / 'patches').iterdir())
        require(set(entries) == {('BLAKE2s', archive_name), ('SHA512', archive_name), ('Size', archive_name)} |
                {('SHA1', p.name) for p in patches}, 'distinfo does not cover exactly every patch')
        patch_records = []
        for patch in patches:
            patch_data = patch.read_bytes()
            filtered = b''.join(l for l in patch_data.splitlines(keepends=True) if b'$NetBSD' not in l)
            require(hashlib.sha1(filtered).hexdigest() == entries['SHA1', patch.name],
                    f'patch checksum differs: {patch.name}')
            for header in re.findall(rb'^(?:---|\+\+\+) ([^ \t\n]+)', patch_data, re.M):
                if header == b'/dev/null':
                    continue
                name = header.decode()
                require(not name.startswith('/') and all(p not in ('', '.', '..') for p in name.split('/')),
                        f'unsafe patch header: {name}')
            patch_records.append(dict(name=patch.name, sha256=digest(patch_data)))
        checks.append('pristine-archive-and-complete-patch-checksums')

        with tempfile.TemporaryDirectory(prefix='source-', dir=args.work) as temporary:
            stage = Path(temporary)
            seen = set()
            with tarfile.open(fileobj=io.BytesIO(data), mode='r:bz2') as packed:
                for member in packed:
                    name = member.name.rstrip('/')
                    require(name not in seen, 'duplicate upstream archive path')
                    seen.add(name)
                    parts = name.split('/')
                    require(parts[0] == manifest['upstream']['distname'] and
                            all(p not in ('', '.', '..') for p in parts) and '\\' not in name and
                            not any(ord(c) < 32 or ord(c) == 127 for c in name), 'unsafe upstream archive path')
                    require(member.isdir() or member.isfile(), 'upstream archive contains a link or special file')
                packed.extractall(stage, filter='data')
            source = stage / manifest['upstream']['distname']
            refusal('unpatched-source-control', lambda: check_subset(source, expected))
            m4_baseline = stage / 'm4-baseline/common/sys'
            m4_sources = ('common/sys/elfconstants.m4', 'common/sys/elfdefinitions.m4')
            m4_patch_seen = False
            for patch in patches:
                if patch.name == 'patch-02-symbol-table-indices':
                    require(not m4_patch_seen, 'duplicate symbol-table-index patch')
                    m4_baseline.mkdir(parents=True)
                    for name in m4_sources:
                        (m4_baseline / Path(name).name).write_bytes((source / name).read_bytes())
                    m4_patch_seen = True
                elif m4_patch_seen:
                    headers = re.findall(rb'^(?:---|\+\+\+) ([^ \t\n]+)', patch.read_bytes(), re.M)
                    targets = {header.decode().removesuffix('.orig') for header in headers}
                    require(not targets.intersection(m4_sources),
                            'a later patch changes the symbol-table-index causal fixture')
                backup = stage / 'backups' / patch.name
                backup.mkdir(parents=True)
                for header in re.findall(rb'^(?:---|\+\+\+) ([^ \t\n]+)', patch.read_bytes(), re.M):
                    if header != b'/dev/null':
                        (backup / header.decode()).parent.mkdir(parents=True, exist_ok=True)
                run([args.patch_tool, '-f', '-E', '-p0', '-F0', '-V', 'none', '-B', str(backup) + '/'],
                    cwd=source, data=patch.read_bytes())
            require(not any(p.name.endswith(('.orig', '.rej')) for p in source.rglob('*')),
                    'patch application left backups or rejects')
            final = check_subset(source, expected)
            checks.append('all-patches-and-complete-prepared-subset')
            require(m4_patch_seen, 'symbol-table-index patch is missing')
            def generate_elfdefinitions(sysdir):
                return run([args.m4, '-I' + str(sysdir), '-D', 'SRCDIR=' + str(sysdir),
                            'elfdefinitions.m4'], cwd=sysdir)
            generated_header = generate_elfdefinitions(source / 'common/sys')
            baseline_header = generate_elfdefinitions(m4_baseline)
            stn_undef = re.compile(rb'(?m)^#define[ \t]+STN_UNDEF[ \t]+0(?:[ \t]|$)')
            require(len(stn_undef.findall(generated_header)) == 1,
                    'patched M4 output does not define STN_UNDEF exactly once')
            require(not stn_undef.search(baseline_header),
                    'the no-patch-02 M4 control unexpectedly defines STN_UNDEF')
            checks.append('generated-symbol-table-index-and-causal-control')
            header = source / 'libelf/libelf.h'
            original = header.read_bytes()
            header.write_bytes(original + b'\n/* Deliberate source mismatch. */\n')
            refusal('changed-header-control', lambda: check_subset(source, expected))
            header.write_bytes(original)
            extra = source / 'common/native-elf-format'
            extra.write_bytes(b'deliberate obsolete input\n')
            refusal('unexpected-subset-file-control', lambda: check_subset(source, expected))
            extra.unlink()
            check_subset(source, expected)

            pkgsrc = stage / 'fixture/pkgsrc'
            target = pkgsrc / 'devel/elftoolchain'
            target.mkdir(parents=True)
            (pkgsrc / 'mk').mkdir()
            for name in ('bsd.prefs.mk', 'bsd.pkg.mk'):
                (pkgsrc / 'mk' / name).write_text('# Metadata fixture. No build commands.\n')
            production_makefile = (recipe / 'Makefile').read_text()
            (target / 'Makefile').write_text(production_makefile)
            roots = {name: stage / name for name in ('host', 'target')}
            for root in roots.values():
                (root / 'usr/share/emberbsd/ports').mkdir(parents=True)
            marker = roots['target'] / 'usr/share/emberbsd/ports/elftoolchain.distinfo'
            host_marker = roots['host'] / 'usr/share/emberbsd/ports/elftoolchain.distinfo'
            host_marker.write_text('host identity must not qualify a cross target\n')
            export_marker = pkgsrc / 'EMBERBSD-PKGSRC-REVISION'
            cases = [
                ('plain-native', 'NetBSD', 'no', 'no', False, False, False),
                ('profile-native', 'NetBSD', 'yes', 'no', False, False, True),
                ('export-native', 'NetBSD', 'no', 'no', True, False, True),
                ('plain-cross', 'NetBSD', 'no', 'yes', False, False, False),
                ('profile-cross', 'NetBSD', 'yes', 'yes', False, False, True),
                ('export-cross', 'NetBSD', 'no', 'yes', True, False, True),
                ('target-marker-cross', 'NetBSD', 'no', 'yes', False, True, True),
                ('host-marker-only-cross', 'NetBSD', 'no', 'yes', False, False, False),
                ('other-bsd', 'FreeBSD', 'no', 'no', False, False, False),
                ('other-platform-guard', 'Darwin', 'yes', 'no', False, False, False),
            ]
            for label, opsys, profile, cross, exported, marked, blocked in cases:
                for path, present in ((marker, marked), (export_marker, exported)):
                    if present:
                        path.write_text('metadata fixture\n')
                    elif path.exists():
                        path.unlink()
                result = run([args.bmake, '-r', '-f', 'Makefile', '-V', 'PKG_FAIL_REASON',
                              'OPSYS=' + opsys, 'EMBERBSD_PORTS=' + profile,
                              'USE_CROSS_COMPILE=' + cross, 'TOOLS_CROSS_DESTDIR=' + str(roots['target']),
                              '_TEST_HOST_ROOT=' + str(roots['host'])], cwd=target).decode()
                require(('EmberBSD base provides libelf.' in result) == blocked,
                        f'provider guard differs: {label}')
                checks.append('provider-' + label)
            mutant = production_makefile.replace('${TOOLS_CROSS_DESTDIR}/usr/share/emberbsd/ports/',
                                                 '${_TEST_HOST_ROOT}/usr/share/emberbsd/ports/')
            require(mutant != production_makefile, 'provider marker must select the target root')
            (target / 'Makefile').write_text(mutant)
            result = run([args.bmake, '-r', '-f', 'Makefile', '-V', 'PKG_FAIL_REASON',
                          'OPSYS=NetBSD', 'EMBERBSD_PORTS=no', 'USE_CROSS_COMPILE=yes',
                          'TOOLS_CROSS_DESTDIR=' + str(roots['target']),
                          '_TEST_HOST_ROOT=' + str(roots['host'])], cwd=target).decode()
            require('EmberBSD base provides libelf.' in result, 'host-root causal mutant was not detected')
            checks.append('wrong-host-root-control')
            plist = (recipe / 'PLIST').read_text().splitlines()
            require(all(p in plist for p in ('include/sys/elfdefinitions.h', 'man/man3/elf_getversion.3',
                                             'lib/libelf.so.2', 'lib/libelf.so.2.0')) and
                    not any(p.startswith('lib/libelf.so.1') for p in plist), 'portable package ABI/header PLIST differs')
            checks.append('portable-package-abi-and-header-metadata')
            (target / 'Makefile').write_text(production_makefile)
            floor = run([args.bmake, '-r', '-f', 'Makefile', '-V', 'GCC_REQD',
                         'OPSYS=FreeBSD', 'TOOLS_CROSS_DESTDIR=' + str(roots['target'])], cwd=target).decode()
            require('16.2' in floor.split() and 'rm:-Werror' not in production_makefile,
                    'canonical compiler floor or diagnostics differ')
            checks.append('gcc16-floor-and-retained-diagnostics')

            # Execute only the production data-install recipe in a make fixture.
            # The object directory contains header data, not compiled objects.
            fixture_source = stage / 'install-source'
            (fixture_source / 'common/sys').mkdir(parents=True)
            wrapper = (source / 'common/elfdefinitions.h').read_bytes()
            (fixture_source / 'common/elfdefinitions.h').write_bytes(wrapper)
            object_dir = stage / 'header-objects'
            object_dir.mkdir()
            generated = b'/* Independent generated-header fixture. */\n'
            (object_dir / 'elfdefinitions.h').write_bytes(generated)
            (fixture_source / 'common/sys/Makefile').write_text(
                '.if ${INCSDIR:U} != "/usr/pkg/include" || '
                '${CWARNFLAGS:U} != "-Wfirst -Wsecond" || ${TEST_ENV:U} != "from-recipe"\n'
                '.error The actual make query lost MAKE_FLAGS or MAKE_ENV\n'
                '.endif\n')
            env_helper = stage / 'exec-env.py'
            env_helper.write_text('import os,sys\n'
                                 'args=sys.argv[1:]\n'
                                 'while args and "=" in args[0] and not args[0].startswith("/"):\n'
                                 ' key,value=args.pop(0).split("=",1); os.environ[key]=value\n'
                                 'os.execv(args[0],args)\n')
            copy_helper = stage / 'copy-data.py'
            copy_helper.write_text('import shutil,sys\n'
                                  'shutil.copyfile(sys.argv[1],sys.argv[2])\n')
            destination = stage / 'install'
            (destination / 'usr/pkg/include/sys').mkdir(parents=True)
            install_arguments = [args.bmake, '-r', '-f', 'Makefile', 'post-install',
                'OPSYS=FreeBSD', 'EMBERBSD_PORTS=no',
                'TOOLS_CROSS_DESTDIR=' + str(roots['target']),
                'WRKSRC=' + str(fixture_source), 'DESTDIR=' + str(destination), 'PREFIX=/usr/pkg',
                'RUN=', 'SETENV=' + shlex.join([sys.executable, str(env_helper)]),
                'MAKE_ENV=' + shlex.join(['TEST_ENV=from-recipe', 'MAKEOBJDIR=' + str(object_dir)]),
                'MAKE_PROGRAM=' + str(args.bmake),
                'MAKE_FLAGS=' + shlex.join(['INCSDIR=/usr/pkg/include', 'CWARNFLAGS=-Wfirst -Wsecond']),
                'INSTALL_DATA=' + shlex.join([sys.executable, str(copy_helper)])]
            run(install_arguments, cwd=target)
            require((destination / 'usr/pkg/include/sys/elfdefinitions.h').read_bytes() == generated and
                    (destination / 'usr/pkg/include/elfdefinitions.h').read_bytes() == wrapper,
                    'the production install recipe mixed the wrapper and generated sys header')
            checks.append('production-header-install-with-bsd-make-query')
            failed_query = stage / 'failed-query.py'
            failed_query.write_text('import sys\nprint(' + repr(str(object_dir)) + ')\nsys.exit(7)\n')
            refused_destination = stage / 'refused-install'
            (refused_destination / 'usr/pkg/include/sys').mkdir(parents=True)
            failed_arguments = [
                ('DESTDIR=' + str(refused_destination)) if str(a).startswith('DESTDIR=') else
                ('MAKE_PROGRAM=' + shlex.join([sys.executable, str(failed_query)]))
                if str(a).startswith('MAKE_PROGRAM=') else a for a in install_arguments]
            run(failed_arguments, cwd=target, actual_exit=1)
            require(not list(refused_destination.rglob('elfdefinitions.h')),
                    'a failed object query still copied headers')
            checks.append('failed-object-query-control')
        require(recipe_identity() == inputs, 'recipe input changed during the check')
        for name, tool in tools.items():
            require(digest(getattr(args, name).read_bytes()) == tool['sha256'],
                    f'tool changed during the check: {name}')
        report = dict(scope='source-receiver-generated-header-and-metadata-only', status='PASS',
                      recipe_inputs=inputs, tool_drivers=tools,
                      manifest_sha256=digest(manifest_bytes), upstream_archive=observed,
                      os_revision=args.os_revision, base=manifest['base'],
                      patches=patch_records, subset_files=len(final),
                      exact_base_files=len(final) - len(manifest['packaging_overrides']),
                      exact_code_header_m4_files=sum(p.endswith(('.c', '.h', '.m4')) for p in final),
                      packaging_overrides=manifest['packaging_overrides'], checks=checks,
                      commands=commands,
                      boundary='M4 only generates the ELF definitions header. No compiler, configure, '
                               'real package build/install, target ELF execution, '
                               'ABI runtime acceptance or production SDK source receipt. '
                               'The post-install execution copies only data in its isolated test fixture.')
    except Exception as error:
        report.update(error=str(error), checks=checks, commands=commands)
    (args.work / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('status', 'scope')} |
                     {'checks': len(checks), 'result': str(args.work / 'result.json')}))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
