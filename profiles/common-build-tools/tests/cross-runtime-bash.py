#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the host and target Bash roles through the real OCCT recipe."""

import argparse
from pathlib import Path
import shlex
import subprocess


VARIABLES = (
    "PKG_FAIL_REASON", "DEPENDS", "TOOL_DEPENDS", "BASH", "TOOLS_PATH.bash",
    "_TOOLS_DEPMETHOD.bash", "REPLACE.sys-bash.new", "REPLACE_BASH",
)


def query(args, pkgsrc, sysroot, mode, *extra, pkgpath="cad/occt"):
    argv = [
        args.bmake, "-C", str(pkgsrc / pkgpath),
        "MAKECONF=" + str(args.makeconf), "USE_CROSS_COMPILE=" + mode,
        "EMBERBSD_CROSS_SYSROOT=" + str(sysroot), *extra,
    ]
    for variable in VARIABLES:
        argv.extend(("-v", variable))
    result = subprocess.run(argv, check=True, text=True, capture_output=True)
    values = result.stdout.splitlines()
    if len(values) != len(VARIABLES):
        raise RuntimeError("Unexpected bmake response: " + repr(result.stdout))
    return dict(zip(VARIABLES, values))


def unstaged_view(sysroot, view):
    """Mirror the sysroot with symbolic links, without the target Bash."""
    parts = ("usr", "pkg", "bin")
    source, target = sysroot, view
    target.mkdir()
    for depth in range(len(parts) + 1):
        for entry in sorted(source.iterdir()):
            if depth < len(parts) and entry.name == parts[depth]:
                continue
            if depth == len(parts) and entry.name == "bash":
                continue
            (target / entry.name).symlink_to(entry)
        if depth < len(parts):
            source, target = source / parts[depth], target / parts[depth]
            target.mkdir()


