#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted), Python PAX extraction regression.
"""Make finite archive fixtures, or run them with one explicit selected tar.

Run actual tools through the SDK owned-process interface. Fixtures use synthetic
payloads and the eight full Python 3.15.2 paths affected by legacy extraction.
No compiler or interpreter from the package under test is executed.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import tarfile

PYTHON_PATHS = (
    'Python-3.15.2/Lib/test/test_tomllib/data/invalid/multiline-basic-str/unclosed-ends-in-whitespace-escape.toml',
    'Python-3.15.2/Modules/_xxtestfuzz/fuzz_elementtree_parsewhole_corpus/out_inNsContent_c14nPrefixQnameXpathElem.xml',
    'Python-3.15.2/Modules/_xxtestfuzz/fuzz_elementtree_parsewhole_corpus/out_inNsContent_c14nQnameElem.xml',
    'Python-3.15.2/Modules/_xxtestfuzz/fuzz_elementtree_parsewhole_corpus/out_inNsContent_c14nQnameXpathElem.xml',
    'Python-3.15.2/Modules/_xxtestfuzz/fuzz_elementtree_parsewhole_corpus/out_inNsPushdown_c14nDefault.xml',
    'Python-3.15.2/Modules/_xxtestfuzz/fuzz_elementtree_parsewhole_corpus/out_inNsSuperfluous_c14nDefault.xml',
    'Python-3.15.2/Modules/_xxtestfuzz/fuzz_elementtree_parsewhole_corpus/out_inNsSuperfluous_c14nPrefix.xml',
    'Python-3.15.2/Platforms/Apple/testbed/iOSTestbed.xcodeproj/xcshareddata/xcschemes/iOSTestbed.xcscheme',
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def record(key, value):
    tail = b' ' + key.encode() + b'=' + value.encode() + b'\n'
    length = len(tail) + 1
    while len(str(length)) + len(tail) != length:
        length = len(str(length)) + len(tail)
    return str(length).encode() + tail


def member(name, data=b'', *, kind=tarfile.REGTYPE, link='', size=None, mode=0o644):
    item = tarfile.TarInfo(name)
    item.type, item.linkname = kind, link
    item.mode, item.mtime, item.uid, item.gid = mode, 946684800, 0, 0
    item.size = len(data) if size is None else size
    return item.tobuf(format=tarfile.USTAR_FORMAT) + data + b'\0' * (-len(data) % 512)


def extension(values, *, kind=tarfile.XHDTYPE):
    return member('PaxHeader', b''.join(record(key, value) for key, value in values), kind=kind)


def fixtures(work):
    require(len(PYTHON_PATHS) == 8 and len(set(PYTHON_PATHS)) == 8, 'Require all eight distinct Python names')
    cases = []

    def put(name, data, expected=None, *, reject=False):
        path = work / (name + '.tar')
        path.write_bytes(data + b'\0' * 1024)
        cases.append(dict(name=name, archive=str(path), archive_sha256=digest(path.read_bytes()),
                          expected=expected, reject=reject))

    data, expected = b'', {}
    for number, name in enumerate(PYTHON_PATHS):
        payload = ('python-name-fixture-' + str(number) + '\n').encode()
        require(len(name.encode()) > 100, 'Expected a PAX path longer than the tar name field')
        data += extension([('path', name)]) + member(name[:100], payload)
        expected[name] = dict(kind='file', sha256=digest(payload), mode=0o644, mtime=946684800)
    put('python-eight-paths', data, expected)

    long_name = 'long/' + 'n' * 130
    long_link = 'links/' + 'l' * 130
    data = extension([('path', long_name), ('size', '3'), ('mtime', '946684801.25'),
                      ('VENDOR.ignored', 'value')]) + member('short-header', b'abc', size=0)
    data += extension([('path', long_link), ('linkpath', '../' + long_name)])
    data += member('short-link', kind=tarfile.SYMTYPE, link='wrong-link')
    data += extension([('linkpath', long_name)]) + member('hardlink', kind=tarfile.LNKTYPE, link='wrong-link')
    data += member('after', b'after\n', mode=0o600)
    put('pax-local-semantics', data, {
        long_name: dict(kind='file', sha256=digest(b'abc'), mode=0o644, mtime=946684801.25),
        long_link: dict(kind='symlink', link='../' + long_name),
        'hardlink': dict(kind='hardlink', link=long_name),
        'after': dict(kind='file', sha256=digest(b'after\n'), mode=0o600, mtime=946684800),
    })
    put('ordinary-ustar', member('ordinary', b'ordinary\n'), {
        'ordinary': dict(kind='file', sha256=digest(b'ordinary\n'), mode=0o644, mtime=946684800)})
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w', format=tarfile.GNU_FORMAT) as archive:
        item = tarfile.TarInfo(long_name); item.size = 4; item.mode = 0o644; item.mtime = 946684800
        archive.addfile(item, io.BytesIO(b'gnu\n'))
        item = tarfile.TarInfo('gnu-link'); item.type = tarfile.SYMTYPE; item.linkname = long_name
        archive.addfile(item)
    put('gnu-long-names', buffer.getvalue(), {
        long_name: dict(kind='file', sha256=digest(b'gnu\n'), mode=0o644, mtime=946684800),
        'gnu-link': dict(kind='symlink', link=long_name)})
    put('global-unknown', extension([('VENDOR.ignored', 'value')], kind=tarfile.XGLTYPE)
        + member('after', b'after\n'), {
            'after': dict(kind='file', sha256=digest(b'after\n'), mode=0o644, mtime=946684800)})
    for key, value in [('path', 'global-name'), ('size', '1')]:
        put('global-unsupported-' + key,
            extension([(key, value)], kind=tarfile.XGLTYPE) + member('fallback', b'x'), reject=True)
    invalid = {
        'length-zero': b'0 path=x\n', 'length-short': b'4 path=x\n',
        'length-negative': b'-1 path=x\n', 'length-nondigit': b'x path=x\n',
        'length-overflow': b'999999999999999999999999 path=x\n',
        'length-past-body': b'1000 path=x\n',
        'missing-newline': record('path', 'x')[:-1] + b'!',
        'empty-extension': b'',
    }
    for name, body in invalid.items():
        put(name, member('PaxHeader', body, kind=tarfile.XHDTYPE) + member('fallback', b'x'), reject=True)
    # Independently read valid fixtures with the standard library. This accepts
    # fixture encoding, not the selected native provider or package extraction.
    for case in cases:
        if case['reject']:
            continue
        with tarfile.open(case['archive']) as archive:
            require(set(archive.getnames()) == set(case['expected']), 'Fixture member roster differs')
            for item in archive:
                expected = case['expected'][item.name]
                if expected['kind'] == 'file':
                    require(item.isfile() and digest(archive.extractfile(item).read()) == expected['sha256'],
                            'Fixture payload differs')
                    require(item.mode == expected['mode'] and item.mtime == expected['mtime'],
                            'Fixture mode or timestamp differs')
                else:
                    require(item.linkname == expected['link'] and
                            (item.issym() if expected['kind'] == 'symlink' else item.islnk()),
                            'Fixture link differs')
            if case['name'] == 'python-eight-paths':
                require(all(m.pax_headers.get('path') == m.name for m in archive), 'Missing real PAX path records')
    return cases


def check_tree(root, expected):
    actual = {str(path.relative_to(root)) for path in root.rglob('*')
              if path.is_symlink() or not path.is_dir()}
    require(actual == set(expected), 'Extracted file roster differs')
    for name, value in expected.items():
        path = root / name
        info = path.lstat()
        if value['kind'] == 'symlink':
            require(stat.S_ISLNK(info.st_mode) and os.readlink(path) == value['link'], 'Link target differs')
        elif value['kind'] == 'hardlink':
            target = (root / value['link']).stat()
            require(stat.S_ISREG(info.st_mode) and (info.st_dev, info.st_ino) ==
                    (target.st_dev, target.st_ino), 'Hardlink identity differs')
        else:
            require(stat.S_ISREG(info.st_mode) and digest(path.read_bytes()) == value['sha256'], 'Payload differs')
            require(stat.S_IMODE(info.st_mode) == value['mode'], 'Mode differs')
            require(abs(info.st_mtime - value['mtime']) < 0.001, 'Timestamp differs')


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--new-work', type=Path, required=True)
    cli.add_argument('--tar', type=Path)
    cli.add_argument('--env-json', type=Path)
    cli.add_argument('--baseline-tar', type=Path)
    args = cli.parse_args()
    work = args.new_work
    require(work.is_absolute() and work.resolve() == work and not os.path.lexists(work), 'Use new absolute work')
    require((args.tar is None) == (args.env_json is None), 'Pair explicit tar and complete environment JSON')
    require(args.baseline_tar is None or args.tar is not None, 'Baseline needs selected tar comparison')
    work.mkdir(mode=0o700)
    cases = fixtures(work)
    (work / 'fixtures.json').write_text(json.dumps(cases, indent=2) + '\n')
    if args.tar is None:
        print(json.dumps(dict(status='PASS', scope='Fixture encoding only', fixtures=len(cases), actual_tar=None)))
        return
    environment_bytes = args.env_json.read_bytes()
    environment = json.loads(environment_bytes)
    require(isinstance(environment, dict) and all(isinstance(k, str) and isinstance(v, str)
            for k, v in environment.items()), 'Supply a complete string environment')
    require(environment.get('LC_ALL') == 'C' and 'PATH' in environment, 'Supply explicit PATH and LC_ALL=C')
    tool_hashes = {}
    for tool in (args.tar, args.baseline_tar):
        if tool is not None:
            require(tool.is_absolute() and tool.is_file() and os.access(tool, os.X_OK), 'Select an executable tar')
            tool_hashes[tool] = digest(tool.read_bytes())
    records = []

    def run(tool, case, label):
        output = work / label; output.mkdir()
        argv = [str(tool), '-xpf', case['archive'], '-C', str(output)]
        result = subprocess.run(argv, cwd=work, env=environment, capture_output=True, timeout=60)
        (work / (label + '.stdout')).write_bytes(result.stdout)
        (work / (label + '.stderr')).write_bytes(result.stderr)
        records.append(dict(label=label, argv=argv, actual_exit=result.returncode,
            stdout_sha256=digest(result.stdout), stderr_sha256=digest(result.stderr),
            tool_sha256=tool_hashes[tool], environment_sha256=digest(environment_bytes)))
        (work / 'commands.json').write_text(json.dumps(records, indent=2) + '\n')
        return result, output

    for case in cases:
        result, output = run(args.tar, case, case['name'] + '-selected')
        if case['reject']:
            require(result.returncode != 0, 'Malformed or unsupported PAX archive was accepted')
        else:
            require(result.returncode == 0 and result.stderr == b'', 'Selected extractor failed')
            check_tree(output, case['expected'])
    if args.baseline_tar is not None:
        case = cases[0]
        result, output = run(args.baseline_tar, case, 'python-eight-paths-baseline')
        require(result.returncode == 0, 'Baseline must reproduce silent truncation, not a different failure')
        require(all(not os.path.lexists(output / name) for name in PYTHON_PATHS), 'Baseline did not lose all eight names')
        require(all((output / name[:100]).is_file() for name in PYTHON_PATHS), 'Baseline did not create header-truncated files')
    require(args.env_json.read_bytes() == environment_bytes and
            all(digest(tool.read_bytes()) == value for tool, value in tool_hashes.items()),
            'Tool or environment input changed during the check')
    print(json.dumps(dict(status='PASS', scope='Selected tar archive fixtures only; no package acceptance',
                          actual_cases=len(records))))


if __name__ == '__main__':
    main()
