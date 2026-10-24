#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; exercise the production source preparer and pinned diff.
import shutil
from concurrent.futures import ThreadPoolExecutor
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
profile = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(profile / 'runtime/recipe/files'))
import sdk_source


def main():
    args = sdk_source.arguments(sys.argv[1:])
    if len(args) != 2:
        raise SystemExit('usage: gcc-source-prerequisite.py PKGSRC GCC_ARCHIVE --sdk-source SOURCE')
    sys.path.insert(0, str(profile))
    from host import SDKError, prepare_source, source_prerequisite
    pkgsrc, archive = (Path(arg).resolve(strict=True) for arg in args)
    patches = ['patch-gcc_darwin_llvm_mc']
    with tempfile.TemporaryDirectory(prefix='ember-gcc-source-') as temporary:
        work = Path(temporary)
        delta = source_prerequisite(archive, patches, work)
        assert delta is not None
        assert source_prerequisite(archive, [], work) is None
        bad_cache = work / 'bad-cache'
        bad_cache.mkdir()
        cached = bad_cache / delta.name
        shutil.copyfile(delta, cached)
        with cached.open('ab') as output:
            output.write(b'corrupt')
        try:
            source_prerequisite(bad_cache / archive.name, patches, bad_cache)
        except SDKError as error:
            assert 'SHA256 mismatch' in str(error), str(error)
        else:
            raise AssertionError('A corrupt cached source prerequisite was accepted')
        print('PASS corrupt prerequisite refusal and recipe without prerequisite', flush=True)
        readonly = work / 'readonly'
        readonly.mkdir()
        readonly.chmod(0o555)
        cache = work / 'cache'
        cache.mkdir()
        try:
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(source_prerequisite, readonly / archive.name, patches, cache)
                           for _ in range(4)]
                outputs = [future.result() for future in futures]
            assert len(set(outputs)) == 1 and outputs[0] == cache / delta.name
            assert not list(cache.glob('.*'))
            assert not list(readonly.iterdir())
        finally:
            readonly.chmod(0o755)
        print('PASS concurrent atomic cache fill with read-only archive directory', flush=True)
        source = work / 'source'
        prepare_source(pkgsrc, archive, source, runtime=False)
        assert (source / 'gcc/config/aarch64/darwin.h').is_file()
        assert 'DARWIN_LLVM_MC' in (source / 'gcc/config/darwin.h').read_text()
        assert not list(source.rglob('*.rej'))
        diff = (work / 'source-darwin.diff').read_text()
        assert 'diff --git a/libgcobol/configure.tgt' not in diff
        assert 'diff --git a/gcc/config/aarch64/darwin.h' in diff
        print('PASS complete production GCC source preparation without patch rejects')


if __name__ == '__main__':
    main()
