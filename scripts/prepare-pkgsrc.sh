#!/bin/sh
# Prepare a pinned pkgsrc tree with the local EmberBSD recipes.
set -eu
umask 022

[ "$#" -ge 1 ] && [ "$#" -le 2 ] || {
    echo 'Usage: sh scripts/prepare-pkgsrc.sh ABSOLUTE_NEW_DIRECTORY [development-toolchain|common-build-tools|common-graphics|common-media|plasma-mobile|electron]' >&2
    exit 2
}
profile=${2:-}
case "$profile" in
    ''|development-toolchain|common-build-tools|common-graphics|common-media|plasma-mobile|electron) ;;
    *) echo 'Unknown profile.' >&2; exit 2 ;;
esac
firmware_toolchain=${EMBERBSD_FIRMWARE_TOOLCHAIN:-no}
case "$firmware_toolchain" in
    yes|no) ;;
    *) echo 'EMBERBSD_FIRMWARE_TOOLCHAIN must be yes or no.' >&2; exit 2 ;;
esac
destination=$1
case "$destination" in
    /*) ;;
    *) echo 'Destination must be absolute.' >&2; exit 2 ;;
esac
case "$destination" in
    *[!a-zA-Z0-9_./-]*) echo 'pkgsrc requires a path without whitespace or shell metacharacters.' >&2; exit 2 ;;
esac
[ ! -e "$destination" ] && [ ! -L "$destination" ] || { echo 'Destination already exists.' >&2; exit 2; }
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
# Common-tools pkgsrc infrastructure patches, in application order.
# The preflight and the export use this one list. The Boost patch is applied
# separately, after the toolkit recipes.
common_tools_deltas="python315-current-selection.patch current-libtool.patch libiconv-libtool-tag.patch pkgsrc-gts-libtool-tag.patch mozilla-rootcerts-cross-tools.patch pkgsrc-curl-security.patch pkgsrc-openssl-security.patch pkgsrc-cross-packages.patch pkgsrc-pkg-admin-destdir.patch pkgsrc-gettext-go-detection.patch pkgsrc-macho-load-commands.patch pkgsrc-cross-case-files.patch pkgsrc-check-error-dir.patch pkgsrc-wrkref-append-stream.patch pkgsrc-ncurses-terminfo-aliases.patch pkgsrc-ncurses-native-headers.patch pkgsrc-host-autoconf.patch pkgsrc-cwrappers-unwrap-boundary.patch pkgsrc-cross-passthrough-rpath.patch pkgsrc-bsdtar-common-zlib.patch pkgsrc-font-runtime-roles.patch pkgsrc-stale-metadata.patch pkgsrc-vala-valadoc-option.patch pkgsrc-vala-array-termination.patch pkgsrc-vala-dbus-fd-exhaustion.patch"
if [ "$firmware_toolchain" = yes ]; then
    [ -n "$profile" ] || {
        echo 'The firmware toolchain requires a development or common profile.' >&2; exit 2;
    }
    # This separate build-host checkpoint must be complete before it can
    # replace any pinned provider. Standard profiles do not select it.
    for recipe in devel/gmake sysutils/dtc cross/aarch64-none-elf-binutils cross/aarch64-none-elf-gcc; do
        source=$root/profiles/development-toolchain/recipes/$recipe
        for name in Makefile DESCR PLIST distinfo; do
            [ -s "$source/$name" ] || {
                echo "Incomplete GCC16 firmware toolchain: $recipe/$name. Complete the source checkpoint or use EMBERBSD_FIRMWARE_TOOLCHAIN=no." >&2
                exit 2
            }
        done
        [ "$(find "$source" -type l | wc -l | tr -d ' ')" = 0 ] || {
            echo "Unexpected firmware recipe link: $recipe" >&2; exit 2;
        }
        required=$(awk '/^SHA1 \(patch-/ { gsub(/[()]/, "", $2); print $2 }' "$source/distinfo")
        for name in $required; do
            [ -f "$source/patches/$name" ] || {
                echo "Missing firmware patch: $recipe/$name" >&2; exit 2;
            }
            recorded=$(awk -v name="($name)" '$1 == "SHA1" && $2 == name { print $4 }' "$source/distinfo")
            computed=$(sed '/[$]NetBSD.*/d' "$source/patches/$name" | shasum -a 1 | awk '{ print $1 }')
            [ "$recorded" = "$computed" ] || {
                echo "Firmware patch checksum differs: $recipe/$name" >&2; exit 2;
            }
        done
    done
    [ -s "$root/profiles/development-toolchain/recipes/devel/gmake/options.mk" ] || {
        echo 'Incomplete firmware gmake recipe: options.mk' >&2; exit 2;
    }
    grep -Eq '^DISTNAME=[[:space:]]*gcc-16[.]' \
        "$root/profiles/development-toolchain/recipes/cross/aarch64-none-elf-gcc/Makefile" || {
        echo 'The firmware compiler must use the common GCC16 line.' >&2; exit 2;
    }
