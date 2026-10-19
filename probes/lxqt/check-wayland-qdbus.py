#!/usr/bin/env python3
"""Check the LXQt Wayland qdbus wrapper with the package's real patch."""

from __future__ import annotations

import argparse
import os
import subprocess
import tarfile
import tempfile
from pathlib import Path


SOURCE_MEMBER = "lxqt-wayland-session-0.4.1/lxqt-qdbus.in"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("distfile", type=Path)
    parser.add_argument("recipe", type=Path)
    args = parser.parse_args()
    args.distfile = args.distfile.resolve()
    args.recipe = args.recipe.resolve()

    patch_dir = args.recipe / "patches"
    patch_file = patch_dir / "patch-lxqt-qdbus.in"
    makefile = args.recipe / "Makefile"
    with tarfile.open(args.distfile, "r:xz") as archive:
        source = archive.extractfile(SOURCE_MEMBER)
        if source is None:
            raise SystemExit(f"missing {SOURCE_MEMBER} in {args.distfile}")
        upstream = source.read()

    with tempfile.TemporaryDirectory(prefix="lxqt-wayland-qdbus-") as tmp:
        root = Path(tmp)
        source_path = root / "lxqt-qdbus.in"
        source_path.write_bytes(upstream)
        subprocess.run(
            ["patch", "-p0", "-i", str(patch_file)],
            cwd=root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        patched = source_path.read_text()
        if not patched.startswith("#!/bin/sh\n"):
            raise SystemExit("patched helper does not use the target /bin/sh")
        if any(token in patched for token in ("[[", "]]", "=~", "valid=(")):
            raise SystemExit("patched helper still contains Bash-only syntax")
        subprocess.run(["/bin/sh", "-n", str(source_path)], check=True)

        prefix = root / "target-prefix"
        qdbus = prefix / "qt6" / "bin" / "qdbus"
        qdbus.parent.mkdir(parents=True)
        log = root / "qdbus.log"
        qdbus.write_text(
            "#!/bin/sh\n"
            "printf '%s\\n' \"$*\" >> \"$QDBUS_LOG\"\n"
            "printf '%s\\n' fancymenu\n"
        )
        qdbus.chmod(0o755)

        configured = patched.replace("@CMAKE_INSTALL_PREFIX@", str(prefix))
        if "@CMAKE_INSTALL_PREFIX@" in configured:
            raise SystemExit("configured qdbus path still has a CMake placeholder")
        installed = root / "lxqt-qdbus"
        installed.write_text(configured)
        installed.chmod(0o755)

        env = os.environ.copy()
        env["PATH"] = "/usr/bin:/bin"
        env["QDBUS_LOG"] = str(log)
        result = subprocess.run(
            [str(installed), "openmenu"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            raise SystemExit(
                "openmenu failed under /bin/sh:\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
        calls = log.read_text().splitlines()
        expected = [
            "org.kde.StatusNotifierWatcher",
            "org.kde.StatusNotifierWatcher fancymenu/show_hide "
            "org.lxqt.global_key_shortcuts.client.activated",
        ]
        if calls != expected:
            raise SystemExit(f"unexpected qdbus calls: {calls!r}")

    recipe = makefile.read_text()
    if any(line.startswith("REPLACE_SH=") for line in recipe.splitlines()):
        raise SystemExit("POSIX target shell must not be replaced with a host interpreter")
    if "DEPENDS+=\tqt6-qttools>=6.12.0:../../devel/qt6-qttools" not in recipe:
        raise SystemExit("the qdbus runtime provider is not a package dependency")
    print("LXQt qdbus target path, POSIX shell, and runtime provider checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
