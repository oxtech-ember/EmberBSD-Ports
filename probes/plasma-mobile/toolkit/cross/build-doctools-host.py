#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted), native documentation generators.
"""Build pinned native KArchive and KDocTools without target installation."""

import argparse
import os
from pathlib import Path
import platform
import re
import sys
import stat
import tarfile

sys.dont_write_bytecode = True
PORTS = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PORTS / 'pkgsrc/lang/llvm/files'))
import sdk_source

VERSION = '6.31.0'
PROGRAMS = ('meinproc6', 'checkXML6', 'docbookl10nhelper')
ENVIRONMENT = ('PERL5LIB', 'PKG_CONFIG_PATH', 'PKG_CONFIG_LIBDIR', 'SDKROOT',
               'MACOSX_DEPLOYMENT_TARGET', 'CFLAGS', 'CXXFLAGS', 'CPPFLAGS', 'LDFLAGS')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pin(table, archive):
    rows = [line.split('\t') for line in table.read_text(encoding='utf-8').splitlines()]
    rows = [row for row in rows if len(row) > 1 and row[1] == archive]
    require(len(rows) == 1 and len(rows[0]) == 4, 'Missing or duplicate source pin: ' + archive)
    require(re.fullmatch('[0-9a-f]{64}', rows[0][2]) and rows[0][3].startswith('https://'),
            'Invalid source pin: ' + archive)
    return dict(sha256=rows[0][2], url=rows[0][3])


def extract(archive, destination, component):
    # The pinned upstream archives contain directories and regular files only.
    # Reject extra roots and links before extracting any member.
    with tarfile.open(archive, 'r:xz') as source:
        members = source.getmembers()
        root = component + '-' + VERSION
        require(members and all((m.name == root or m.name.startswith(root + '/'))
                               and '..' not in Path(m.name).parts
                               and (m.isfile() or m.isdir()) for m in members),
                'Unexpected source archive member: ' + str(archive))
        source.extractall(destination, members=members, filter='data')


