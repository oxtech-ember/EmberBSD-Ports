"""Real flock/exec tests for the Browser-owned profile helper."""
import argparse, json, os, pathlib, subprocess, sys, tempfile, time
parser = argparse.ArgumentParser()
parser.add_argument('--helper', type=pathlib.Path, required=True)
P = parser.parse_args().helper.resolve(strict=True)
L = json.loads(P.with_name('webapp-layout.json').read_text())
with tempfile.TemporaryDirectory(prefix='webapp-profile-test-') as tmp:
    root = pathlib.Path(tmp); home = root / 'home'; home.mkdir(mode=0o700)
    config = home / '.config'; config.mkdir(mode=0o700)
    env = dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(config))
    app = config / L['application']; normal = app / L['normal']; private = app / L['private']; locks = app / L['locks']
    stub = root / 'stub.py'; ready = root / 'ready'
    stub.write_text('import os,sys,time\nopen(os.environ["READY"],"w").write(str(os.getpid()))\ntime.sleep(120)\n')
    env['READY'] = str(ready)
    def invoke(*args, extra=None):
        return subprocess.run([sys.executable, str(P), sys.executable, str(stub), *args], env=extra or env, capture_output=True, text=True, timeout=10)
    def clear(ident='test'): return invoke('--webapp-clear='+ident)
    def profiles():
        for ns in (normal, private):
            (ns / 'test').mkdir(parents=True, exist_ok=True); (ns / 'test' / 'data').write_text('retain')
    def launch(private_mode):
        if ready.exists(): ready.unlink()
        args = ['--webapp-id=test'] + (['--webapp-private'] if private_mode else [])
        proc = subprocess.Popen([sys.executable, str(P), sys.executable, str(stub), *args], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        end = time.monotonic()+10
        while not ready.exists() and proc.poll() is None and time.monotonic()<end: time.sleep(.02)
        assert ready.exists() and int(ready.read_text()) == proc.pid, 'exec child did not start'
        return proc
    profiles(); (app/'ordinary').write_text('ordinary'); (normal/'other').mkdir(); (normal/'other'/'data').write_text('other')
    for mode in (False, True):
        proc = launch(mode)
        try:
            r = clear(); assert r.returncode != 0 and 'Close this web app' in r.stderr
            assert (normal/'test'/'data').exists() and (private/'test'/'data').exists()
        finally:
            proc.terminate(); proc.wait(timeout=10)
            proc.stdout.close(); proc.stderr.close()
    inode = (locks/'test').stat().st_ino
    assert clear().returncode == 0
    assert not (normal/'test').exists() and not (private/'test').exists()
    assert (app/'ordinary').read_text() == 'ordinary' and (normal/'other'/'data').read_text() == 'other'
    assert clear().returncode == 0 and (locks/'test').stat().st_ino == inode
    for bad in ('../escape', '', 'a/b', 'a'*65): assert clear(bad).returncode != 0
    assert invoke('--webapp-clear=test', extra=dict(env, XDG_CONFIG_HOME='relative')).returncode != 0
    no_home = {k: v for k, v in env.items() if k not in ('HOME', 'XDG_CONFIG_HOME')}
    assert invoke('--webapp-clear=test', extra=no_home).returncode != 0
    only_xdg = dict(no_home, XDG_CONFIG_HOME=str(config))
    assert invoke('--webapp-clear=test', extra=only_xdg).returncode == 0
    profiles()
    for ns in (normal, private):
        profiles(); (ns/'test'/'SingletonLock').symlink_to('stale')
        assert clear().returncode != 0
        assert (normal/'test'/'data').exists() and (private/'test'/'data').exists()
        (ns/'test'/'SingletonLock').unlink()
    for ns in (normal, private):
        (ns/'test').rename(ns/'saved'); (ns/'test').symlink_to(ns/'saved', target_is_directory=True)
        assert clear().returncode != 0
        assert (normal/'test'/'data').exists() and (private/'test'/'data').exists()
        (ns/'test').unlink(); (ns/'saved').rename(ns/'test')
    for ns in (normal, private):
        ns.rename(app/'saved'); ns.symlink_to(app/'saved', target_is_directory=True)
        assert clear().returncode != 0
        assert (normal/'test'/'data').exists() and (private/'test'/'data').exists()
        ns.unlink(); (app/'saved').rename(ns)
    (locks/'test').unlink(); (locks/'test').symlink_to(root/'outside')
    assert clear().returncode != 0 and (normal/'test'/'data').exists() and (private/'test'/'data').exists()
print('PASS: real shared flock across exec; both-mode clear exclusion, safe clear, stable inode, invalid paths and symlink/singleton refusal')
