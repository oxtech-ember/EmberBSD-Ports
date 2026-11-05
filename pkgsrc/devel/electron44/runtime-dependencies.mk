# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Direct package owners of the selected Electron runtime ELF dependencies.
# libnotify is loaded dynamically and therefore is not listed in DT_NEEDED.
# The split LLVM runtime buildlinks select runtime and build-only development packages.

# The selected GN graph links the shared GNU libintl from this pkgsrc tree.
# A base gettext implementation does not provide that package dependency.
PREFER.gettext= pkgsrc

# Node loads the selected common JavaScript provider from its installed prefix.
DEPENDS+= undici>=8.12.3:../../www/undici

# The selected GN graph consumes these header-only providers only while building.
BUILDLINK_DEPMETHOD.flatbuffers= build
BUILDLINK_DEPMETHOD.eigen3= build
BUILDLINK_DEPMETHOD.fp16= build
.include "../../devel/flatbuffers/buildlink3.mk"
.include "../../devel/fp16/buildlink3.mk"
.include "../../math/eigen3/buildlink3.mk"

.include "../../archivers/brotli/buildlink3.mk"
.include "../../archivers/zstd/buildlink3.mk"
.include "../../databases/sqlite3/buildlink3.mk"
.include "../../devel/abseil/buildlink3.mk"
.include "../../devel/ada-idna/buildlink3.mk"
.include "../../devel/ada-url/buildlink3.mk"
.include "../../devel/at-spi2-core/buildlink3.mk"
.include "../../devel/gettext-lib/buildlink3.mk"
.include "../../devel/glib2/buildlink3.mk"
.include "../../devel/hdr-histogram/buildlink3.mk"
.include "../../devel/libepoll-shim/buildlink3.mk"
.include "../../devel/libffi/buildlink3.mk"
.include "../../devel/libudev-bsd/buildlink3.mk"
.include "../../devel/libuv/buildlink3.mk"
.include "../../devel/merve/buildlink3.mk"
.include "../../devel/nbytes/buildlink3.mk"
.include "../../devel/nspr/buildlink3.mk"
.include "../../devel/nss/buildlink3.mk"
.include "../../devel/pango/buildlink3.mk"
.include "../../devel/protobuf/buildlink3.mk"
.include "../../devel/re2/buildlink3.mk"
.include "../../devel/simdjson/buildlink3.mk"
.include "../../devel/simdutf/buildlink3.mk"
.include "../../devel/uvwasi/buildlink3.mk"
.include "../../fonts/fontconfig/buildlink3.mk"
.include "../../fonts/harfbuzz/buildlink3.mk"
.include "../../graphics/MesaLib/buildlink3.mk"
.include "../../graphics/cairo/buildlink3.mk"
.include "../../graphics/gdk-pixbuf2/buildlink3.mk"
.include "../../lang/libcxx/buildlink3.mk"
.include "../../lang/libcxxabi/buildlink3.mk"
.include "../../lang/libunwind/buildlink3.mk"
.include "../../net/libcares/buildlink3.mk"
.include "../../print/libcups/buildlink3.mk"
.include "../../sysutils/dbus/buildlink3.mk"
.include "../../sysutils/libnotify/buildlink3.mk"
.include "../../textproc/expat/buildlink3.mk"
.include "../../textproc/icu/buildlink3.mk"
.include "../../www/llhttp/buildlink3.mk"
.include "../../www/nghttp2/buildlink3.mk"
.include "../../x11/gtk3/buildlink3.mk"
.include "../../x11/libX11/buildlink3.mk"
.include "../../x11/libXext/buildlink3.mk"
.include "../../x11/libXi/buildlink3.mk"
.include "../../x11/libdrm/buildlink3.mk"
.include "../../x11/libxcb/buildlink3.mk"
.include "../../x11/libxkbcommon/buildlink3.mk"
.include "../../x11/libxshmfence/buildlink3.mk"

.include "../../devel/crc32c/buildlink3.mk"
.include "../../security/libsrtp/buildlink3.mk"
.include "../../multimedia/libyuv/buildlink3.mk"

.if ${EMBERBSD_ELECTRON_SHARED_FFMPEG:Uno} == "yes"
BUILDLINK_API_DEPENDS.ffmpeg9+= ffmpeg9>=9.0.2nb6
BUILDLINK_ABI_DEPENDS.ffmpeg9+= ffmpeg9>=9.0.2nb6
.include "../../multimedia/ffmpeg9/buildlink3.mk"
.endif

.if ${EMBERBSD_ELECTRON_SHARED_MINIZIP:Uno} == "yes"
BUILDLINK_API_DEPENDS.minizip-ng+= minizip-ng>=4.2.2nb1
BUILDLINK_ABI_DEPENDS.minizip-ng+= minizip-ng>=4.2.2nb1
.include "../../archivers/minizip-ng/buildlink3.mk"
.endif
