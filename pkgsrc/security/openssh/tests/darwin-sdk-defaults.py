#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Exercise the compiled OpenSSH defaults in a disposable Darwin prefix."""
import argparse
import getpass
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--prefix", type=Path, required=True,
                    help="qualified Darwin prefix containing OpenSSH and its libraries")
parser.add_argument("--work-parent", type=Path, required=True)
parser.add_argument("--trust-probe", type=Path, required=True,
                    help="WRKSRC/darwin-trust-probe from check-darwin-sdk-trust")
args = parser.parse_args()
trust = args.trust_probe.resolve(strict=True)
if platform.system() != "Darwin":
    parser.error("this regression uses the Darwin executable-path interface")
original = args.prefix.resolve(strict=True)
with tempfile.TemporaryDirectory(prefix="openssh-defaults-", dir=args.work_parent) as td:
    trial = Path(td).resolve()
    for entry in ["bin/ssh", "bin/ssh-keygen", "sbin/sshd",
                  "libexec/sshd-session", "libexec/sshd-auth"]:
        dest = trial / entry
        dest.parent.mkdir(exist_ok=True)
        shutil.copy2(original / entry, dest)
    (trial / "lib").symlink_to(original / "lib", target_is_directory=True)
    (trial / "var/chroot/sshd").mkdir(parents=True)
    conf = trial / "etc/ssh"
    conf.mkdir(parents=True)
    (conf / "ssh_config").write_text("Host ember-defaults-test\n    Port 28242\n")
    explicit = trial / "external-config"
    explicit.write_text("Host ember-defaults-test\n    Port 31459\n")
    server = trial / "test-sshd-config"
    server.touch()
    home = trial / "home"
    home.mkdir()
    key = trial / "host-key"
    environment = dict(os.environ, HOME=str(home), LC_ALL="C")
    # OpenSSH selects the per-user configuration from the real account record.
    policy = "(version 1)(allow default)(deny file-read* (subpath " + json.dumps(
        str(Path.home() / ".ssh")) + "))"

    def run(*command):
        return subprocess.run(["/usr/bin/sandbox-exec", "-p", policy, *command],
                              env=environment, check=True, text=True,
                              stdout=subprocess.PIPE).stdout

    def settings(text):
        options = {}
        for line in text.splitlines():
            key, separator, value = line.partition(" ")
            if separator:
                options[key.lower()] = value
        return options

    client = settings(run(trial / "bin/ssh", "-G", "ember-defaults-test"))
    assert client["port"] == "28242"
    assert str(conf / "ssh_known_hosts") in client["globalknownhostsfile"].split()
    assert client["xauthlocation"] == str(trial / "bin/xauth")
    custom = settings(run(trial / "bin/ssh", "-F", explicit, "-G", "ember-defaults-test"))
    assert custom["port"] == "31459"
    run(trial / "bin/ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", key)
    daemon = settings(run(trial / "sbin/sshd", "-T", "-f", server, "-h", key))
    assert daemon["sshdsessionpath"] == str(trial / "libexec/sshd-session")
    assert daemon["sshdauthpath"] == str(trial / "libexec/sshd-auth")
    assert daemon["pidfile"] == str(trial / "var/run/sshd.pid")

    def check_trust(mode, path, accepted, diagnostic=""):
        result = subprocess.run([trust, mode, path], text=True, capture_output=True)
        assert (result.returncode == 0) == accepted, (mode, path, result.stderr)
        assert diagnostic in result.stderr, (mode, path, result.stderr)

    check_trust("required", "/bin/ls", True)
    check_trust("required", "/etc/hosts", True)
    check_trust("optional", "/bin/.ember-missing-trust-fixture", True)
    check_trust("optional", "/private/tmp/.ember-missing-trust-fixture", False,
                "unsafe privileged OpenSSH path")
    acl_file = trial / "acl-data"
    acl_file.touch()
    check_trust("acl", acl_file, True)
    grant = "user:" + getpass.getuser() + " allow write"
    subprocess.run(["/bin/chmod", "+a", grant, acl_file], check=True)
    check_trust("acl", acl_file, False, "unsafe privileged OpenSSH installation ACL")
    inherited = trial / "acl-directory"
    inherited.mkdir()
    for flags, allowed in [
        ("file_inherit", {"acl", "new-directory"}),
        ("directory_inherit", {"acl", "new-file"}),
        ("file_inherit,limit_inherit", {"acl", "new-directory", "new-subtree"}),
    ]:
        subprocess.run(["/bin/chmod", "+a", grant + "," + flags + ",only_inherit", inherited],
                       check=True)
        for mode in ("acl", "new-file", "new-directory", "new-subtree"):
            check_trust(mode, inherited, mode in allowed,
                        "" if mode in allowed else "unsafe privileged OpenSSH installation ACL")
        subprocess.run(["/bin/chmod", "-N", inherited], check=True)
print("Relocated OpenSSH configuration, helpers, privilege boundaries and inherited ACLs passed.")
