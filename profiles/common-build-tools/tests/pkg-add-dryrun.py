#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Actual-source package replacement regression.
"""Check actual replacement functions with private metadata fixtures."""
import sys
sys.dont_write_bytecode = True
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-source', required=True)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--work', required=True, type=Path)
    parser.add_argument('--compiler', default=os.environ.get('HOST_CC', 'cc'))
    parser.add_argument('--cflag', action='append', default=[])
    parser.add_argument('--extract-only', action='store_true')
    args = parser.parse_args()
    ports = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(ports / 'profiles/development-toolchain/runtime/recipe/files'))
    import sdk_source
    sdk_source.load(args.sdk_source)
    sdk_source.install_signal_handlers()
    from emberbsd_sdk.errors import CommandError, ProcessOwnershipError
    from emberbsd_sdk.process import run_logged

    source = args.source.resolve(strict=True)
    raw = source.read_bytes()
    text = raw.decode('utf-8')
    license_match = re.search(r'/\*-\n.*?\*/', text, re.S)
    if license_match is None:
        raise ValueError('Missing source license')
    functions = []
    for name in ('preserve_meta_data_file', 'start_replacing'):
        matches = list(re.finditer(r'^static int\n' + name + r'\([^\n]*\)\n\{\n.*?^\}', text, re.M | re.S))
        if len(matches) != 1:
            raise ValueError('Expected exactly one actual function: ' + name)
        match = matches[0]
        line = text[:match.start()].count('\n') + 1
        functions.append('#line ' + str(line) + ' ' + json.dumps(str(source)) + '\n' + match[0] + '\n')
    work = args.work.absolute()
    if work.exists() or work.is_symlink():
        raise ValueError('Output already exists')
    fixture = Path(__file__).with_suffix('.c')
    fixture_raw = fixture.read_bytes()
    work.mkdir(parents=True)
    (work / 'functions.inc').write_text(license_match[0] + '\n' + '\n'.join(functions))
    shutil.copyfile(fixture, work / 'fixture.c')
    receipt = dict(source=str(source), source_sha256=hashlib.sha256(raw).hexdigest(),
                   fixture_sha256=hashlib.sha256(fixture_raw).hexdigest(),
                   status='extracted', commands=[], scope='Two complete actual functions and explicit adapters. No real package tool or target execution.')
    code = 0
    try:
        if not args.extract_only:
            flags = ['-std=c99', '-O1', '-g', '-Wall', '-Wextra', '-Werror', *args.cflag]
            command = [args.compiler, *flags, str(work / 'fixture.c'), '-o', str(work / 'fixture.host')]
            receipt['commands'].append(command)
            run_logged(command, work / 'compile.log')
            cases = work / 'cases'
            cases.mkdir()
            command = [str(work / 'fixture.host'), str(cases)]
            receipt['commands'].append(command)
            run_logged(command, work / 'run.log')
            receipt['status'] = 'actual-source-cases-pass'
        if source.read_bytes() != raw or fixture.read_bytes() != fixture_raw:
            raise ValueError('Source changed during the regression')
    except CommandError as error:
        code = error.returncode
        receipt.update(status='command-failed', error=str(error), returncode=code)
    except ProcessOwnershipError as error:
        code = 1
        receipt.update(status='ownership-unproven', sid=error.sid, error=str(error))
    except (OSError, ValueError) as error:
        code = 1
        receipt.update(status='validation-failed', error=str(error))
    finally:
        (work / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(receipt['status'])
    return code


if __name__ == '__main__':
    sys.exit(main())
