#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check production graphics profile selection and AMDGPU source closure."""

import argparse
import hashlib
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tarfile
import tempfile


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = ROOT.parents[1]
MAKE = shlex.split(os.environ.get("BMAKE", "bmake"))


def check(name, condition):
    if not condition:
        raise SystemExit(f"FAIL: {name}")
    print(f"PASS: {name}")


def make_fixture(work):
    (work / "profile.mk").write_text((ROOT / "mk.conf").read_text())
    for name in (
        "EMBERBSD-COMMON-GRAPHICS-SOURCES",
        "EMBERBSD-COMMON-TOOLS-MK.CONF",
        "inputs.sha256",
        "receipt.json",
        "llvm-config",
        "scanner",
    ):
        (work / name).write_text("")
    (work / "bin").mkdir()
    (work / "bin/flex").write_text("")
    (work / "helper/bin").mkdir(parents=True)
    (work / "helper/bin/llvm-config").write_text("")
    for name in ("inputs.sha256", "receipt.json"):
        (work / "helper" / name).write_text("")

    for name, path in {
        "mesa": "graphics/MesaLib",
        "drm": "x11/libdrm",
    }.items():
        recipe = REPOSITORY / "pkgsrc" / path / "Makefile"
        contents = "".join(
            line for line in recipe.read_text().splitlines(keepends=True)
            if not line.startswith(".include")
        )
        (work / f"{name}.mk").write_text(contents)

    vars_ = [
        "PKG_FAIL_REASON",
        "ONLY_FOR_PLATFORM",
        "MESON_ARGS",
        "PLIST.intel",
        "PLIST.v3d",
        "PLIST.radeonsi",
        "PLIST.amdgpu",
        "_EMBERBSD_MESA_LLVM_TRIPLE",
        "EMBERBSD_COMMON_GRAPHICS",
        "OPSYS",
    ]
    makefile = f"""\
BSD_PKG_MK=1
OPSYS=NetBSD
OS_VERSION=11.0
MACHINE_ARCH?=aarch64
CROSS_MACHINE_ARCH?=${{MACHINE_ARCH}}
CROSS_OPSYS=NetBSD
USE_CROSS_COMPILE?=yes
EMBERBSD_COMMON_GRAPHICS_CROSS=yes
EMBERBSD_CROSS_TOOLS={work}
TOOLDIR={work}
TOOLBASE={work}
EMBERBSD_CROSS_SYSROOT={work}
CROSS_DESTDIR={work}
EMBERBSD_CROSS_HOST_PREFIX={work}
CROSS_LOCALBASE=/usr/pkg
EMBERBSD_SDK_SOURCE={work}/sdk-source
PKGSRC_COMPILER=gcc
EMBERBSD_CROSS_COMPILER_FAMILY=gcc
USE_NATIVE_GCC=yes
USE_PKGSRC_GCC=no
USE_PKGSRC_GCC_RUNTIME=no
_TOOLS_USE_PKGSRC.flex=no
PKGPATH?=graphics/MesaLib
PKG_OPTIONS=llvm x11 wayland
DISTNAME=mesa-26.2.5
PKGREVISION=10
.if ${{USE_CROSS_COMPILE:Uno:tl}} == "yes"
EMBERBSD_GRAPHICS_LLVM_CONFIG={work}/helper/bin/llvm-config
EMBERBSD_WAYLAND_SCANNER={work}/scanner
.endif
.include "{work}/profile.mk"
.include "{work}/${{RECIPE:Umesa}}.mk"
show:
.for key in {' '.join(vars_)}
\t@printf '%s\\n' ${{${{key}}:Q}}
.endfor
"""
    (work / "fixture.mk").write_text(makefile)
    return vars_


