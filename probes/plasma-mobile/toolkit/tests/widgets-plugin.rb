#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), upstream cross-option and target plugin regression.
require 'fileutils'
require 'open3'
require 'digest'
abort 'usage: widgets-plugin.rb PKGSRC MAKECONF CONFIGURED_SOURCE SYSROOT READELF NEW_WORK' unless ARGV.length == 6
tree, conf, source, sysroot, readelf = ARGV.first(5).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'NEW_WORK must be new and absolute' unless ARGV.last.start_with?('/') && !File.exist?(work)
FileUtils.mkdir_p(work)
make = ENV.fetch('BMAKE', 'bmake')
cmake = ENV.fetch('CMAKE', 'cmake')
input = "#{source}/CMakeLists.txt"
fixed = File.read(input).lines.find { |line| line.start_with?('option(BUILD_DESIGNERPLUGIN ') }
abort 'corrected upstream option missing' unless fixed
original = fixed.sub('option(', 'cmake_dependent_option(').sub(' ON)', ' ON "NOT CMAKE_CROSSCOMPILING" OFF)')
[[false, original, 'ON'], [true, original, 'OFF'], [false, fixed, 'ON'], [true, fixed, 'ON']].each_with_index do |(cross, option, expected), i|
  script = "#{work}/option-#{i}.cmake"
  File.write(script, "cmake_minimum_required(VERSION 3.21)\ninclude(CMakeDependentOption)\nset(CMAKE_CROSSCOMPILING #{cross ? 'TRUE' : 'FALSE'})\n#{option}\nfile(WRITE \"#{work}/result-#{i}\" \"${BUILD_DESIGNERPLUGIN}\")\n")
  output, status = Open3.capture2e(cmake, '-P', script)
  File.write("#{work}/option-#{i}.log", output)
  abort 'unexpected option behavior' unless status.success? && File.read("#{work}/result-#{i}") == expected
end
out, status = Open3.capture2e(make, '-C', "#{tree}/x11/kf6-kwidgetsaddons", "MAKECONF=#{conf}", '-V', '${DEPENDS}', '-V', '${BUILD_DEPENDS}')
File.write("#{work}/dependencies.txt", out)
abort 'dependency query failed' unless status.success? && out.lines.length == 2
runtime, build = out.lines
abort 'QtTools should be a build dependency only' unless build.include?('qt6-qttools>=6.12.0') && !runtime.include?('qt6-qttools')
abort 'Qtbase runtime dependency missing' unless runtime.include?('qt6-qtbase>=6.12.0')
plugin = "#{sysroot}/usr/pkg/qt6/plugins/designer/kwidgetsaddons6widgets.so"
out, status = Open3.capture2e(readelf, '-h', '-d', plugin)
File.write("#{work}/plugin.elf", out)
abort 'installed target plugin missing' unless status.success? && out.include?('AArch64') && out.include?('[libKF6WidgetsAddons.so.6]')
abort 'unexpected QtTools DSO' if out.match?(/NEEDED.*libQt6(?:Designer|Help|UiTools)/)
inputs = [__FILE__, input, plugin, "#{tree}/x11/kf6-kwidgetsaddons/Makefile"]
File.write("#{work}/inputs.sha256", inputs.map { |f| "#{Digest::SHA256.file(f).hexdigest}  #{f}\n" }.join)
puts 'PASS: old cross exclusion reproduced; native default preserved; installed AArch64 plugin and build-only QtTools verified'
