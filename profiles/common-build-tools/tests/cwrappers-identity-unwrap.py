#!/usr/bin/env python3
"""Exercise libtool metadata unwrap with real selected cwrappers."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--wrapper', type=Path, required=True)
p.add_argument('--true', type=Path, required=True)
p.add_argument('--cc-wrapper', type=Path, required=True)
p.add_argument('--cc', type=Path, required=True)
p.add_argument('--consumer', type=Path, required=True)
a = p.parse_args()
with tempfile.TemporaryDirectory(prefix='cwrappers-unwrap-') as tmp:
    root = Path(tmp)
    host = root / 'host'
    stage = root / 'stage'
    wrong = root / 'wrong'
    config = root / 'config'
    config.mkdir()
    (root / '.libs').mkdir()
    wrapper = root / 'shlibtool'
    wrapper.symlink_to(a.wrapper.resolve())
    def run(rules, dependencies):
        (config / 'shlibtool').write_text('worklog=/dev/null\nexec_path=' + str(wrapper) + '\nexec=' + str(a.true) + '\n' +
            ''.join('unwrap=' + src + ':' + dst + '\n' for src, dst in rules))
        for name in ('libprobe.la', '.libs/libprobe.lai'):
            (root / name).write_text("dependency_libs='" + dependencies + "'\n")
        env = dict(os.environ, CWRAPPERS_CONFIG_DIR=str(config))
        subprocess.run([str(wrapper), '--mode=link', '-o', 'libprobe.la'],
                       cwd=root, env=env, check=True, timeout=5)
        return (root / '.libs/libprobe.lai').read_text()
    # The first matching no-op must terminate the rule search for both forms.
    identity = run([(str(host), str(host)), (str(host), str(wrong))],
                   '-L' + str(host / 'lib') + ' ' + str(host / 'lib/libfoo.la'))
    assert str(wrong) not in identity and '-L' + str(host / 'lib') in identity, identity
    assert str(host / 'lib/libfoo.la') in identity, identity
    # Rewriting a real stage path terminates at the selected logical prefix.
    chain = run([(str(stage), str(host)), (str(host), str(host)),
                 (str(host), str(wrong))],
                '-L' + str(stage / 'lib') + ' -L' + str(stage / 'lib') + ' ' + str(stage / 'lib/libfoo.la'))
    assert str(wrong) not in chain and str(stage) not in chain, chain
    assert chain.count('-L' + str(host / 'lib')) == 1 and '-lfoo' in chain, chain
    # A nested provider has precedence over its parent.
    nested = run([(str(stage / 'nested'), str(host / 'nested')),
                  (str(stage), str(host))], '-L' + str(stage / 'nested/lib'))
    assert '-L' + str(host / 'nested/lib') in nested, nested
    cc = root / 'cc'
    cc.symlink_to(a.cc_wrapper.resolve())
    (config / 'cc').write_text('worklog=/dev/null\nexec_path=' + str(cc) +
                               '\nexec=' + str(a.cc) + '\n')
    env = dict(os.environ, CWRAPPERS_CONFIG_DIR=str(config))
    exe = root / 'consumer'
    subprocess.run([str(cc), '-Werror', str(a.consumer), '-o', str(exe)],
                   env=env, cwd=root, check=True, timeout=30)
    subprocess.run([str(exe)], env=env, check=True, timeout=5)
print('PASS: identity, .la, chain, nested, dedup and ordinary C compile/run')
