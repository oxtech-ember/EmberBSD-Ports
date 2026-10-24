#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD; AI-assisted finite source and make-route controls.
"""Check GCC link-only changes or prepare finite make work, without a compiler."""

import argparse
import json
import os
from pathlib import Path
import sys
import time

PREFIX = '$(if $(GCC_HOST_LINKER_LAUNCHER),$(GCC_HOST_LINKER_LAUNCHER) )'
DRIVERS = [('LINKER', 'CXX'), ('LINKER', 'CC'), ('LINKER_FOR_BUILD', 'CXX_FOR_BUILD')]


def require(value, message):
    if not value:
        raise ValueError(message)


def check(before, after):
    expected = before
    for name, driver in DRIVERS:
        original = name + ' = $(' + driver + ')\n'
        require(expected.count(original) == 1, 'Changed GCC driver source: ' + name)
        expected = expected.replace(original, name + ' = ' + PREFIX + '$(' + driver + ')\n')
    require(after == expected, 'The patch changes more than the three link assignments')
    require(after.replace(PREFIX, '') == before, 'Empty launcher changes original commands')


def make_fragment(source):
    start = source.index('# The name of the compiler to use.\n')
    end = source.index('\nEXTRA_GCC_OBJS =', start)
    frontend = source[start:end]
    # This finite fixture does not execute GCC's separate local mutex script.
    frontend = frontend.replace('@DO_LINK_MUTEX@', 'false').replace('@CET_HOST_FLAGS@', '')
    start = source.index('# Native compiler that we use.')
    end = source.index('# Native linker and preprocessor flags.', start)
    return frontend + '\n' + source[start:end] + '''
.PHONY: all compile-one compile-two link-one link-two
all: compile-one compile-two link-one link-two
compile-one compile-two:
\t$(COMPILER) --events $(EVENTS) --label $@ --kind compile
link-one:
\t+$(LLINKER) --events $(EVENTS) --label $@ --kind link
link-two:
\t+$(LINKER_FOR_BUILD) --events $(EVENTS) --label $@ --kind link
'''


def record(args):
    require(args.events.is_absolute(), 'Use an absolute owned event path')
    require(args.label.startswith(args.kind + '-'), 'Event label and kind differ')
    def event(phase):
        data = json.dumps(dict(label=args.label, kind=args.kind, phase=phase,
                               time=time.monotonic_ns(), pid=os.getpid())).encode() + b'\n'
        fd = os.open(args.events, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            require(os.write(fd, data) == len(data), 'Short event write')
        finally:
            os.close(fd)
    event('start')
    if args.kind == 'compile':
        ready = args.events.with_name(args.label + '.ready')
        ready.write_text('ready\n')
        other = args.events.with_name('compile-' + ('two' if args.label == 'compile-one' else 'one') + '.ready')
        deadline = time.monotonic() + 5
        while not other.exists():
            require(time.monotonic() < deadline, 'Compile work was serialized')
            time.sleep(.01)
    time.sleep(.5)
    event('end')


def verify(path):
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    intervals = {}
    for label in ('compile-one', 'compile-two', 'link-one', 'link-two'):
        own = [row for row in rows if row['label'] == label]
        require([row['phase'] for row in own] == ['start', 'end'], 'Incomplete work: ' + label)
        intervals[label] = [row['time'] for row in own]
    require(len(rows) == 8, 'Unexpected work events')
    def overlap(first, second):
        a, b = intervals[first], intervals[second]
        return max(a[0], b[0]) < min(a[1], b[1])
    require(overlap('compile-one', 'compile-two'), 'Compile jobs did not overlap')
    require(not overlap('link-one', 'link-two'), 'Final link jobs overlapped')


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    sub = cli.add_subparsers(dest='mode', required=True)
    source = sub.add_parser('source')
    source.add_argument('before', type=Path)
    source.add_argument('after', type=Path)
    source.add_argument('--new-fixtures', type=Path)
    work = sub.add_parser('record')
    work.add_argument('--events', type=Path, required=True)
    work.add_argument('--label', choices=['compile-one', 'compile-two', 'link-one', 'link-two'], required=True)
    work.add_argument('--kind', choices=['compile', 'link'], required=True)
    result = sub.add_parser('verify')
    result.add_argument('events', type=Path)
    args = cli.parse_args()
    if args.mode == 'record':
        record(args)
    elif args.mode == 'verify':
        verify(args.events)
    else:
        before, after = args.before.read_text(), args.after.read_text()
        check(before, after)
        mutants = [after.replace(PREFIX + '$(CXX_FOR_BUILD)', '$(CXX_FOR_BUILD)'),
                   after.replace('COMPILER = $(CXX)', 'COMPILER = ' + PREFIX + '$(CXX)'),
                   after.replace(PREFIX + '$(CC)', PREFIX + '$(CXX)')]
        for mutant in mutants:
            try:
                check(before, mutant)
            except ValueError:
                continue
            raise ValueError('A missing link hook or changed compiler was accepted')
        if args.new_fixtures:
            require(args.new_fixtures.is_absolute(), 'Use an absolute new fixture path')
            args.new_fixtures.mkdir()
            for name, text in [('before.mk', before), ('after.mk', after)]:
                (args.new_fixtures / name).write_text(make_fragment(text))
        print(json.dumps(dict(status='PASS', source_mutants_rejected=len(mutants),
                              scope='Source only. No make, compiler, launcher or native input execution.')))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2)
