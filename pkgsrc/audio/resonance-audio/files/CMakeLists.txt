# Copyright (C) 2022 The Qt Company Ltd.
# SPDX-License-Identifier: BSD-3-Clause
# Origin: Qt Multimedia 6.12 CMake source list; EmberBSD contributors (AI-assisted).
cmake_minimum_required(VERSION 3.16)
project(resonance_audio VERSION 1.0.0 LANGUAGES CXX)
include(GNUInstallDirs)
find_package(Eigen3 5.0.1 REQUIRED NO_MODULE)
find_package(pffft CONFIG REQUIRED)
find_package(Threads REQUIRED)
add_library(resonance_audio
  platforms/common/utils.cc
  resonance_audio/ambisonics/ambisonic_binaural_decoder.cc
  resonance_audio/ambisonics/ambisonic_lookup_table.cc
  resonance_audio/ambisonics/associated_legendre_polynomials_generator.cc
  resonance_audio/ambisonics/foa_rotator.cc
  resonance_audio/ambisonics/hoa_rotator.cc
  resonance_audio/ambisonics/stereo_from_soundfield_converter.cc
  resonance_audio/api/binaural_surround_renderer.cc
  resonance_audio/api/resonance_audio_api.cc
  resonance_audio/base/audio_buffer.cc
  resonance_audio/base/channel_view.cc
  resonance_audio/base/misc_math.cc
  resonance_audio/base/simd_utils.cc
  resonance_audio/base/spherical_angle.cc
  resonance_audio/config/source_config.cc
  resonance_audio/dsp/biquad_filter.cc
  resonance_audio/dsp/channel_converter.cc
  resonance_audio/dsp/circular_buffer.cc
  resonance_audio/dsp/delay_filter.cc
  resonance_audio/dsp/distance_attenuation.cc
  resonance_audio/dsp/fft_manager.cc
  resonance_audio/dsp/filter_coefficient_generators.cc
  resonance_audio/dsp/fir_filter.cc
  resonance_audio/dsp/gain.cc
  resonance_audio/dsp/gain_mixer.cc
  resonance_audio/dsp/gain_processor.cc
  resonance_audio/dsp/mixer.cc
  resonance_audio/dsp/mono_pole_filter.cc
  resonance_audio/dsp/multi_channel_iir.cc
  resonance_audio/dsp/near_field_processor.cc
  resonance_audio/dsp/occlusion_calculator.cc
  resonance_audio/dsp/partitioned_fft_filter.cc
  resonance_audio/dsp/reflections_processor.cc
  resonance_audio/dsp/resampler.cc
  resonance_audio/dsp/reverb_onset_compensator.cc
  resonance_audio/dsp/reverb_onset_update_processor.cc
  resonance_audio/dsp/sh_hrir_creator.cc
  resonance_audio/dsp/shoe_box_room.cc
  resonance_audio/dsp/spectral_reverb.cc
  resonance_audio/dsp/stereo_panner.cc
  resonance_audio/dsp/utils.cc
  resonance_audio/graph/ambisonic_binaural_decoder_node.cc
  resonance_audio/graph/ambisonic_mixing_encoder_node.cc
  resonance_audio/graph/binaural_surround_renderer_impl.cc
  resonance_audio/graph/buffered_source_node.cc
  resonance_audio/graph/foa_rotator_node.cc
  resonance_audio/graph/gain_mixer_node.cc
  resonance_audio/graph/gain_node.cc
  resonance_audio/graph/graph_manager.cc
  resonance_audio/graph/hoa_rotator_node.cc
  resonance_audio/graph/mixer_node.cc
  resonance_audio/graph/mono_from_soundfield_node.cc
  resonance_audio/graph/near_field_effect_node.cc
  resonance_audio/graph/occlusion_node.cc
  resonance_audio/graph/reflections_node.cc
  resonance_audio/graph/resonance_audio_api_impl.cc
  resonance_audio/graph/reverb_node.cc
  resonance_audio/graph/source_parameters_manager.cc
  resonance_audio/graph/stereo_mixing_panner_node.cc
  resonance_audio/node/processing_node.cc
  resonance_audio/node/sink_node.cc
  resonance_audio/node/source_node.cc
  platforms/common/room_effects_utils.cc
  resonance_audio/utils/buffer_crossfader.cc
  resonance_audio/utils/buffer_partitioner.cc
  resonance_audio/utils/buffer_unpartitioner.cc
  resonance_audio/utils/lockless_task_queue.cc
  resonance_audio/utils/planar_interleaved_conversion.cc
  resonance_audio/utils/sample_type_conversion.cc
  resonance_audio/utils/sum_and_difference_processor.cc
  resonance_audio/utils/wav.cc
  resonance_audio/utils/wav_reader.cc
  third_party/SADIE_hrtf_database/generated/hrtf_assets.cc
)
add_library(resonance_audio::resonance_audio ALIAS resonance_audio)
set_target_properties(resonance_audio PROPERTIES VERSION 1.0.0 SOVERSION 1)
target_compile_features(resonance_audio PUBLIC cxx_std_14)
target_compile_definitions(resonance_audio PRIVATE EIGEN_MPL2_ONLY)
if(CMAKE_SIZEOF_VOID_P EQUAL 4)
  target_compile_definitions(resonance_audio PRIVATE DISABLE_SIMD)
endif()
target_include_directories(resonance_audio PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/resonance_audio>
  $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}/resonance_audio>
  $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}/resonance_audio/resonance_audio>
  PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/third_party/SADIE_hrtf_database/generated)
target_link_libraries(resonance_audio PUBLIC Eigen3::Eigen PFFFT::PFFFT Threads::Threads)
install(TARGETS resonance_audio EXPORT resonance-audio-targets)
install(DIRECTORY resonance_audio/ DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/resonance_audio/resonance_audio FILES_MATCHING PATTERN "*.h")
install(DIRECTORY platforms/common/ DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/resonance_audio/platforms/common FILES_MATCHING PATTERN "*.h")
install(EXPORT resonance-audio-targets NAMESPACE resonance_audio:: DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/resonance_audio)
include(CMakePackageConfigHelpers)
configure_package_config_file(${CMAKE_CURRENT_SOURCE_DIR}/resonance_audio-config.cmake.in ${CMAKE_CURRENT_BINARY_DIR}/resonance_audio-config.cmake INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/resonance_audio)
write_basic_package_version_file(${CMAKE_CURRENT_BINARY_DIR}/resonance_audio-config-version.cmake VERSION ${PROJECT_VERSION} COMPATIBILITY ExactVersion)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/resonance_audio-config.cmake ${CMAKE_CURRENT_BINARY_DIR}/resonance_audio-config-version.cmake DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/resonance_audio)