fi
expected=$(git -C "$root" ls-files --stage -- upstream/pkgsrc | awk '$1 == "160000" { print $2 }')
actual=$(git -C "$root/upstream/pkgsrc" rev-parse HEAD)
[ -n "$expected" ] && [ "$actual" = "$expected" ] || {
    echo 'Initialize the pinned submodule with git submodule update --init upstream/pkgsrc.' >&2
    exit 2
}
if [ "$profile" = development-toolchain ] || [ "$profile" = common-build-tools ] || [ "$profile" = common-graphics ] || [ "$profile" = common-media ] || [ "$profile" = plasma-mobile ]; then
    # Tcl and Tk share one current release selection and the standard prefix.
    for pair in common-build-tools:lang/tcl common-graphics:x11/tk; do
        owner=${pair%%:*}
        recipe=${pair#*:}
        source=$root/profiles/$owner/recipes/$recipe
        for name in Makefile Makefile.version DESCR PLIST options.mk buildlink3.mk distinfo patches/patch-target-platform; do
            [ -s "$source/$name" ] || { echo "Incomplete Tcl/Tk recipe: $recipe/$name" >&2; exit 2; }
        done
        if [ "$recipe" = lang/tcl ]; then
            approved='patch-doc_Encoding.3 patch-itcl-configured-ldflags patch-sqlite-system-extern patch-target-platform patch-thread-darwin-install-name patch-unix-wait-timeout'
            patch_count=6
        else
            approved='patch-target-platform'
            patch_count=1
        fi
        [ "$(find "$source" -type l | wc -l | tr -d ' ')" = 0 ] &&
            [ "$(find "$source/patches" -name 'patch-*' | wc -l | tr -d ' ')" = "$patch_count" ] &&
            [ "$(awk '/^SHA1 \(patch-/ { n++ } END { print n+0 }' "$source/distinfo")" = "$patch_count" ] || {
            echo "Unexpected Tcl/Tk patch inventory: $recipe" >&2; exit 2;
        }
        for name in $approved; do
            [ -s "$source/patches/$name" ] || { echo "Missing Tcl/Tk patch: $recipe/$name" >&2; exit 2; }
            recorded=$(awk -v name="($name)" '$1 == "SHA1" && $2 == name { print $4 }' "$source/distinfo")
            computed=$(sed '/[$]NetBSD.*/d' "$source/patches/$name" | shasum -a 1 | awk '{ print $1 }')
            [ "$recorded" = "$computed" ] || { echo "Tcl/Tk patch checksum differs: $recipe/$name" >&2; exit 2; }
        done
    done
    tcl_pin=$(awk -F '\t' '$1 == "tcl9.1.0-src.tar.gz" { print $2 ":" $3 }' "$root/profiles/common-build-tools/sources.tsv")
    [ "$tcl_pin" = '536c45543f64d6eb11832d97ba3494aacff046fbc5040273bd55258d0e448ff1:https://downloads.sourceforge.net/project/tcl/Tcl/9.1.0/tcl9.1.0-src.tar.gz' ] || {
        echo 'Invalid current Tcl source pin.' >&2; exit 2;
    }
    for recipe in lang/tcl lang/python315 lang/perl5 lang/rust-bin lang/rust-std-aarch64-netbsd lang/rust-std-x86_64-netbsd devel/meson devel/flex lang/llvm lang/clang devel/lld devel/py-llvm-lit devel/binutils devel/py-mako devel/zlib devel/abseil devel/protobuf textproc/py-markupsafe textproc/py-yaml textproc/groff net/mDNSResponder textproc/icu; do
        source=$root/profiles/common-build-tools/recipes/$recipe
        [ -f "$source/Makefile" ] && [ -f "$source/PLIST" ] && \
            [ -f "$source/distinfo" ] || {
            echo "Incomplete common-tools recipe: $recipe" >&2; exit 2;
        }
        if [ "$recipe" = lang/rust-bin ]; then
            [ -s "$source/files/darwin-llvm.py" ] || {
                echo 'Missing Darwin Rust LLVM helper.' >&2; exit 2;
            }
        fi
        required=$(awk '/^SHA1 \(patch-/ { gsub(/[()]/, "", $2); print $2 }' "$source/distinfo")
        case "$recipe" in
            lang/rust-bin|lang/rust-std-x86_64-netbsd|devel/lld|devel/py-llvm-lit|devel/py-mako|textproc/py-markupsafe|textproc/py-yaml) ;;
            *) [ -n "$required" ] || { echo "No patch checksums: $recipe" >&2; exit 2; } ;;
        esac
        for name in $required; do
            [ -f "$source/patches/$name" ] || {
                echo "Missing required patch: $recipe/$name" >&2; exit 2;
            }
        done
        if [ "$recipe" = net/mDNSResponder ]; then
            for name in DESCR buildlink3.mk builtin.mk files/mdnsd.sh; do
                [ -s "$source/$name" ] || { echo "Incomplete mDNSResponder recipe: $name" >&2; exit 2; }
            done
            [ "$(find "$source" -type l | wc -l | tr -d ' ')" = 0 ] &&
                [ "$(find "$source/patches" -name 'patch-*' | wc -l | tr -d ' ')" = 9 ] &&
                [ "$(printf '%s\n' "$required" | awk 'NF { n++ } END { print n+0 }')" = 9 ] || {
                echo 'Unexpected mDNSResponder patch inventory.' >&2; exit 2;
            }
            for name in $required; do
                recorded=$(awk -v name="($name)" '$1 == "SHA1" && $2 == name { print $4 }' "$source/distinfo")
                computed=$(sed '/[$]NetBSD.*/d' "$source/patches/$name" | shasum -a 1 | awk '{ print $1 }')
                [ "$recorded" = "$computed" ] || { echo "mDNSResponder patch checksum differs: $name" >&2; exit 2; }
            done
            mdns_pin=$(awk -F '\t' '$1 == "mDNSResponder-2881.120.11.tar.gz" { print $2 ":" $3 }' "$root/profiles/common-build-tools/sources.tsv")
            [ "$mdns_pin" = 'f665cf02b5c930f9b70fb39b7567f03dd821997594c56ce399098eaa0372fb15:https://github.com/apple-oss-distributions/mDNSResponder/archive/refs/tags/mDNSResponder-2881.120.11.tar.gz' ] || {
                echo 'Invalid current mDNSResponder source pin.' >&2; exit 2;
            }
        fi
        if [ "$recipe" = textproc/icu ]; then
            for name in DESCR buildlink3.mk PLIST.full-cross PLIST.runtime files/cross-metadata.awk files/sdk_source.py files/select-stage.py; do
                [ -s "$source/$name" ] || { echo "Incomplete ICU recipe: $name" >&2; exit 2; }
            done
            [ "$(find "$source" -type l | wc -l | tr -d ' ')" = 0 ] &&
                [ "$(find "$source/patches" -name 'patch-*' | wc -l | tr -d ' ')" = 20 ] &&
                [ "$(printf '%s\n' "$required" | awk 'NF { n++ } END { print n+0 }')" = 20 ] || {
                echo 'Unexpected ICU patch inventory.' >&2; exit 2;
            }
            for name in $required; do
                recorded=$(awk -v name="($name)" '$1 == "SHA1" && $2 == name { print $4 }' "$source/distinfo")
                computed=$(sed '/[$]NetBSD.*/d' "$source/patches/$name" | shasum -a 1 | awk '{ print $1 }')
                [ "$recorded" = "$computed" ] || { echo "ICU patch checksum differs: $name" >&2; exit 2; }
            done
        fi
        if [ "$recipe" = lang/llvm ]; then
            for name in PLIST.runtime files/select-package-stage.py files/sdk_source.py files/reuse-package-stage.py files/prepare-reuse-inputs.py; do
                [ -s "$source/$name" ] || {
                    echo "Incomplete LLVM recipe: $name" >&2; exit 2;
                }
            done
        fi
        if [ "$recipe" = devel/abseil ]; then
            [ -f "$source/DESCR" ] && [ -f "$source/buildlink3.mk" ] &&
                [ -f "$source/patches/patch-absl_debugging_CMakeLists.txt" ] &&
                grep -q '^SHA1 (patch-absl_debugging_CMakeLists.txt) = ' "$source/distinfo" &&
                [ -f "$source/patches/patch-absl_debugging_internal_stacktrace_config.h" ] &&
                grep -q '^SHA1 (patch-absl_debugging_internal_stacktrace_config.h) = ' "$source/distinfo" || {
                echo 'Incomplete Abseil cross metadata repair.' >&2; exit 2;
            }
            [ "$(find "$source" -type l | wc -l | tr -d ' ')" = 0 ] &&
                [ "$(find "$source/patches" -name 'patch-*' | wc -l | tr -d ' ')" = 7 ] &&
                [ "$(printf '%s\n' "$required" | awk 'NF { n++ } END { print n+0 }')" = 7 ] || {
                echo 'Unexpected Abseil patch inventory.' >&2; exit 2;
            }
            for name in $required; do
                recorded=$(awk -v name="($name)" '$1 == "SHA1" && $2 == name { print $4 }' "$source/distinfo")
                computed=$(sed '/[$]NetBSD.*/d' "$source/patches/$name" | shasum -a 1 | awk '{ print $1 }')
                [ "$recorded" = "$computed" ] || { echo "Abseil patch checksum differs: $name" >&2; exit 2; }
            done
        fi
        if [ "$recipe" = devel/protobuf ]; then
            for name in DESCR buildlink3.mk host-protoc.mk PLIST.runtime files/select-package-stage.pl; do
                [ -f "$source/$name" ] || { echo "Incomplete protobuf recipe: $name" >&2; exit 2; }
            done
            fixes='patch-src_google_protobuf_compiler_main.cc patch-upb_message_array_oom patch-upb_message_copy.c patch-upb_message_string_oom'
            for name in $fixes; do
                [ -L "$source/patches/$name" ] &&
                [ "$(readlink "$source/patches/$name")" = "../../../../../../probes/kicad/protobuf/patches/$name" ] || {
                    echo "Unexpected protobuf patch origin: $name" >&2; exit 2;
                }
                grep -q "^SHA1 ($name) = " "$source/distinfo" || exit 2
            done
            [ "$(find "$source" -type l | wc -l | tr -d ' ')" = 4 ] &&
                [ "$(find "$source/patches" -name 'patch-*' | wc -l | tr -d ' ')" = 6 ] &&
                [ "$(printf '%s\n' "$required" | awk 'NF { n++ } END { print n+0 }')" = 6 ] || {
                echo 'Unexpected protobuf patch inventory.' >&2; exit 2;
            }
            for name in $required; do
                recorded=$(awk -v name="($name)" '$1 == "SHA1" && $2 == name { print $4 }' "$source/distinfo")
                computed=$(sed '/[$]NetBSD.*/d' "$source/patches/$name" | shasum -a 1 | awk '{ print $1 }')
                [ "$recorded" = "$computed" ] || { echo "Protobuf patch checksum differs: $name" >&2; exit 2; }
            done
        fi
    done
    icu_pin=$(awk -F '\t' '$1 == "icu4c-78.3-sources.tgz" { print $2 ":" $3 }' "$root/profiles/common-build-tools/sources.tsv")
    [ "$icu_pin" = '3a2e7a47604ba702f345878308e6fefeca612ee895cf4a5f222e7955fabfe0c0:https://github.com/unicode-org/icu/releases/download/release-78.3/icu4c-78.3-sources.tgz' ] || {
        echo 'Invalid ICU source pin.' >&2; exit 2;
    }
    for icu_sdk_file in Makefile buildlink3.mk DESCR PLIST; do
        [ -s "$root/profiles/common-build-tools/recipes/textproc/icu-devel/$icu_sdk_file" ] || {
            echo "Incomplete ICU SDK recipe: $icu_sdk_file" >&2; exit 2;
        }
    done
    [ "$(find "$root/profiles/common-build-tools/recipes/textproc/icu-devel" -type l | wc -l | tr -d ' ')" = 0 ] || {
        echo 'Unexpected ICU SDK recipe link.' >&2; exit 2;
    }
    for protobuf_sdk_file in Makefile buildlink3.mk DESCR PLIST; do
        [ -s "$root/profiles/common-build-tools/recipes/devel/protobuf-devel/$protobuf_sdk_file" ] || {
            echo "Incomplete protobuf SDK recipe: $protobuf_sdk_file" >&2; exit 2;
        }
    done
    [ "$(find "$root/profiles/common-build-tools/recipes/devel/protobuf-devel" -type l | wc -l | tr -d ' ')" = 0 ] || {
        echo 'Unexpected protobuf SDK recipe link.' >&2; exit 2;
    }
    for delta in $common_tools_deltas pkgsrc-boost-cross-target.patch; do
        [ -s "$root/profiles/common-build-tools/patches/$delta" ] || {
            echo "Missing common-tools infrastructure patch: $delta" >&2; exit 2;
        }
    done
    [ -x "$root/profiles/common-build-tools/cross/sort-c.sh" ] || {
        echo 'Missing executable common-tools cross sort helper.' >&2; exit 2;
    }
    [ -s "$root/profiles/common-build-tools/cross/mk.conf" ] || exit 2
    [ -s "$root/profiles/common-build-tools/cross/check-files-case.sh" ] || exit 2
    [ -s "$root/profiles/common-build-tools/cross/gcc16-external-runtime.sh" ] || exit 2
fi
if [ "$profile" = common-build-tools ] || [ "$profile" = common-graphics ] || [ "$profile" = common-media ] || [ "$profile" = plasma-mobile ]; then
    swig=$root/profiles/common-build-tools/recipes/devel/swig4
    for name in Makefile DESCR PLIST distinfo patches/patch-CCache_ccache.c; do
        [ -s "$swig/$name" ] || { echo "Incomplete current SWIG recipe: $name" >&2; exit 2; }
    done
    [ "$(find "$swig" -type l | wc -l | tr -d ' ')" = 0 ] &&
        [ "$(find "$swig/patches" -name 'patch-*' | wc -l | tr -d ' ')" = 1 ] || {
        echo 'Unexpected SWIG patch inventory.' >&2; exit 2;
    }
    recorded=$(awk '$1 == "SHA1" && $2 == "(patch-CCache_ccache.c)" { print $4 }' "$swig/distinfo")
    computed=$(sed '/[$]NetBSD.*/d' "$swig/patches/patch-CCache_ccache.c" | shasum -a 1 | awk '{ print $1 }')
    [ "$recorded" = "$computed" ] || { echo 'SWIG patch checksum differs.' >&2; exit 2; }
    swig_pin=$(awk -F '\t' '$1 == "swig-4.5.1.tar.gz" { print $2 ":" $3 }' "$root/profiles/common-build-tools/sources.tsv")
    [ "$swig_pin" = '7fec50b27deddab5455a9633780b6341eddfb96215a7619e93a76eb27178f653:https://downloads.sourceforge.net/project/swig/swig/swig-4.5.1/swig-4.5.1.tar.gz' ] || {
        echo 'Invalid current SWIG source pin.' >&2; exit 2;
    }
    # One source owner supplies PCRE2 to SWIG and the graphics dependency graph.
    shared_pcre2=$root/profiles/common-graphics/recipes/devel/pcre2
    for name in Makefile DESCR PLIST distinfo buildlink3.mk options.mk; do
        [ -s "$shared_pcre2/$name" ] || { echo "Incomplete shared PCRE2 recipe: $name" >&2; exit 2; }
    done
    [ "$(find "$shared_pcre2" -type l | wc -l | tr -d ' ')" = 0 ] || {
        echo 'Unexpected shared PCRE2 recipe link.' >&2; exit 2;
    }
    pcre2_pin=$(awk -F '\t' '$1 == "devel/pcre2" { print $2 ":" $3 ":" $4 }' "$root/profiles/common-graphics/sources.tsv")
    [ "$pcre2_pin" = 'pcre2-10.49.tar.gz:929f0b20e62879252a15886b06c89f1edef61a363cbd5826fb041080a5e557ae:https://github.com/PCRE2Project/pcre2/releases/download/pcre2-10.49/pcre2-10.49.tar.gz' ] || {
        echo 'Invalid shared PCRE2 source pin.' >&2; exit 2;
    }
    for llvm_sdk_file in Makefile buildlink3.mk DESCR PLIST; do
        [ -s "$root/profiles/common-build-tools/recipes/lang/llvm-devel/$llvm_sdk_file" ] || {
            echo "Incomplete LLVM SDK recipe: $llvm_sdk_file" >&2; exit 2;
        }
    done
fi
if [ "$profile" = common-media ] || [ "$profile" = plasma-mobile ]; then
    media=$root/profiles/common-media
    sh "$media/validate.sh"
fi
if [ "$profile" = plasma-mobile ]; then
    toolkit=$root/probes/plasma-mobile/toolkit
    toolkit_inventory=$(sh "$toolkit/validate.sh" --inventory "$toolkit")
