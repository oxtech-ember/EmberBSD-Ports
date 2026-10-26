#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD; AI-assisted diagnostic fuzz evidence adapter.
"""Build an SDK manifest for Cairo fuzzing and memory-check evidence."""

import argparse
import filecmp
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile

# Ports harness, corpus and recipe inputs used by the Cairo LZO build.
PORTS_EVIDENCE_PATHS = (
    'pkgsrc/archivers/lzo/Makefile',
    'pkgsrc/archivers/lzo/distinfo',
    'pkgsrc/archivers/lzo/patches',
    'pkgsrc/graphics/cairo/Makefile',
    'pkgsrc/graphics/cairo/buildlink3.mk',
    'pkgsrc/graphics/cairo/distinfo',
    'pkgsrc/graphics/cairo/options.mk',
    'pkgsrc/graphics/cairo/patches',
    'profiles/common-graphics/tests/cairo-lzo-bounds.c',
    'profiles/common-graphics/tests/cairo-lzo-bounds.py',
    'profiles/common-graphics/tests/cairo-lzo-corpus',
    'profiles/common-graphics/tests/cairo-lzo-evidence.py',
    'profiles/common-graphics/tests/cairo-lzo-fuzz.c',
    'profiles/common-graphics/tests/cairo-lzo-lsan-probe.c',
    'profiles/common-graphics/tests/cairo-lzo-seedgen.c',
)

# Files that fuzz-check.py imports, including lazily selected host backends.
SDK_FUZZ_CHECK_PATHS = (
    'scripts/fuzz-check.py',
    'src/emberbsd_sdk/__init__.py',
    'src/emberbsd_sdk/_darwin_process.py',
    'src/emberbsd_sdk/_linux_process.py',
    'src/emberbsd_sdk/_netbsd_process.py',
    'src/emberbsd_sdk/errors.py',
    'src/emberbsd_sdk/fuzz_check.py',
    'src/emberbsd_sdk/jsonio.py',
    'src/emberbsd_sdk/paths.py',
    'src/emberbsd_sdk/process.py',
    'src/emberbsd_sdk/stream.py',
)


def _tree(root):
    return sorted(path.relative_to(root) for path in root.rglob('*'))


def _same_tree(left, right):
    names = _tree(left)
    return names == _tree(right) and all(
        filecmp.cmp(left / name, right / name, shallow=False)
        for name in names if (left / name).is_file())


