# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
# Imported targets for the OpenCV contrib modules that graphics/opencv-contrib
# installs. graphics/opencv's OpenCVConfig.cmake includes this file when it
# exists, so find_package(OpenCV COMPONENTS xobjdetect ...) finds them.
get_filename_component(_OpenCVContrib_PREFIX "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)
set(_OpenCVContrib_LINK_ml "opencv_core;opencv_flann;opencv_geometry")
set(_OpenCVContrib_LINK_plot "opencv_core;opencv_flann;opencv_geometry;opencv_imgproc")
set(_OpenCVContrib_LINK_xobjdetect "opencv_core;opencv_flann;opencv_geometry;opencv_imgproc;opencv_dnn;opencv_features;opencv_imgcodecs")
set(_OpenCVContrib_LINK_face "opencv_core;opencv_flann;opencv_geometry;opencv_imgproc;opencv_photo;opencv_dnn;opencv_features;opencv_imgcodecs;opencv_xobjdetect")
set(_OpenCVContrib_LINK_tracking "opencv_core;opencv_flann;opencv_geometry;opencv_imgproc;opencv_plot;opencv_dnn;opencv_features;opencv_imgcodecs;opencv_video;opencv_videoio;opencv_highgui")
foreach(_OpenCVContrib_m IN ITEMS ml plot xobjdetect face tracking)
  set(_OpenCVContrib_t opencv_${_OpenCVContrib_m})
  if(NOT TARGET ${_OpenCVContrib_t})
    add_library(${_OpenCVContrib_t} SHARED IMPORTED)
    set_target_properties(${_OpenCVContrib_t} PROPERTIES
      IMPORTED_LOCATION "${_OpenCVContrib_PREFIX}/lib/${CMAKE_SHARED_LIBRARY_PREFIX}${_OpenCVContrib_t}${CMAKE_SHARED_LIBRARY_SUFFIX}"
      INTERFACE_LINK_LIBRARIES "${_OpenCVContrib_LINK_${_OpenCVContrib_m}}")
  endif()
  if(NOT ";${OpenCV_LIB_COMPONENTS};" MATCHES ";${_OpenCVContrib_t};")
    list(APPEND OpenCV_LIB_COMPONENTS ${_OpenCVContrib_t})
  endif()
  unset(_OpenCVContrib_LINK_${_OpenCVContrib_m})
endforeach()
unset(_OpenCVContrib_m)
unset(_OpenCVContrib_t)
unset(_OpenCVContrib_PREFIX)
