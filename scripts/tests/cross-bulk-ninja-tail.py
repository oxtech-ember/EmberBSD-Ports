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

import cross_bulk_replace_fixture as replacement

HERE = Path(__file__).resolve()
PORTS = HERE.parents[2]
PACKAGES = ('long', 'short1', 'short2', 'short3', 'short4')


def log(event):
    with (Path(os.environ['TAIL_WORK']) / 'events').open('a') as output:
        output.write(json.dumps(event) + '\n')


def compile_command(command):
    request = replacement.request_time(Path(os.environ['TAIL_WORK'])) if 'TAIL_PKG_INFO' in os.environ else None
    start = time.monotonic()
    proc = subprocess.Popen(command)
    _, status, usage = os.wait4(proc.pid, 0)
    proc.returncode = os.waitstatus_to_exitcode(status)
    # Darwin reports bytes, Linux reports KiB.
    rss = usage.ru_maxrss if sys.platform == 'darwin' else usage.ru_maxrss * 1024
    log(dict(kind='compile', pkg=Path.cwd().name, start=start, end=time.monotonic(), rss=int(rss), request=request))
    return proc.returncode


def worker(pkg, jobs):
    work = Path(os.environ['TAIL_WORK']) / pkg
    start = time.monotonic()
    if 'TAIL_PKG_INFO' not in os.environ or pkg == 'long':
        subprocess.run([os.environ['TAIL_BMAKE'], '-r', '-f', str(work.parent / 'worker.mk'),
                        '_MAKE_JOBS_N=' + jobs, 'PKGPATH=t/' + pkg, 'all'], cwd=work, check=True)
    if 'TAIL_PKG_INFO' in os.environ and pkg in ('long', 'short1'):
        replacement.build_package(work.parent, Path(os.environ['TAIL_PKG_INFO']).parents[1], pkg)
    log(dict(kind='worker', pkg=pkg, start=start, end=time.monotonic(), jobs=int(jobs)))


def peak(compiles, cutoff):
    events = sorted((t, delta) for c in compiles if c['end'] > cutoff for t, delta in
                    ((max(c['start'], cutoff), 1), (c['end'], -1)))
    count = maximum = 0
    for _, change in events:
        count += change
        maximum = max(maximum, count)
    return maximum


def trial(base, name, sdk, prefix, python, units, functions, waiting_replace):
    work = base / name
    work.mkdir()
    capture = work / 'events'
    capture.touch()
    fragment = PORTS / 'profiles/common-build-tools/ninja-worker.mk'
    (work / 'worker.mk').write_text(f'.include "{fragment}"\nall:\n\t${{_EMBER_NINJA}} ${{_EMBER_NINJA_JOBS}}\n')
    source = ''.join(f'unsigned f{i}(unsigned v){{for(int i=0;i<80;i++)v=(v>>3)^(v*{i+3}u);return v;}}\n'
                     for i in range(functions))
    if waiting_replace:
        replacement.prepare(work, prefix, python, HERE, units, source)
    else:
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
    env.pop('TAIL_PKG_INFO', None)
    if waiting_replace:
        env['TAIL_PKG_INFO'] = str(prefix / 'sbin/pkg_info')
    if name.startswith('fixed'):
        env['CROSS_BULK_MAKE_JOBS'] = '2'
    bulk = work / 'bulk'
    start = time.monotonic()
    clock_offset = time.time() - start
    scenario = '--ninja-replace' if waiting_replace else '--ninja-tail'
    subprocess.run(['/bin/sh', str(HERE.with_name('cross-bulk-parallel.sh')), str(bulk), scenario],
                   env=env, check=True)
    elapsed = time.monotonic() - start
    data = [json.loads(line) for line in capture.read_text().splitlines()]
    compiles = [event for event in data if event['kind'] == 'compile']
    workers = [event for event in data if event['kind'] == 'worker']
    by_package = {worker['pkg']: worker for worker in workers}
    assert {worker['jobs'] for worker in workers} == {2}
    long_end = by_package['long']['end']
    if waiting_replace:
        assert len(compiles) == units and sorted(by_package) == ['long', 'next1', 'next2', 'short1']
        requests = [c['request'] for c in compiles if c['request'] is not None]
        assert requests, 'No compiler started during the replacement wait. Increase --units.'
        cutoff = min(requests) - clock_offset
        # The reader also requests replacement. Both jobs are parked before
        # the first writer gets its allocation back. Their successors start a new wave.
        first, second = sorted((e for e in data if e['kind'] == 'replaced'), key=lambda e: e['start'])
        assert long_end <= first['start'] <= first['end'] <= second['start'] <= second['end']
        assert second['end'] <= min(by_package[p]['start'] for p in ('next1', 'next2'))
        writers = {e['pkg']: e for e in (first, second)}
        assert writers['short1']['allocation'] == 2
        assert writers['long']['allocation'] == (2 if name.startswith('fixed') else 4)
        timing = dict(writer_wait_s=round(writers['short1']['start'] - cutoff, 3))
        capacity = 4
    else:
        assert len(compiles) == units + 16 and sorted(by_package) == sorted(PACKAGES)
        cutoff = max(worker['end'] for worker in workers if worker['pkg'] != 'long')
        # Includes staging, waiting for the database lock, and the fixture installation.
        installed = max((bulk / 'target-db' / pkg).stat().st_mtime for pkg in PACKAGES if pkg != 'long')
        timing = dict(short_install_drain_s=round(installed - clock_offset - cutoff, 3))
        capacity = 10
    report = dict(
        mode=name, units=len(compiles), elapsed_s=round(elapsed, 3),
        compile_peak=peak(compiles, 0), tail_compile_peak=peak(compiles, cutoff),
        tail_s=round(long_end - cutoff, 3), **timing,
        max_single_compiler_rss_bytes=max(event['rss'] for event in compiles),
    )
    print(json.dumps(report, sort_keys=True), flush=True)
    assert report['compile_peak'] <= capacity
    if name.startswith('fixed'):
        assert report['tail_compile_peak'] <= 2
    else:
        assert report['tail_compile_peak'] > 2, 'No overlap above two jobs in the tail. Increase --units.'


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'compile':
        return compile_command([os.environ['TAIL_CC'], '-O1', '-ffreestanding', '-c', 'unit.c', '-o', sys.argv[2]])
    if len(sys.argv) > 1 and sys.argv[1] == 'compiler':
        return compile_command(sys.argv[2:])
    if len(sys.argv) > 1 and sys.argv[1] == 'replace':
        start = time.monotonic()
        pkg, jobs = sys.argv[2:]
        budget = os.environ.get('EMBERBSD_BULK_NINJA_BUDGET')
        allocation = int(Path(budget).read_text()) if budget else int(jobs)
        replacement.replace(Path(os.environ['TAIL_WORK']), Path(os.environ['TAIL_PKG_INFO']).parents[1], pkg)
        log(dict(kind='replaced', start=start, end=time.monotonic(), pkg=pkg, allocation=allocation))
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == 'worker':
        worker(sys.argv[2], sys.argv[3])
        return 0

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-source', type=Path, required=True)
    parser.add_argument('--host-prefix', type=Path, required=True)
    parser.add_argument('--waiting-replace', action='store_true', help='measure the last reader before an exclusive pkg_add')
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
                      Path(sys.executable).resolve(), args.units, args.functions, args.waiting_replace)
    return 0


if __name__ == '__main__':
    sys.exit(main())