def static_profile_checks():
    mesa_plist = (REPOSITORY / "pkgsrc/graphics/MesaLib/PLIST").read_text().splitlines()
    drm_plist = (REPOSITORY / "pkgsrc/x11/libdrm/PLIST").read_text().splitlines()
    check(
        "Mesa architecture driver PLIST follows profile selection",
        all("${PLIST.intel}" + name in mesa_plist for name in (
            "lib/dri/iris_dri.so", "share/drirc.d/00-iris-defaults.conf"
        ))
        and all("${PLIST.v3d}" + name in mesa_plist for name in (
            "lib/dri/v3d_dri.so", "share/drirc.d/00-v3d-defaults.conf"
        ))
        and all("${PLIST.radeonsi}" + name in mesa_plist for name in (
            "lib/dri/radeonsi_dri.so", "share/drirc.d/00-radeonsi-defaults.conf"
        )),
    )
    check(
        "libdrm AMDGPU DSO, headers, metadata and ID table are conditional",
        all("${PLIST.amdgpu}" + name in drm_plist for name in (
            "include/libdrm/amdgpu.h",
            "lib/libdrm_amdgpu.so",
            "lib/libdrm_amdgpu.so.1",
            "lib/libdrm_amdgpu.so.1.134.0",
            "lib/pkgconfig/libdrm_amdgpu.pc",
            "share/libdrm/amdgpu.ids",
        )),
    )
    mesa_makefile = (REPOSITORY / "pkgsrc/graphics/MesaLib/Makefile").read_text()
    drm_makefile = (REPOSITORY / "pkgsrc/x11/libdrm/Makefile").read_text()
    profile = (ROOT / "mk.conf").read_text()
    check(
        "Mesa amd64 recipe selects RadeonSI and pins the matching libdrm API",
        'MACHINE_ARCH} == "x86_64"' in mesa_makefile
        and "-Dgallium-drivers=iris,radeonsi,virgl,softpipe,llvmpipe,zink" in mesa_makefile
        and "PLIST.radeonsi=\tyes" in mesa_makefile
        and "BUILDLINK_API_DEPENDS.libdrm+=\tlibdrm>=2.4.134nb7" in mesa_makefile,
    )
    check(
        "libdrm amd64 profile enables its module and other targets keep it disabled",
        'MACHINE_ARCH} == "x86_64"' in drm_makefile
        and "-Damdgpu=enabled" in drm_makefile
        and "PLIST.amdgpu=\tyes" in drm_makefile
        and "-Damdgpu=disabled" in drm_makefile,
    )
    check(
        "common profile enforces libdrm 2.4.134nb8",
        "libdrm>=2.4.134nb8" in profile and 'PKGREVISION:U} != "8"' in profile,
    )
    check(
        "common profile enforces MesaLib 26.2.5nb10",
        "MesaLib>=26.2.5nb10" in profile,
    )


