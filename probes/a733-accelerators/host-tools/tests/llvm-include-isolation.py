#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Origin: EmberBSD contributors (AI-assisted).
"""Check native include selection, exact compiler argv and sealer input records."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import sys

sys.dont_write_bytecode = True
PORTS = Path(__file__).resolve().parents[4]
HELPERS = PORTS / 'probes/a733-accelerators/host-tools'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-source', type=Path, required=True)
    parser.add_argument('--compiler', type=Path, required=True)
    parser.add_argument('work', type=Path)
    args = parser.parse_args()
    assert args.work.is_absolute() and not os.path.lexists(args.work)
    sys.path.insert(0, str(args.sdk_source / 'src'))
    import emberbsd_sdk
    from emberbsd_sdk.errors import CommandError
    from emberbsd_sdk.process import ContextLocks
    from emberbsd_sdk.stream import capture_streamed
    assert emberbsd_sdk.API_VERSION == 1
    assert Path(emberbsd_sdk.__file__).resolve().parent == (args.sdk_source / 'src/emberbsd_sdk').resolve()
    for number in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(number, lambda number, frame: sys.exit(128+number))
    with ContextLocks([str(PORTS), str(args.sdk_source)], str(args.work.parent), shared=True), ContextLocks([str(args.work)], str(args.work.parent)):
        args.work.mkdir()
        root = args.work
        (root / 'tmp').mkdir()
        env = dict(os.environ, TMPDIR=str(root / 'tmp'), TMP=str(root / 'tmp'), TEMP=str(root / 'tmp'))
        overlay_module = load(HELPERS / 'prepare-llvm-include-overlay.py', 'native_include_view')
        sealer = load(PORTS / 'profiles/common-graphics/cross/seal-mesa-generators.py', 'native_sealer_records')
        host, llvm, overlay = [root / value for value in ('host', 'llvm', 'overlay')]
        for directory in (host / 'llvm/Config', host / 'llvm-c', llvm / 'llvm/Config', llvm / 'llvm-c'):
            directory.mkdir(parents=True)
        (host / 'llvm/Config/llvm-config.h').write_text('#define LLVM_VERSION_MAJOR 99\n')
        (llvm / 'llvm/Config/llvm-config.h').write_text('#define LLVM_VERSION_MAJOR 23\n')
        (host / 'ordinary.h').write_text('#define ORDINARY 7\n')
        manifest = Path(overlay_module.prepare(str(host), str(llvm), str(overlay)))
        assert (overlay / 'llvm').resolve() == llvm / 'llvm'
        assert (overlay / 'llvm-c').resolve() == llvm / 'llvm-c'
        assert (overlay / 'ordinary.h').resolve() == host / 'ordinary.h'
        first = manifest.read_bytes()
        assert overlay_module.prepare(str(host), str(llvm), str(overlay)) == str(manifest)
        assert manifest.read_bytes() == first
        commands = []

        def run(label, argv, expected=0):
            try:
                result = capture_streamed(list(map(str, argv)), env=env, timeout=30)
                code, out, err = 0, result.value, result.stderr
                assert not result.stderr_truncated
            except CommandError as error:
                code, out, err = error.returncode, error.stdout, error.stderr
                assert not error.stdout_truncated and not error.stderr_truncated
            (root / (label + '.stdout')).write_bytes(out)
            (root / (label + '.stderr')).write_bytes(err)
            commands.append(dict(label=label, argv=list(map(str, argv)), exit=code,
                                 stdout_sha256=hashlib.sha256(out).hexdigest(),
                                 stderr_sha256=hashlib.sha256(err).hexdigest()))
            assert code == expected, (label, code)
            return out

        source = root / 'headers.c'
        source.write_text('#include <llvm/Config/llvm-config.h>\n#include <ordinary.h>\nLLVM_VERSION_MAJOR\nORDINARY\n')
        original = [args.compiler, '-E', '-P', '-I'+str(host), '-isystem', llvm, source]
        assert run('unisolated', original).split() == [b'99', b'7']
        prefix = ['/bin/sh', HELPERS / 'llvm-include-wrapper.sh', args.compiler, host, overlay]
        assert run('isolated', prefix + original[1:]).split() == [b'23', b'7']
        recorder = root / 'argv-recorder'
        recorder.write_text('#!'+sys.executable+' -B\nimport json,sys\nprint(json.dumps(sys.argv[1:]))\n')
        recorder.chmod(0o755)
        prefix[2] = recorder
        for option in ('-I', '-isystem', '-iquote', '-idirafter'):
            for joined in (False, True):
                values = [option+str(host)] if joined else [option, str(host)]
                values += ['-DUNCHANGED=1', 'literal argument with spaces', '-I'+str(llvm)]
                expected = [option+str(overlay)] if joined else [option, str(overlay)]
                expected += values[(1 if joined else 2):]
                assert json.loads(run(option[1:]+str(joined), prefix+values)) == expected
        run('dangling-include', prefix+['-I'], 2)
        run('relative-compiler', ['/bin/sh', HELPERS/'llvm-include-wrapper.sh', 'cc', host, overlay], 2)
        inputs = [recorder, host, overlay]
        try:
            {str(path): sealer.sha(path) for path in inputs}
        except IsADirectoryError:
            pass
        else:
            raise AssertionError('The original directory-hash failure was not reproduced')
        records, directories = sealer.input_records(inputs)
        assert directories == sorted([str(host), str(overlay)])
        assert set(records) == {str(recorder), str(manifest)}
        assert records[str(manifest)] == hashlib.sha256(first).hexdigest()
        foreign = overlay / 'unexpected.h'
        foreign.write_text('unrelated\n')
        try:
            overlay_module.prepare(str(host), str(llvm), str(overlay))
        except ValueError:
            pass
        else:
            raise AssertionError('An extra overlay entry was accepted')
        foreign.unlink()
        (overlay / 'llvm').unlink()
        (overlay / 'llvm').symlink_to(host / 'llvm')
        try:
            overlay_module.prepare(str(host), str(llvm), str(overlay))
        except ValueError:
            pass
        else:
            raise AssertionError('A host LLVM replacement was accepted')
        (root / 'result.json').write_text(json.dumps(dict(status='PASS', commands=commands,
            scope='Only private include/argv/manifest fixtures and native preprocessing. No Mesa build, N/S input, target object, shader or seal acceptance.'), indent=2)+'\n')


if __name__ == '__main__':
    main()
