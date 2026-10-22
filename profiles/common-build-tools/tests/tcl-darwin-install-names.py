#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check actual Tcl Mach-O extension libraries.

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile


def run(arguments):
    return subprocess.run(arguments, text=True, capture_output=True)


def install_name(path):
    result = run(["otool", "-D", str(path)])
    result.check_returncode()
    lines = result.stdout.splitlines()
    if len(lines) != 2:
        raise RuntimeError(f"Expected one native Mach-O install name: {path}")
    return lines[1].strip()


parser = argparse.ArgumentParser(description="Check Tcl Darwin install names and causal Itcl header padding")
parser.add_argument("baseline_itcl", type=Path)
parser.add_argument("baseline_thread", type=Path)
parser.add_argument("stage_prefix", type=Path)
parser.add_argument("installed_prefix", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
libraries = {
    "itcl4.3.8": "libtcl9itcl4.3.8.dylib",
    "sqlite3.53.4": "libtcl9sqlite3.53.4.dylib",
    "tdbc1.1.15": "libtcl9tdbc1.1.15.dylib",
    "tdbcmysql1.1.15": "libtcl9tdbcmysql1.1.15.dylib",
    "tdbcodbc1.1.15": "libtcl9tdbcodbc1.1.15.dylib",
    "tdbcpostgres1.1.15": "libtcl9tdbcpostgres1.1.15.dylib",
    "thread3.0.7": "libtcl9thread3.0.7.dylib",
}
records = []
for directory, name in libraries.items():
    relative = Path("lib") / directory / name
    path = args.stage_prefix / relative
    expected = str(args.installed_prefix / relative)
    actual = install_name(path)
    if actual != expected:
        raise RuntimeError(f"Incorrect install name for {path}: {actual}")
    records.append({"library": str(relative), "install_name": actual,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
# The eighth bundled extension is Tcl code, not a Mach-O library.
if not (args.stage_prefix / "lib/tcl9/9.1/tdbc/sqlite3-1.1.15.tm").is_file():
    raise RuntimeError("The TDBC SQLite extension is absent")
relative = Path("lib/itcl4.3.8/libtcl9itcl4.3.8.dylib")
baseline = args.output / "baseline-itcl.dylib"
fixed = args.output / "fixed-itcl.dylib"
shutil.copy2(args.baseline_itcl, baseline)
shutil.copy2(args.stage_prefix / relative, fixed)
intended_name = str(args.installed_prefix / relative)
bad = run(["install_name_tool", "-id", intended_name, str(baseline)])
if bad.returncode == 0 or "larger updated load commands do not fit" not in bad.stderr:
    raise RuntimeError("The baseline did not reproduce the Mach-O header-padding failure")
good = run(["install_name_tool", "-id", intended_name, str(fixed)])
good.check_returncode()
# Exercise spare capacity, not merely rewriting the existing name in place.
long_name = "/tcl-install-name-check/" + ("component" * 20 + "/") * 4 + "itcl.dylib"
padded = run(["install_name_tool", "-id", long_name, str(fixed)])
padded.check_returncode()
if install_name(fixed) != long_name:
    raise RuntimeError("The longer install name was not retained")
thread_relative = Path("lib/thread3.0.7/libtcl9thread3.0.7.dylib")
thread_before = args.output / "baseline-thread.dylib"
shutil.copy2(args.baseline_thread, thread_before)
thread_error = run(["install_name_tool", "-id", str(args.installed_prefix / thread_relative),
                    str(thread_before)])
if thread_error.returncode == 0 or "__LINKEDIT segment does not cover the end of the file" not in thread_error.stderr:
    raise RuntimeError("The Thread baseline did not reproduce the appended-ZIP editing failure")
zip_hashes = []
for path in (args.baseline_thread, args.stage_prefix / thread_relative):
    with zipfile.ZipFile(path) as archive:
        if archive.namelist() != ["ttrace.tcl"] or archive.testzip() is not None:
            raise RuntimeError(f"Thread ZipFS payload differs: {path}")
        zip_hashes.append(hashlib.sha256(archive.read("ttrace.tcl")).hexdigest())
if zip_hashes[0] != zip_hashes[1]:
    raise RuntimeError("The repair changed Thread's embedded script bytes")
receipt = {"status": "PASS", "libraries": records, "bundled_extensions": 8,
           "thread_zipfs_script_sha256": zip_hashes[0],
           "thread_baseline_returncode": thread_error.returncode,
           "baseline_returncode": bad.returncode, "baseline_stderr": bad.stderr,
           "long_install_name_bytes": len(long_name.encode()),
           "scope": "Mach-O metadata and actual install_name_tool changes. Installed loading is a separate check."}
(args.output / "result.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt, indent=2))
