#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Write Cargo's standard configuration with separate native and target tools."""

import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import tomllib


def require(condition, message):
    if not condition:
        raise ValueError(message)


def command(value, tool_path):
    words = shlex.split(value)
    require(words, "a selected tool command is required")
    executable = shutil.which(words[0], path=tool_path)
    require(executable is not None, f"selected command is missing: {words[0]}")
    # Resolve a command name once in pkgsrc's explicitly supplied tool path.
    # Preserve wrapper paths: resolving a wrapper symlink can change dispatch.
    words[0] = str(Path(executable).absolute())
    return words


def atomic_write(path, content, mode=0o644):
    require(not path.is_symlink(), f"generated output must not be a symlink: {path}")
    with tempfile.NamedTemporaryFile(prefix="." + path.name + "-", dir=path.parent,
                                     mode="w", delete=False) as output:
        temporary = Path(output.name)
        try:
            output.write(content)
            output.flush()
            os.fchmod(output.fileno(), mode)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def toml_value(value):
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return json.dumps(value)
    if isinstance(value, dict) and all(isinstance(item, str) for item in value.values()):
        return "{ " + ", ".join(json.dumps(key) + " = " + json.dumps(item) for key, item in value.items()) + " }"
    raise ValueError("Cargo build-script values must be strings, string arrays or string tables")


