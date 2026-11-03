#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Check an installed Perl at a relocated SDK prefix, including XS and its shell."""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess


PROGRAM = r'''
use strict;
use warnings;
use Config;
use JSON::PP;
use Cwd qw(getcwd);
use File::Spec;
use POSIX qw(floor);
use Time::HiRes qw(time);
die "XS modules failed" unless floor(1.9) == 1 && time() > 0 && length(getcwd());
my $shell = qx{printf '%s' "\$KSH_VERSION"};
die "runtime shell failed" if $?;
print JSON::PP->new->encode({inc => \@INC, shell => $shell,
    config => {map { $_ => $Config{$_} } qw(prefixexp archlibexp privlibexp scriptdir targetsh useshrplib)}});
'''


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--prefix', type=Path, required=True)
    cli.add_argument('--producer-prefix', type=Path, required=True)
    cli.add_argument('--deny-producer', action='store_true', help='deny producer reads in the Darwin child process')
    args = cli.parse_args()
    prefix, original = args.prefix.resolve(strict=True), args.producer_prefix.resolve()
    if prefix == original or prefix.is_relative_to(original):
        cli.error('select a distinct relocated prefix outside the producer')
    command = [str(prefix / 'bin/perl'), '-e', PROGRAM]
    if args.deny_producer:
        if platform.system() != 'Darwin':
            cli.error('--deny-producer uses Darwin sandbox-exec')
        policy = '(version 1)(allow default)(deny file-read* (subpath ' + json.dumps(str(original)) + '))'
        command = ['/usr/bin/sandbox-exec', '-p', policy, '--', *command]
    env = {key: value for key, value in os.environ.items()
           if not key.startswith('PERL') and not key.startswith('DYLD_')}
    env.update(PATH=str(prefix / 'bin') + ':' + str(prefix / 'sbin'), LC_ALL='C')
    result = subprocess.run(command, env=env, capture_output=True, text=True)
    if result.returncode:
        raise SystemExit('Perl relocation failed: ' + result.stderr[-4096:])
    data = json.loads(result.stdout)
    for name in data['inc']:
        if not isinstance(name, str) or not Path(name).resolve().is_relative_to(prefix):
            raise SystemExit('Perl include path escapes selected prefix: ' + str(name))
    for key in ('prefixexp', 'archlibexp', 'privlibexp', 'scriptdir', 'targetsh'):
        if not Path(data['config'][key]).resolve().is_relative_to(prefix):
            raise SystemExit('Perl config path escapes selected prefix: ' + key)
    expected = subprocess.check_output([str(prefix / 'bin/mksh'), '-c', "printf '%s' \"$KSH_VERSION\""],
                                       env=env, text=True)
    if not expected or data['shell'] != expected or data['config']['useshrplib'] != 'true':
        raise SystemExit('Perl runtime shell or shared library contract differs')
    print('Perl relocation: core modules, XS, Config, include paths and selected shell passed' +
          (' with producer reads denied' if args.deny_producer else ''))


if __name__ == '__main__':
    main()
