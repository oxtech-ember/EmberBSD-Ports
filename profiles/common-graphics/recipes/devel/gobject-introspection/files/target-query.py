#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), ported from the EmberBSD Ruby launcher.
"""Run GI queries with verified EmberBSD providers and a real SSH target."""

import atexit
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import signal
import shutil
import subprocess
import sys
import tempfile


class QueryError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise QueryError(message)


def digest(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inside(path, root):
    return path == root or path.startswith(root + "/")


def canonical(value):
    return str(Path(value).resolve(strict=True))


def status_of(result):
    return result.returncode if result.returncode >= 0 else 1


def capture(command, *, data=None, merged=True):
    try:
        return subprocess.run(command, input=data, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT if merged else subprocess.PIPE,
                              timeout=180, check=False)
    except subprocess.TimeoutExpired as error:
        raise QueryError("host command timed out: " + command[0]) from error


def main(args):
    with open(os.environ["EMBERBSD_GI_QUERY_CONFIG"], encoding="utf-8") as stream:
        config = json.load(stream)
    target = config.get("target", "aarch64")
    targets = {"aarch64": ("aarch64", "AArch64"),
               "amd64": ("x86_64", "Advanced Micro Devices X86-64")}
    require(target in targets, "unsupported GI target")
    processor, machine = targets[target]
    require(os.environ.get("EMBERBSD_GI_TARGET", target) == target,
            "configuration differs from recipe target")

    def absolute(key):
        value = config[key]
        require(isinstance(value, str) and value.startswith("/"), key + " must be absolute")
        return canonical(value)

    base, sysroot, cache, readelf = map(absolute, ("build_root", "sysroot", "cache", "readelf"))
    require(os.path.isfile(readelf) and os.access(readelf, os.X_OK), "readelf is not executable")
    roots = (base, sysroot)
    require(not inside(base, sysroot) and not inside(sysroot, base), "build/sysroot overlap")
    require(not inside(cache, sysroot) and not inside(sysroot, cache), "cache overlaps providers")
    host = config["ssh"]
    require(isinstance(host, str) and re.fullmatch(
        r"(?:[A-Za-z0-9_][A-Za-z0-9_.-]*@)?[A-Za-z0-9][A-Za-z0-9_.-]*", host),
        "invalid SSH destination")
    ssh = ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
           "-o", "ConnectTimeout=5", "-o", "ServerAliveInterval=10",
           "-o", "ServerAliveCountMax=3"]
    if "host_key_alias" in config:
        alias = config["host_key_alias"]
        require(isinstance(alias, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", alias),
                "invalid host key alias")
        ssh += ["-o", "HostKeyAlias=" + alias]
    ssh.append(host)
    if args and args[0] == "--check":
        require(len(args) in (4, 5), "usage: --check WORKDIR SYSROOT READELF [aarch64|amd64]")
        workdir, target_root, tool = map(canonical, args[1:4])
        expected = args[4] if len(args) == 5 else "aarch64"
        require(inside(workdir, base) and target_root == sysroot and tool == readelf and expected == target,
                "configuration differs from recipe")
        print("PASS: GI query configuration matches the selected work, sysroot and readelf")
        return 0

    execute = bool(args and args[0] == "--execute")
    if execute:
        args = args[1:]
    completed = [False]
    if execute and "EMBERBSD_GI_FAILURE_MARKER" in os.environ:
        marker = os.environ["EMBERBSD_GI_FAILURE_MARKER"]
        require(marker.startswith("/") and inside(canonical(os.path.dirname(marker)), base)
                and not os.path.islink(marker), "failure marker outside build root")

        def record_failure():
            if not completed[0]:
                try:
                    with open(marker, "x", encoding="utf-8", opener=lambda p, f: os.open(p, f, 0o600)) as stream:
                        stream.write("Target query did not complete with verified execution and cleanup.\n")
                except FileExistsError:
                    pass
        atexit.register(record_failure)

    require(bool(args), "binary required")
    program, *arguments = args
    if "/" not in program:
        require(execute and program == "getconf", "unsupported target command: " + program)
        exe = sysroot + "/usr/bin/getconf"
        require(os.path.isfile(exe), "target command missing from sysroot: " + program)
        require(not os.path.islink(exe) and canonical(exe) == exe,
                "target command is not a sysroot regular file: " + program)
    else:
        exe = canonical(program)
        require(inside(exe, base), "binary outside build root")
    require(execute or not arguments or (len(arguments) == 1 and arguments[0].startswith("--introspect-dump=")),
            "only an optional introspect-dump argument is supported")
    in_path = out_path = None
    if not execute and arguments:
        paths = arguments[0].removeprefix("--introspect-dump=").split(",", 1)
        require(len(paths) == 2 and all(p.startswith("/") for p in paths), "invalid dump paths")
        in_path, out_path = canonical(paths[0]), paths[1]
        require(inside(in_path, base) and inside(canonical(os.path.dirname(out_path)), base),
                "dump paths outside build root")
        require(not os.path.lexists(out_path), "dump output already exists")
    work = Path(tempfile.mkdtemp(prefix="gi-query-", dir=cache))
    stage = work / "stage"
    (stage / "lib").mkdir(parents=True)

    def run(name, *command, data=None):
        result = capture(list(command), data=data)
        (work / (name + ".log")).write_bytes(result.stdout)
        require(result.returncode == 0, f"{name} failed ({status_of(result)}); see {work}")
        return result.stdout

    def mapdir(path):
        if os.path.isdir(path):
            resolved = canonical(path)
            if any(inside(resolved, root) for root in roots):
                return resolved
        if any(inside(path, root) for root in roots):
            return path
        return sysroot + path if path.startswith("/") else os.path.abspath(path)

    search = config.get("library_dirs", []) + os.environ.get("LD_LIBRARY_PATH", "").split(":")
    search = list(dict.fromkeys(mapdir(p) for p in search if p))
    defaults = [mapdir(p) for p in ("/usr/pkg/gcc16/lib", "/usr/pkg/lib", "/usr/lib", "/lib")]
    files, pending = {}, [exe]
    while pending:
        file = pending.pop(0)
        header = capture([readelf, "-h", file])
        text = header.stdout.decode("utf-8", errors="replace")
        actual = re.search(r"^\s*Machine:\s*(.*?)\s*$", text, re.M)
        require(header.returncode == 0 and actual and actual[1] == machine
                and re.search(r"Class:.*ELF64", text) and re.search(r"Data:.*little endian", text),
                f"not little-endian {processor} ELF64: {file}")
        dynamic = capture([readelf, "-d", file])
        require(dynamic.returncode == 0, "readelf failed")
        text = dynamic.stdout.decode("utf-8", errors="replace")
        localdirs = [mapdir(p.replace("${ORIGIN}", os.path.dirname(file)).replace("$ORIGIN", os.path.dirname(file)))
                     for paths in re.findall(r"\((?:RPATH|RUNPATH)\).*\[(.*?)\]", text)
                     for p in paths.split(":")]
        for name in re.findall(r"\(NEEDED\).*\[(.*?)\]", text):
            require(re.fullmatch(r"[a-zA-Z0-9._+-]+", name), "unsafe SONAME")
            candidate = next((d + "/" + name for d in search + localdirs + defaults
                              if os.path.isfile(d + "/" + name)), None)
            require(candidate is not None, "missing provider: " + name)
            candidate = canonical(candidate)
            require(any(inside(candidate, r) for r in roots), "provider outside target/build roots")
            if name in files:
                require(digest(candidate) == digest(files[name]),
                        f"conflicting {name}: {files[name]} versus {candidate}")
            else:
                files[name] = candidate
                pending.append(candidate)
    sources = {p: digest(p) for p in sorted({exe, *files.values(), *([in_path] if in_path else [])})}
    shutil.copyfile(exe, stage / "query")
    (stage / "query").chmod(0o755)
    for name, path in files.items():
        shutil.copyfile(path, stage / "lib" / name)
    if in_path:
        shutil.copyfile(in_path, stage / "types.txt")
    entries = sorted(p for p in stage.rglob("*") if p.is_file())
    manifest = "".join(f"{digest(p)}  {p.relative_to(stage)}\n" for p in entries)
    (stage / "files.sha256").write_text(manifest, encoding="utf-8")
    (work / "files.sha256").write_text(manifest, encoding="utf-8")
    (work / "sources.sha256").write_text("".join(f"{h}  {p}\n" for p, h in sources.items()), encoding="utf-8")
    remote = None
    try:
        remote = run("allocate", *ssh, 'test "$(uname -s)" = NetBSD && test "$(uname -p)" = '
                     + processor + ' && umask 077 && mktemp -d /tmp/ember-gir.XXXXXXXX').decode().strip()
        require(re.fullmatch(r"/tmp/ember-gir\.[A-Za-z0-9]{8}", remote), "invalid temporary directory")
        reusable = {n: p for n, p in files.items() if inside(p, sysroot)}
        if reusable:
            script = "set -eu\ncd " + shlex.quote(remote) + "\nmkdir -p lib\n"
            for name, path in reusable.items():
                installed, output, expected = shlex.quote(path[len(sysroot):]), shlex.quote("lib/" + name), sources[path]
                script += (f'if test -f {installed} && test "$(sha256 -q {installed})" = {expected}; then\n'
                           f'  cp {installed} {output}\n'
                           f'  test "$(sha256 -q {output})" = {expected} || exit 92\n'
                           f"  printf '%s\\n' {shlex.quote(name)}\nfi\n")
            (work / "reuse.sh").write_text(script, encoding="utf-8")
            reused = run("reuse", *ssh, "sh -s -- ember-gir-reuse", data=script.encode()).decode().splitlines()
            require(len(set(reused)) == len(reused) and all(n in reusable for n in reused),
                    "invalid reused library response")
            for name in reused:
                (stage / "lib" / name).unlink()
        archive = work / "input.tar.gz"
        run("tar", "/usr/bin/env", "COPYFILE_DISABLE=1", "tar", "--format=ustar", "--no-xattrs",
            "-czf", str(archive), "-C", str(stage), ".")
        (work / "transfer-size.txt").write_text(str(archive.stat().st_size) + "\n", encoding="ascii")
        run("transfer", *ssh, "tar -xzf - -C " + shlex.quote(remote), data=archive.read_bytes())
        invocation = [remote + "/query"]
        if execute:
            invocation += arguments
        if out_path:
            invocation += [f"--introspect-dump={remote}/types.txt,{remote}/dump.xml"]
        script = f'''set -eu
cd {shlex.quote(remote)}
while read hash name; do
  test "$(sha256 -q "$name")" = "$hash" || exit 90
done < files.sha256
ulimit -c 0
ulimit -f 16384
export LD_LIBRARY_PATH={shlex.quote(remote + '/lib')}
unset LD_PRELOAD
set +e
timeout -k 5 60 {shlex.join(invocation)} > stdout.log 2> stderr.log
result=$?
set -e
while read hash name; do
  test "$(sha256 -q "$name")" = "$hash" || exit 91
done < files.sha256
cat stdout.log
cat stderr.log >&2
printf '%s\\n' "$result" > execution.status
exit "$result"
'''
        result = capture([*ssh, "sh -s"], data=script.encode(), merged=not execute)
        (work / "target.log").write_bytes(result.stdout)
        if execute:
            (work / "target-stderr.log").write_bytes(result.stderr)
            sys.stdout.buffer.write(result.stdout)
            sys.stderr.buffer.write(result.stderr)
        else:
            sys.stderr.buffer.write(result.stdout)
        target_status = status_of(result)
        (work / "exit.txt").write_text(str(target_status) + "\n", encoding="ascii")
        if execute:
            receipt = run("execution-status", *ssh, "cat " + remote + "/execution.status").decode().strip()
            require(receipt == str(target_status), "target execution receipt differs from transport status")
        require(execute or result.returncode == 0, f"target query failed ({target_status}), {work}")
        if out_path:
            xml_result = capture([*ssh, f"test -s {remote}/dump.xml && cat {remote}/dump.xml"], merged=False)
            xml = xml_result.stdout
            (work / "xml-transfer.log").write_bytes(
                f"exit={status_of(xml_result)} bytes={len(xml)}\n".encode() + xml_result.stderr)
            if len(xml) <= 16 * 1024 * 1024:
                (work / "dump.xml").write_bytes(xml)
            require(xml_result.returncode == 0 and len(xml) <= 16 * 1024 * 1024 and b"<dump" in xml,
                    "invalid introspection XML")
    finally:
        if remote and re.fullmatch(r"/tmp/ember-gir\.[A-Za-z0-9]{8}", remote):
            result = capture([*ssh, "rm -rf -- " + shlex.quote(remote)])
            (work / "cleanup.log").write_bytes(str(status_of(result)).encode() + b"\n" + result.stdout)
            require(result.returncode == 0, "remote cleanup failed: " + remote)
    require(all(digest(p) == h for p, h in sources.items()), "source providers changed during query")
    if out_path:
        with open(out_path, "xb", opener=lambda p, f: os.open(p, f, 0o600)) as stream:
            stream.write(xml)
    shutil.rmtree(stage)
    archive.unlink()
    completed[0] = True
    return target_status if execute else 0


def terminated(signum, _frame):
    # Unwind the transfer finally block before recording an interrupted query.
    raise SystemExit(128 + signum)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, terminated)
    try:
        sys.exit(main(sys.argv[1:]))
    except (QueryError, OSError, ValueError, KeyError, TypeError) as error:
        sys.exit(str(error))
