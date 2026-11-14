#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted); not submitted upstream.
"""Check the real Ninja environment caps nested Python worker pools."""
import argparse
import importlib.util
from pathlib import Path
import shlex
import sys
import tempfile
from types import SimpleNamespace

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--sdk-source', type=Path, required=True)
parser.add_argument('--host-prefix', type=Path, required=True)
args = parser.parse_args()
sdk = args.sdk_source.resolve(strict=True)
prefix = args.host_prefix.resolve(strict=True)
sys.path.insert(0, str(sdk / 'src'))
from emberbsd_sdk import host_prefix, process
native = host_prefix.load_host_prefix(str(prefix), required_roles=('python', 'ninja'))
owner = Path(__file__).resolve().parents[1] / '../../pkgsrc/devel/electron44/files/build-electron.py'
spec = importlib.util.spec_from_file_location('electron_build_generator_jobs', owner)
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)

# Fail before Pool creation if the limit is missing, including on old code.
action = '''import multiprocessing as mp\nimport os\nimport pathlib\nimport sys\nimport time\n\ndef worker(x):\n    time.sleep(0.03)\n    return os.getpid()\n\nif __name__ == "__main__":\n    assert os.cpu_count() == os.process_cpu_count() == mp.cpu_count() == 1\n    with mp.Pool(processes=mp.cpu_count()) as pool:\n        assert len(set(pool.map(worker, range(4)))) == 1\n    pathlib.Path(sys.argv[1]).write_text("ok")\n'''
with tempfile.TemporaryDirectory(prefix='electron-generator-jobs-') as tmp:
    work = Path(tmp)
    output = work / 'out'
    output.mkdir()
    script = work / 'action.py'
    script.write_text(action)
    python = shlex.quote(native.tool('python'))
    action_path = shlex.quote(str(script))
    (output / 'build.ninja').write_text(
        'rule action\n  command = ' + python + ' ' + action_path + ' $out\n'
        'rule archive\n  command = ' + python + ' -c "open(\'dist.zip\',\'wb\').write(b\'ok\')"\n'
        'build a: action\nbuild b: action\nbuild dist.zip: archive a b\n'
        'build electron_dist_zip: phony dist.zip\n')
    seen = []
    class RecordingProcess:
        @staticmethod
        def run_logged(argv, *a, **kw):
            seen.append(list(argv))
            return process.run_logged(argv, *a, **kw)
    env = dict(process.sanitized_environment(), PATH=native.path, PYTHON_CPU_COUNT='8')
    original = env.copy()
    b.run_ninja(SimpleNamespace(work=work, jobs=2), {'process': RecordingProcess}, native, work, env)
    assert len(seen) == 1 and seen[0][seen[0].index('-j') + 1] == '2'
    assert env == original and env['PYTHON_CPU_COUNT'] == '8'
    assert (output / 'a').read_text() == (output / 'b').read_text() == 'ok'
print('PASS: Ninja -j2 preserves caller environment and caps Python worker pools')
