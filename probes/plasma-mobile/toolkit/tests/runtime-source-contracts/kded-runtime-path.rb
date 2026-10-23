#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Evaluate the real KDED source CMake file. External framework targets are doubled.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'
abort "Usage: #{$PROGRAM_NAME} DISTFILES NEW_OUTPUT" unless ARGV.size == 2
distfiles, output = ARGV.map { |path| File.expand_path(path) }
abort 'Output exists' if File.exist?(output)
FileUtils.mkdir_p(output)
recipe = File.expand_path('../../../../../pkgsrc/x11/kf6-kded', __dir__)
archive = File.join(distfiles, 'kded-6.31.0.tar.xz')
distinfo = File.read(File.join(recipe, 'distinfo'))
expected = distinfo[/^SHA512 \(kded-6\.31\.0\.tar\.xz\) = (\h+)$/, 1]
abort 'Archive hash mismatch' unless expected && Digest::SHA512.file(archive).hexdigest == expected
patch = File.join(recipe, 'patches/patch-src_CMakeLists.txt')
expected = distinfo[/^SHA1 \(patch-src_CMakeLists\.txt\) = (\h+)$/, 1]
canonical = File.readlines(patch).reject { |line| line.match?(/\$NetBSD.*/) }.join
abort 'Patch hash mismatch' unless expected && Digest::SHA1.hexdigest(canonical) == expected

def run(command, log, **options)
  stdout, stderr, status = Open3.capture3(*command, **options)
  File.write(log, command.shelljoin + "\n" + stdout + stderr + "\nexit=#{status.exitstatus}\n")
  abort "Command failed: #{log}" unless status.success?
end

run(['tar', '-xf', archive, '-C', output], output+'/extract.log')
FileUtils.mv(output+'/kded-6.31.0', output+'/baseline')
FileUtils.cp_r(output+'/baseline', output+'/patched')
run(['patch', '-p0', '-F', '0', '-i', patch], output+'/patch.log', chdir: output+'/patched')

cases = [
  ['cross', true, '/usr/pkg/libexec/kf6', '/build-host/bin/kconf_update'],
  ['cross-prefix', true, '/opt/ember tools/libexec/kf6', '/build-host/bin/kconf_update'],
  ['cross-libexec', true, '/custom/libexec/kf6', '/build-host/bin/kconf_update'],
  ['native', false, '/usr/pkg/libexec/kf6', '/native/build/bin/kconf_update']
]
results = []
cmake = ENV.fetch('CMAKE', 'cmake')
cases.each do |name, cross, libexec, imported|
  %w[baseline patched].each do |variant|
    source = File.join(output, name+'-'+variant)
    FileUtils.mkdir_p(source)
    File.write(source+'/CMakeLists.txt', <<~CMAKE)
      cmake_minimum_required(VERSION 3.30)
      project(KdedRuntimePath LANGUAGES CXX)
      # These are the public inputs supplied by KDEInstallDirs in the full build.
      set(KDE_INSTALL_FULL_LIBEXECDIR_KF "#{libexec}")
      set(KDE_INSTALL_FULL_BINDIR "/usr/pkg/bin")
      set(KDE_INSTALL_SYSTEMDUSERUNITDIR "lib/systemd/user")
      set(KDE_INSTALL_DBUSINTERFACEDIR "share/dbus-1/interfaces")
      set(KDE_INSTALL_LOGGINGCATEGORIESDIR "share/qlogging-categories6")
      set(KF_INSTALL_TARGETS_DEFAULT_ARGS RUNTIME DESTINATION bin)
      add_executable(KF6::kconf_update IMPORTED GLOBAL)
      set_target_properties(KF6::kconf_update PROPERTIES IMPORTED_LOCATION "#{imported}")
      foreach(dependency Qt6::Widgets KF6::Service KF6::CoreAddons KF6::DBusAddons KF6::Crash KF6::ConfigCore)
        add_library(${dependency} INTERFACE IMPORTED GLOBAL)
      endforeach()
      function(ecm_qt_declare_logging_category)
      endfunction()
      function(ecm_mark_nongui_executable)
      endfunction()
      function(kdbusaddons_generate_dbus_service_file)
      endfunction()
      function(ecm_qt_install_logging_categories)
      endfunction()
      function(qt_generate_dbus_interface header name)
        file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/${name}" "")
      endfunction()
      add_subdirectory("#{output}/#{variant}/src" real-src)
      file(GENERATE OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/definitions.txt"
        CONTENT "$<TARGET_PROPERTY:kded6,COMPILE_DEFINITIONS>\n")
      file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/cross.txt" "${CMAKE_CROSSCOMPILING}\n")
    CMAKE
    command = [cmake, '-S', source, '-B', source+'/build', '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON']
    command << '-DCMAKE_SYSTEM_NAME=Generic' if cross
    run(command, source+'/configure.log')
    actual_cross = File.read(source+'/build/cross.txt').strip == 'TRUE'
    abort "Wrong CMake cross mode: #{name}" unless actual_cross == cross
    definition = File.read(source+'/build/definitions.txt').strip
    wanted = cross ? libexec+'/kconf_update' : imported
    correct = definition == "KCONF_UPDATE_EXE=\"#{wanted}\""
    should_pass = variant == 'patched' || !cross
    abort "Wrong runtime selection in #{name}/#{variant}: #{definition}" unless correct == should_pass
    if !should_pass && definition != "KCONF_UPDATE_EXE=\"#{imported}\""
      abort "Baseline failed for an unrelated reason: #{definition}"
    end
    commands = JSON.parse(File.read(source+'/build/compile_commands.json'))
    abort 'Missing real kded.cpp compile command' unless commands.any? { |entry| File.basename(entry['file']) == 'kded.cpp' }
    results << {case: name, source: variant, cross: cross, definition: definition,
                target_runtime_path: wanted, correct_runtime_path: correct}
  end
end
File.write(output+'/results.json', JSON.pretty_generate(results)+"\n")
puts 'PASS: actual KDED CMake rejects three host-tool runtime paths; patched cross prefixes and native target selection pass'
