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
BUILDLINK_API_DEPENDS.ffmpeg9+= ffmpeg9>=9.0.2nb6
BUILDLINK_ABI_DEPENDS.ffmpeg9+= ffmpeg9>=9.0.2nb6
.include "../../multimedia/ffmpeg9/buildlink3.mk"
.endif