def profile_checks():
    if not MAKE or shutil.which(MAKE[0]) is None:
        raise SystemExit("bmake is required for profile checks; set BMAKE to its path")
    with tempfile.TemporaryDirectory(prefix="ember-graphics-amd64-") as temp:
        work = Path(temp).resolve()
        vars_ = make_fixture(work)

        def query(*args):
            result = subprocess.run(
                [*MAKE, "-r", "-m", "/", "-f", str(work / "fixture.mk"), "show", *args],
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode:
                raise SystemExit(result.stdout + result.stderr)
            lines = result.stdout.splitlines()
            if len(lines) != len(vars_):
                raise SystemExit(result.stdout + result.stderr)
            return dict(zip(vars_, lines))

        arm = query("MACHINE_ARCH=aarch64")
        check(
            "AArch64 Mesa retains V3D without RadeonSI",
            not arm["PKG_FAIL_REASON"]
            and "-Dgallium-drivers=v3d,virgl,softpipe,llvmpipe,zink" in arm["MESON_ARGS"]
            and arm["PLIST.v3d"] == "yes"
            and not arm["PLIST.radeonsi"],
        )
        amd = query("MACHINE_ARCH=x86_64")
        check(
            "amd64 Mesa selects RadeonSI and its libdrm API floor",
            not amd["PKG_FAIL_REASON"]
            and "-Dgallium-drivers=iris,radeonsi,virgl,softpipe,llvmpipe,zink" in amd["MESON_ARGS"]
            and amd["PLIST.intel"] == "yes"
            and amd["PLIST.radeonsi"] == "yes"
            and amd["_EMBERBSD_MESA_LLVM_TRIPLE"] == "x86_64-unknown-netbsd"
            and "-Dmesa-clc=system" in amd["MESON_ARGS"]
            and "-Dprecomp-compiler=system" in amd["MESON_ARGS"],
        )
        native = query(
            "MACHINE_ARCH=x86_64", "USE_CROSS_COMPILE=no",
            "EMBERBSD_COMMON_GRAPHICS_CROSS=no", "USE_NATIVE_GCC=yes",
            "USE_PKGSRC_GCC=no", "USE_PKGSRC_GCC_RUNTIME=no",
            "EMBERBSD_COMMON_TOOLS=yes",
        )
        check(
            "amd64 native Mesa keeps RadeonSI and builds its shader generators natively",
            not native["PKG_FAIL_REASON"]
            and native["EMBERBSD_COMMON_GRAPHICS"] == "yes"
            and native["PLIST.radeonsi"] == "yes"
            and "-Dgallium-drivers=iris,radeonsi,virgl,softpipe,llvmpipe,zink" in native["MESON_ARGS"]
            and "-Dmesa-clc=enabled" in native["MESON_ARGS"]
            and "-Dprecomp-compiler=enabled" in native["MESON_ARGS"]
            and "-Dspirv-tools=enabled" in native["MESON_ARGS"]
            and "-Dinstall-mesa-clc=false" in native["MESON_ARGS"]
            and "-Dinstall-precomp-compiler=false" in native["MESON_ARGS"],
        )
        check(
            "Mesa platform selection is exactly the two NetBSD 11 targets",
            sorted(amd["ONLY_FOR_PLATFORM"].split())
            == ["NetBSD-11.*-aarch64", "NetBSD-11.*-x86_64"],
        )
        mixed = query("MACHINE_ARCH=x86_64", "CROSS_MACHINE_ARCH=aarch64")
        check("mixed profile target is rejected", bool(mixed["PKG_FAIL_REASON"]))
        foreign = query("MACHINE_ARCH=riscv64")
        check("foreign graphics target is rejected", bool(foreign["PKG_FAIL_REASON"]))
        host = query("OPSYS=Darwin", "MACHINE_ARCH=arm64", "USE_CROSS_COMPILE=no")
        check(
            "recursive host dependency retains Darwin and no graphics profile",
            not host["EMBERBSD_COMMON_GRAPHICS"] and host["OPSYS"] == "Darwin",
        )

        drm_arm = query(
            "MACHINE_ARCH=aarch64", "PKGPATH=x11/libdrm", "RECIPE=drm",
            "DISTNAME=libdrm-2.4.134", "PKGREVISION=8"
        )
        drm_amd = query(
            "MACHINE_ARCH=x86_64", "PKGPATH=x11/libdrm", "RECIPE=drm",
            "DISTNAME=libdrm-2.4.134", "PKGREVISION=8"
        )
        check(
            "AArch64 libdrm disables Intel and AMDGPU modules",
            not drm_arm["PKG_FAIL_REASON"]
            and "-Dintel=disabled" in drm_arm["MESON_ARGS"]
            and "-Damdgpu=disabled" in drm_arm["MESON_ARGS"]
            and not drm_arm["PLIST.intel"]
            and not drm_arm["PLIST.amdgpu"],
        )
        check(
            "amd64 libdrm selects Intel and AMDGPU client modules",
            not drm_amd["PKG_FAIL_REASON"]
            and "-Dintel=enabled" in drm_amd["MESON_ARGS"]
            and "-Damdgpu=enabled" in drm_amd["MESON_ARGS"]
            and drm_amd["PLIST.intel"] == "yes"
            and drm_amd["PLIST.amdgpu"] == "yes",
        )

def source_checks(distfiles):
    pins = {}
    for line in (ROOT / "sources.tsv").read_text().splitlines()[1:]:
        fields = line.split("\t")
        if len(fields) >= 3:
            pins[fields[1]] = fields[2]

    validated = set()

    def source_text(archive_name, member):
        archive_path = distfiles / archive_name
        if not archive_path.is_file():
            raise SystemExit(f"missing source archive: {archive_path}")
        if archive_name not in validated:
            actual = hashlib.sha256(archive_path.read_bytes()).hexdigest()
            check(f"{archive_name} matches sources.tsv", actual == pins.get(archive_name))
            validated.add(archive_name)
        with tarfile.open(archive_path, "r:*") as archive:
            try:
                return archive.extractfile(member).read().decode("utf-8")
            except (KeyError, AttributeError) as error:
                raise SystemExit(f"missing source member {member}: {error}") from error

    mesa_top = source_text("mesa-26.2.5.tar.xz", "mesa-26.2.5/meson.build")
    mesa_dri = source_text(
        "mesa-26.2.5.tar.xz", "mesa-26.2.5/src/gallium/targets/dril/meson.build"
    )
    mesa_amd = source_text(
        "mesa-26.2.5.tar.xz", "mesa-26.2.5/src/amd/common/ac_gpu_info.c"
    )
    drm_amdgpu = source_text(
        "libdrm-2.4.134.tar.xz", "libdrm-2.4.134/amdgpu/meson.build"
    )
    drm_data = source_text("libdrm-2.4.134.tar.xz", "libdrm-2.4.134/data/meson.build")
    check(
        "Mesa source links RadeonSI to libdrm_amdgpu >= 2.4.133",
        "_drm_amdgpu_ver = '2.4.133'" in mesa_top
        and "with_gallium_radeonsi" in mesa_top
        and "'libdrm_' + d[0]" in mesa_top
        and "dep_libdrm_amdgpu" in mesa_top,
    )
    check(
        "Mesa source creates the radeonsi DRI alias",
        "[with_gallium_radeonsi, ['radeonsi']]" in mesa_dri,
    )
    check(
        "Mesa source retains the AMDGPU DRM 3.54 runtime API gate",
        "if (info->drm_minor < 54)" in mesa_amd
        and "only compatible with 3.54.0" in mesa_amd,
    )
    patch_path = REPOSITORY / "pkgsrc/graphics/MesaLib/patches/patch-src_amd_common_ac_gpu_info.c"
    with tempfile.TemporaryDirectory(prefix="ember-mesa-drm-api-") as temp:
        work = Path(temp).resolve()
        source_path = work / "src/amd/common/ac_gpu_info.c"
        source_path.parent.mkdir(parents=True)
        source_path.write_text(mesa_amd)
        result = subprocess.run(
            ["patch", "-p0", "--batch", "--forward", "-i", str(patch_path)],
            cwd=work,
            capture_output=True,
            text=True,
            check=False,
        )
        check("Mesa NetBSD DRM compatibility patch applies to the pinned source", result.returncode == 0)
        patched = source_path.read_text()
    check(
        "Mesa uses DRM 3.36 only on NetBSD and retains the 3.54 gate elsewhere",
        "#if defined(__NetBSD__)\n   if (info->drm_minor < 36)" in patched
        and "#else\n   if (info->drm_minor < 54)" in patched
        and "#endif\n      return AC_QUERY_GPU_INFO_FAIL;" in patched,
    )
    check(
        "libdrm source installs linked AMDGPU library, header and pkg-config metadata",
        "link_with : libdrm" in drm_amdgpu
        and "install_headers('amdgpu.h', subdir : 'libdrm')" in drm_amdgpu
        and "pkg.generate(" in drm_amdgpu
        and "name : 'libdrm_amdgpu'" in drm_amdgpu
        and "version : '1.@0@.0'.format(patch_ver)" in drm_amdgpu,
    )
    check(
        "libdrm source installs amdgpu.ids only with the AMDGPU module",
        "if with_amdgpu" in drm_data
        and "'amdgpu.ids'" in drm_data
        and "install_dir : datadir_amdgpu" in drm_data,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--distfiles",
        type=Path,
        help="also verify pinned Mesa/libdrm archive contents in this distfiles directory",
    )
    parser.add_argument(
        "--skip-bmake",
        action="store_true",
        help="run static profile/PLIST checks without expanding Makefile conditions",
    )
    args = parser.parse_args()
    static_profile_checks()
    if not args.skip_bmake:
        profile_checks()
    if args.distfiles:
        source_checks(args.distfiles)
    if args.skip_bmake:
        print("PASS: static profile/PLIST checks; bmake selection expansion was not run")
    else:
        print("PASS: production graphics/Mesa/libdrm profile; no package build or hardware acceptance")


if __name__ == "__main__":
    main()