def save(work, name, values):
    (work / name).write_text("\n".join(key + "=" + values[key] for key in VARIABLES) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pkgsrc", type=Path, required=True)
    parser.add_argument("--baseline-pkgsrc", type=Path, required=True)
    parser.add_argument("--makeconf", type=Path, required=True)
    parser.add_argument("--sysroot", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--bmake", required=True)
    args = parser.parse_args()
    args.pkgsrc = args.pkgsrc.resolve(strict=True)
    args.baseline_pkgsrc = args.baseline_pkgsrc.resolve(strict=True)
    args.makeconf = args.makeconf.resolve(strict=True)
    args.sysroot = args.sysroot.resolve(strict=True)
    work = args.work.resolve()
    if work.exists():
        parser.error("Work directory already exists")
    if not (args.sysroot / "usr/pkg/bin/bash").is_file():
        parser.error("Sysroot must contain the target Bash package")
    work.mkdir(parents=True)

    # Upstream pkgsrc and older EmberBSD revisions refuse OCCT when the target
    # Bash is not staged yet. That refusal hid the run dependency from bulk
    # dependency ordering.
    unstaged = work / "unstaged-sysroot"
    unstaged_view(args.sysroot, unstaged)
    baseline = query(args, args.baseline_pkgsrc, unstaged, "yes")
    save(work, "baseline.log", baseline)
    refusal = "bash:run not supported in cross-compilation"
    if refusal not in baseline["PKG_FAIL_REASON"]:
        raise RuntimeError("The unpatched OCCT consumer did not reproduce the failure")

    cross = query(args, args.pkgsrc, args.sysroot, "yes")
    save(work, "target-bash.log", cross)
    if cross["PKG_FAIL_REASON"]:
        raise RuntimeError("Staged target Bash was refused: " + cross["PKG_FAIL_REASON"])
    if "bash-[0-9]*:../../shells/bash" not in cross["DEPENDS"].split():
        raise RuntimeError("Bash is not a target runtime dependency")
    if "bash-[0-9]*:../../shells/bash" not in cross["TOOL_DEPENDS"].split():
        raise RuntimeError("OCCT has no host Bash dependency")
    if cross["_TOOLS_DEPMETHOD.bash"] != "TOOL_DEPENDS":
        raise RuntimeError("The build wrapper does not use the host dependency")
    if cross["REPLACE.sys-bash.new"] != "/usr/pkg/bin/bash":
        raise RuntimeError("The installed shebang does not use target Bash")
    host_bash = shlex.split(cross["BASH"])
    if not host_bash or host_bash[0] != cross["TOOLS_PATH.bash"]:
        raise RuntimeError("The Bash generator path and tools path differ")
    if host_bash[0] == "/usr/pkg/bin/bash" or str(args.sysroot) in host_bash[0]:
        raise RuntimeError("A target Bash was selected for build-host execution")
    result = subprocess.run(
        host_bash + ["-c", "values=(host generator); printf '%s\\n' \"${values[*]}\""],
        check=True, text=True, capture_output=True,
    )
    if result.stdout != "host generator\n":
        raise RuntimeError("The selected Bash cannot run a host generator")
    (work / "host-generator.log").write_text(result.stdout)

    # An unstaged target Bash is a run dependency, not a refusal. Otherwise
    # a bulk build cannot order shells/bash before its consumers.
    missing = query(args, args.pkgsrc, unstaged, "yes",
                    "TOOLS_PLATFORM.bash=" + host_bash[0])
    save(work, "missing-target-bash.log", missing)
    if missing["PKG_FAIL_REASON"]:
        raise RuntimeError("An unstaged target Bash was refused: " + missing["PKG_FAIL_REASON"])
    if "bash-[0-9]*:../../shells/bash" not in missing["DEPENDS"].split():
        raise RuntimeError("An unstaged target Bash is not a run dependency")
    if missing["REPLACE.sys-bash.new"] != "/usr/pkg/bin/bash":
        raise RuntimeError("An unstaged target Bash changed the installed shebang")

    # REPLACE_BASH without bash:run also installs target Bash scripts.
    for root, name in ((args.baseline_pkgsrc, "replace-only-baseline.log"),
                       (args.pkgsrc, "replace-only.log")):
        values = query(args, root, unstaged, "yes", pkgpath="textproc/cwdiff")
        save(work, name, values)
        if root == args.baseline_pkgsrc:
            replace_only_baseline = values
    replace_only = values
    if replace_only["PKG_FAIL_REASON"] or not replace_only["REPLACE_BASH"]:
        raise RuntimeError("Update the regression for the cwdiff script contract")
    if replace_only["REPLACE.sys-bash.new"] != "/usr/pkg/bin/bash":
        raise RuntimeError("A REPLACE_BASH script retained a host shebang")
    if "bash-[0-9]*:../../shells/bash" not in replace_only["DEPENDS"].split():
        raise RuntimeError("A REPLACE_BASH package has no target Bash run dependency")
    if replace_only_baseline["REPLACE.sys-bash.new"] == "/usr/pkg/bin/bash" and \
            "bash-[0-9]*:../../shells/bash" in replace_only_baseline["DEPENDS"].split():
        raise RuntimeError("The baseline cwdiff consumer did not reproduce the defect")
    platform = query(args, args.pkgsrc, args.sysroot, "yes",
                     "TOOLS_PLATFORM.bash=" + host_bash[0])
    save(work, "host-platform-bash.log", platform)
    if platform["PKG_FAIL_REASON"] or "bash-[0-9]*:../../shells/bash" not in platform["DEPENDS"].split():
        raise RuntimeError("A platform host Bash removed the target runtime dependency")

    native_base = query(args, args.baseline_pkgsrc, args.sysroot, "no")
    native = query(args, args.pkgsrc, args.sysroot, "no")
    save(work, "native-baseline.log", native_base)
    save(work, "native.log", native)
    if native != native_base:
        raise RuntimeError("Native OCCT Bash tool selection changed")

    # Exercise pkgsrc's real replacement target with OCCT's declared script.
    scripts = cross["REPLACE_BASH"].split()
    if "adm/templates/draw.sh" not in scripts:
        raise RuntimeError("Update the regression for the OCCT script contract")
    source = work / "source"
    script = source / "adm/templates/draw.sh"
    script.parent.mkdir(parents=True)
    script.write_text("#!/usr/bin/env bash\nvalues=(target runtime)\n")
    script.chmod(0o755)
    result = subprocess.run([
        args.bmake, "-C", str(args.pkgsrc / "cad/occt"),
        "MAKECONF=" + str(args.makeconf), "WRKSRC=" + str(source),
        "WRKDIR=" + str(work / "pkgsrc-work"), "replace-interpreter",
    ], check=True, text=True, capture_output=True)
    (work / "replace-interpreter.log").write_text(result.stdout + result.stderr)
    if script.read_text() != "#!/usr/pkg/bin/bash\nvalues=(target runtime)\n":
        raise RuntimeError("OCCT's installed script retained a host shebang")
    if script.stat().st_mode & 0o111 != 0o111:
        raise RuntimeError("Interpreter replacement changed executable permissions")
    print("PASS: OCCT keeps a host Bash generator and target Bash runtime; native behavior, unstaged target Bash and REPLACE_BASH dependencies pass")


if __name__ == "__main__":
    main()
