# Native C++ providers selected for Electron's build-host actions.
# Runtime libraries and their transitive dependencies remain owned by Ports.
.include "../../devel/protobuf/buildlink3.mk"
.include "../../devel/libffi/buildlink3.mk"
.include "../../devel/simdutf/buildlink3.mk"
.include "../../devel/libuv/buildlink3.mk"
.include "../../devel/hdr-histogram/buildlink3.mk"
.include "../../devel/simdjson/buildlink3.mk"
.include "../../www/nghttp2/buildlink3.mk"
.include "../../devel/uvwasi/buildlink3.mk"
.include "../../archivers/brotli/buildlink3.mk"
.include "../../devel/nbytes/buildlink3.mk"
.include "../../databases/sqlite3/buildlink3.mk"
.include "../../devel/merve/buildlink3.mk"
.include "../../www/llhttp/buildlink3.mk"
.include "../../devel/ada-url/buildlink3.mk"
.include "../../archivers/zstd/buildlink3.mk"
.include "../../net/libcares/buildlink3.mk"
.include "../../textproc/icu/buildlink3.mk"
.include "../../devel/re2/buildlink3.mk"

.if ${EMBERBSD_ELECTRON_SHARED_FFMPEG:Uno} == "yes"
BUILDLINK_API_DEPENDS.ffmpeg9+= ffmpeg9>=9.0.2nb7
BUILDLINK_ABI_DEPENDS.ffmpeg9+= ffmpeg9>=9.0.2nb7
.include "../../multimedia/ffmpeg9/buildlink3.mk"
.endif

.if ${EMBERBSD_ELECTRON_SHARED_MINIZIP:Uno} == "yes"
BUILDLINK_API_DEPENDS.minizip-ng+= minizip-ng>=4.2.2nb2
BUILDLINK_ABI_DEPENDS.minizip-ng+= minizip-ng>=4.2.2nb2
.include "../../archivers/minizip-ng/buildlink3.mk"
.endif

.if ${EMBERBSD_ELECTRON_SHARED_XML:Uno} == "yes"
BUILDLINK_API_DEPENDS.libxml2+= libxml2>=2.15.4nb5
BUILDLINK_ABI_DEPENDS.libxml2+= libxml2>=2.15.4nb5
BUILDLINK_API_DEPENDS.libxslt+= libxslt>=1.1.45nb3
BUILDLINK_ABI_DEPENDS.libxslt+= libxslt>=1.1.45nb3
.include "../../textproc/libxml2/buildlink3.mk"
.include "../../textproc/libxslt/buildlink3.mk"
.endif

.if ${EMBERBSD_ELECTRON_SHARED_IMAGE:Uno} == "yes"
BUILDLINK_API_DEPENDS.libjpeg-turbo+= libjpeg-turbo>=3.2.1nb1
BUILDLINK_ABI_DEPENDS.libjpeg-turbo+= libjpeg-turbo>=3.2.1nb1
BUILDLINK_API_DEPENDS.libwebp+= libwebp>=1.6.0nb4
BUILDLINK_ABI_DEPENDS.libwebp+= libwebp>=1.6.0nb4
.include "../../graphics/libjpeg-turbo/buildlink3.mk"
.include "../../graphics/libwebp/buildlink3.mk"
.endif

.if ${EMBERBSD_ELECTRON_SHARED_FONT:Uno} == "yes"
BUILDLINK_API_DEPENDS.freetype2+= freetype2>=2.15.0nb2
BUILDLINK_ABI_DEPENDS.freetype2+= freetype2>=2.15.0nb2
BUILDLINK_API_DEPENDS.harfbuzz+= harfbuzz>=15.0.0nb3
BUILDLINK_ABI_DEPENDS.harfbuzz+= harfbuzz>=15.0.0nb3
.include "../../graphics/freetype2/buildlink3.mk"
.include "../../fonts/harfbuzz/buildlink3.mk"
.endif

.if ${EMBERBSD_ELECTRON_SHARED_EXPAT:Uno} == "yes"
BUILDLINK_API_DEPENDS.expat+= expat>=2.10.0nb1
BUILDLINK_ABI_DEPENDS.expat+= expat>=2.10.0nb1
.include "../../textproc/expat/buildlink3.mk"
.endif

.if ${EMBERBSD_ELECTRON_SHARED_PFFFT:Uno} == "yes"
BUILDLINK_API_DEPENDS.pffft+= pffft>=1.1.0nb2
BUILDLINK_ABI_DEPENDS.pffft+= pffft>=1.1.0nb2
.include "../../audio/pffft/buildlink3.mk"
.endif

.if ${EMBERBSD_ELECTRON_SHARED_OPENH264:Uno} == "yes"
BUILDLINK_API_DEPENDS.openh264+= openh264>=2.7.0
BUILDLINK_ABI_DEPENDS.openh264+= openh264>=2.7.0
.include "../../multimedia/openh264/buildlink3.mk"
.endif

.if ${EMBERBSD_ELECTRON_SHARED_CODECS:Uno} == "yes"
BUILDLINK_API_DEPENDS.dav1d+= dav1d>=1.5.4
BUILDLINK_ABI_DEPENDS.dav1d+= dav1d>=1.5.4
.include "../../multimedia/dav1d/buildlink3.mk"
BUILDLINK_API_DEPENDS.libaom+= libaom>=3.15.2
BUILDLINK_ABI_DEPENDS.libaom+= libaom>=3.15.2
.include "../../multimedia/libaom/buildlink3.mk"
BUILDLINK_API_DEPENDS.libvpx+= libvpx>=1.17.0
BUILDLINK_ABI_DEPENDS.libvpx+= libvpx>=1.17.0
.include "../../multimedia/libvpx/buildlink3.mk"
BUILDLINK_API_DEPENDS.libopus+= libopus>=1.6.1nb1
BUILDLINK_ABI_DEPENDS.libopus+= libopus>=1.6.1nb1
.include "../../audio/libopus/buildlink3.mk"
BUILDLINK_API_DEPENDS.flac+= flac>=1.5.0nb1
BUILDLINK_ABI_DEPENDS.flac+= flac>=1.5.0nb1
.include "../../audio/flac/buildlink3.mk"
.endif