fi
if [ "$profile" = common-graphics ] || [ "$profile" = common-media ] || [ "$profile" = plasma-mobile ]; then
    graphics=$root/profiles/common-graphics
    [ -s "$graphics/cross/current-cups.patch" ] || {
        echo 'Missing common CUPS dependency patch.' >&2; exit 2;
    }
    awk -F '\t' '
        /^#/ || /^$/ { next }
        NF != 4 || ($1 != "security/libsecret" && $1 != "security/mit-krb5" && $1 != "graphics/MesaLib" && $1 != "x11/libdrm" &&
            $1 != "devel/wayland" && $1 != "devel/wayland-protocols" &&
            $1 != "x11/xorgproto" && $1 != "devel/libudev-bsd" &&
            $1 != "wayland/wlroots" && $1 != "wayland/labwc" && $1 != "wayland/sway" && $1 != "wayland/swaylock" && $1 != "devel/libevdev-chunk" && $1 != "textproc/json-c" && $1 != "x11/xkeyboard-config" && $1 != "devel/input-headers" && $1 != "x11/libxkbcommon" && $1 != "sysutils/hwdata" && $1 != "sysutils/seatd" && $1 != "x11/libdisplay-info" && $1 != "graphics/libliftoff" && $1 != "devel/libopeninput" &&
            $1 != "net/nng" && $1 != "math/eigen3" && $1 != "textproc/rapidjson" && $1 != "cad/ng-spice" && $1 != "cad/kicad10" && $1 != "cad/occt" && $1 != "devel/glib2" && $1 != "devel/libffi" &&
            $1 != "devel/pcre2" && $1 != "textproc/fmtlib" && $1 != "x11/libspnav" &&
            $1 != "x11/pixman" && $1 != "graphics/cairo" &&
            $1 != "fonts/harfbuzz" &&
            $1 != "converters/fribidi" &&
            $1 != "graphics/openexr" && $1 != "graphics/OpenJPH" && $1 != "graphics/jbigkit" && $1 != "graphics/lerc" && $1 != "graphics/png" && $1 != "graphics/freeimage" && $1 != "graphics/freeimageplus" && $1 != "graphics/libraw" &&
            $1 != "graphics/freetype2" &&
            $1 != "archivers/lzo" && $1 != "x11/libXt" && $1 != "devel/pango" && $1 != "devel/libsfdo" && $1 != "sysutils/dbus" && $1 != "devel/gobject-introspection" && $1 != "graphics/librsvg" && $1 != "multimedia/dav1d" && $1 != "devel/xxhash" && $1 != "graphics/gdk-pixbuf2" && $1 != "databases/shared-mime-info" && $1 != "x11/gtk3" && $1 != "x11/wxGTK32" && $1 != "www/webkit-gtk41" && $1 != "www/webkit-gtk60" && $1 != "devel/at-spi2-core" && $1 != "x11/tk") ||
            $2 !~ /^[a-zA-Z0-9][a-zA-Z0-9._+-]*\.tar\.(xz|gz|bz2)$/ ||
            length($3) != 64 || $3 !~ /^[0-9a-f]+$/ ||
            $4 !~ /^https:\/\// || seen[$1]++ { bad=1 }
        END { if (bad || !seen["graphics/MesaLib"] || !seen["x11/libdrm"] ||
            !seen["devel/wayland"] || !seen["devel/wayland-protocols"] ||
            !seen["x11/xorgproto"] || !seen["devel/libudev-bsd"] ||
            !seen["wayland/wlroots"] || !seen["wayland/labwc"] || !seen["wayland/sway"] || !seen["wayland/swaylock"] || !seen["devel/libevdev-chunk"] || !seen["textproc/json-c"] || !seen["x11/xkeyboard-config"] || !seen["devel/input-headers"] || !seen["x11/libxkbcommon"] || !seen["sysutils/hwdata"] || !seen["sysutils/seatd"] || !seen["x11/libdisplay-info"] || !seen["graphics/libliftoff"] || !seen["devel/libopeninput"] ||
            !seen["net/nng"] || !seen["math/eigen3"] || !seen["textproc/rapidjson"] || !seen["cad/ng-spice"] || !seen["cad/kicad10"] || !seen["cad/occt"] || !seen["devel/glib2"] || !seen["devel/libffi"] ||
            !seen["devel/pcre2"] || !seen["textproc/fmtlib"] || !seen["x11/libspnav"] ||
            !seen["x11/pixman"] || !seen["graphics/cairo"] ||
            !seen["fonts/harfbuzz"] ||
            !seen["converters/fribidi"] ||
            !seen["graphics/openexr"] || !seen["graphics/OpenJPH"] || !seen["graphics/jbigkit"] || !seen["graphics/lerc"] || !seen["graphics/png"] || !seen["graphics/freeimage"] || !seen["graphics/freeimageplus"] || !seen["graphics/libraw"] ||
            !seen["graphics/freetype2"] ||
            !seen["archivers/lzo"] || !seen["x11/libXt"] || !seen["devel/pango"] || !seen["devel/libsfdo"] || !seen["sysutils/dbus"] || !seen["devel/gobject-introspection"] || !seen["graphics/librsvg"] || !seen["multimedia/dav1d"] || !seen["devel/xxhash"] || !seen["graphics/gdk-pixbuf2"] || !seen["databases/shared-mime-info"] || !seen["x11/gtk3"] || !seen["x11/wxGTK32"] || !seen["www/webkit-gtk41"] || !seen["www/webkit-gtk60"] || !seen["devel/at-spi2-core"] || !seen["x11/tk"] || !seen["security/mit-krb5"] || !seen["security/libsecret"]) exit 1 }
    ' "$graphics/sources.tsv" || { echo 'Invalid common graphics manifest.' >&2; exit 2; }
    while IFS="$(printf '\t')" read -r recipe archive sha url; do
        case "$recipe" in
            ''|'#'*) continue ;;
            x11/tk) pin='tk9.1.0-src.tar.gz:772ce7a97c07c2db4c957c93af7ab4dff4bd3037772836b6afbcd0974023b3d6:https://downloads.sourceforge.net/project/tcl/Tcl/9.1.0/tk9.1.0-src.tar.gz' ;;
            net/nng) pin='nng-1.12.3.tar.gz:036a925790034efdeef8a6803f3e4402c3ab509383326f8bc2f15ecee75a2fa2:https://github.com/nanomsg/nng/archive/refs/tags/v1.12.3.tar.gz' ;;
            math/eigen3) pin='eigen-5.0.1.tar.gz:e9c326dc8c05cd1e044c71f30f1b2e34a6161a3b6ecf445d56b53ff1669e3dec:https://gitlab.com/libeigen/eigen/-/archive/5.0.1/eigen-5.0.1.tar.gz' ;;
            textproc/rapidjson) pin='rapidjson-1.1.0.20250205-24b5e7a8b27f42fa16b96fc70aade9106cf7102f.tar.gz:2d2601a82d2d3b7e143a3c8d43ef616671391034bc46891a9816b79cf2d3e7a8:https://github.com/Tencent/rapidjson/archive/24b5e7a8b27f42fa16b96fc70aade9106cf7102f.tar.gz' ;;
            cad/occt) pin='OCCT-8.0.1.tar.gz:6297cc55a1720523a437c54d07dc16b9da8c5f5ab5800da3c6ebded568d53c18:https://github.com/Open-Cascade-SAS/OCCT/archive/refs/tags/V8.0.1.tar.gz' ;;
            cad/kicad10) pin='kicad-10.0.7.tar.bz2:2fd6e4a0f6212fe0d26582be01e85c4d6fd59ce664018c0ffb94b2f1b074be51:https://gitlab.com/kicad/code/kicad/-/archive/10.0.7/kicad-10.0.7.tar.bz2' ;;
            cad/ng-spice) pin='ngspice-47.tar.gz:894e649651f1838a14095e5a5439e7d3aa63e87ede14d283173fda4fcdef675f:https://downloads.sourceforge.net/project/ngspice/ng-spice-rework/47/ngspice-47.tar.gz' ;;
            www/webkit-gtk41|www/webkit-gtk60) pin='webkitgtk-2.54.1.tar.xz:ea0bbb02dbdbc596874a4e7ad35b66645b3e0a232bd0e4081de5ed92eb0a397d:https://webkitgtk.org/releases/webkitgtk-2.54.1.tar.xz' ;;
            x11/libspnav) pin='libspnav-1.2.tar.gz:093747e7e03b232e08ff77f1ad7f48552c06ac5236316a5012db4269951c39db:https://github.com/FreeSpacenav/libspnav/releases/download/v1.2/libspnav-1.2.tar.gz' ;;
            x11/wxGTK32) pin='wxWidgets-3.2.12.tar.bz2:a62719bb5e1dcc41c1a6fc1eecd499c7ee8521f70402c7b1bb3342a1e16344e0:https://github.com/wxWidgets/wxWidgets/releases/download/v3.2.12/wxWidgets-3.2.12.tar.bz2' ;;
            x11/gtk3) pin='gtk-3.24.52.tar.xz:80931fa472a77b9a164f6740e3c0b444fac6770054632d35a7ff9d679e5e7b9f:https://download.gnome.org/sources/gtk/3.24/gtk-3.24.52.tar.xz' ;;
            devel/at-spi2-core) pin='at-spi2-core-2.62.1.tar.xz:cca6b6a86e4389d89b370288761ce2385ddeceb10c4412da78689bc30c88af2d:https://download.gnome.org/sources/at-spi2-core/2.62/at-spi2-core-2.62.1.tar.xz' ;;
            security/mit-krb5) pin='krb5-1.22.2.tar.gz:3243ffbc8ea4d4ac22ddc7dd2a1dc54c57874c40648b60ff97009763554eaf13:https://web.mit.edu/kerberos/dist/krb5/1.22/krb5-1.22.2.tar.gz' ;;
            security/libsecret) pin='libsecret-0.20.5.tar.xz:3fb3ce340fcd7db54d87c893e69bfc2b1f6e4d4b279065ffe66dac9f0fd12b4d:https://download.gnome.org/sources/libsecret/0.20/libsecret-0.20.5.tar.xz' ;;
            graphics/MesaLib) pin='mesa-26.2.4.tar.xz:bce5f7fbebb934373b86c999a064d52fb5065878dc57f287f95346648ec832e9:https://archive.mesa3d.org/mesa-26.2.4.tar.xz' ;;
            x11/libdrm) pin='libdrm-2.4.134.tar.xz:ac5e74d157830eb8bee44c6a6bf3ad49774ef0dd2a72bdad74a8f20308b52a95:https://dri.freedesktop.org/libdrm/libdrm-2.4.134.tar.xz' ;;
            devel/wayland) pin='wayland-1.26.0.tar.xz:64176eaa46e4969903e286f8e5ef8331affc17fdf03ac9b58381d2b23162b7a3:https://gitlab.freedesktop.org/wayland/wayland/-/releases/1.26.0/downloads/wayland-1.26.0.tar.xz' ;;
            devel/wayland-protocols) pin='wayland-protocols-1.49.tar.xz:ec4c8f74942d6dff7ace8b4ce4764f0ef9ff618a935d974ea77edee2ad240b14:https://gitlab.freedesktop.org/wayland/wayland-protocols/-/releases/1.49/downloads/wayland-protocols-1.49.tar.xz' ;;
            x11/xorgproto) pin='xorgproto-2026.1.tar.xz:f9bfe4a9ed8c8ab9d2a3b0d49797f046052dadd06b7a8b45dbffaffb137e8290:https://xorg.freedesktop.org/archive/individual/proto/xorgproto-2026.1.tar.xz' ;;
            devel/libudev-bsd) pin='libudev-bsd-0.7.0.1.tar.gz:c4a8c30781438a76720f77876ca362b7a5ecd41d15cd603d52097c2cb10425f0:https://github.com/kikadf/libudev-bsd/archive/v0.7.0.1.tar.gz' ;;
            wayland/labwc) pin='labwc-0.20.2.tar.gz:fae023b6fe022f7057556707a17cdb2d98e0138c5dffaedaa1dade975699f9e8:https://github.com/labwc/labwc/archive/0.20.2.tar.gz' ;;
            wayland/sway) pin='sway-1.12.tar.gz:29ca7caac960d13e02d8213418d91a5422c7c23102a283ceab944c57c5e1efcf:https://github.com/swaywm/sway/archive/refs/tags/1.12.tar.gz' ;;
            wayland/swaylock) pin='swaylock-1.8.6.tar.gz:904376fd012bfff888d042606539c677d90e11f8beeeccc50a9fe387fc41a686:https://github.com/swaywm/swaylock/archive/refs/tags/v1.8.6.tar.gz' ;;
            textproc/json-c) pin='json-c-0.19.tar.gz:37ad0249902e301bd9052bf712e511fcc6acff4ecaad4b5900aad9ce564e26de:https://s3.amazonaws.com/json-c_releases/releases/json-c-0.19.tar.gz' ;;
            devel/libevdev-chunk) pin='libevdev-openbsd-20231112.tar.gz:2689f7bc4c11d3d40dd06ed7f8ca528fb92a24966a8a0031ac3f64956988d319:https://code.tetaneutral.net/mherrb/libevdev-openbsd/archive/20231112.tar.gz' ;;
            wayland/wlroots) pin='wlroots-0.20.2.tar.gz:972c7ac44b17828f4702bfae7cd8347346a3fb5b2c1076cfa2c3fcedac5ec343:https://gitlab.freedesktop.org/wlroots/wlroots/-/archive/0.20.2/wlroots-0.20.2.tar.gz' ;;
            x11/xkeyboard-config) pin='xkeyboard-config-2.48.tar.xz:b77041324f0109f77161ee43743fe04baa485866af8460d31e476ad3f7648fd5:https://xorg.freedesktop.org/archive/individual/data/xkeyboard-config/xkeyboard-config-2.48.tar.xz' ;;
            devel/input-headers) pin='libopeninput-1.31.3-10995219206280da0f1a3ba124abe4c8ef89e021.tar.gz:fbba09ed60a9a411b9ae7ee5c92daf069a3b4926ad052ac8cbcfb7c3ff82abbf:https://github.com/sizeofvoid/libopeninput/archive/10995219206280da0f1a3ba124abe4c8ef89e021.tar.gz' ;;
            sysutils/hwdata) pin='hwdata-0.412.tar.gz:f0c64cd7e31d70a5fb3a52e53ab50a61e74c0421a6381eaa45114eec3bde5fe7:https://github.com/vcrhonek/hwdata/archive/v0.412.tar.gz' ;;
            sysutils/seatd) pin='seatd-0.9.3.tar.gz:302564d54d8e28191fadfd734f2675ecb0c9e0615a58011b89ef15dfa4dbaa96:https://github.com/kennylevinsen/seatd/archive/refs/tags/0.9.3.tar.gz' ;;
            x11/libdisplay-info) pin='libdisplay-info-0.4.0.tar.xz:43b180baa143e2035654759d84e2b2f5ee77d5fe817c423838c7fe59c0d68459:https://gitlab.freedesktop.org/emersion/libdisplay-info/-/releases/0.4.0/downloads/libdisplay-info-0.4.0.tar.xz' ;;
            graphics/libliftoff) pin='libliftoff-0.5.0.tar.gz:3309218c3137a70faada653690802b514e4e46d9b38e7d9d5948ffcc4831f3b1:https://gitlab.freedesktop.org/emersion/libliftoff/-/archive/v0.5.0/libliftoff-v0.5.0.tar.gz' ;;
            devel/libopeninput) pin='libopeninput-1.31.3-10995219206280da0f1a3ba124abe4c8ef89e021.tar.gz:fbba09ed60a9a411b9ae7ee5c92daf069a3b4926ad052ac8cbcfb7c3ff82abbf:https://github.com/sizeofvoid/libopeninput/archive/10995219206280da0f1a3ba124abe4c8ef89e021.tar.gz' ;;
            x11/libxkbcommon) pin='xkbcommon-1.13.2.tar.gz:acc4d5f7c3cbba5f9f8d08d8bdbeede84ecede46792f47929aa9321873385528:https://github.com/xkbcommon/libxkbcommon/archive/xkbcommon-1.13.2.tar.gz' ;;
            devel/glib2) pin='glib-2.90.1.tar.xz:93c941aa17d5eb1d53fe838365f29a8b4e539c222a256d974ec8f30fc413e396:https://download.gnome.org/sources/glib/2.90/glib-2.90.1.tar.xz' ;;
            devel/libffi) pin='libffi-3.8.0.tar.gz:7da3e2d9a171eb0a038f592ecad3ff2bb2550f3496d87b3b29ad0cf4430c0db4:https://github.com/libffi/libffi/releases/download/v3.8.0/libffi-3.8.0.tar.gz' ;;
            devel/pcre2) pin='pcre2-10.49.tar.gz:929f0b20e62879252a15886b06c89f1edef61a363cbd5826fb041080a5e557ae:https://github.com/PCRE2Project/pcre2/releases/download/pcre2-10.49/pcre2-10.49.tar.gz' ;;
            textproc/fmtlib) pin='fmt-12.2.0.tar.gz:8b852bb5aa6e7d8564f9e81394055395dd1d1936d38dfd3a17792a02bebd7af0:https://github.com/fmtlib/fmt/archive/refs/tags/12.2.0.tar.gz' ;;
            x11/pixman) pin='pixman-0.46.4.tar.xz:a098c33924754ad43f981b740f6d576c70f9ed1006e12221b1845431ebce1239:https://xorg.freedesktop.org/archive/individual/lib/pixman-0.46.4.tar.xz' ;;
            graphics/cairo) pin='cairo-1.18.6.tar.xz:1c767308174337a74694da0f3ec069c271452163a1ef4540964c50c301f157d4:https://cairographics.org/releases/cairo-1.18.6.tar.xz' ;;
            fonts/harfbuzz) pin='harfbuzz-14.6.0.tar.xz:d07a007327277708a2a73ae437887cdbaf282937f6d03ca5467723e9099af586:https://github.com/harfbuzz/harfbuzz/releases/download/14.6.0/harfbuzz-14.6.0.tar.xz' ;;
            converters/fribidi) pin='fribidi-1.0.17.tar.xz:6949dcde27d41cebad1fd741fcafc36d55a1020d2d872d4a6eb3914caabbada2:https://github.com/fribidi/fribidi/releases/download/v1.0.17/fribidi-1.0.17.tar.xz' ;;
            graphics/freeimage|graphics/freeimageplus) pin='FreeImage-3.19.25-linux-source.tar.gz:dab013044c3d9122b0a93cee7b53a656426bccc571d3d46880dd8d90a10d1968:https://github.com/danoli3/FreeImage/releases/download/3.19.25/FreeImage-3.19.25-linux-source.tar.gz' ;;
            graphics/openexr) pin='openexr-3.5.2.tar.gz:85a291b9b8563fabef1aa3f6e912d744ce1d4b9fd5a8f978eda194cd51b15ae9:https://github.com/AcademySoftwareFoundation/openexr/archive/refs/tags/v3.5.2.tar.gz' ;;
            graphics/OpenJPH) pin='OpenJPH-0.32.0.tar.gz:5cb1ebe18e5ee1322d23ff2130b37562d447d1ad5586c3d16cf84be3ae30f719:https://github.com/aous72/OpenJPH/archive/refs/tags/0.32.0.tar.gz' ;;
            graphics/lerc) pin='lerc-4.2.0.tar.gz:a1fb593ed1fcb5b38800caf3c4454f872745202e961d00d745e53d81447e17c9:https://github.com/Esri/lerc/archive/v4.2.0.tar.gz' ;;
            graphics/libraw) pin='LibRaw-0.22.2.tar.gz:de86b035655accff8d4010f1a221fdf50d353cb7b1422ba26f14a0db92612cfa:https://www.libraw.org/data/LibRaw-0.22.2.tar.gz' ;;
            graphics/jbigkit) pin='jbigkit-2.2.tar.gz:3302109c93b7befbffa3cfe8bceb4355f19dea0ee7dcb5f33710b1648bf6645c:https://www.cl.cam.ac.uk/~mgk25/jbigkit/download/jbigkit-2.2.tar.gz' ;;
            graphics/png) pin='libpng-1.6.59.tar.xz:d80dd2a38a37f803cb9b6ac7b14bd6e74ddc3b654780a8380bdf93523fdb4389:https://downloads.sourceforge.net/project/libpng/libpng16/1.6.59/libpng-1.6.59.tar.xz' ;;
            graphics/freetype2) pin='freetype-2.14.3.tar.xz:36bc4f1cc413335368ee656c42afca65c5a3987e8768cc28cf11ba775e785a5f:https://download.savannah.gnu.org/releases/freetype/freetype-2.14.3.tar.xz' ;;
            sysutils/dbus) pin='dbus-1.16.2.tar.xz:0ba2a1a4b16afe7bceb2c07e9ce99a8c2c3508e5dec290dbb643384bd6beb7e2:https://dbus.freedesktop.org/releases/dbus/dbus-1.16.2.tar.xz' ;;
            graphics/gdk-pixbuf2) pin='gdk-pixbuf-2.44.8.tar.xz:919f529512961a12e81cd4b4b466a48c3933469e7f9a310c6513cd4fb252ba3c:https://download.gnome.org/sources/gdk-pixbuf/2.44/gdk-pixbuf-2.44.8.tar.xz' ;;
            databases/shared-mime-info) pin='shared-mime-info-2.5.1.tar.bz2:b75b420da9b0be9a3d99b1bee6ed87957b56ab54583ac1a97fbd0dc98ddddb25:https://gitlab.freedesktop.org/xdg/shared-mime-info/-/archive/2.5.1/shared-mime-info-2.5.1.tar.bz2' ;;
            graphics/librsvg) pin='librsvg-2.63.2.tar.xz:852b18e1a00b8605528825a27dc7748bff2a5dd254028f59dc22a34ea57e81b6:https://download.gnome.org/sources/librsvg/2.63/librsvg-2.63.2.tar.xz' ;;
            multimedia/dav1d) pin='dav1d-1.5.4.tar.xz:686616b7c69eb88d44459391ab25cac13b6647a3b288835c5784e71c1514a5c5:https://downloads.videolan.org/pub/videolan/dav1d/1.5.4/dav1d-1.5.4.tar.xz' ;;
            devel/xxhash) pin='xxhash-0.8.4.tar.gz:5738270935e7c3d38a79b3adf7c9692566ce7895a25f67de43ad52ab504acd32:https://github.com/Cyan4973/xxHash/archive/v0.8.4.tar.gz' ;;
            devel/gobject-introspection) pin='gobject-introspection-1.86.0.tar.xz:920d1a3fcedeadc32acff95c2e203b319039dd4b4a08dd1a2dfd283d19c0b9ae:https://download.gnome.org/sources/gobject-introspection/1.86/gobject-introspection-1.86.0.tar.xz' ;;
            devel/libsfdo) pin='libsfdo-0.1.4.tar.gz:9d74a9bff1f872e38ab662d8e2b5f6ecd404d7f82f84e9c324013f856688fa2d:https://gitlab.freedesktop.org/vyivel/libsfdo/-/archive/v0.1.4/libsfdo-v0.1.4.tar.gz' ;;
            devel/pango) pin='pango-1.58.2.tar.xz:342385b6ca3b7c73455d7c80a13b7dbe4489e00bc3bd4c5bd6ed4dce421e374a:https://download.gnome.org/sources/pango/1.58/pango-1.58.2.tar.xz' ;;
            x11/libXt) pin='libXt-1.3.1.tar.xz:e0a774b33324f4d4c05b199ea45050f87206586d81655f8bef4dba434d931288:https://xorg.freedesktop.org/archive/individual/lib/libXt-1.3.1.tar.xz' ;;
            archivers/lzo) pin='lzo-2.10.tar.gz:c0f892943208266f9b6543b3ae308fab6284c5c90e627931446fb49b4221a072:https://www.oberhumer.com/opensource/lzo/download/lzo-2.10.tar.gz' ;;
        esac
        [ "$archive:$sha:$url" = "$pin" ] || { echo "Incorrect common graphics source pin: $recipe" >&2; exit 2; }
    done < "$graphics/sources.tsv"
    for recipe in net/nng graphics/MesaLib x11/libdrm devel/wayland devel/wayland-protocols x11/xorgproto devel/libudev-bsd wayland/wlroots wayland/labwc wayland/sway wayland/swaylock devel/libevdev-chunk textproc/json-c x11/xkeyboard-config devel/input-headers x11/libxkbcommon sysutils/hwdata sysutils/seatd x11/libdisplay-info graphics/libliftoff devel/libopeninput devel/glib2 devel/libffi devel/pcre2 textproc/fmtlib x11/pixman graphics/cairo fonts/harfbuzz converters/fribidi graphics/png graphics/lerc graphics/openexr graphics/OpenJPH graphics/jbigkit graphics/freeimage graphics/freeimageplus graphics/libraw graphics/freetype2 archivers/lzo x11/libXt x11/libspnav devel/pango devel/libsfdo sysutils/dbus devel/gobject-introspection devel/glib2-tools devel/glib2-introspection devel/gdbus-codegen graphics/librsvg multimedia/dav1d devel/xxhash graphics/gdk-pixbuf2 databases/shared-mime-info x11/gtk3 x11/wxGTK32 www/webkit-gtk41 www/webkit-gtk60 devel/at-spi2-core math/eigen3 textproc/rapidjson cad/ng-spice cad/ng-spice-shared cad/kicad10 cad/occt security/libsecret security/mit-krb5 security/mit-krb5-devel; do
        source=$graphics/recipes/$recipe
        recipe_files='Makefile DESCR PLIST distinfo buildlink3.mk'
        case "$recipe" in
            net/nng) recipe_files='Makefile DESCR PLIST distinfo buildlink3.mk options.mk' ;;
            security/mit-krb5-devel) recipe_files='Makefile DESCR PLIST buildlink3.mk' ;;
            security/libsecret) recipe_files='Makefile DESCR PLIST PLIST.cross distinfo buildlink3.mk options.mk' ;;
            security/mit-krb5) recipe_files='Makefile DESCR PLIST distinfo buildlink3.mk builtin.mk options.mk files/kdc.sh files/kadmind.sh files/krb5-config-wrapper.sh' ;;
            x11/pixman) recipe_files='Makefile DESCR PLIST distinfo buildlink3.mk builtin.mk hacks.mk' ;;
            graphics/freeimage) recipe_files='Makefile Makefile.common DESCR PLIST distinfo buildlink3.mk' ;;
            graphics/freeimageplus) recipe_files='Makefile DESCR PLIST buildlink3.mk files/CMakeLists.txt' ;;
            cad/occt) recipe_files='Makefile DESCR PLIST distinfo buildlink3.mk options.mk' ;;
            cad/kicad10) recipe_files='Makefile DESCR PLIST distinfo options.mk' ;;
            cad/ng-spice) recipe_files='Makefile Makefile.common DESCR PLIST distinfo' ;;
            cad/ng-spice-shared) recipe_files='Makefile DESCR PLIST buildlink3.mk' ;;
            www/webkit-gtk41) recipe_files='Makefile Makefile.common DESCR PLIST PLIST.webdriver distinfo buildlink3.mk options.mk cross.mk files/check-gcc16-atomic.sh' ;;
            www/webkit-gtk60) recipe_files='Makefile DESCR PLIST buildlink3.mk' ;;
            x11/wxGTK32) recipe_files='Makefile DESCR PLIST PLIST.Darwin PLIST.cmake PLIST.configure PLIST.gtk3 distinfo buildlink3.mk' ;;
            x11/gtk3) recipe_files='Makefile DESCR PLIST distinfo buildlink3.mk options.mk modules.mk' ;;
            wayland/labwc) recipe_files='Makefile DESCR PLIST distinfo options.mk files/startlabwc.sh.in' ;;
            wayland/sway) recipe_files='Makefile DESCR PLIST distinfo files/startsway.sh' ;;
            wayland/swaylock) recipe_files='Makefile DESCR PLIST distinfo files/swaylock patches/patch-loop.c patches/patch-main.c' ;;
            devel/libevdev-chunk) recipe_files='Makefile DESCR PLIST distinfo buildlink3.mk' ;;
            textproc/json-c) recipe_files='Makefile DESCR PLIST distinfo buildlink3.mk hacks.mk options.mk' ;;
            devel/glib2-tools|devel/glib2-introspection) recipe_files='Makefile DESCR PLIST' ;;
            graphics/gdk-pixbuf2) recipe_files='Makefile DESCR PLIST distinfo buildlink3.mk options.mk loaders.mk files/loaders.tmpl files/target-tools.py files/sdk_source.py' ;;
            databases/shared-mime-info) recipe_files='Makefile DESCR PLIST distinfo buildlink3.mk INSTALL DEINSTALL mimedb.mk files/install.tmpl' ;;
            graphics/librsvg) recipe_files='Makefile DESCR PLIST distinfo buildlink3.mk available.mk options.mk tool.mk cargo-depends.mk cross.mk' ;;
            devel/xxhash) recipe_files='Makefile DESCR PLIST distinfo buildlink3.mk files/Makefile' ;;
            textproc/fmtlib) recipe_files='Makefile DESCR PLIST distinfo buildlink3.mk' ;;
            devel/gobject-introspection) recipe_files='Makefile DESCR PLIST distinfo buildlink3.mk cross.mk files/target-query.py files/sdk_source.py files/elf-needed.sh files/target-pkg-config.sh files/target-gir-scanner.sh' ;;
            devel/gdbus-codegen) recipe_files='Makefile DESCR PLIST distinfo' ;;
            sysutils/dbus) recipe_files='Makefile DESCR PLIST distinfo buildlink3.mk INSTALL options.mk hacks.mk files/dbus.sh files/smf/manifest.xml files/smf/dbus.sh' ;;
        esac
        for name in $recipe_files; do
            [ -f "$source/$name" ] || { echo "Incomplete graphics recipe: $recipe/$name" >&2; exit 2; }
        done
        case "$recipe" in
            net/nng) approved='patch-drain-before-free patch-docs-required' ;;
            security/mit-krb5) approved='patch-z-cross-aclocal_m4 patch-z-cross-configure_ac patch-util_et_Makefile.in patch-zz-libtool-nodelete' ;;
            x11/libspnav) approved='patch-Makefile.in patch-src_spnav.c' ;;
            graphics/freeimage) approved='patch-CMakeLists.txt patch-Source_FreeImage_PluginTIFF.cpp patch-Source_Utilities.h patch-TestAPI_CMakeLists.txt' ;;
            security/mit-krb5-devel|security/libsecret) approved='' ;;
            graphics/freeimageplus) approved='' ;;
            graphics/openexr) approved='patch-cmake_OpenEXRSetup.cmake patch-test-assertions patch-test-tmpdir' ;;
            graphics/OpenJPH) approved='' ;;
            textproc/rapidjson) approved='patch-example_CMakeLists.txt patch-system-gtest patch-gtest-suite patch-float-oracle patch-wide-stream patch-allocator-ownership patch-pointer-token-copy patch-shared-pool-owner' ;;
            graphics/lerc) approved='patch-src_LercLib_fpl__EsriHuffman.cpp' ;;
            graphics/libraw) approved='patch-libraw__r.pc.in' ;;
            cad/occt) approved='patch-failure-stack-size patch-netbsd-runtime patch-pkgsrc-install patch-stacktrace-bounds patch-tk9-discovery patch-rwstl-netbsd patch-sunos-portability patch-rwstl-alignment' ;;
            cad/kicad10) approved='patch-3d-viewer_3d_cache_sg_CMakeLists.txt patch-cmake_config.h.cmake patch-common_import__gfx_dxf__import__plugin.cpp patch-cvpcb_CMakeLists.txt patch-eeschema_CMakeLists.txt patch-eeschema_sim_kibis_kibis.cpp patch-eeschema_sim_sim_property.cpp patch-gerbview_CMakeLists.txt patch-include_kiway.h patch-pagelayout__editor_CMakeLists.txt patch-pcb__calculator_CMakeLists.txt patch-pcbnew_CMakeLists.txt patch-plugins_3d_idf_CMakeLists.txt patch-plugins_3d_vrml_CMakeLists.txt patch-thirdparty_libcontext_libcontext.h patch-emberbsd-occt8-api patch-emberbsd-netbsd-proto-macros patch-libs_kinng_src_kinng.cpp' ;;
            cad/ng-spice) approved='patch-01-libedit-netbsd patch-02-history-substitution patch-03-cli-circuit-file patch-04-xspice-cross-generator patch-05-netbsd-dlopen patch-06-dotcards-token-list patch-07-shared-preinit patch-08-dotcards-parenthesis patch-09-process-name-return patch-10-source-name-lifetime patch-11-parser-error-ownership patch-12-shared-command-cleanup patch-13-target-memory-query' ;;
            x11/pixman|math/eigen3|cad/ng-spice-shared) approved='' ;;
            devel/libffi) approved='patch-configure patch-configure_host patch-src_aarch64_ffi.c patch-src_arm_sysv.S patch-src_closures.c patch-src_m68k_ffi.c patch-src_m88k_elfbsd.S patch-src_mips_ffi.c patch-src_mips_ffitarget.h patch-src_powerpc_ffi.c patch-src_powerpc_ffi__powerpc.h patch-testsuite_lib_libffi.exp patch-testsuite_libffi.call_float2.c' ;;
            devel/at-spi2-core) approved='patch-meson-gir-cross.build patch-meson.build patch-registryd_registry.c' ;;
            www/webkit-gtk41) approved='patch-Source_JavaScriptCore_assembler_ARM64Assembler.h patch-Source_JavaScriptCore_parser_VariableEnvironment.h patch-Source_JavaScriptCore_runtime_DefinePropertyAttributes.h patch-Source_JavaScriptCore_runtime_JSCBytecodeCacheVersion.cpp patch-Source_ThirdParty_ANGLE_src_common_SimpleMutex.h patch-Source_ThirdParty_ANGLE_src_common_platform.h patch-Source_ThirdParty_ANGLE_src_common_system__utils__linux.cpp patch-Source_ThirdParty_ANGLE_src_libANGLE_renderer_gl_egl_DisplayEGL.cpp patch-Source_ThirdParty_skia_CMakeLists.txt patch-Source_ThirdParty_skia_locale-l patch-Source_ThirdParty_skia_src_ports_SkMemory__malloc.cpp patch-Source_WTF_wtf_InlineASM.h patch-Source_WTF_wtf_PlatformEnable.h patch-Source_WTF_wtf_StackBounds.cpp patch-Source_WebCore_loader_cache_CachedResource.h patch-Source_WebCore_page_NavigatorBase.cpp patch-Source_WebCore_platform_graphics_gbm_MemoryMappedGPUBuffer.cpp patch-Source_WebCore_platform_graphics_skia_PlatformDisplaySkia.cpp patch-Source_WebCore_platform_graphics_x11_XErrorTrapper.h patch-Source_WebCore_rendering_RenderBox.h patch-Source_WebCore_rendering_shapes_ShapeOutsideInfo.cpp patch-Source_WebKit_UIProcess_gtk_AcceleratedBackingStore.cpp patch-Source_WebKit_UIProcess_gtk_DisplayX11.cpp patch-Source_WebKit_WebProcess_WebPage_CoordinatedGraphics_ThreadedCompositor.cpp patch-Source_cmake_FindFlite.cmake patch-Source_cmake_FindGI.cmake patch-Source_cmake_WebKitFeatures.cmake' ;;
            www/webkit-gtk60) approved='' ;;
            x11/wxGTK32) approved='patch-configure patch-src_unix_glegl.cpp patch-src_unix_utilsunx.cpp' ;;
            x11/gtk3) approved='patch-gdk_wayland_gdkdevice-wayland.c patch-gdk_x11_gdkscreen-x11.h patch-gdk_x11_gdkwindow-x11.h patch-gtk_a11y_gtkaccessibility.c patch-gtk_fallback-c89.c patch-gtk_gtkfontchooserwidget.c patch-gtk_gtklabel.c patch-meson-gir-cross.build patch-meson.build patch-meson_options.txt patch-tests_gtkgears.c' ;;
            devel/glib2) approved='patch-girepository_compiler_meson.build patch-meson_gir-cross.build patch-gio_gcredentialsprivate.h patch-gio_gdbus-2.0_codegen_meson.build patch-gio_glib-compile-schemas.c patch-gio_gresource-tool.c patch-gio_gunixcredentialsmessage.c patch-gio_gunixmounts.c patch-gio_inotify_inotify-kernel.c patch-gio_meson.build patch-gio_tests_iptosmessage.c patch-gio_tests_meson.build patch-girepository_gitypelib.c patch-glib_gatomic.c patch-glib_gatomic.h patch-glib_genviron.c patch-glib_glib-unix.c patch-glib_gspawn-posix.c patch-glib_gthread.c patch-glib_tests_hash.c patch-glib_tests_include.c patch-glib_tests_meson.build patch-glib_tests_testing.c patch-glib_tests_thread.c patch-gmodule_gmodule-dl.c patch-gmodule_gmodule.c patch-gobject_glib-mkenums.in patch-gobject_meson.build patch-meson.build patch-meson.options' ;;
            devel/gobject-introspection) approved='patch-gir_meson.build patch-girepository_gitypelib.c patch-girepository_gthash-memory patch-giscanner_ast.py patch-giscanner_ccompiler.py patch-meson.build patch-tests_meson.build patch-tests_scanner_test_ccompiler.py patch-tools_compiler.c patch-tools_generate.c patch-tools_meson.build' ;;
            graphics/gdk-pixbuf2) approved='patch-emberbsd_build-aux_gen-thumbnailer.py patch-emberbsd_gdk-pixbuf_meson.build patch-emberbsd_meson.build patch-emberbsd_thumbnailer_meson.build patch-gdk-pixbuf_gdk-pixbuf-scaled-anim.c patch-gdk-pixbuf_meson.build patch-tests_meson.build patch-thumbnailer_meson.build' ;;
            databases/shared-mime-info) approved='patch-src_update-mime-database.cpp' ;;
            graphics/librsvg) approved='patch-.._vendor_matrixmultiply-0.3.11_src_dgemm__kernel.rs patch-.._vendor_matrixmultiply-0.3.11_src_sgemm__kernel.rs patch-.._vendor_memchr-2.8.3_src_arch_aarch64_memchr.rs patch-.._vendor_memchr-2.8.3_src_arch_aarch64_mod.rs patch-.._vendor_memchr-2.8.3_src_memchr.rs patch-.._vendor_memchr-2.8.3_src_memmem_searcher.rs patch-.._vendor_memchr-2.8.3_src_vector.rs patch-.._vendor_wide-1.7.1_src_f32x4__.rs patch-.._vendor_wide-1.7.1_src_f64x2__.rs patch-.._vendor_wide-1.7.1_src_i16x16__.rs patch-.._vendor_wide-1.7.1_src_i16x32__.rs patch-.._vendor_wide-1.7.1_src_i16x8__.rs patch-.._vendor_wide-1.7.1_src_i32x16__.rs patch-.._vendor_wide-1.7.1_src_i32x4__.rs patch-.._vendor_wide-1.7.1_src_i32x8__.rs patch-.._vendor_wide-1.7.1_src_i64x2__.rs patch-.._vendor_wide-1.7.1_src_i64x4__.rs patch-.._vendor_wide-1.7.1_src_i64x8__.rs patch-.._vendor_wide-1.7.1_src_i8x16__.rs patch-.._vendor_wide-1.7.1_src_i8x32__.rs patch-.._vendor_wide-1.7.1_src_u16x8__.rs patch-.._vendor_wide-1.7.1_src_u32x4__.rs patch-.._vendor_wide-1.7.1_src_u64x2__.rs patch-.._vendor_wide-1.7.1_src_u8x16__.rs patch-.._vendor_zune-jpeg-0.5.15_src_idct.rs patch-.._vendor_zune-jpeg-0.5.15_src_unsafe__utils.rs patch-.._vendor_zune-jpeg-0.5.15_src_unsafe__utils__neon.rs patch-meson.build patch-meson_gir-cross.build patch-rsvg_meson.build patch-gdk-pixbuf-loader_meson.build' ;;
            devel/pcre2|textproc/fmtlib|devel/libsfdo|devel/xxhash|multimedia/dav1d) approved='' ;;
            sysutils/dbus) approved='patch-bus_meson.build patch-meson.build patch-tools_meson.build' ;;
            graphics/cairo) approved='patch-meson.build patch-src_cairo-bentley-ottmann-rectangular.c patch-src_cairo-colr-glyph-render.c patch-src_cairo-image-surface.c patch-test_pdf-structure.c patch-util_cairo-missing_getline.c' ;;
            fonts/harfbuzz) approved='patch-src_meson.build patch-util_meson.build' ;;
            converters/fribidi) approved='patch-bin_Makefile.am patch-bin_Makefile.in' ;;
            graphics/jbigkit) approved='patch-cli-cleanup patch-Makefile patch-libjbig_Makefile patch-pbmtools_Makefile patch-test-cleanup' ;;
            graphics/png) approved='patch-libpng-config.in patch-pngpriv.h' ;;
            graphics/freetype2) approved='patch-builds_unix_freetype-config.in patch-builds_unix_unix-cc.in' ;;
            devel/pango) approved='patch-emberbsd-gir-cross.build patch-pango_pangocairo-coretextfont.c patch-pango_pangocairo-coretextfontmap.c patch-pango_pangocoretext-private.h patch-pango_pangocoretext.c patch-pangocairo-coretext.h' ;;
            x11/libXt) approved='patch-include_X11_Xtos.h patch-util_Makefile.in' ;;
            archivers/lzo) approved='patch-aa patch-src_lzo1f__d.ch' ;;
            devel/glib2-tools) approved='' ;;
            devel/glib2-introspection) approved='' ;;
            devel/gdbus-codegen) approved='patch-meson.build' ;;
            graphics/MesaLib)
                approved='patch-include_drm-uapi_pvr__drm.h patch-bin_symbols-check.py patch-dso-lifetime patch-include_c99__alloca.h patch-meson-python-selection patch-meson-xcb-pkgconfig patch-src_imagination_vulkan_pvr__physical__device.c patch-src_imagination_common_pvr__iface.h patch-src_vulkan_wsi_wsi__common__wayland.c patch-src_gallium_auxiliary_vl_vl__csc.c patch-src_util_half__float.c' ;;
            x11/libdrm)
                approved='patch-ac patch-amdgpu_amdgpu__cs.c patch-include_drm_drm.h patch-libsync.h patch-symbols-check.py patch-tests_nouveau_threaded.c patch-xf86drm.c patch-xf86drmMode.c patch-zz-native-identity patch-zzz-native-warnings' ;;
            devel/wayland)
                approved='patch-meson.build patch-meson__options.txt patch-scanner.c patch-src_meson.build patch-src_wayland-os.c patch-tests_client-test.c patch-tests_test-helpers.c' ;;
            devel/wayland-protocols)
                approved='patch-stable_xdg-shell_xdg-shell.xml patch-unstable_xdg-output_xdg-output-unstable-v1.xml' ;;
            wayland/labwc)
                approved='patch-docs_meson.build patch-meson.build patch-src_common_string-helpers.c patch-src_cycle_osd-field.c' ;;
            wayland/sway) approved='patch-common_stringop.c patch-common_util.c patch-include_ipc.h patch-include_stringop.h patch-meson.build patch-sway_commands.c patch-sway_commands_move.c patch-sway_commands_rename.c patch-sway_commands_workspace.c patch-sway_input_input-manager.c patch-sway_input_seat.c patch-sway_ipc-json.c patch-sway_ipc-server.c patch-sway_ipc-startup.c patch-sway_tree_output.c patch-sway_tree_workspace.c patch-swaybar_i3bar.c patch-swaybar_tray_icon.c' ;;
            wayland/swaylock) approved='patch-loop.c patch-main.c' ;;
            devel/libevdev-chunk) approved='patch-libevdev.c patch-libevdev_libevdev.h' ;;
            textproc/json-c) approved='patch-json_object.c patch-tests_test_json_parse_cli.test' ;;
            wayland/wlroots)
                approved='patch-backend_libinput_meson.build patch-render_allocator_allocator.c patch-render_drm__syncobj.c patch-render_vulkan_vulkan.c patch-software-primary-node patch-util_shm.c patch-xcursor_xcursor.c' ;;
            x11/xkeyboard-config) approved='patch-meson.build' ;;
            x11/libxkbcommon) approved='patch-meson-legacy-root' ;;
            sysutils/hwdata) approved='patch-Makefile' ;;
            sysutils/seatd) approved='patch-common_drm.c patch-common_terminal.c patch-wscons-keyboard-restore' ;;
            x11/libdisplay-info) approved='patch-meson.build' ;;
            devel/libopeninput) approved='patch-src_wscons.c patch-src_wscons.h patch-wscons-absolute-pointer' ;;
            devel/libudev-bsd) approved='patch-evdev-sysctl patch-render-nodes patch-udev-drm-change' ;;
            x11/xorgproto|devel/input-headers|graphics/libliftoff) approved='' ;;
        esac
        case "$recipe" in
            graphics/MesaLib|x11/libdrm|x11/xkeyboard-config)
                [ -f "$source/builtin.mk" ] || { echo "Missing builtin guard: $recipe" >&2; exit 2; } ;;
            devel/wayland)
                [ -f "$source/cross-scanner.mk" ] && [ -f "$source/platform.mk" ] &&
                [ -s "$source/PLIST.runtime" ] && [ -s "$source/files/select-package-stage.pl" ] || exit 2 ;;
            devel/wayland-protocols)
                [ -f "$source/cross-scanner.mk" ] || { echo 'Missing protocols host scanner integration' >&2; exit 2; } ;;
        esac
        if [ "$recipe" = wayland/wlroots ]; then
            [ -f "$source/options.mk" ] || { echo 'Missing wlroots feature selection' >&2; exit 2; }
        fi
        if [ "$recipe" = sysutils/hwdata ]; then
            [ -f "$source/native-meson.mk" ] || { echo "Missing native graphics metadata guard" >&2; exit 2; }
        fi
        if [ "$recipe" = x11/libxkbcommon ] || [ "$recipe" = devel/libopeninput ] || [ "$recipe" = devel/glib2 ] || [ "$recipe" = fonts/harfbuzz ]; then
            [ -f "$source/Makefile.common" ] || { echo 'Missing xkbcommon common recipe' >&2; exit 2; }
        fi
        case "$recipe" in
            security/mit-krb5-devel)
                grep -q '^.include "../../security/mit-krb5/Makefile"' "$source/Makefile" || exit 2
                continue ;;
            www/webkit-gtk60)
                grep -q '^.include "../../www/webkit-gtk41/Makefile.common"' "$source/Makefile" || exit 2
                continue ;;
            graphics/freeimageplus)
                grep -q '^.include "../../graphics/freeimage/Makefile.common"' "$source/Makefile" || exit 2
                continue ;;
            cad/ng-spice-shared)
                grep -q '^.include "../../cad/ng-spice/Makefile.common"' "$source/Makefile" || exit 2
                continue ;;
            devel/glib2-tools|devel/glib2-introspection)
                grep -q '^.include "../../devel/glib2/Makefile.common"' "$source/Makefile" || exit 2
                grep -q '^DISTINFO_FILE=.*../../devel/glib2/distinfo' "$source/Makefile" || exit 2
                continue ;;
        esac
        for name in $approved; do
            grep -q "^SHA1 ($name) = " "$source/distinfo" && [ -f "$source/patches/$name" ] || {
                echo "Missing required graphics patch: $recipe/$name" >&2; exit 2;
            }
        done
        required=$(awk '/^SHA1 \(patch-/ { gsub(/[()]/, "", $2); print $2 }' "$source/distinfo")
        case "$recipe" in
            x11/pixman|graphics/OpenJPH|math/eigen3|x11/xorgproto|devel/libudev-bsd|devel/input-headers|graphics/libliftoff|devel/pcre2|textproc/fmtlib|devel/libsfdo|devel/xxhash|multimedia/dav1d|security/libsecret) ;;
            *) [ -n "$required" ] || { echo "No graphics patch checksums: $recipe" >&2; exit 2; } ;;
        esac
        actual=0
        if [ -d "$source/patches" ]; then
            if [ "$recipe" = net/nng ]; then
                for name in $approved; do
                    origin=${name#patch-}.patch
                    [ -L "$source/patches/$name" ] &&
                    [ "$(readlink "$source/patches/$name")" = "../../../../../../probes/kicad/nng/patches/$origin" ] || {
                        echo "Unexpected NNG patch origin: $name" >&2; exit 2;
                    }
                done
                [ "$(find "$source" -type l | wc -l | tr -d ' ')" = 2 ] || {
                    echo 'Unexpected additional NNG recipe link.' >&2; exit 2;
                }
                actual=$(find "$source/patches" -name 'patch-*' | wc -l | tr -d ' ')
            elif [ "$recipe" = cad/ng-spice ] || [ "$recipe" = cad/occt ]; then
                # Keep one reviewed source patch set. Dereference only these
                # exact public links when materializing the exported recipe.
                for name in $approved; do
                    case "$recipe" in
                        cad/ng-spice) origin=${name#patch-??-}.patch; probe=ngspice; links=13 ;;
                        cad/occt) origin=${name#patch-}.patch; probe=occt; links=8 ;;
                    esac
                    [ -L "$source/patches/$name" ] &&
                    [ "$(readlink "$source/patches/$name")" = "../../../../../../probes/kicad/$probe/patches/$origin" ] || {
                        echo "Unexpected source patch origin: $name" >&2; exit 2;
                    }
                done
                [ "$(find "$source" -type l | wc -l | tr -d ' ')" = "$links" ] || {
                    echo 'Unexpected additional source recipe link.' >&2; exit 2;
                }
                actual=$(find "$source/patches" -name 'patch-*' | wc -l | tr -d ' ')
            else
                actual=$(find "$source/patches" -type f -name 'patch-*' | wc -l | tr -d ' ')
            fi
        fi
        count=$(printf '%s\n' "$required" | awk 'NF { n++ } END { print n+0 }')
        [ "$actual" = "$count" ] || { echo "Graphics patch inventory differs: $recipe" >&2; exit 2; }
        for name in $required; do
            [ -f "$source/patches/$name" ] || { echo "Missing required patch: $recipe/$name" >&2; exit 2; }
            recorded=$(awk -v name="($name)" '$1 == "SHA1" && $2 == name { print $4 }' "$source/distinfo")
            computed=$(sed '/[$]NetBSD.*/d' "$source/patches/$name" | shasum -a 1 | awk '{ print $1 }')
            [ "$recorded" = "$computed" ] || { echo "Graphics patch checksum differs: $recipe/$name" >&2; exit 2; }
        done
    done
    for name in features.mk options.mk version.mk mesa-generators.mk verify-mesa-generators.sh; do
        [ -f "$graphics/recipes/graphics/MesaLib/$name" ] || { echo "Incomplete Mesa recipe: $name" >&2; exit 2; }
    done
    for wayland_sdk_file in Makefile buildlink3.mk DESCR PLIST; do
        [ -s "$graphics/recipes/devel/wayland-devel/$wayland_sdk_file" ] || {
            echo "Incomplete Wayland SDK recipe: $wayland_sdk_file" >&2; exit 2;
        }
    done
    [ "$(find "$graphics/recipes/devel/wayland-devel" -type l | wc -l | tr -d ' ')" = 0 ] || {
        echo 'Unexpected Wayland SDK recipe link.' >&2; exit 2;
    }
    [ -f "$graphics/mk.conf" ] || { echo 'Missing common graphics configuration.' >&2; exit 2; }
fi
export_archive=$(mktemp "${TMPDIR:-/tmp}/ember-pkgsrc.XXXXXXXX")
trap 'rm -f "$export_archive"' EXIT
trap 'exit 130' INT
trap 'exit 143' HUP TERM
git -C "$root/upstream/pkgsrc" archive --format=tar --output="$export_archive" "$expected"
mkdir "$destination"
tar -xf "$export_archive" -C "$destination"
for category in "$root"/pkgsrc/*; do
    [ -d "$category" ] || continue
    name=${category##*/}
    [ ! -e "$destination/$name" ] && [ ! -L "$destination/$name" ] || {
        echo "Upstream already has $name; review the overlay." >&2
        exit 2
    }
    cp -R "$category" "$destination/$name"
