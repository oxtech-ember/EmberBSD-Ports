# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted).
PKG_OPTIONS_VAR=	PKG_OPTIONS.onnxruntime
PKG_SUPPORTED_OPTIONS=	webgpu
PKG_SUGGESTED_OPTIONS=	webgpu

.include "../../mk/bsd.options.mk"

.if !empty(PKG_OPTIONS:Mwebgpu)
CMAKE_CONFIGURE_ARGS+=	-Donnxruntime_USE_WEBGPU=ON
CMAKE_CONFIGURE_ARGS+=	-Donnxruntime_USE_EP_API_ADAPTERS=ON
CMAKE_CONFIGURE_ARGS+=	-Donnxruntime_ENABLE_DAWN_BACKEND_VULKAN=ON
CMAKE_CONFIGURE_ARGS+=	-Donnxruntime_ENABLE_DAWN_BACKEND_D3D12=OFF
CMAKE_CONFIGURE_ARGS+=	-Donnxruntime_BUILD_DAWN_SHARED_LIBRARY=OFF
CMAKE_CONFIGURE_ARGS+=	-Donnxruntime_CUSTOM_DAWN_SRC_PATH=${WRKDIR}/dawn-20260916.214021
CMAKE_CONFIGURE_ARGS+=	-DFETCHCONTENT_SOURCE_DIR_DAWN=${WRKDIR}/dawn-20260916.214021
CMAKE_CONFIGURE_ARGS+=	-DDAWN_FETCH_DEPENDENCIES=OFF
# Core WebGPU llm ops reuse contrib::webgpu sources (e.g. RotaryEmbedding).
CMAKE_CONFIGURE_ARGS+=	-Donnxruntime_DISABLE_CONTRIB_OPS=OFF
BUILD_TARGET+=		onnxruntime_providers_webgpu
PLIST.webgpu=		yes
DEPENDS+=		vulkan-loader>=1.4.357.0:../../graphics/vulkan-loader
.include "../../graphics/vulkan-headers/buildlink3.mk"
.include "../../graphics/vulkan-loader/buildlink3.mk"
.endif
