# $NetBSD: Makefile,v 1.61 2026/08/26 10:19:07 adam Exp $

# can't use ninja because we only want to install parts of it
CMAKE_GENERATORS_INCOMPATIBLE=	ninja
INSTALL_DIRS=		modules/face modules/ml modules/plot modules/tracking modules/xobjdetect
# The one cv2 Python module, built here where every module is available.
INSTALL_DIRS+=		modules/python3

.include "../../graphics/opencv/Makefile.common"

DISTNAME=	opencv_contrib-${OPENCV_VERSION}
PKGNAME=	${DISTNAME:S/_contrib/-contrib/}
PKGREVISION=	3
GITHUB_PROJECT=	opencv_contrib

MAINTAINER=	markd@NetBSD.org
COMMENT=	OpenCV contributed modules and the cv2 Python module

PY_PATCHPLIST=		yes
PYTHON_VERSIONS_INCOMPATIBLE=	310 311
CMAKE_CONFIGURE_ARGS+=		-DPYTHON_EXECUTABLE=${PYTHONBIN}

DISTFILES=	${DEFAULT_DISTFILES} opencv-${PKGVERSION_NOREV}${EXTRACT_SUFX} opencv-${PKGVERSION_NOREV}_face_landmark_model.dat
# use the hash from modules/face/CMakeLists.txt
SITES.opencv-5.0.0_face_landmark_model.dat=	-https://raw.githubusercontent.com/opencv/opencv_3rdparty/8afa57abc8229d611c4937165d20e2a2d9fc5a12/face_landmark_model.dat

WRKSRC=		${WRKDIR}/opencv-${PKGVERSION_NOREV}
# The OpenCV sources are the graphics/opencv sources.
DISTINFO_FILE=	${.CURDIR}/../../graphics/opencv/distinfo
PATCHDIR=	${.CURDIR}/../../graphics/opencv/patches

# Give the face model to the OpenCV download cache under the hash from
# modules/face/CMakeLists.txt, and never download during the build.
FACE_MODEL_MD5=	7505c44ca4eb54b4ab1e4777cb96ac05
CMAKE_CONFIGURE_ARGS+=		-DOPENCV_DOWNLOAD_PATH=${WRKDIR}/opencv-download
CMAKE_CONFIGURE_ARGS+=		-DOPENCV_DOWNLOAD_TRIES_LIST=

post-extract:
	${MKDIR} ${WRKDIR}/opencv-download/data
	${CP} ${WRKDIR}/opencv-${PKGVERSION_NOREV}_face_landmark_model.dat \
	    ${WRKDIR}/opencv-download/data/${FACE_MODEL_MD5}-face_landmark_model.dat

# Build the OpenCV modules with the options of graphics/opencv, so cv2
# matches the installed libraries.
.include "../../graphics/opencv/options.mk"

CMAKE_CONFIGURE_ARGS+=		-DOPENCV_EXTRA_MODULES_PATH=${WRKDIR}/${DISTNAME}/modules
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_adas=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_aruco=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_bgsegm=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_bioinspired=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_ccalib=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_contrib_world=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_cvv=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_datasets=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_dnn_objdetect=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_dpm=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_fuzzy=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_hdf=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_hfs=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_img_hash=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_intensity_transform=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_latentsvm=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_line_descriptor=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_matlab=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_optflow=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_phase_unwrapping=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_rapid=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_reg=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_rgbd=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_saliency=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_shape=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_signal=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_structured_light=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_surface_matching=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_text=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_xfeatures2d=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_ximgproc=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_xphoto=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_dnn_superres=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_quality=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_wechat_qrcode=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_xstereo=OFF

CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_ml=ON
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_python2=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_python3=ON
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_superres=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_ts=OFF
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_videostab=OFF

# needed by face
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_xobjdetect=ON
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_geometry=ON
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_photo=ON
# needed by xobjdetect
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_objdetect=ON
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_features=ON
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_imgcodecs=ON
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_flann=ON
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_imgproc=ON
# needed by flann and objdetect
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_core=ON

# needed by tracking
CMAKE_CONFIGURE_ARGS+=		-DBUILD_opencv_video=ON

# OpenCVConfig.cmake from graphics/opencv loads this file, so the modules
# above are find_package(OpenCV) components.
INSTALLATION_DIRS+=	lib/cmake/opencv5
post-install:
	${INSTALL_DATA} ${FILESDIR}/OpenCVContribModules.cmake \
	    ${DESTDIR}${PREFIX}/lib/cmake/opencv5/

BUILDLINK_API_DEPENDS.opencv+=	opencv>=${PKGVERSION_NOREV}
.include "../../graphics/opencv/buildlink3.mk"
.include "../../lang/python/extension.mk"
.include "../../math/py-numpy/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
