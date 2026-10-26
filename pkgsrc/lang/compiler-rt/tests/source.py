#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Exercise the actual common source producer and changed-input refusals."""
import argparse
import importlib.util
from pathlib import Path
import sys


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('sdk-source', 'archive', 'git', 'patch', 'work'):
        cli.add_argument('--' + name, required=True)
    args = cli.parse_args()
    path = Path(__file__).resolve().parents[1] / 'files/source.py'
    spec = importlib.util.spec_from_file_location('llvm_runtime_producer', path)
    producer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(producer)
    producer.load_sdk(['--sdk-source', args.sdk_source])
    work = Path(args.work)
    work.mkdir()
    source = work / 'source'
    record = producer.prepare_source(args.archive, source, args.patch, args.git)
    assert producer.verify_source(source, args.git) == record
    # These modules are shared with lang/llvm; preparation must use its patches.
    assert 'LLVM_DARWIN_ARCHIVE_TOOL' in (source / 'llvm/cmake/modules/UseLibtool.cmake').read_text()
    assert 'PKGSRC_LLVM_PTHREADLIB' in (source / 'llvm/cmake/config-ix.cmake').read_text()
    assert 'INSTALL_NAME_DIR "${CMAKE_INSTALL_PREFIX}/lib"' in (source / 'llvm/cmake/modules/AddLLVM.cmake').read_text()

    def rejected(action, reason):
        try:
            action()
        except producer.SDKError as error:
            assert reason in str(error), str(error)
        else:
            raise AssertionError('accepted ' + reason)

    rejected(lambda: producer.prepare_source(args.archive, source, args.patch, args.git),
             'output already exists')
    fixture = source / 'compiler-rt/lib/builtins/comparetf2.c'
    original = fixture.read_bytes()
    fixture.write_bytes(original + b'\n/* changed */\n')
    rejected(lambda: producer.verify_source(source, args.git), 'tree changed')
    fixture.write_bytes(original)
    extra = source / 'unexpected.h'
    extra.write_text('/* unselected source */\n')
    rejected(lambda: producer.verify_source(source, args.git), 'tree changed')
    extra.unlink()
    manifest = source / producer.SOURCE_MANIFEST
    original = manifest.read_bytes()
    altered = dict(record, llvm_version='1.0.0')
    manifest.write_bytes(producer.jsonio.json_bytes(altered))
    rejected(lambda: producer.verify_source(source, args.git), 'selection changed')
    manifest.write_bytes(original)
    invalid = work / Path(args.archive).name
    invalid.write_bytes(b'not the selected source archive')
    rejected(lambda: producer.prepare_source(invalid, work / 'bad-source', args.patch, args.git),
             'archive bytes differ')
    assert not (work / 'bad-source').exists()
    assert producer.verify_source(source, args.git) == record
    producer.jsonio.write_json(work / 'result.json', dict(status='PASS', source=record,
        checks=['actual archive and zero-fuzz patches', 'complete source inventory',
                'existing output', 'changed file', 'extra file', 'changed identity', 'wrong archive']))
    print('PASS: common LLVM source preparation and five changed-input controls; no target compilation')


if __name__ == '__main__':
    main()
