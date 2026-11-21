#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Compare fixed and adaptive worker budgets on identical native C compilations."""

import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve()
PORTS = HERE.parents[2]
PACKAGES = ('long', 'short1', 'short2', 'short3', 'short4')


def log(event):
    with (Path(os.environ['TAIL_WORK']) / 'events').open('a') as output:
        output.write(json.dumps(event) + '\n')


def compile_unit(output):
    start = time.monotonic()
    proc = subprocess.Popen([os.environ['TAIL_CC'], '-O1', '-ffreestanding', '-c', 'unit.c', '-o', output])
    _, status, usage = os.wait4(proc.pid, 0)
    proc.returncode = os.waitstatus_to_exitcode(status)
    # Darwin reports bytes, Linux reports KiB.
    rss = usage.ru_maxrss if sys.platform == 'darwin' else usage.ru_maxrss * 1024
    log(dict(kind='compile', pkg=Path.cwd().name, start=start, end=time.monotonic(), rss=int(rss)))
    return proc.returncode


def worker(pkg, jobs):
    work = Path(os.environ['TAIL_WORK']) / pkg
    start = time.monotonic()
    subprocess.run([os.environ['TAIL_BMAKE'], '-r', '-f', str(work.parent / 'worker.mk'),
                    '_MAKE_JOBS_N=' + jobs, 'PKGPATH=t/' + pkg, 'all'], cwd=work, check=True)
    log(dict(kind='worker', pkg=pkg, start=start, end=time.monotonic(), jobs=int(jobs)))


def peak(compiles, cutoff):
    events = sorted((t, delta) for c in compiles if c['end'] > cutoff for t, delta in
                    ((max(c['start'], cutoff), 1), (c['end'], -1)))
    count = maximum = 0
    for _, change in events:
        count += change
        maximum = max(maximum, count)
    return maximum


def trial(base, name, sdk, prefix, python, units, functions):
    work = base / name
    work.mkdir()
    capture = work / 'events'
    capture.touch()
    fragment = PORTS / 'profiles/common-build-tools/ninja-worker.mk'
    (work / 'worker.mk').write_text(f'.include "{fragment}"\nall:\n\t${{_EMBER_NINJA}} ${{_EMBER_NINJA_JOBS}}\n')
    source = ''.join(f'unsigned f{i}(unsigned v){{for(int i=0;i<80;i++)v=(v>>3)^(v*{i+3}u);return v;}}\n'
                     for i in range(functions))
    for pkg in PACKAGES:
        directory = work / pkg
        directory.mkdir()
        (directory / 'unit.c').write_text(source)
        command = shlex.join([str(python), '-B', str(HERE), 'compile']) + ' $out'
        count = units if pkg == 'long' else 4
        (directory / 'build.ninja').write_text('rule cc\n  command = ' + command + '\n' +
            ''.join(f'build {i}.o: cc unit.c\n' for i in range(count)))
    tools = prefix / 'bin'
    env = dict(os.environ, PATH=str(tools) + os.pathsep + os.environ['PATH'],
               EMBERBSD_HOST_PYTHON=str(python), EMBERBSD_SDK_SOURCE=str(sdk),
               CROSS_BULK_TEST_HOST_PYTHON=str(python), CROSS_BULK_TEST_SDK_SOURCE=str(sdk),
               CROSS_BULK_TEST_NINJA_PROBE=str(HERE), TAIL_WORK=str(work),
               TAIL_BMAKE=str(tools / 'bmake'), TAIL_CC=str(tools / 'clang'), PYTHONDONTWRITEBYTECODE='1')
    env.pop('CROSS_BULK_MAKE_JOBS', None)
    if name.startswith('fixed'):
        env['CROSS_BULK_MAKE_JOBS'] = '2'
    bulk = work / 'bulk'
    start = time.monotonic()
    clock_offset = time.time() - start
    subprocess.run(['/bin/sh', str(HERE.with_name('cross-bulk-parallel.sh')), str(bulk), '--ninja-tail'],
                   env=env, check=True)
    elapsed = time.monotonic() - start
    data = [json.loads(line) for line in capture.read_text().splitlines()]
    compiles = [event for event in data if event['kind'] == 'compile']
    workers = [event for event in data if event['kind'] == 'worker']
    assert len(compiles) == units + 16
    assert sorted(worker['pkg'] for worker in workers) == sorted(PACKAGES)
    assert {worker['jobs'] for worker in workers} == {2}

    cutoff = max(worker['end'] for worker in workers if worker['pkg'] != 'long')
    long_end = next(worker['end'] for worker in workers if worker['pkg'] == 'long')
    # The fixture records completion after its serialized pkg_add. This interval
    # includes staging, queueing for the database lock, and the fixture install.
    short_installed = max((bulk / 'target-db' / pkg).stat().st_mtime for pkg in PACKAGES if pkg != 'long')
    report = dict(
        mode=name, units=len(compiles), elapsed_s=round(elapsed, 3),
        compile_peak=peak(compiles, 0), tail_compile_peak=peak(compiles, cutoff),
        tail_s=round(long_end - cutoff, 3),
        short_install_drain_s=round(short_installed - clock_offset - cutoff, 3),
        max_single_compiler_rss_bytes=max(event['rss'] for event in compiles),
    )
    print(json.dumps(report, sort_keys=True), flush=True)
    assert report['compile_peak'] <= 10
    if name.startswith('fixed'):
        assert report['tail_compile_peak'] <= 2
    else:
        assert report['tail_compile_peak'] > 2


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'compile':
        return compile_unit(sys.argv[2])
    if len(sys.argv) > 1 and sys.argv[1] == 'worker':
        worker(sys.argv[2], sys.argv[3])
        return 0

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-source', type=Path, required=True)
    parser.add_argument('--host-prefix', type=Path, required=True)
    parser.add_argument('--rounds', type=int, default=1)
    parser.add_argument('--units', type=int, default=48, help='C objects for the final long-running package')
    parser.add_argument('--functions', type=int, default=100)
    args = parser.parse_args()
    if args.rounds < 1 or args.units <= 16 or args.functions < 1:
        parser.error('select positive rounds/functions and more than 16 long-package units')
    with tempfile.TemporaryDirectory(prefix='ember-tail-', dir='/tmp') as base:
        for run in range(args.rounds):
            order = ('fixed', 'adaptive') if run % 2 == 0 else ('adaptive', 'fixed')
            for mode in order:
                trial(Path(base), mode + str(run + 1), args.sdk_source.resolve(), args.host_prefix.resolve(),
                      Path(sys.executable).resolve(), args.units, args.functions)
    return 0


if __name__ == '__main__':
    sys.exit(main())
