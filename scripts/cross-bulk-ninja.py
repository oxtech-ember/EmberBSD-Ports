#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Run a pkgsrc Ninja stage against its worker's CPU allocation."""

import argparse
from contextlib import ExitStack
import errno
import fcntl
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import tempfile


def allocation(state):
    state.seek(0)
    value = int(state.readline())
    if value < 1:
        raise ValueError('invalid worker CPU allocation')
    return value


def grant(budget, capacity):
    """Grow the last worker once, including a Ninja which already started."""
    with budget.open('r+') as state:
        fcntl.flock(state, fcntl.LOCK_EX)
        previous = allocation(state)
        if previous >= capacity:
            return
        # Record the budget first. A retry cannot issue these tokens twice.
        state.seek(0)
        state.write(str(capacity) + '\n')
        state.truncate()
        state.flush()
        try:
            writer = os.open(budget.with_suffix('.ninja'), os.O_NONBLOCK | os.O_WRONLY)
        except OSError as error:
            if error.errno in (errno.ENOENT, errno.ENXIO):
                return  # No active Ninja. Its next invocation will read the new budget.
            raise
        try:
            if not stat.S_ISFIFO(os.fstat(writer).st_mode):
                raise ValueError('active Ninja jobserver is not a FIFO')
            tokens = b'+' * (capacity - previous)
            while tokens:
                tokens = tokens[os.write(writer, tokens):]
        except BrokenPipeError:
            pass  # The stage exited while the scheduler was granting its slots.
        finally:
            os.close(writer)


def explicit_limit(command, limit):
    # Ninja disables its jobserver on an explicit -j. Preserve a package's lower
    # limit and other arguments, and keep it within the allocation of this worker.
    explicit = False
    for index, arg in enumerate(command[1:], start=1):
        if arg == '--':
            break
        if arg == '-j' and index + 1 < len(command) and command[index + 1].isdigit():
            value = int(command[index + 1])
            command[index + 1] = str(min(value or limit, limit))
            explicit = True
        elif arg.startswith('-j') and arg[2:].isdigit():
            value = int(arg[2:])
            command[index] = '-j' + str(min(value or limit, limit))
            explicit = True
    return explicit


def worker_makeflags(inherited, fifo):
    # bmake quotes whitespace in command-line assignments. Preserve those words
    # and GNU make's -- variable section, replacing only the parent's job options.
    words = iter(re.findall(r'(?:\\.|[^\s\\])+', inherited or ''))
    kept = []
    word = next(words, None)
    while word is not None and word != '--':
        if word in ('-j', '--jobs', '-J'):
            option, word = word, next(words, None)
            argument = r'\d+,\d+' if option == '-J' else r'\d+'
            if word is not None and re.fullmatch(argument, word):
                word = next(words, None)
            continue
        if not re.fullmatch(r'-j\d+|-J\d+,\d+|--jobs=\d+|--jobserver-(?:auth|fds|style)=.*', word):
            kept.append(word)
        word = next(words, None)
    job_options = ['-j', f'--jobserver-auth=fifo:{fifo}']
    # Ninja treats 'n' in the first bare word as GNU make's dry-run flag.
    # bmake may put a package variable assignment in that position.
    if kept and not kept[0].startswith('-') and '=' in kept[0]:
        kept = job_options + kept
    else:
        kept.extend(job_options)
    if word == '--':
        kept.extend((word, *words))
    return ' '.join(kept)


def run_child(command, env):
    child = None
    received = []

    def stop(signum, _frame):
        if child is None:
            received.append(signum)
        else:
            child.send_signal(signum)

    previous = {sig: signal.signal(sig, stop) for sig in (signal.SIGINT, signal.SIGHUP, signal.SIGTERM)}
    try:
        child = subprocess.Popen(command, env=env)
        for signum in received:
            child.send_signal(signum)
        result = child.wait()
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
    return result if result >= 0 else 128 - result


def run(budget, fixed, command, sdk_source, safe, capped):
    if os.environ.get('EMBERBSD_BULK_NINJA_ACTIVE') == str(budget):
        # A build command can call pkgsrc recursively. It already occupies one
        # outer Ninja slot and must not wait on its own worker lock.
        if not explicit_limit(command, 1):
            command[1:1] = ['-j', '1']
        os.execvp(command[0], command)
    # All Ninja invocations in this worker share its single implicit slot,
    # including fixed/serial and custom multidir recipes.
    with budget.with_suffix('.ninja-lock').open('a') as client, ExitStack() as server:
        fcntl.flock(client, fcntl.LOCK_EX)
        env = dict(os.environ, EMBERBSD_BULK_NINJA_ACTIVE=str(budget))
        with budget.open() as state:
            fcntl.flock(state, fcntl.LOCK_EX)
            available = allocation(state)
            limit = 1 if safe == 'no' else min(available, fixed)
            if not explicit_limit(command, limit):
                adaptive = safe != 'no' and capped != 'yes'
                if adaptive:
                    sys.path.insert(0, str(sdk_source / 'src'))
                    from emberbsd_sdk import jobserver, profile_build
                    adaptive = (hasattr(profile_build, 'NINJA_MINIMUM') and
                                profile_build.ninja_version(command[0]) >= profile_build.NINJA_MINIMUM)
                if adaptive:
                    # GNU make and Ninja delimit the authentication word with whitespace.
                    directory = '/tmp' if any(c.isspace() for c in str(budget.parent)) else budget.parent
                    root = Path(server.enter_context(tempfile.TemporaryDirectory(dir=directory, prefix='.ninja-')))
                    fifo = root / 'jobs'
                    server.enter_context(jobserver.serve(fifo, available))
                    active = budget.with_suffix('.ninja')
                    active.unlink(missing_ok=True)
                    active.symlink_to(fifo)
                    server.callback(active.unlink, missing_ok=True)
                    env['MAKEFLAGS'] = worker_makeflags(env.get('MAKEFLAGS'), fifo)
                    if 'MFLAGS' in env:
                        env['MFLAGS'] = worker_makeflags(env['MFLAGS'], fifo)
                else:
                    command[1:1] = ['-j', str(limit)]
        return run_child(command, env)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest='action', required=True)
    for name in ('grant', 'run'):
        action = subparsers.add_parser(name)
        action.add_argument('budget', type=Path)
        action.add_argument('jobs', type=int)
        if name == 'run':
            action.add_argument('safe')
            action.add_argument('capped', choices=('yes', 'no'))
            action.add_argument('sdk_source', type=Path)
            action.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.jobs < 1 or not args.budget.is_absolute():
        parser.error('select a positive allocation and an absolute worker budget path')
    try:
        if args.action == 'grant':
            grant(args.budget, args.jobs)
            return 0
        if not args.command:
            parser.error('select the Ninja command')
        return run(args.budget, args.jobs, args.command, args.sdk_source, args.safe, args.capped)
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, f'cross-bulk-ninja: {error}\n')


if __name__ == '__main__':
    sys.exit(main())