done
if [ "$profile" = electron ]; then
    # Export the Electron source probes only for the explicit electron profile.
    # Their pkgsrc paths define the dependency relationship used by Blanc.
    for pair in devel/electron44:electron44 www/blanc:blanc; do
        recipe=${pair%%:*}
        source_name=${pair#*:}
        source=$root/probes/electron/$source_name
        [ -s "$source/Makefile" ] || {
            echo "Incomplete Electron probe recipe: $source_name/Makefile" >&2; exit 2;
        }
        [ ! -e "$destination/$recipe" ] && [ ! -L "$destination/$recipe" ] || {
            echo "Upstream already owns $recipe; review the Electron probe overlay." >&2
            exit 2;
        }
        mkdir -p "$(dirname "$destination/$recipe")"
        cp -R "$source" "$destination/$recipe"
    done
    grep -F 'CATEGORIES=	www' "$destination/www/blanc/Makefile" >/dev/null || {
        echo 'Exported Blanc recipe is not in www.' >&2; exit 2;
    }
    grep -F 'BLANC_ELECTRON_PKGDIR=	../../devel/electron44' \
        "$destination/www/blanc/Makefile" >/dev/null || {
        echo 'Exported Blanc recipe does not depend on devel/electron44.' >&2; exit 2;
    }
fi
if [ "$profile" = development-toolchain ] || [ "$profile" = common-build-tools ] || \
    [ "$profile" = common-graphics ] || [ "$profile" = common-media ] || [ "$profile" = plasma-mobile ]; then
    for delta in pkgsrc-gcc16.2.patch strict-tests.patch current-prerequisites.patch texinfo-gettext-order.patch gsed-mbstate-zero.patch libxslt-rvt-security.patch stable-expect.patch gcc-tsvc-netbsd.patch gcc-modules-fallocate.patch gcc-netbsd-locale.patch gcc-netbsd-math.patch gcc-package-requires.patch gcc-netbsd-tls.patch gcc-cross-native.patch; do
        patch -f -E -d "$destination" -p1 -F 0 < \
            "$root/profiles/development-toolchain/patches/$delta"
    done
    # One current debugger recipe; dereference the shared Ports patch links.
    rm -rf "$destination/devel/gdb"
    cp -RL "$root/profiles/development-toolchain/recipes/devel/gdb" "$destination/devel/gdb"
    if [ "$firmware_toolchain" = yes ]; then
        for recipe in devel/gmake sysutils/dtc cross/aarch64-none-elf-binutils cross/aarch64-none-elf-gcc; do
            rm -rf "$destination/$recipe"
            cp -R "$root/profiles/development-toolchain/recipes/$recipe" "$destination/$recipe"
        done
    fi
    cp "$root/profiles/development-toolchain/mk.conf" \
        "$destination/EMBERBSD-DEVELOPMENT-MK.CONF"
    # Package audited external target runtimes without installing a compiler.
    runtime_recipe=$root/profiles/development-toolchain/runtime/recipe
    [ -f "$runtime_recipe/files/runtime.py" ] || {
        echo 'The GCC16 runtime recipe is incomplete.' >&2; exit 2;
    }
    [ ! -e "$destination/lang/gcc16-runtime" ] || {
        echo 'Upstream now owns lang/gcc16-runtime; review the overlay.' >&2; exit 2;
    }
    cp -R "$runtime_recipe" "$destination/lang/gcc16-runtime"
fi
if [ "$profile" = development-toolchain ] || [ "$profile" = common-build-tools ] || [ "$profile" = common-graphics ] || [ "$profile" = common-media ] || [ "$profile" = plasma-mobile ]; then
    for recipe in lang/tcl lang/python315 lang/perl5 lang/rust-bin lang/rust-std-aarch64-netbsd lang/rust-std-x86_64-netbsd devel/meson devel/flex lang/llvm lang/clang devel/lld devel/py-llvm-lit devel/binutils devel/py-mako devel/zlib devel/abseil devel/protobuf textproc/py-markupsafe textproc/py-yaml textproc/groff net/mDNSResponder textproc/icu; do
        source=$root/profiles/common-build-tools/recipes/$recipe
        # Replace only recipe paths inside this newly created export.
        rm -rf "$destination/$recipe"
        if [ "$recipe" = devel/protobuf ]; then
            # The preflight approved exactly four public source patch links.
            cp -RL "$source" "$destination/$recipe"
        else
            cp -R "$source" "$destination/$recipe"
        fi
    done
    [ ! -e "$destination/lang/llvm-devel" ] && [ ! -L "$destination/lang/llvm-devel" ] || {
        echo 'Upstream now owns lang/llvm-devel; review the overlay.' >&2; exit 2;
    }
    rm -rf "$destination/x11/tk"
    cp -R "$root/profiles/common-graphics/recipes/x11/tk" "$destination/x11/tk"
    cp -R "$root/profiles/common-build-tools/recipes/lang/llvm-devel" "$destination/lang/llvm-devel"
    [ ! -e "$destination/devel/protobuf-devel" ] && [ ! -L "$destination/devel/protobuf-devel" ] || {
        echo 'Upstream now owns devel/protobuf-devel; review the overlay.' >&2; exit 2;
    }
    cp -R "$root/profiles/common-build-tools/recipes/devel/protobuf-devel" "$destination/devel/protobuf-devel"
    [ ! -e "$destination/textproc/icu-devel" ] && [ ! -L "$destination/textproc/icu-devel" ] || {
        echo 'Upstream now owns textproc/icu-devel; review the overlay.' >&2; exit 2;
    }
    cp -R "$root/profiles/common-build-tools/recipes/textproc/icu-devel" "$destination/textproc/icu-devel"
    patch -f -N -d "$destination" -p1 -F 0 < \
        "$root/profiles/common-build-tools/patches/current-python-selection.patch"
    for delta in $common_tools_deltas; do
        patch -f -N -d "$destination" -p1 -F 0 < \
            "$root/profiles/common-build-tools/patches/$delta"
    done
    cp "$root/profiles/common-build-tools/cross/check-files-case.sh" \
        "$destination/mk/check/ember-case-files.sh"
    cp "$root/profiles/common-build-tools/mk.conf" \
        "$destination/EMBERBSD-COMMON-TOOLS-MK.CONF"
    cp "$root/profiles/common-build-tools/cross/sort-c.sh" \
        "$destination/sort-c.sh"
    cp "$root/profiles/common-build-tools/cross/gcc16-external-runtime.sh" \
        "$destination/gcc16-external-runtime.sh"
    cp "$root/profiles/common-build-tools/cross/mk.conf" \
        "$destination/EMBERBSD-CROSS-MK.CONF"
fi
if [ "$profile" = common-build-tools ] || [ "$profile" = common-graphics ] || [ "$profile" = common-media ] || [ "$profile" = plasma-mobile ]; then
    rm -rf "$destination/devel/swig4" "$destination/devel/pcre2"
    cp -R "$swig" "$destination/devel/swig4"
    cp -R "$shared_pcre2" "$destination/devel/pcre2"
fi
if [ "$profile" = common-graphics ] || [ "$profile" = common-media ] || [ "$profile" = plasma-mobile ]; then
    for recipe in net/nng graphics/MesaLib x11/libdrm devel/wayland devel/wayland-protocols x11/xorgproto devel/libudev-bsd wayland/wlroots wayland/labwc wayland/sway wayland/swaylock devel/libevdev-chunk textproc/json-c x11/xkeyboard-config devel/input-headers x11/libxkbcommon sysutils/hwdata sysutils/seatd x11/libdisplay-info graphics/libliftoff devel/libopeninput devel/glib2 devel/libffi devel/pcre2 textproc/fmtlib x11/pixman graphics/cairo fonts/harfbuzz converters/fribidi graphics/png graphics/lerc graphics/openexr graphics/OpenJPH graphics/jbigkit graphics/freeimage graphics/freeimageplus graphics/libraw graphics/freetype2 archivers/lzo x11/libXt x11/libspnav devel/pango devel/libsfdo sysutils/dbus devel/gobject-introspection devel/glib2-tools devel/glib2-introspection devel/gdbus-codegen graphics/librsvg multimedia/dav1d devel/xxhash graphics/gdk-pixbuf2 databases/shared-mime-info x11/gtk3 x11/wxGTK32 www/webkit-gtk41 www/webkit-gtk60 devel/at-spi2-core math/eigen3 textproc/rapidjson cad/ng-spice cad/ng-spice-shared cad/kicad10 cad/occt security/libsecret security/mit-krb5 security/mit-krb5-devel; do
        rm -rf "$destination/$recipe"
        if [ "$recipe" = cad/ng-spice ] || [ "$recipe" = net/nng ] || [ "$recipe" = cad/occt ]; then
            cp -RL "$graphics/recipes/$recipe" "$destination/$recipe"
        else
            cp -R "$graphics/recipes/$recipe" "$destination/$recipe"
        fi
    done
    patch -f -N -d "$destination" -p1 -F 0 < \
        "$graphics/cross/current-cups.patch"
    patch -f -N -d "$destination" -p1 -F 0 < \
        "$graphics/cross/git-base-cross-tools.patch"
    patch -f -N -d "$destination" -p1 -F 0 < \
        "$graphics/cross/graphene-gir-cross.patch"
    patch -f -N -d "$destination" -p1 -F 0 < \
        "$graphics/cross/iso-codes-host-python.patch"
    patch -f -N -d "$destination" -p1 -F 0 < \
        "$graphics/cross/hyphen-cross-no-perl-helper.patch"
    patch -f -N -d "$destination" -p1 -F 0 < \
        "$graphics/cross/libnotify-cross-tools.patch"
    patch -f -N -d "$destination" -p1 -F 0 < \
        "$graphics/cross/gsettings-desktop-schemas-cross-gir.patch"
    patch -f -N -d "$destination" -p1 -F 0 < \
        "$graphics/cross/netpbm-native-build-tools.patch"
    patch -f -N -d "$destination" -p1 -F 0 < \
        "$graphics/cross/netpbm-cross-no-manweb.patch"
    patch -f -N -d "$destination" -p1 -F 0 < \
        "$graphics/cross/libproxy-cross-disable-introspection.patch"
    patch -f -N -d "$destination" -p1 -F 0 < \
        "$graphics/cross/libsoup3-cross-disable-tls-probe.patch"
    patch -f -N -d "$destination" -p1 -F 0 < \
        "$graphics/cross/check-interpreter-base-cross.patch"
    glib_networking=$destination/net/glib-networking
    glib_networking_patch=patch-emberbsd_meson.build
    [ ! -e "$glib_networking/patches/$glib_networking_patch" ] || {
        echo "Unexpected pkgsrc patch collision: net/glib-networking/$glib_networking_patch" >&2; exit 2;
    }
    cp "$graphics/cross/glib-networking-gio-module-path.patch" \
        "$glib_networking/patches/$glib_networking_patch"
    glib_networking_patch_sha=$(sed '/[$]NetBSD.*/d' \
        "$glib_networking/patches/$glib_networking_patch" | shasum -a 1 | awk '{ print $1 }')
    printf 'SHA1 (%s) = %s\n' "$glib_networking_patch" "$glib_networking_patch_sha" \
        >> "$glib_networking/distinfo"
    # Select GLEW's platform from the target, not the build host's uname.
    patch -f -N -d "$destination" -p1 -F 0 < \
        "$graphics/cross/glew-target-system.patch"
    [ ! -e "$destination/devel/wayland-devel" ] && [ ! -L "$destination/devel/wayland-devel" ] || {
        echo 'Upstream now owns devel/wayland-devel; review the overlay.' >&2; exit 2;
    }
    cp -R "$graphics/recipes/devel/wayland-devel" "$destination/devel/wayland-devel"
    cp "$graphics/mk.conf" "$destination/EMBERBSD-COMMON-GRAPHICS-MK.CONF"
    cp "$graphics/sources.tsv" "$destination/EMBERBSD-COMMON-GRAPHICS-SOURCES"
fi
if [ "$profile" = common-media ] || [ "$profile" = plasma-mobile ]; then
    # Install each complete media recipe from the verified manifest.
    while IFS="$(printf '\t')" read -r recipe archive sha url; do
        case "$recipe" in ''|'#'*) continue ;; esac
        rm -rf "$destination/$recipe"
        cp -R "$media/recipes/$recipe" "$destination/$recipe"
    done < "$media/sources.tsv"
    cp "$media/mk.conf" "$destination/EMBERBSD-COMMON-MEDIA-MK.CONF"
    cp "$media/sources.tsv" "$destination/EMBERBSD-COMMON-MEDIA-SOURCES"
