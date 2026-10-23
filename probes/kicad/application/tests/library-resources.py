#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the real upstream symbol packer and its default table transport."""
import argparse
import contextlib
import hashlib
import io
import json
import logging
from pathlib import Path
import runpy
import sys


def invoke(script, arguments):
    """Run the unchanged upstream CLI in this Python process. Start no child."""
    previous_argv = sys.argv
    root = logging.getLogger()
    previous_handlers = root.handlers[:]
    previous_level = root.level
    root.handlers.clear()
    stdout, stderr = io.StringIO(), io.StringIO()
    status = 0
    try:
        sys.argv = [str(script), *map(str, arguments)]
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                # The upstream CLI uses the site-provided exit helper.
                # Supply its documented SystemExit behavior when this test uses -S.
                runpy.run_path(str(script), run_name='__main__',
                               init_globals={'exit': sys.exit})
            except SystemExit as error:
                status = error.code
    finally:
        sys.argv = previous_argv
        for handler in root.handlers:
            handler.close()
        root.handlers[:] = previous_handlers
        root.setLevel(previous_level)
    return dict(status=status, stdout=stdout.getvalue(), stderr=stderr.getvalue())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack-script', type=Path, required=True)
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    assert sys.version_info[:2] == (3, 15), 'Use Python 3.15'
    script = args.pack_script.resolve(strict=True)
    digest = hashlib.sha256(script.read_bytes()).hexdigest()
    assert digest == args.expected_sha256, 'Upstream packer source differs'
    work = args.work
    assert work.is_absolute() and work.resolve() == work and not work.exists()
    work.mkdir()
    library = work/'Fixture.kicad_symdir'
    library.mkdir()
    header = '(kicad_symbol_lib\n\t(version 20241209)\n'
    a = '\t(symbol "A"\n\t\t(property "Reference" "U")\n\t)\n'
    b = '\t(symbol "B"\n\t\t(extends "A")\n\t)\n'
    (library/'B.kicad_sym').write_text(header+b+')\n')
    (library/'A.kicad_sym').write_text(header+a+')\n')
    original = '(sym_lib_table\n  (lib (name "Fixture")(type "KiCad")(uri "${KICAD10_SYMBOL_DIR}/Fixture.kicad_symdir")(options "")(descr ""))\n)\n'
    table = work/'sym-lib-table'
    table.write_text(original)
    good = invoke(script, ['--input', library, '--output', work/'good', '--table', table])
    assert good['status'] == 0
    assert (work/'good/Fixture.kicad_sym').read_text() == header+a+b+')\n'
    assert (work/'good/sym-lib-table').read_text() == original.replace('.kicad_symdir', '.kicad_sym')
    invalid = work/'invalid-table'
    invalid.write_text('(unrelated_table)\n')
    bad = invoke(script, ['--input', library, '--output', work/'bad', '--table', invalid])
    assert bad['status'] == 1 and 'does not appear to be a valid symbol library table' in bad['stderr']
    absent = invoke(script, ['--output', work/'absent'])
    assert absent['status'] == 2 and 'No input files or folders specified' in absent['stderr']
    assert hashlib.sha256(script.read_bytes()).hexdigest() == digest
    result = dict(status='PASS', upstream_script_sha256=digest,
                  cases={'packed_symbols_and_table': good, 'invalid_table': bad,
                         'missing_input': absent},
                  limits='Three source CLI cases in one Python process. No CMake, package, target program, full library data or GUI acceptance.')
    (work/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
