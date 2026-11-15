"""Regression: application-mode startup must not change the ordinary profile."""
import argparse
import json
import os
import shutil
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--host-prefix', type=Path, required=True)
parser.add_argument('--launcher', type=Path, required=True)
args = parser.parse_args()
prefix_tools = args.host_prefix.resolve(strict=True)
shell = prefix_tools / 'bin/mksh'
python = prefix_tools / 'bin/python3.15'
for tool in (shell, python):
    if not tool.is_file() or not os.access(tool, os.X_OK):
        parser.error('missing selected native tool: ' + str(tool))
script = args.launcher.read_text()
with tempfile.TemporaryDirectory(prefix='webapp-wrapper-') as temporary:
    root = Path(temporary)
    prefix = root / 'prefix'
    (prefix / 'bin').mkdir(parents=True)
    (prefix / 'lib/ember-browser').mkdir(parents=True)
    for name in ('webapp-profile.py', 'webapp-layout.json'):
        shutil.copyfile(args.launcher.parent / name, prefix / 'lib/ember-browser' / name)
    (prefix / 'bin/python3.15').symlink_to(python)
    stub = prefix / 'bin/electron'
    stub.write_text('#!' + str(shell) + '\nprintf "%s\\n" "$@" > "$CAPTURE"\n')
    stub.chmod(0o755)
    launcher = root / 'blanc.sh'
    launcher.write_text(script.replace('@PREFIX@', str(prefix)))
    fixture_home = root / 'home'
    config = fixture_home / '.config/Ember Browser'
    config.mkdir(parents=True)
    state = config / 'Local State'
    cache = config / 'GPUCache'
    cache.mkdir()
    (cache / 'sentinel').write_text('retain')
    original = {'windowStates': {'old': {'left': 0, 'top': 0, 'right': 0, 'bottom': 0}},
                'other': 'retained'}
    state.write_text(json.dumps(original))
    capture = root / 'args'
    environment = {'HOME': str(fixture_home), 'CAPTURE': str(capture),
                   'PATH': str(prefix_tools / 'bin') + ':' + str(prefix_tools / 'gnu/bin')}
    def run(arguments):
        result = subprocess.run([str(shell), str(launcher), *arguments], env=environment,
                                capture_output=True, text=True, timeout=20)
        assert result.returncode == 0, result.stderr
        return capture.read_text().splitlines()
    valid = ['--webapp-id=example', '--webapp-url=https://example.com/path?q=a%20b',
             '--webapp-name=Пример']
    actual = run(valid)
    assert (cache / 'sentinel').read_text() == 'retain'
    assert json.loads(state.read_text()) == original
    assert not (config / 'Local State.bak-ozone-x11').exists()
    assert actual[-3:] == valid
    assert '--ozone-platform=x11' in actual and '--in-process-gpu' in actual
    invalid = subprocess.run([str(shell), str(launcher), '--webapp-invalid'], env=environment, capture_output=True, text=True, timeout=20)
    assert invalid.returncode != 0, 'invalid WebApp request must fail'
    assert cache.exists() and json.loads(state.read_text()) == original
    run([])
    assert not cache.exists()
    assert json.loads(state.read_text()) == {'other': 'retained'}
    assert json.loads((config / 'Local State.bak-ozone-x11').read_text()) == original
print('PASS: WebApp preserves ordinary profile; ordinary recovery and launcher flags retained')
