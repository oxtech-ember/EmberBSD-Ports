#!/usr/bin/env python3
"""Check a real installed Sway compositor and IPC on an explicit SSH target."""
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
import argparse
import json
from pathlib import Path
import shlex
import subprocess
import time
import uuid

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--host", required=True)
parser.add_argument("--results", type=Path, required=True)
parser.add_argument("--renderer", choices=["gles2", "pixman"], required=True)
args = parser.parse_args()
assert not args.results.exists(), "Use a new result directory"
args.results.mkdir(parents=True)
remote = "/tmp/emberbsd-sway-headless-" + uuid.uuid4().hex
runtime = remote + "/runtime"
pid = None
failure = None

def ssh(command, data=None, timeout=30):
    return subprocess.run(["ssh", "-o", "ConnectTimeout=15", args.host, command],
                          input=data, capture_output=True, timeout=timeout)

def checked(command, data=None):
    result = ssh(command, data)
    assert result.returncode == 0, (command, result.stderr)
    return result.stdout

identity = checked("uname -srm; id -u nobody; id -g nobody").decode().splitlines()
assert identity[0].startswith("NetBSD ")
uid, gid = map(int, identity[1:])
(args.results / "target.txt").write_bytes(checked(
    "uname -srm; /usr/sbin/pkg_info -e sway; /usr/sbin/pkg_info -e wlroots"))
checked("umask 077; mkdir " + shlex.quote(remote))
socket = None
results = {}

def process_exit():
    path = shlex.quote(remote + "/exit.status")
    result = ssh("if [ -f " + path + " ]; then cat " + path + "; else exit 3; fi")
    assert result.returncode in (0, 3), ("exit status query", result.stderr)
    return int(result.stdout) if result.returncode == 0 else None

def wait_for_exit(seconds, required=True):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        status = process_exit()
        if status is not None:
            return status
        time.sleep(0.1)
    if required:
        raise AssertionError("Sway supervisor did not record process termination")
    return None

try:
    checked("umask 077; mkdir " + shlex.quote(runtime))
    configuration = b"output * mode 640x480\nfont monospace 10\n"
    checked("cat > " + shlex.quote(remote + "/config"), configuration)
    checked(shlex.join(["/usr/sbin/chown", "-R", f"{uid}:{gid}", remote]))
    command = shlex.join(["env", "PATH=/usr/pkg/bin:/usr/bin:/bin", "HOME=" + remote,
        "XDG_RUNTIME_DIR=" + runtime, "XDG_CONFIG_HOME=" + remote,
        "WLR_BACKENDS=headless", "WLR_HEADLESS_OUTPUTS=1", "WLR_LIBINPUT_NO_DEVICES=1",
        "WLR_RENDERER=" + args.renderer, "LIBGL_ALWAYS_SOFTWARE=1",
        "WLR_RENDERER_ALLOW_SOFTWARE=1", "/usr/pkg/bin/sway", "--debug", "--config", remote + "/config"])
    # Keep a parent that waits for Sway and records its actual exit status.
    supervise = ("cd " + shlex.quote(remote) + "; " + command + " </dev/null >" +
        shlex.quote(remote + "/sway.log") + " 2>&1 & child=$!; " +
        "printf '%s\\n' \"$child\" >" + shlex.quote(remote + "/pid") +
        "; wait \"$child\"; status=$?; printf '%s\\n' \"$status\" >" +
        shlex.quote(remote + "/exit.status") + "; exit \"$status\"")
    launch = shlex.join(["su", "-m", "nobody", "-c", supervise])
    checked(launch + " </dev/null >" + shlex.quote(remote + "/supervisor.log") + " 2>&1 &")
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if pid is None:
            found = ssh("cat " + shlex.quote(remote + "/pid"))
            assert found.returncode in (0, 1), ("PID query", found.stderr)
            if found.returncode == 0:
                pid = int(found.stdout)
                assert pid > 1
        matches = checked("find " + shlex.quote(runtime) + " -type s -name 'sway-ipc.*.sock'").decode().splitlines()
        if matches and pid is not None:
            assert len(matches) == 1
            socket = matches[0]
            break
        if process_exit() is not None:
            break
        time.sleep(0.2)
    assert socket is not None, "Sway did not establish its real IPC socket; inspect sway.log"

    def ipc(label, kind, command=None):
        argv = ["/usr/pkg/bin/swaymsg", "-s", socket, "-r", "-t", kind]
        if command is not None:
            argv.append(command)
        result = ssh(shlex.join(argv))
        (args.results / (label + ".stdout")).write_bytes(result.stdout)
        (args.results / (label + ".stderr")).write_bytes(result.stderr)
        assert result.returncode == 0, (label, result.stderr)
        value = json.loads(result.stdout)
        results[label] = value
        return value

    version = ipc("version", "get_version")
    assert version["major"] == 1 and version["minor"] == 12
    outputs = ipc("initial-outputs", "get_outputs")
    assert len(outputs) == 1 and outputs[0]["active"]
    assert outputs[0]["current_mode"]["width"] == 640
    assert outputs[0]["current_mode"]["height"] == 480
    status = ipc("workspace-command", "command", "workspace 7; workspace 8; workspace 7")
    assert len(status) == 3 and all(item["success"] for item in status)
    workspaces = ipc("workspaces", "get_workspaces")
    assert any(ws["focused"] and ws["name"] == "7" for ws in workspaces)
    status = ipc("create-output", "command", "create_output")
    assert all(item["success"] for item in status)
    outputs = ipc("two-outputs", "get_outputs")
    assert len(outputs) == 2 and all(output["active"] for output in outputs)
    tree = ipc("tree", "get_tree")
    assert tree["type"] == "root"
    status = ipc("exit", "command", "exit")
    assert len(status) == 1 and status[0]["success"]
    results["process_exit_status"] = wait_for_exit(15)
    assert results["process_exit_status"] == 0, "IPC exit did not stop Sway successfully"
except BaseException as error:
    failure = {"type": type(error).__name__, "message": str(error)}
    raise
finally:
    cleanup_error = None
    removed = False
    try:
        for name in ("sway.log", "supervisor.log"):
            log = ssh("cat " + shlex.quote(remote + "/" + name))
            (args.results / name).write_bytes(log.stdout + log.stderr)
        if pid is not None:
            # An IPC error can arrive while orderly display teardown is active.
            status = wait_for_exit(15, required=False)
            if status is None:
                actual = checked(shlex.join(["ps", "-p", str(pid), "-o", "pid=",
                    "-o", "ppid=", "-o", "uid=", "-o", "command="])).decode()
                results["cleanup_process_identity"] = actual
                fields = actual.split(None, 3)
                assert len(fields) == 4 and int(fields[0]) == pid and int(fields[2]) == uid
                assert remote + "/config" in fields[3], "Refuse to stop a different process"
                checked(shlex.join(["kill", "-TERM", str(pid)]))
                status = wait_for_exit(15)
            results["cleanup_exit_status"] = status
        checked("rm -rf " + shlex.quote(remote) + "; test ! -e " + shlex.quote(remote))
        removed = True
    except Exception as error:
        cleanup_error = {"type": type(error).__name__, "message": str(error)}
    (args.results / "receipt.json").write_text(json.dumps({"target": identity[0],
        "renderer": args.renderer, "uid": uid, "pid": pid, "checks": results,
        "failure": failure, "cleanup_error": cleanup_error,
        "remote_work_removed": removed}, indent=2) + "\n")
    if cleanup_error is not None and failure is None:
        raise AssertionError(cleanup_error)
print("PASS: real Sway 1.12 headless outputs, workspace commands, tree and orderly IPC exit")