def configure(config, vendor, output, rustc, shell, tool_path, mode, target,
              host_cc, host_cxx, host_ar, target_cc, target_cxx, target_ar,
              host_ldflags="", target_ldflags="", rustflags="",
              host_cflags="", host_cxxflags="", host_cppflags="",
              target_cflags="", target_cxxflags="", target_cppflags="",
              build_script_overrides=None):
    require(mode in ("native", "cross"), "select native or cross mode explicitly")
    paths = tool_path.split(os.pathsep)
    require(paths and all(part and Path(part).is_absolute() for part in paths),
            "tool path must contain explicit absolute directories")
    for name, path in (("rustc", rustc), ("shell", shell)):
        require(path.is_absolute() and path.is_file() and os.access(path, os.X_OK),
                f"selected {name} must be an absolute executable")
    require(not re.search(r"\s", str(shell)), "selected shell path cannot contain shebang whitespace")
    require(vendor.is_absolute() and vendor.is_dir(), "vendor must name the prepared crate directory")
    require(config.is_absolute() and output.is_absolute(), "Cargo output paths must be absolute")
    require(not config.parent.is_symlink() and not output.is_symlink(), "Cargo output directory is a symlink")
    for name in ("RUSTC_WRAPPER", "RUSTC_WORKSPACE_WRAPPER", "CARGO_BUILD_RUSTC_WRAPPER",
                 "CARGO_BUILD_RUSTC_WORKSPACE_WRAPPER"):
        require(not os.environ.get(name), f"undeclared Rust compiler wrapper: {name}")
    info = subprocess.run([str(rustc), "-vV"], capture_output=True, text=True, check=False)
    require(info.returncode == 0, "selected rustc cannot report its host")
    hosts = re.findall(r"^host: ([a-zA-Z0-9_.-]+)$", info.stdout, re.MULTILINE)
    require(len(hosts) == 1 and re.fullmatch(r"[a-z0-9_]+(?:-[a-z0-9_.]+){2,}", hosts[0]),
            "selected rustc reported no unique target triple")
    host = hosts[0]
    if mode == "native":
        require(not target or target == host, "native package target differs from the Rust host")
        require(not any((target_cc, target_cxx, target_ar)),
                "native mode uses the selected native tools for its package target")
        target = host
        target_cc, target_cxx, target_ar = host_cc, host_cxx, host_ar
        target_ldflags = host_ldflags
        target_cflags, target_cxxflags, target_cppflags = host_cflags, host_cxxflags, host_cppflags
    else:
        require(target and re.fullmatch(r"[a-z0-9_]+(?:-[a-z0-9_.]+){2,}", target),
                "cross mode requires an explicit Rust target triple")
        require(target != host, "cross host and target triples must differ")
    selected = {}
    for side, cc, cxx, ar, ldflags, cppflags in (
            ("host", host_cc, host_cxx, host_ar, host_ldflags, host_cppflags),
            ("target", target_cc, target_cxx, target_ar, target_ldflags, target_cppflags)):
        selected[side] = {"cc": command(cc, tool_path), "cxx": command(cxx, tool_path),
                          "ar": command(ar, tool_path)}
        selected[side]["linker"] = selected[side]["cc"] + shlex.split(ldflags)
        # cc crate reads CFLAGS/CXXFLAGS but not CPPFLAGS. Put preprocessor
        # arguments in the real compiler command, before caller C/C++ flags.
        # Rust's link-only driver keeps only its selected command/LDFLAGS.
        selected[side]["cc"] += shlex.split(cppflags)
        selected[side]["cxx"] += shlex.split(cppflags)
    flags = shlex.split(rustflags)
    overrides = {}
    if build_script_overrides is not None:
        overrides = tomllib.loads(build_script_overrides.read_text())
        require(all(re.fullmatch(r"[A-Za-z0-9_-]+", name) and isinstance(values, dict)
                    for name, values in overrides.items()), "build-script overrides must be tables keyed by links name")
        # These are Cargo's ordinary target.<triple>.<links> entries. Source
        # ownership, ABI and library policy remain with the consuming recipe.
        for values in overrides.values():
            for value in values.values():
                toml_value(value)
    config.parent.mkdir(parents=True, exist_ok=True)
    wrappers = config.parent / "cargo-tools"
    require(not wrappers.is_symlink(), "Cargo tool directory must not be a symlink")
    wrappers.mkdir(exist_ok=True)
    for side, roles in selected.items():
        for role in roles:
            require(not (wrappers / (side + "-" + role)).is_symlink(), "Cargo tool output must not be a symlink")
    selected_paths = {}
    for side, roles in selected.items():
        selected_paths[side] = {}
        for role, argv in roles.items():
            path = wrappers / (side + "-" + role)
            atomic_write(path, "#!" + str(shell) + "\nexec " + shlex.join(argv) + ' "$@"\n', 0o755)
            selected_paths[side][role] = str(path)
    quote = json.dumps
    text = '[build]\nrustc = ' + quote(str(rustc)) + '\ntarget = ' + quote(target)
    text += '\ntarget-dir = ' + quote(str(output)) + '\n'
    text += '\n[source.crates-io]\nreplace-with = "vendored-sources"\n'
    text += '\n[source.vendored-sources]\ndirectory = ' + quote(str(vendor)) + '\n'
    for triple, side in (((host, "host"),) if target == host else ((host, "host"), (target, "target"))):
        text += '\n[target.' + quote(triple) + ']\nlinker = ' + quote(selected_paths[side]["linker"]) + '\n'
        if triple == target:
            text += "rustflags = " + quote(flags) + "\n"
    # --target remains explicit even for native packages. Cargo then keeps
    # target Rust flags separate from host build-script/proc-macro compilation.
    for name, values in overrides.items():
        text += '\n[target.' + quote(target) + '.' + quote(name) + ']\n'
        text += ''.join(quote(key) + ' = ' + toml_value(value) + '\n' for key, value in values.items())
    environment = {"RUSTC": str(rustc), "CC_SHELL_ESCAPED_FLAGS": "1"}
    # CPPFLAGS already live in the compiler wrappers: clear the environment
    # to avoid duplicate -include or -D when another build script reads it.
    side_flags = {"host": {"CFLAGS": host_cflags, "CXXFLAGS": host_cxxflags, "CPPFLAGS": ""},
                  "target": {"CFLAGS": target_cflags, "CXXFLAGS": target_cxxflags, "CPPFLAGS": ""}}
    for side, triple in (("host", host), ("target", target)):
        values = {role.upper(): selected_paths[side][role] for role in ("cc", "cxx", "ar")}
        values.update(side_flags[side])
        for name, value in values.items():
            environment[side.upper() + "_" + name] = value
            # cc supports both exact and underscore-normalized target keys;
            # define both so an inherited alternate spelling cannot win.
            for key in {triple, triple.replace("-", "_")}:
                environment[name + "_" + key] = value
            if side == "host":
                environment[name] = value
    text += '\n[env]\n'
    text += ''.join(quote(name) + ' = { value = ' + quote(value) + ', force = true }\n'
                    for name, value in environment.items())
    atomic_write(config, text)
    return host, target