def build(arguments, sdk_root):
    from emberbsd_sdk.errors import ProcessOwnershipError
    from emberbsd_sdk.inventory import sha256_file, snapshot_installed_tree, required_file, INSTALLED_TREE_INVENTORY_API
    from emberbsd_sdk.jsonio import write_json
    from emberbsd_sdk.paths import canonical_new, entry, real_directory, reject_overlap
    from emberbsd_sdk.process import ContextLocks, run_logged, sanitized_environment
    from emberbsd_sdk.provenance import git_source

    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('distfiles', 'host_qt', 'native_prefix', 'ecm_cmake_dir', 'new_work'):
        parser.add_argument(name)
    args = parser.parse_args(arguments)
    require(INSTALLED_TREE_INVENTORY_API == 1, 'SDK installed inventory API 1 is required')
    jobs = int(os.environ.get('JOBS', '2'))
    require(1 <= jobs <= 256, 'JOBS must be in the range 1..256')
    selected = {name: os.environ.get(name, '') for name in ('CMAKE', 'NINJA', 'HOST_CC', 'HOST_CXX')}
    for value in [*vars(args).values(), *selected.values()]:
        require(re.fullmatch(r'/[a-zA-Z0-9_./+-]+', value),
                'Use absolute paths without shell/CMake metacharacters')
    distfiles, qt, native, ecm = [Path(value).resolve(strict=True) for value in
                                 (args.distfiles, args.host_qt, args.native_prefix, args.ecm_cmake_dir)]
    for path in (distfiles, qt, native, ecm):
        require(re.fullmatch(r'/[a-zA-Z0-9_./+-]+', str(path)), 'Unsupported resolved build path')
        real_directory(str(path))
    work = Path(canonical_new(args.new_work))
    require(re.fullmatch(r'/[a-zA-Z0-9_./+-]+', str(work)), 'Unsupported resolved work path')
    real_directory(str(work.parent))
    require(entry(work) is None, 'NEW_WORK must not exist; preserve earlier work')
    for path in (distfiles, qt, native, ecm, PORTS, Path(sdk_root)):
        reject_overlap(str(work), str(path))
    tools = {name: Path(value).resolve(strict=True) for name, value in selected.items()}
    tools['qmake'] = (qt / 'bin/qmake').resolve(strict=True)
    for path in tools.values():
        require(re.fullmatch(r'/[a-zA-Z0-9_./+-]+', str(path)), 'Unsupported resolved tool path')
        require(path.is_file() and os.access(path, os.X_OK), 'Missing native executable: ' + str(path))
        reject_overlap(str(work), str(path))
    table = PORTS / 'probes/plasma-mobile/toolkit/sources.tsv'
    archives = {}
    for component in ('karchive', 'kdoctools'):
        path = distfiles / (component + '-' + VERSION + '.tar.xz')
        record = pin(table, path.name)
        require(sha256_file(path) == record['sha256'], 'Wrong archive SHA256: ' + str(path))
        archives[component] = dict(path=str(path), **record)
    sources = dict(ports=git_source(str(PORTS), kind='ports'), sdk=git_source(sdk_root))
    files = [Path(__file__).resolve(), Path(sdk_source.__file__).resolve(), table]
    files.extend(sorted((Path(sdk_root) / 'src/emberbsd_sdk').glob('*.py')))
    source_hashes = {str(path): sha256_file(path) for path in files}
    provider_paths = {name: str(path) for name, path in tools.items()}
    provider_hashes = {name: sha256_file(path) for name, path in tools.items()}
    environment = sanitized_environment()
    environment.update({key: os.environ[key] for key in ENVIRONMENT if key in os.environ})
    environment.update(TMPDIR=str(work / 'tmp'), TMP=str(work / 'tmp'), TEMP=str(work / 'tmp'),
                       PYTHONDONTWRITEBYTECODE='1')
    with ContextLocks([str(work)], str(work.parent)), ContextLocks(
            sorted({str(qt), str(native), str(ecm)}), str(work.parent), shared=True):
        require(entry(work) is None, 'NEW_WORK appeared before admission')
        work.mkdir()
        for name in ('source', 'tooling/KF6DocTools', 'logs', 'commands', 'tmp'):
            (work / name).mkdir(parents=True)
        write_json(work / 'incomplete.json', dict(status='incomplete'))
        write_json(work / 'inputs.json', dict(schema='ember-doctools-host-inputs-v1', sources=sources,
                   source_sha256=source_hashes, archives=archives, tools=provider_paths,
                   tool_sha256=provider_hashes, python=dict(path=str(Path(sys.executable).resolve()),
                   version=sys.version, sha256=sha256_file(Path(sys.executable).resolve())),
                   platform=platform.platform(), directories=dict(qt=str(qt), native=str(native), ecm=str(ecm)),
                   jobs=jobs, environment=environment,
                   boundary='Native dependency trees are selected, not sealed by this receipt.'))

        def run(argv, name):
            argv = list(map(str, argv))
            write_json(work / 'commands' / (name + '.json'), dict(argv=argv, cwd=str(work)))
            try:
                run_logged(argv, work / 'logs' / (name + '.log'), cwd=str(work), env=environment)
            except ProcessOwnershipError as error:
                write_json(work / sdk_source.PRODUCER_QUARANTINE,
                           dict(step=name, session_id=error.sid, error=str(error)))
                raise
            return work / 'logs' / (name + '.log')

        require(run([tools['qmake'], '-query', 'QT_VERSION'], 'qt-version').read_text(encoding='utf-8').strip() == '6.12.0',
                'Native Qt 6.12.0 is required')
        for name in selected:
            run([tools[name], '--version'], name.lower() + '-version')
        for component, record in archives.items():
            extract(record['path'], work / 'source', component)
        for component, directory in (('karchive', 'archive'), ('kdoctools', 'doctools')):
            configure = [tools['CMAKE'], '-S', work / 'source' / (component + '-' + VERSION),
                         '-B', work / directory, '-G', 'Ninja', '-DCMAKE_MAKE_PROGRAM=' + str(tools['NINJA']),
                         '-DCMAKE_C_COMPILER=' + str(tools['HOST_CC']),
                         '-DCMAKE_CXX_COMPILER=' + str(tools['HOST_CXX']),
                         '-DCMAKE_PREFIX_PATH=' + (str(work / 'prefix') + ';' if component == 'kdoctools' else '')
                         + str(qt) + ';' + str(native), '-DECM_DIR=' + str(ecm),
                         '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_INSTALL_PREFIX=' + str(work / 'prefix'),
                         '-DBUILD_TESTING=OFF']
            if component == 'kdoctools':
                configure += ['-DCMAKE_DISABLE_FIND_PACKAGE_KF6I18n=ON', '-DINSTALL_INTERNAL_TOOLS=ON',
                              '-DLIBXML2_XMLLINT_EXECUTABLE=' + str(native / 'bin/xmllint'),
                              '-DDocBookXML4_DTD_DIR=' + str(native / 'share/xml/docbook/4.5'),
                              '-DDOCBOOKXSL_DIR=' + str(native / 'share/xsl/docbook')]
            run(configure, directory + '-configure')
            run([tools['CMAKE'], '--build', work / directory, '--parallel', str(jobs)], directory + '-build')
            run([tools['CMAKE'], '--install', work / directory], directory + '-install')
        programs = {}
        for name in PROGRAMS:
            path = required_file(str(work / 'prefix'), 'bin/' + name)
            require(os.access(path, os.X_OK), 'Missing native generator: ' + name)
            programs[name] = path
        version = run([programs['meinproc6'], '--version'], 'meinproc-version')
        # Upstream's tool banner says 5.0. The generated header owns the KF version.
        header = work / 'doctools/src/kdoctools_version.h'
        require('#define KDOCTOOLS_VERSION_STRING "' + VERSION + '"' in
                header.read_text(encoding='utf-8').splitlines(), 'Incorrect configured Frameworks version')
        (work / 'version.txt').write_bytes(version.read_bytes())
        require(source_hashes == {path: sha256_file(path) for path in source_hashes}, 'Builder source changed')
        require(provider_paths == {name: str(Path(selected.get(name, qt / 'bin/qmake')).resolve(strict=True))
                                   for name in tools}, 'Native tool path changed')
        require(provider_hashes == {name: sha256_file(path) for name, path in tools.items()}, 'Native tool changed')
        require(all(sha256_file(record['path']) == record['sha256'] for record in archives.values()),
                'Source archive changed')
        require(sources == dict(ports=git_source(str(PORTS), kind='ports'), sdk=git_source(sdk_root)),
                'Source commits changed')
        imports = work / 'tooling/KF6DocTools/KF6DocToolsToolsTargets.cmake'
        imports.write_text('foreach(program meinproc6 checkXML6 docbookl10nhelper)\n'
                           '  if(NOT TARGET KF6::${program})\n'
                           '    add_executable(KF6::${program} IMPORTED)\n'
                           '    set_target_properties(KF6::${program} PROPERTIES IMPORTED_LOCATION "'
                           + str(work / 'prefix/bin') + '/${program}")\n'
                           '  endif()\nendforeach()\n', encoding='utf-8')
        (work / 'outputs.sha256').write_text(''.join(sha256_file(path) + '  ' + path + '\n'
                                                    for path in programs.values()), encoding='utf-8')
        # The marker is the existing consumer admission gate. Publish it last.
        ready = work / '.version-ready'
        with ready.open('xb') as stream:
            stream.write((VERSION + '\n').encode('ascii'))
            stream.flush()
            os.fsync(stream.fileno())
        prefix = snapshot_installed_tree(str(work / 'prefix'))
        prefix['share/ember-doctools-version'] = dict(kind='file',
                   mode=stat.S_IMODE(ready.stat().st_mode), size=ready.stat().st_size, sha256=sha256_file(ready))
        write_json(work / 'outputs.json', dict(schema='ember-doctools-host-outputs-v1', status='built',
                   inputs_sha256=sha256_file(work / 'inputs.json'), prefix=prefix,
                   tooling=snapshot_installed_tree(str(work / 'tooling')),
                   logs={p.name: sha256_file(p) for p in sorted((work / 'logs').iterdir())},
                   commands={p.name: sha256_file(p) for p in sorted((work / 'commands').iterdir())},
                   configured_version_sha256=sha256_file(header),
                   boundary='Host build only; upstream tests, consumer checks and target execution are separate.'))
        (work / 'incomplete.json').unlink()
        try:
            os.link(ready, work / 'prefix/share/ember-doctools-version')
        except OSError:
            write_json(work / 'incomplete.json', dict(status='marker-publication-failed'))
            raise
    print('Built native KDocTools: ' + str(work / 'tooling'))


if __name__ == '__main__':
    sdk_source.install_signal_handlers()
    try:
        require(sys.version_info[:2] == (3, 15), 'Host Python 3.15 is required')
        sdk_root, arguments = sdk_source.load_sdk()
        build(arguments, sdk_root)
    except Exception as error:
        sdk_source.exit_error(error)
