#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual daemon descriptor failure regression.
"""Check native daemon error paths with real sockets and all ordinary objects."""
import argparse
import os
from pathlib import Path
import shlex
import shutil
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk-source", required=True)
    parser.add_argument("--source", required=True, help="Ordinary native package WRKSRC")
    parser.add_argument("--build-log", required=True, help="Matching ordinary native package log")
    parser.add_argument("--work", required=True)
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 15) or sys.platform != "linux":
        parser.error("The qualified Linux/Python 3.15 host is required.")
    sdk = Path(args.sdk_source).resolve(strict=True)
    sys.path.insert(0, str(sdk / "src"))
    import emberbsd_sdk
    from emberbsd_sdk import inventory, jsonio, paths, process
    from emberbsd_sdk.errors import CommandError
    if emberbsd_sdk.API_VERSION != 1:
        parser.error("SDK library API 1 is required.")
    source = Path(args.source).resolve(strict=True)
    log = Path(args.build_log).resolve(strict=True)
    work = Path(paths.canonical_new(args.work))
    paths.reject_overlap(str(work), str(source))
    if len(str(work / "test.sock").encode()) >= 108:
        parser.error("Select a work path short enough for an AF_UNIX socket.")
    for name in ("timeout", "valgrind"):
        if not shutil.which(name):
            parser.error(f"Missing native tool: {name}")
    work.mkdir()
    fixture = Path(__file__).with_suffix(".c").resolve(strict=True)
    cwd = source / "mDNSPosix"
    cc = source.parent / ".cwrapper/bin/cc"
    env = dict(os.environ, CWRAPPERS_CONFIG_DIR=str(cc.parent.parent / "config"))
    commands = []

    def run(label, argv, expected=0):
        argv = [str(x) for x in argv]
        try:
            result = process.capture(argv, cwd=str(cwd), env=env)
            stdout, stderr, status = result.stdout, result.stderr, result.returncode
        except CommandError as error:
            stdout, stderr, status = error.stdout, error.stderr, error.returncode
        (work / (label + ".stdout")).write_bytes(stdout)
        (work / (label + ".stderr")).write_bytes(stderr)
        commands.append(dict(label=label, argv=argv, cwd=str(cwd), status=status))
        jsonio.write_json(work / "commands.json", commands, exclusive=False)
        if status != expected:
            raise SystemExit(f"Unexpected {label} status {status}; inspect {work}.")
        return stdout

    assert run("compiler-version", [cc, "-dumpfullversion"]).strip() == b"16.2.0"
    inventory.required_elf(str(cwd), "objects/prod/mDNS.c.o", 62, 1)
    lines = log.read_text().splitlines()
    line = next(x for x in lines if x.startswith("cc ") and x.endswith(" ../mDNSShared/uds_daemon.c"))
    argv = shlex.split(line)
    assert argv[-4:-2] == ["-c", "-o"] and "-DHAVE_LINUX" in argv
    flags = [x for x in argv[1:-4] if not x.startswith(("-DPID_FILE=", "-DMDNS_UDS_SERVERPATH="))]
    flags += ['-DPID_FILE="' + str(work / "test.pid") + '"',
              '-DMDNS_UDS_SERVERPATH="' + str(work / "test.sock") + '"']
    after = source / "mDNSShared/uds_daemon.c"
    text = after.read_text()
    fixed_flags = "    const int flags = fcntl(skt, F_GETFL, 0);\n    if (flags == -1 || fcntl(skt, F_SETFL, flags | O_NONBLOCK) != 0)"
    cleanup = "    if (!skts && dnssd_SocketValid(listenfd))\n    {\n        dnssd_close(listenfd);\n        listenfd = dnssd_InvalidSocket;\n    }\n"
    assert text.count(fixed_flags) == 1 and text.count(cleanup) == 1
    before = work / "uds-before.c"
    before.write_text(text.replace(fixed_flags,
        "    if (fcntl(skt, F_SETFL, fcntl(skt, F_GETFL, 0) | O_NONBLOCK) != 0)").replace(cleanup, ""))
    run("daemon-entry", [cc, *flags, "-Dmain=mdns_daemon_main", "-c", "PosixDaemon.c", "-o", work / "entry.o"])
    run("fixture", [cc, *flags, "-std=c23", "-UNDEBUG", "-c", fixture, "-o", work / "fixture.o"])
    link = shlex.split(next(x for x in lines if x.startswith("cc -o build/prod/mdnsd ")))[3:]
    objects = [x for x in link if not x.endswith(("/PosixDaemon.c.o", "/uds_daemon.c.o"))]
    for variant, unit in (("before", before), ("after", after)):
        run(variant + "-compile", [cc, *flags, "-c", unit, "-o", work / (variant + ".o")])
        run(variant + "-link", [cc, "-o", work / variant, work / "entry.o", work / "fixture.o",
            work / (variant + ".o"), *objects,
            "-Wl,--wrap=socket,--wrap=bind,--wrap=fcntl,--wrap=listen,--wrap=udsSupportAddFDToEventLoop"])
        result = run(variant + "-run", ["timeout", "30", work / variant], 1 if variant == "before" else 0)
        assert (b"12 failures" if variant == "before" else b"0 failures") in result
    run("memcheck", ["timeout", "60", "valgrind", "--tool=memcheck", "--leak-check=full",
        "--show-leak-kinds=all", "--errors-for-leak-kinds=all", "--track-fds=yes",
        "--error-exitcode=97", work / "after"])
    memory = (work / "memcheck.stderr").read_text()
    assert "ERROR SUMMARY: 0 errors" in memory and "in use at exit: 0 bytes in 0 blocks" in memory
    assert "FILE DESCRIPTORS: 3 open (3 std) at exit." in memory
    jsonio.write_json(work / "result.json", dict(status="PASS", cases=10, baseline_status=1,
        scope="Real socket negative startup paths, complete native objects. No daemon service or target execution.",
        inputs={str(p): inventory.sha256_file(p) for p in (after, before, fixture, log,
            Path(__file__).resolve(), cc.resolve(), *(sdk / "src/emberbsd_sdk" / name for name in
            ("__init__.py", "inventory.py", "jsonio.py", "paths.py", "process.py")))}))
    print("PASS: 10 real daemon failure cases; owned descriptors close, caller descriptors remain; strict Memcheck clean.")


if __name__ == "__main__":
    main()