def run_cargo(cargo, config, source, arguments):
    require(cargo.is_absolute() and cargo.is_file() and os.access(cargo, os.X_OK),
            "selected Cargo must be an absolute executable")
    configuration = tomllib.loads(config.read_text())
    rustc = Path(configuration["build"]["rustc"])
    require(cargo.parent.resolve() == rustc.parent.resolve(),
            "Cargo and rustc must come from the same selected native tool directory")
    env = os.environ.copy()
    # Cargo's special flag environment variables override target.<triple>.rustflags.
    # Those flags were explicitly captured in the generated target configuration.
    for name in ("RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS"):
        env.pop(name, None)
    for name in ("RUSTC_WRAPPER", "RUSTC_WORKSPACE_WRAPPER", "CARGO_BUILD_RUSTC_WRAPPER",
                 "CARGO_BUILD_RUSTC_WORKSPACE_WRAPPER"):
        require(not env.get(name), f"undeclared Rust compiler wrapper: {name}")
    env.update(RUSTC=str(rustc), CARGO_HOME=str(config.parent), CARGO_NET_OFFLINE="true")
    if arguments[:1] == ["install"]:
        # cargo install intentionally ignores build.target. Preserve the same
        # target when pkgsrc uses its ordinary do-cargo-install target.
        require(not any(arg == "--target" or arg.startswith("--target=") for arg in arguments),
                "cargo install target is selected by the generated configuration")
        arguments = ["install", "--target", configuration["build"]["target"], *arguments[1:]]
    # Remain in pkgsrc's process group. Its parent owns the package build and
    # receives normal child status; this wrapper does not detach or retry.
    return subprocess.run([str(cargo), "--config", str(config), *arguments],
                          cwd=source, env=env).returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    run = commands.add_parser("run", help="run selected Cargo with the generated configuration")
    for name in ("cargo", "config", "source"):
        run.add_argument("--" + name, type=Path, required=True)
    run.add_argument("arguments", nargs=argparse.REMAINDER)
    configure_parser = commands.add_parser("configure", help="prepare separate host/target commands")
    for name in ("config", "vendor", "output", "rustc", "shell"):
        configure_parser.add_argument("--" + name, type=Path, required=True)
    configure_parser.add_argument("--tool-path", required=True)
    configure_parser.add_argument("--mode", choices=("native", "cross"), required=True)
    configure_parser.add_argument("--target", default="")
    for side in ("host", "target"):
        for role in ("cc", "cxx", "ar"):
            configure_parser.add_argument("--" + side + "-" + role, required=side == "host", default="")
        for flags in ("ldflags", "cflags", "cxxflags", "cppflags"):
            configure_parser.add_argument("--" + side + "-" + flags, default="")
    configure_parser.add_argument("--rustflags", default="")
    configure_parser.add_argument("--build-script-overrides", type=Path)
    args = parser.parse_args()
    try:
        values = vars(args)
        action = values.pop("action")
        if action == "run":
            if values["arguments"][:1] == ["--"]:
                values["arguments"] = values["arguments"][1:]
            parser.exit(run_cargo(**values))
        host, target = configure(**values)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Cargo configuration failed: {exc}\n")
    print(f"Configured Cargo host {host}, package target {target}; no crate compilation ran.")


if __name__ == "__main__":
    main()
