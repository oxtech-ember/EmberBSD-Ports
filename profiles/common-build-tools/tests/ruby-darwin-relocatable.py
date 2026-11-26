#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check the Darwin Ruby package overlay with the selected pkgsrc tools."""

import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tarfile
import tempfile


def check_source(archive_path):
    source = archive_path.name.removesuffix(".tar.xz")
    checks = {
        f"{source}/configure": (b"--enable-load-relative", b"ac_cv_func_dladdr"),
        f"{source}/configure.ac": (b'RUST_LIB="$(pwd)/${RUST_LIB}"', b"AC_SUBST(RUST_LIB)"),
        f"{source}/ruby.c": (b"runtime_libruby_path", b"dladdr(", b"#if defined LOAD_RELATIVE"),
    }
    with tarfile.open(archive_path, "r|xz") as archive:
        for member in archive:
            if member.name in checks:
                data = archive.extractfile(member).read()
                assert all(token in data for token in checks.pop(member.name)), member.name
                if not checks:
                    return
    raise AssertionError(f"Missing upstream files: {', '.join(checks)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("pkgsrc", "query-pkgsrc", "makeconf", "cross-makeconf", "bmake", "patch", "darwin-overlay",
                   "target-overlay", "archive", "miniruby", "staged-prefix", "strip", "find"):
        parser.add_argument("--" + option, type=Path, required=True)
    args = parser.parse_args()
    check_source(args.archive)
    with tempfile.TemporaryDirectory(prefix="ruby-relocatable-") as tmp:
        root = Path(tmp)
        for entry in args.pkgsrc.iterdir():
            destination = root / entry.name
            if entry.name == "lang":
                destination.mkdir()
                for lang_entry in entry.iterdir():
                    if lang_entry.name in ("ruby40", "ruby"):
                        shutil.copytree(lang_entry, destination / lang_entry.name)
                    else:
                        (destination / lang_entry.name).symlink_to(lang_entry.resolve(), target_is_directory=True)
            else:
                destination.symlink_to(entry.resolve(), target_is_directory=entry.is_dir())
        package = root / "lang/ruby40"
        query_package = args.query_pkgsrc / "lang/ruby40"
        env_base = dict(os.environ, PATH=f"{args.bmake.parent}:/usr/bin:/bin:/usr/sbin:/sbin:{os.environ['PATH']}",
                        PKGSRCDIR=str(args.query_pkgsrc))

        patch_dir = args.darwin_overlay.parent
        prior_overlays = (
            "pkgsrc-ruby40-optional-jit.patch",
            "ruby-no-test-extensions.patch",
            "pkgsrc-ruby-dtrace-cpppath.patch",
            "pkgsrc-ruby-one-version.patch",
            "pkgsrc-ruby-4.0.10.patch",
        )
        for name in prior_overlays:
            subprocess.run([args.patch, "-d", root, "-p1", "-F0", "-i", patch_dir / name], check=True)

        def metadata(mode, unstripped="no"):
            command = [
                args.bmake, "-C", query_package, "-f", package / "Makefile", "USE_CROSS_COMPILE=" + mode,
                "INSTALL_UNSTRIPPED=" + unstripped, "-V", "${OPSYS}",
                "-V", "${PKGREVISION}", "-V", "${CONFIGURE_ARGS}",
                "-V", "${.ALLTARGETS:Mruby-strip-darwin-debug}",
                "-V", "${.ALLTARGETS:Mruby-install-darwin-rbconfig}",
                "-V", "${.ALLTARGETS:Mruby-install-target-metadata}",
            ]
            result = subprocess.run(command, check=True, text=True, stdout=subprocess.PIPE,
                                    env=dict(env_base, MAKECONF=str(
                                        args.cross_makeconf if mode == "yes" else args.makeconf)))
            opsys, revision, configure_args, strip_hook, config_hook, target_hook = result.stdout.splitlines()
            return (opsys, revision, configure_args.split(), strip_hook, config_hook, target_hook)

        def dry_run(target, unstripped="no"):
            command = [args.bmake, "-C", query_package, "-f", package / "Makefile",
                       "USE_CROSS_COMPILE=no", "INSTALL_UNSTRIPPED=" + unstripped,
                       "-n", target]
            result = subprocess.run(command, check=True, text=True, stdout=subprocess.PIPE,
                                    env=dict(env_base, MAKECONF=str(args.makeconf)))
            return result.stdout

        subprocess.run([args.patch, "-d", root, "-p1", "-F0", "-i", args.darwin_overlay], check=True)
        subprocess.run([args.patch, "-d", root, "-p1", "-F0", "-i",
                        patch_dir / "pkgsrc-ruby40-netbsd-openssl.patch"], check=True)
        subprocess.run([args.patch, "-d", root, "-p1", "-F0", "-i", args.target_overlay], check=True)
        native = metadata("no")
        assert native[:2] == ("Darwin", "2")
        assert "--enable-load-relative" in native[2]
        assert any(arg.startswith("--with-destdir=") for arg in native[2])
        assert native[3:] == ("ruby-strip-darwin-debug", "ruby-install-darwin-rbconfig", "")
        unstripped = metadata("no", unstripped="yes")
        assert unstripped[3:] == ("", "ruby-install-darwin-rbconfig", "")
        target = metadata("yes")
        assert target[0:2] == ("NetBSD", "1")
        assert target[3:] == ("", "", "ruby-install-target-metadata")
        assert "--enable-load-relative" not in target[2]

        staged_prefix = args.staged_prefix
        strip = dry_run("ruby-strip-darwin-debug")
        strip_command = shlex.split(strip.splitlines()[0])
        assert len(strip_command) == 5 and strip_command[1] == "-S", strip
        static_lib = next(staged_prefix.rglob(Path(strip_command[2]).name))
        ruby_bin = next(staged_prefix.rglob(Path(strip_command[3]).name))
        shared_lib = next(staged_prefix.rglob(Path(strip_command[4]).name))
        bundle = next(staged_prefix.rglob("*.bundle"))
        rbconfig_source = next(staged_prefix.glob("lib/ruby/*/*/rbconfig.rb"))
        ruby_name = ruby_bin.name
        ruby_archlib = str(rbconfig_source.parent.relative_to(staged_prefix))
        ruby_staticlib = static_lib.name.removeprefix("libruby")
        ruby_shlib = shared_lib.name.removeprefix("libruby")
        assert "-S" in strip and "-name '*.bundle'" in strip
        assert "exec strip -S {} +" in strip, strip
        assert all(path.name in strip for path in (ruby_bin, static_lib, shared_lib)), strip
        assert sum("strip -S" in line for line in strip.splitlines()) == 2, strip

        normalize = dry_run("ruby-install-darwin-rbconfig")
        assert "miniruby --disable-gems" in normalize
        assert "install-rbconfig.rb" in normalize and "rbconfig.rb" in normalize
        assert "native" in normalize
        helper = package / "install-rbconfig.rb"
        assert helper.is_file()

        build_dir = root / "work/ruby-4.0.10"
        config = root / "rbconfig.rb"
        rust_lib = str(build_dir / "target/release/$(YJIT_LIBS)")
        source_cc = str(build_dir / "bin/clang")
        config.write_text(
            "module RbConfig\n"
            "  MAKEFILE_CONFIG = {}\n"
            "  CONFIG = MAKEFILE_CONFIG\n"
            f"  CONFIG[\"RUST_LIB\"] = {json.dumps(rust_lib)}\n"
            f"  CONFIG[\"CC\"] = {json.dumps(source_cc)}\n"
            "end\n"
        )
        subprocess.run([args.miniruby, "--disable-gems", str(helper),
                        str(config), str(build_dir), "native"], check=True)
        normalized = config.read_text()
        assert 'CONFIG["RUST_LIB"] = "target/release/$(YJIT_LIBS)"' in normalized
        assert f'CONFIG["CC"] = "{source_cc}"' in normalized
        assert rust_lib not in normalized

        cross_config = root / "cross-rbconfig.rb"
        cross_config.write_text(
            "module RbConfig\n"
            "  MAKEFILE_CONFIG = {}\n"
            "  CONFIG = MAKEFILE_CONFIG\n"
            f"  CONFIG[\"RUST_LIB\"] = {json.dumps(rust_lib)}\n"
            f"  CONFIG[\"INSTALL\"] = {json.dumps(str(build_dir / 'tools/install'))}\n"
            f"  CONFIG[\"MKDIR_P\"] = {json.dumps(str(build_dir / 'tools/mkdir'))}\n"
            f"  CONFIG[\"MAKEDIRS\"] = {json.dumps(str(build_dir / 'tools/mkdir'))}\n"
            f"  CONFIG[\"SHELL\"] = {json.dumps(str(build_dir / 'tools/sh'))}\n"
            f"  CONFIG[\"AR\"] = {json.dumps(str(build_dir / 'tools/ar'))}\n"
            f"  CONFIG[\"RANLIB\"] = {json.dumps(str(build_dir / 'tools/ranlib'))}\n"
            f"  CONFIG[\"RUSTC\"] = {json.dumps(str(build_dir / 'tools/rustc'))}\n"
            f"  CONFIG[\"CC_VERSION_MESSAGE\"] = {json.dumps('clang\nInstalledDir: ' + str(build_dir / 'bin'))}\n"
            f"  CONFIG[\"configure_args\"] = {json.dumps('--with-baseruby=' + str(build_dir / 'ruby') + ' --enable-shared')}\n"
            "end\n"
        )
        subprocess.run([args.miniruby, "--disable-gems", "-I", args.miniruby.parent / "lib", str(helper),
                        str(cross_config), str(build_dir), "cross"], check=True)
        cross_normalized = cross_config.read_text()
        assert 'CONFIG["RUST_LIB"] = "target/release/$(YJIT_LIBS)"' in cross_normalized
        assert 'CONFIG["INSTALL"] = "/usr/bin/install -c"' in cross_normalized
        assert 'CONFIG["AR"] = "ar"' in cross_normalized
        assert '--with-baseruby\\\\=ruby' in cross_normalized, cross_normalized
        assert 'InstalledDir:' not in cross_normalized

        recipe_stage = root / "recipe-stage"
        staged_prefix = recipe_stage / "usr/pkg"
        staged_files = (
            ruby_bin.relative_to(args.staged_prefix),
            static_lib.relative_to(args.staged_prefix),
            shared_lib.relative_to(args.staged_prefix),
            bundle.relative_to(args.staged_prefix),
            rbconfig_source.relative_to(args.staged_prefix),
        )
        for relative in staged_files:
            source = args.staged_prefix / relative
            target_path = staged_prefix / relative
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target_path)

        recipe_env = dict(env_base, MAKECONF=str(args.makeconf))
        recipe_vars = [
            f"WRKSRC={args.miniruby.parent}",
            f"DESTDIR={recipe_stage}",
            "PREFIX=/usr/pkg",
            f"RUBY_ARCHLIB={ruby_archlib}",
            f"RUBY_STATICLIB={ruby_staticlib}",
            f"RUBY_SHLIB={ruby_shlib}",
            f"RUBY_NAME={ruby_name}",
            f"STRIP={args.strip}",
            f"FIND={args.find}",
        ]
        for target_name in ("ruby-install-darwin-rbconfig", "ruby-strip-darwin-debug"):
            subprocess.run([args.bmake, "-C", query_package, "-f", package / "Makefile",
                            *recipe_vars, target_name], check=True, env=recipe_env)
        installed_rbconfig = recipe_stage / "usr/pkg" / rbconfig_source.relative_to(args.staged_prefix)
        assert rust_lib not in installed_rbconfig.read_text()


if __name__ == "__main__":
    main()