fi
if [ "$profile" = plasma-mobile ]; then
    printf '%s\n' "$toolkit_inventory" | while IFS="$(printf '\t')" read -r recipe owner kind; do
        if [ "$kind" = overlay ]; then
            [ -f "$destination/$recipe/Makefile" ] || { echo "Missing exported overlay base: $recipe" >&2; exit 2; }
            cp -R "$toolkit/recipes/$recipe/." "$destination/$recipe/"
        else
            rm -rf "$destination/$recipe"
            if [ "$kind" = local ]; then
                cp -RL "$toolkit/recipes/$recipe" "$destination/$recipe"
            else
                cp -R "$toolkit/recipes/$recipe" "$destination/$recipe"
            fi
        fi
    done
    cp "$toolkit/sources.tsv" "$destination/EMBERBSD-PLASMA-TOOLKIT-SOURCES"
    cp "$toolkit/source-owners.tsv" "$destination/EMBERBSD-PLASMA-TOOLKIT-SOURCE-OWNERS"
    patch -f -N -d "$destination" -p1 -F 0 < "$toolkit/libproxy-cross.patch"
    patch -f -N -d "$destination" -p1 -F 0 < "$toolkit/current-network-deps.patch"
    patch -f -N -d "$destination" -p1 -F 0 < "$toolkit/current-crypto-deps.patch"
    patch -f -N -d "$destination" -p1 -F 0 < "$toolkit/current-polkit.patch"
    patch -f -N -d "$destination" -p1 -F 0 < "$toolkit/docbook-cross.patch"
    patch -f -N -d "$destination" -p1 -F 0 < "$toolkit/current-fonts.patch"
    cp -R "$toolkit/shared/." "$destination/"
    cp "$toolkit/mk.conf" "$destination/EMBERBSD-PLASMA-TOOLKIT-MK.CONF"
fi
if [ "$profile" = development-toolchain ] || [ "$profile" = common-build-tools ] || [ "$profile" = common-graphics ] || [ "$profile" = common-media ] || [ "$profile" = plasma-mobile ]; then
    # Apply after complete toolkit recipes so the shared Boost revision and
    # native b2 cross roles survive every composed common profile.
    patch -f -N -d "$destination" -p1 -F 0 < \
        "$root/profiles/common-build-tools/patches/pkgsrc-boost-cross-target.patch"
fi
printf '%s\n' "$expected" > "$destination/EMBERBSD-PKGSRC-REVISION"
printf 'profile=%s\nfirmware_toolchain=%s\n' "$profile" "$firmware_toolchain" > \
    "$destination/EMBERBSD-PKGSRC-CONFIG"
printf 'Prepared %s with pkgsrc %s\n' "$destination" "$expected"