def snapshot_commit(checkout, paths, parent):
    """Extract paths from the checkout's HEAD commit below parent/<commit>.

    The copy is independent of later changes to the checkout. An existing
    snapshot is reused only when it still matches the commit bytes exactly.
    """
    checkout = Path(checkout).resolve(strict=True)
    revision = subprocess.check_output(
        ['git', '-C', str(checkout), 'rev-parse', '--verify', 'HEAD^{commit}'],
        text=True).strip()
    archive = subprocess.check_output(
        ['git', '-C', str(checkout), 'archive', '--format=tar', revision, '--',
         *paths])
    parent = Path(parent)
    parent.mkdir(parents=True, exist_ok=True)
    destination = parent / revision
    staging = Path(tempfile.mkdtemp(prefix='.snapshot-', dir=parent))
    try:
        with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
            stream.extractall(staging, filter='data')
        missing = [path for path in paths if not (staging / path).exists()]
        if missing:
            raise SystemExit(f'commit {revision} lacks evidence inputs: {missing}')
        for path in _tree(staging):
            if (staging / path).is_file():
                os.chmod(staging / path, 0o444)
        if destination.exists():
            if not _same_tree(staging, destination):
                raise SystemExit(f'snapshot differs from commit {revision}: {destination}')
        else:
            staging.rename(destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return destination, revision


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ports-root', type=Path, required=True)
    parser.add_argument('--sdk-root', type=Path, required=True)
    parser.add_argument('--work-root', type=Path, required=True)
    parser.add_argument('--distfiles', type=Path, required=True)
    parser.add_argument('--clang', type=Path, required=True)
    parser.add_argument('--gcc', type=Path, required=True)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--ninja', type=Path, required=True)
    parser.add_argument('--pkg-config', type=Path, required=True)
    parser.add_argument('--cppcheck', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()

    work = args.work_root.resolve(strict=True)
    distfiles = args.distfiles.resolve(strict=True)
    checkout = args.ports_root.resolve(strict=True)
    if subprocess.check_output(['git', '-C', str(checkout), 'status', '--porcelain'],
                               text=True).strip():
        parser.error('Ports checkout must be clean before creating evidence')
    ports, ports_revision = snapshot_commit(checkout, PORTS_EVIDENCE_PATHS,
                                            work / 'ports-snapshots')
    args.cairo_source = work / 'cairo-1.18.6'
    args.baseline_source = work / 'cairo-before-lzo/cairo-1.18.6'
    args.lzo_clang_source = work / 'lzo-2.10'
    args.lzo_gcc_source = work / 'lzo-gcc-src/src'
    args.meson_source = work / 'tool-src/meson-1.12.1'
    args.cairo_archive = distfiles / 'cairo-1.18.6.tar.xz'
    args.lzo_archive = distfiles / 'lzo-2.10.tar.gz'
    args.meson_archive = distfiles / 'meson-1.12.1.tar.gz'
    args.clang_build = work / 'meson-builds/clang2'
    args.gcc_build = work / 'meson-builds/gcc16'
    args.memcheck_build = work / 'meson-builds/gcc16-memcheck'
    args.baseline_build = work / 'meson-builds/before-lzo'
    args.lzo_clang_prefix = work / 'prefix/clang-lzo'
    args.lzo_gcc_prefix = work / 'prefix/gcc-lzo'
    args.fuzzer = work / 'bin/cairo-lzo-fuzzer-patched'
    args.replay = work / 'bin/cairo-lzo-replay-gcc16'
    args.memcheck = work / 'bin/cairo-lzo-replay-gcc16-memcheck'
    args.lsan_probe = work / 'bin/cairo-lzo-lsan-probe'
    args.lsan_replay = work / 'bin/cairo-lzo-replay-lsan'
    args.corpus = ports / 'profiles/common-graphics/tests/cairo-lzo-corpus'
    args.logs = work / 'results/accepted'
    if args.memcheck.is_file() != args.memcheck_build.is_dir():
        parser.error('Memcheck binary and its separate Meson build must be present together')

    sdk_root, sdk_revision = snapshot_commit(args.sdk_root, SDK_FUZZ_CHECK_PATHS,
                                             work / 'sdk-snapshots')
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(sdk_root / 'src'))
    from emberbsd_sdk.fuzz_check import FUZZ_MANIFEST_VERSION, file_sha256, tree_files

    sources = []
    seen_paths = set()

    def add_file(name, revision, path):
        path = Path(path).resolve(strict=True)
        if path in seen_paths:
            parser.error(f'duplicate evidence input: {path}')
        seen_paths.add(path)
        sources.append({'name': name, 'revision': revision,
                        'path': str(path), 'sha256': file_sha256(path)})

    def add_tree(name, revision, root):
        root = Path(root).resolve(strict=True)
        for item in tree_files(root):
            add_file(f'{name}/{item["path"]}', revision, root / item['path'])

    def expected_hash(distinfo, algorithm, filename):
        pattern = f'{algorithm} ({filename}) = '
        for line in distinfo.read_text(encoding='utf-8').splitlines():
            if line.startswith(pattern):
                return line[len(pattern):].strip()
        parser.error(f'missing {algorithm} for {filename}: {distinfo}')

    def digest(path, algorithm):
        hasher = hashlib.new(algorithm.lower())
        with Path(path).open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                hasher.update(block)
        return hasher.hexdigest()

    cairo_dist = ports / 'pkgsrc/graphics/cairo'
    lzo_dist = ports / 'pkgsrc/archivers/lzo'
    if digest(args.cairo_archive, 'sha512') != expected_hash(
            cairo_dist / 'distinfo', 'SHA512', 'cairo-1.18.6.tar.xz'):
        parser.error('Cairo archive does not match Ports distinfo')
    if digest(args.lzo_archive, 'sha512') != expected_hash(
            lzo_dist / 'distinfo', 'SHA512', 'lzo-2.10.tar.gz'):
        parser.error('LZO archive does not match Ports distinfo')
    if digest(args.meson_archive, 'sha256') != (
            'ab0a6ca09f8ef70c564c8241fb5a23957886a0b53fb58412b5e07eaf07dba743'):
        parser.error('Meson 1.12.1 archive SHA256 mismatch')
    add_file('cairo-1.18.6-archive', 'Ports-main:' + ports_revision, args.cairo_archive)
    add_file('lzo-2.10-archive', 'Ports-main:' + ports_revision, args.lzo_archive)
    add_file('meson-1.12.1-archive-sha256-ab0a6ca0',
             'Meson 1.12.1 archive SHA256 ab0a6ca09f8ef70c564c8241fb5a23957886a0b53fb58412b5e07eaf07dba743',
             args.meson_archive)
    add_tree('cairo-patched', 'Cairo 1.18.6 plus Ports main ' + ports_revision,
             args.cairo_source)
    add_tree('cairo-before-lzo', 'Cairo 1.18.6 before LZO patches plus Ports main ' + ports_revision,
             args.baseline_source)
    for label, root, revision in (
            ('lzo-clang-build', args.lzo_clang_source,
             'LZO 2.10 plus Clang sanitizer configure'),
            ('lzo-gcc-build', args.lzo_gcc_source,
             'LZO 2.10 plus GCC16 sanitizer configure')):
        for relative in ('config.h', 'src/lzo_init.c', 'src/lzo_func.h',
                         'src/lzo_dict.h', 'src/lzo1a.c', 'src/lzo1b_1.c',
                         'src/lzo1f_1.c',
                         'src/lzo1a_sm.ch', 'src/lzo1b_sm.ch',
                         'src/lzo1f_sm.ch', 'minilzo/minilzo.c'):
            path = root / relative
            if path.is_file():
                add_file(label + '-' + relative.replace('/', '-'), revision, path)
    add_tree('meson-1.12.1-source', 'Meson 1.12.1 archive SHA256 ab0a6ca09f8ef70c564c8241fb5a23957886a0b53fb58412b5e07eaf07dba743',
             args.meson_source)

    add_tree('ports', 'Ports commit ' + ports_revision + ' (git archive)', ports)
    add_tree('sdk', 'SDK commit ' + sdk_revision + ' (git archive)', sdk_root)

    add_file('gcc16-cairo-fuzzer-macro-context',
             'GCC 16.2.0 aarch64-apple-darwin27; Cairo Script Interpreter headers included',
             work / 'results/cairo-fuzz-gcc16-macros.txt')
    add_file('gcc16-lzo-macro-context',
             'GCC 16.2.0 aarch64-apple-darwin27; LZO configuration headers included',
             work / 'results/lzo-gcc16-macros.txt')

    tools = {}
    tool_specs = [
            ('clang', args.clang, ['-O1', '-g', '-fsanitize=fuzzer-no-link,address,undefined',
                                   '-fsanitize=fuzzer,address,undefined', '-fno-omit-frame-pointer']),
            ('gcc', args.gcc, ['-O1', '-g', '-fsanitize=address,undefined',
                               '-fno-omit-frame-pointer']),
            ('clang_lsan', args.clang, ['-O1', '-g', '-fsanitize=address,undefined',
                                        '-fno-omit-frame-pointer'])]
    if args.memcheck.is_file():
        tool_specs.append(('gcc_memcheck', args.gcc,
                           ['-O1', '-g', '-fno-omit-frame-pointer']))
    for name, compiler, flags in tool_specs:
        compiler = compiler.resolve(strict=True)
        tools[name] = {'path': str(compiler), 'sha256': file_sha256(compiler),
                       'version': subprocess.check_output(
                           [str(compiler), '--version'], text=True).strip(),
                       'flags': flags}

    for name, path in (('python3.15', args.python), ('ninja', args.ninja),
                       ('pkg-config', args.pkg_config), ('cppcheck', args.cppcheck)):
        executable = path.resolve(strict=True)
        add_file(name, 'resolved build tool executable bytes', executable)

    build_roots = [('clang-build', args.clang_build),
                   ('gcc16-build', args.gcc_build),
                   ('upstream-control-build', args.baseline_build)]
    if args.memcheck_build.is_dir():
        build_roots.append(('memcheck-build', args.memcheck_build))
    for label, root in build_roots:
        root = Path(root).resolve(strict=True)
        for relative in ('build.ninja', 'compile_commands.json', 'config.h',
                         'meson-private/cmd_line.txt',
                         'meson-info/intro-buildoptions.json',
                         'meson-info/intro-targets.json'):
            path = root / relative
            if path.is_file():
                add_file(label + '-' + relative.replace('/', '-'),
                         'Meson configured build inputs', path)
        for relative in ('src/cairo-features.h',):
            path = root / relative
            if path.is_file():
                add_file(label + '-' + relative.replace('/', '-'),
                         'Meson generated feature header', path)

    binaries = {}
    binary_inputs = [('fuzzer', args.fuzzer), ('replay', args.replay),
                     ('lsan_probe', args.lsan_probe), ('lsan_replay', args.lsan_replay)]
    if args.memcheck.is_file():
        binary_inputs.append(('memcheck', args.memcheck))
    for name, path in binary_inputs:
        path = Path(path).resolve(strict=True)
        binaries[name] = {'path': str(path), 'sha256': file_sha256(path)}

    corpus_root = args.corpus.resolve(strict=True)
    corpus_files = tree_files(corpus_root)
    log_root = args.logs.resolve(strict=True)
    build_logs = []
    for path in sorted(log_root.iterdir()):
        if not path.is_file() or path.is_symlink():
            continue
        build_logs.append({'path': str(path.resolve(strict=True)),
                           'sha256': file_sha256(path)})
    if not build_logs:
        parser.error('the build-log directory is empty')

    manifest = {
        'schema': FUZZ_MANIFEST_VERSION,
        'name': 'cairo-lzo-script-interpreter',
        'scope': 'diagnostic-host',
        'host': {'system': platform.system(), 'machine': platform.machine()},
        'sources': sources,
        'tools': tools,
        'binaries': binaries,
        'corpus': {'path': str(corpus_root), 'files': corpus_files},
        'build_logs': build_logs,
        'limitations': [
            'This ' + platform.system() + '/' + platform.machine() + ' host run is not a target EmberBSD ABI or device result.',
            'Pixman and FreeType are host shared libraries and were not instrumented in this build.',
            'Valgrind Memcheck is optional and only passes when it runs successfully on a supported host; unsupported or unavailable status is not a pass.',
            'The LZO Ports patch expresses supported byte alignment for GCC/Clang unaligned-access aliases in the library and bundled minilzo. GCC16 ASan/UBSan make check and make test pass with the patch. Clang ASan/UBSan fail-fast make check still reports pointer-overflow in upstream LZO1B compression at src/lzo1b_sm.ch:45; broader LZO1B/1A/1F checks need separate repair before claiming suite-wide sanitizer compatibility.',
            'This finite campaign has no coverage acceptance threshold and is not formal verification or certification.',
            'The manifest is unsigned and cannot establish source origin or compiler identity independently.'
        ],
        'sanitizer_options': {
            'ASAN_OPTIONS': 'abort_on_error=1:detect_leaks=1',
            'UBSAN_OPTIONS': 'halt_on_error=1:print_stacktrace=1'
        }
    }
    if args.output.exists():
        parser.error(f'manifest output already exists: {args.output}')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n',
                           encoding='utf-8')
    print(f'wrote {args.output}: {len(sources)} source inputs, '
          f'{len(build_logs)} build logs, {len(corpus_files)} seed files')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
