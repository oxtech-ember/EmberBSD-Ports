#!/usr/bin/env python3
"""Run independent libxslt API cases. Signals and nonzero exits fail a case."""
import argparse
import json
import pathlib
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('executable', type=pathlib.Path)
parser.add_argument('output', type=pathlib.Path)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
cases = [f'{prefix}-{kind}' for prefix in ('registered', 'xpath')
         for kind in ('persist', 'local', 'tmp')]
cases += ['release-null', 'release-cache', 'release-full', 'null-rvt',
          'id-cleanup', 'exslt']
results = []
for case in cases:
    try:
        p = subprocess.run([str(args.executable.resolve()), case],
                           capture_output=True, text=True, timeout=60)
        row = {'case': case, 'returncode': p.returncode,
               'stdout': p.stdout, 'stderr': p.stderr,
               'passed': p.returncode == 0}
    except subprocess.TimeoutExpired as exc:
        row = {'case': case, 'passed': False, 'error': str(exc)}
    results.append(row)
    print(('PASS' if row['passed'] else 'FAIL'), case, flush=True)
report = {'cases': results, 'passed': sum(r['passed'] for r in results),
          'total': len(results)}
(args.output / 'results.json').write_text(json.dumps(report, indent=2)+'\n')
raise SystemExit(0 if report['passed'] == report['total'] else 1)
