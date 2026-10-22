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


def query(args, pkgsrc, sysroot, mode, *extra):
    argv = [
        args.bmake, "-C", str(pkgsrc / "cad/occt"),
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

    baseline = query(args, args.baseline_pkgsrc, args.sysroot, "yes")
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

    empty_sysroot = work / "empty-sysroot"
    empty_sysroot.mkdir()
    missing = query(args, args.pkgsrc, empty_sysroot, "yes",
                    "TOOLS_PLATFORM.bash=" + host_bash[0])
    save(work, "missing-target-bash.log", missing)
    if refusal not in missing["PKG_FAIL_REASON"]:
        raise RuntimeError("A host Bash bypassed the missing-target refusal")
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
    if scripts != ["adm/templates/draw.sh"]:
        raise RuntimeError("Update the regression for the OCCT script contract")
    source = work / "source"
    script = source / scripts[0]
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
    print("PASS: OCCT keeps a host Bash generator and target Bash runtime; native behavior and missing-target refusal pass")


if __name__ == "__main__":
    main()
