#!/usr/bin/env python3
"""Exercise actual VLC hook bodies using a selected shell and fake generator."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("--shell", required=True, help="absolute path to selected host shell")
args = parser.parse_args()
shell = Path(args.shell)
assert shell.is_absolute() and shell.is_file()
patch = Path(__file__).resolve().parents[1] / "patches/vlc-ffmpeg9.patch"
text = patch.read_text()
def hook(name):
    section = text.split("+++ b/multimedia/vlc/" + name + "\n", 1)[1].split("\n--- ", 1)[0]
    return "\n".join(line[1:] for line in section.splitlines()[1:] if line.startswith("+")) + "\n"
with tempfile.TemporaryDirectory(prefix="vlc hook ") as temp:
    prefix = Path(temp) / "prefix space"
    plugins = prefix / "lib/vlc/plugins"
    plugins.mkdir(parents=True)
    gen = prefix / "lib/vlc/vlc-cache-gen"
    log = prefix / "calls"
    cache = plugins / "plugins.dat"
    gen.write_text(f"#!{shell}\n" + """printf '%s\n' call >> "$PKG_PREFIX/calls"
case "$GEN_MODE" in
 valid|fail) printf cache > "$1/plugins.dat" ;;
 empty) : > "$1/plugins.dat" ;;
 absent) : ;;
esac
[ "$GEN_MODE" != fail ]
""")
    gen.chmod(0o755)
    env = dict(os.environ, PKG_PREFIX=str(prefix))
    def run(name, stage, mode="valid"):
        e = dict(env, STAGE=stage, GEN_MODE=mode)
        return subprocess.run([str(shell), "-c", hook(name)], env=e, capture_output=True)
    assert run("INSTALL", "PRE-INSTALL").returncode == 0 and not log.exists()
    for initial in (None, "", "old cache"):
        cache.unlink(missing_ok=True)
        if initial is not None: cache.write_text(initial)
        assert run("INSTALL", "POST-INSTALL").returncode == 0
        assert cache.read_text() == "cache"
    assert log.read_text().count("call") == 3
    for mode in ("fail", "empty", "absent"):
        cache.write_text("old cache")
        assert run("INSTALL", "POST-INSTALL", mode).returncode != 0
        assert not cache.exists()
    gen.unlink()
    assert run("INSTALL", "POST-INSTALL").returncode != 0 and not cache.exists()
    cache.write_text("cache")
    assert run("DEINSTALL", "POST-DEINSTALL").returncode == 0 and cache.read_text() == "cache"
    assert run("DEINSTALL", "DEINSTALL").returncode == 0 and not cache.exists()
    assert run("DEINSTALL", "DEINSTALL").returncode == 0
print("VLC cache hook lifecycle passed (host shell; target execution untested)")
