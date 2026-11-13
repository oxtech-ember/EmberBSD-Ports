#!/usr/bin/env python3
import argparse
import subprocess
import tempfile
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--make', required=True)
parser.add_argument('--common', required=True, type=Path)
args = parser.parse_args()
source = args.common.read_text()
start = source.index('.if ', source.index('CHECK_INTERPRETER_SKIP+=\tlib/node_modules/npm/*'))
end = source.index('\nCFLAGS.SunOS', start)
post_start = source.index('.PHONY: paxctl', end)
post_end = source.index('\n.if ${OPSYS} != "Darwin"', post_start)
fragment = source[start:end] + '\n' + source[post_start:post_end]
with tempfile.TemporaryDirectory(prefix='node-pax-matrix-') as directory:
    makefile = Path(directory) / 'Makefile'
    makefile.write_text(fragment + '\nshow:\n\t@echo FILES=${SUBST_FILES.mktools:U}\n')
    cases = [
        ('Darwin', 'Darwin', 'no', [], False),
        ('Darwin', 'NetBSD', 'yes', [], True),
        ('Linux', 'NetBSD', 'yes', [], True),
        ('NetBSD', 'NetBSD', 'no', ['out/tools/v8_gypfiles/mksnapshot.target.mk', 'out/node_mksnapshot.target.mk'], True),
        ('NetBSD', 'NetBSD', 'yes', ['out/tools/v8_gypfiles/mksnapshot.host.mk'], True),
        ('NetBSD', 'Linux', 'yes', ['out/tools/v8_gypfiles/mksnapshot.host.mk'], False),
    ]
    for host, target, cross, files, marked in cases:
        command = [args.make, '-r', '-n', '-f', str(makefile),
                   'NATIVE_OPSYS=' + host, 'OPSYS=' + target,
                   'USE_CROSS_COMPILE=' + cross, 'TOOLS_PLATFORM.paxctl=/selected/paxctl',
                   'PREFIX=/prefix', 'show', 'paxctl']
        out = subprocess.run(command, text=True, capture_output=True, check=True).stdout
        line = next(line for line in out.splitlines() if line.startswith('echo FILES='))
        actual = line.removeprefix('echo FILES=').split()
        observed = '/selected/paxctl +m /prefix/bin/node' in out
        if actual != files or observed != marked:
            raise SystemExit(f'{host}->{target} cross={cross}: files={actual}, node={observed}, expected={files}, {marked}')
        print(f'{host}->{target} cross={cross}: PASS')
