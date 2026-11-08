#!/usr/bin/env python3
"""Exercise WebKit's actual inspector-directory copier with selected host tools."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

SCRIPT_NAME = "copy-user-interface-resources.pl"
START = "sub ditto($$)\n"
END = "\nsub seedFile($$)\n"


def extract_ditto(path: Path) -> str:
    text = path.read_text()
    start = text.index(START)
    end = text.index(END, start)
    return text[start:end]


def perl_harness(source: Path, destination: Path, subroutine: str) -> subprocess.CompletedProcess[str]:
    code = (
        "use warnings;\n"
        "use File::Path qw(make_path);\n"
        "my $useDirCopy = 0; # Exercise the actual no-File::Copy::Recursive fallback.\n"
        f"{subroutine}\n"
        "ditto($ARGV[0], $ARGV[1]);\n"
    )
    return subprocess.run(
        [str(args.perl), "-e", code, str(source), str(destination)],
        env=selected_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def copied_files(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source-script", type=Path, required=True,
                    help="unpatched script from the selected WebKit source stage")
parser.add_argument("--patch", type=Path, required=True,
                    help="Ports patch for the script")
parser.add_argument("--nbpatch", type=Path, required=True,
                    help="selected host-prefix nbpatch executable")
parser.add_argument("--perl", type=Path, required=True,
                    help="selected host-prefix Perl executable")
parser.add_argument("--host-prefix", type=Path, required=True)
parser.add_argument("--tmp-dir", type=Path, required=True)
args = parser.parse_args()

host_bin = args.host_prefix / "bin"
selected_path = os.pathsep.join(
    str(path) for path in (
        host_bin,
        args.host_prefix / "gnu/bin",
    )
)
selected_env = os.environ.copy()
selected_env.update(PATH=selected_path, LC_ALL="C", TMPDIR=str(args.tmp_dir))
if not args.source_script.is_file():
    parser.error(f"source script is missing: {args.source_script}")
if not shutil.which("cp", path=selected_path):
    raise SystemExit("selected host environment has no cp executable")
if shutil.which("ditto", path=selected_path):
    raise SystemExit("causal control requires ditto to be absent from selected PATH")

with tempfile.TemporaryDirectory(prefix="webkit-copy-test-", dir=args.tmp_dir) as temporary:
    root = Path(temporary)
    source = root / "source tree with spaces"
    (source / "nested directory with spaces").mkdir(parents=True)
    (source / ".top-level-hidden").write_bytes(b"hidden top level\n")
    (source / "file name with spaces.txt").write_bytes(b"regular file\n")
    (source / "nested directory with spaces" / ".nested-hidden").write_bytes(b"hidden nested\n")
    (source / "nested directory with spaces" / "nested file.txt").write_bytes(b"nested regular\n")
    expected = copied_files(source)

    old_destination = root / "old destination with spaces"
    old_result = subprocess.run(
        [str(args.perl), "-e", "use warnings; use File::Path qw(make_path); my $useDirCopy=0; "
         + extract_ditto(args.source_script) + " ditto($ARGV[0], $ARGV[1]);",
         str(source), str(old_destination)],
        env=selected_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if old_result.returncode != 0:
        raise SystemExit(f"baseline copier unexpectedly exited {old_result.returncode}: {old_result.stderr}")
    if copied_files(old_destination) == expected:
        raise SystemExit("baseline Darwin ditto branch unexpectedly copied the fixture")
    if "ditto" not in old_result.stderr:
        raise SystemExit(f"baseline did not report the missing ditto executable: {old_result.stderr}")

    patch_tree = root / "patched source tree"
    patch_script = patch_tree / "Source/WebInspectorUI/Scripts" / SCRIPT_NAME
    patch_script.parent.mkdir(parents=True)
    shutil.copyfile(args.source_script, patch_script)
    applied = subprocess.run(
        [str(args.nbpatch), "-d", str(patch_tree), "-p0", "-F0", "-V", "never", "-i", str(args.patch)],
        env=selected_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if applied.returncode != 0:
        raise SystemExit(f"owner patch failed to apply with zero fuzz: {applied.stdout}{applied.stderr}")

    new_destination = root / "new destination with spaces"
    new_result = perl_harness(source, new_destination, extract_ditto(patch_script))
    if new_result.returncode != 0:
        raise SystemExit(f"patched copier failed ({new_result.returncode}): {new_result.stderr}")
    actual = copied_files(new_destination)
    if actual != expected:
        raise SystemExit(f"patched copier output differs: expected {sorted(expected)}, got {sorted(actual)}")

print("PASS: old Darwin ditto path fails without ditto; patched source copies nested, spaced and hidden files using selected tools")
