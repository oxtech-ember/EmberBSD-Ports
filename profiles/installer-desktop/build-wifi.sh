#!/bin/sh
# Origin: EmberBSD GTK3 Wi-Fi manager cross build, prepared with AI assistance.
# SPDX-License-Identifier: BSD-2-Clause
set -eu
[ "$#" = 4 ] || { echo 'Usage: build-wifi.sh archive sysroot cross-gcc new-output' >&2; exit 2; }
archive=$1; sysroot=$2; compiler=$3; output=$4
for path in "$sysroot" "$compiler" "$output"; do
	case $path in /*) ;; *) exit 2;; esac
	case $path in *[!A-Za-z0-9_./-]*) exit 2;; esac
done
[ -d "$sysroot/usr/include" ] && [ -f "$sysroot/usr/pkg/lib/pkgconfig/gtk+-3.0.pc" ] || exit 1
[ -x "$compiler" ] && [ ! -e "$output" ] || exit 1
expected=005fe4ac66ac484b6e00a0fe6e2f577e5d3065aef42808c6e0feb65ee9ccf916e65f17b5a641fa6b22eb239c8cdeb9339f83761811635574cde95cafc525b510
actual=$(shasum -a 512 "$archive"); actual=${actual%% *}
[ "$actual" = "$expected" ] || { echo 'Upstream archive checksum mismatch' >&2; exit 1; }
mkdir "$output"
tar -xf "$archive" -C "$output"
printf '#!/bin/sh\nexec "%s" --sysroot="%s" -B"%s/usr/lib/" -isystem "%s/usr/include" "$@"\n' \
    "$compiler" "$sysroot" "$sysroot" "$sysroot" > "$output/cc"
chmod 755 "$output/cc"
CC=$output/cc
CFLAGS=-O2
LDFLAGS="-Wl,-rpath,/usr/pkg/lib -Wl,-rpath-link,$sysroot/usr/pkg/lib -Wl,-rpath-link,$sysroot/usr/X11R7/lib"
PKG_CONFIG_LIBDIR=$sysroot/usr/pkg/lib/pkgconfig:$sysroot/usr/X11R7/lib/pkgconfig:$sysroot/usr/pkg/share/pkgconfig:$sysroot/usr/lib/pkgconfig
PKG_CONFIG_SYSROOT_DIR=$sysroot
export CC CFLAGS LDFLAGS PKG_CONFIG_LIBDIR PKG_CONFIG_SYSROOT_DIR
cd "$output/dhcpcd-ui-0.8.0"
sh configure --host=x86_64--netbsd --target=x86_64--netbsd \
    --prefix=/usr/pkg --sysconfdir=/usr/pkg/etc --with-gtk+=gtk+-3.0 \
    --without-qt --without-icons --without-dhcpcd-online --without-curses \
    --enable-notification > "$output/configure.log" 2>&1
gmake -j4 AR="${compiler%gcc}ar" RANLIB="${compiler%gcc}ranlib" > "$output/build.log" 2>&1
gmake DESTDIR="$output/install" install > "$output/install.log" 2>&1
printf '%s\n' 'Built original dhcpcd-ui 0.8.0 against the shared GTK3 sysroot.'
