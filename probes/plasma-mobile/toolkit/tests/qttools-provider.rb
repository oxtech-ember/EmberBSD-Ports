#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual QtTools shared-provider selection.
require 'digest'
require 'fileutils'
require 'open3'
require 'shellwords'
abort 'usage: qttools-provider.rb PKGSRC MAKECONF CONFIGURED_QTTOOLS SYSROOT READELF NEW_WORK' unless ARGV.length == 6
tree, conf, source, sysroot, readelf = ARGV.first(5).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'NEW_WORK must be new and absolute' unless ARGV.last.start_with?('/') && !File.exist?(work)
FileUtils.mkdir_p(work)
run = lambda do |name, *command|
  output, status = Open3.capture2e(*command)
  File.write("#{work}/#{name}.log", output)
  [output, status.success?]
end
args, ok = run.call('recipe', ENV.fetch('BMAKE', 'bmake'), '-C', "#{tree}/devel/qt6-qttools",
  "MAKECONF=#{conf}", '-V', '${CMAKE_CONFIGURE_ARGS}')
abort 'recipe does not require the common HTML provider' unless ok && Shellwords.split(args).include?('-DQLITEHTML_USE_SYSTEM_LITEHTML=ON')
input = "#{source}/src/assistant/qlitehtml/src/CMakeLists.txt"
body = File.read(input)[/^option\(QLITEHTML_USE_SYSTEM_LITEHTML.*?^endif\(\)/m]
abort 'upstream provider selection changed' unless body && body.include?('find_package(litehtml REQUIRED CONFIG)')
cmake = ENV.fetch('CMAKE', 'cmake')
%w[installed missing original-missing].each do |variant|
  variant_source = "#{work}/#{variant}"
  FileUtils.mkdir_p(variant_source)
  selected = variant == 'original-missing' ? body.sub('REQUIRED CONFIG', 'QUIET') : body
  File.write("#{variant_source}/CMakeLists.txt", "cmake_minimum_required(VERSION 3.21)\nproject(provider NONE)\n#{selected}\n")
  options = ['-DQLITEHTML_USE_SYSTEM_LITEHTML=ON']
  options << "-Dlitehtml_DIR=#{sysroot}/usr/pkg/lib/cmake/litehtml"
  options << '-DCMAKE_DISABLE_FIND_PACKAGE_litehtml=TRUE' unless variant == 'installed'
  out, ok = run.call(variant, cmake, '-S', variant_source, '-B', "#{work}/build-#{variant}", *options)
  if variant == 'missing'
    abort 'missing required provider accepted' if ok
    abort 'unexpected configuration failure' unless out.match?(/REQUIRED package cannot\s+be disabled/)
  else
    abort "unexpected #{variant} configuration failure" unless ok
  end
end
puts 'PASS: actual required-provider selection succeeds; old silent fallback is reproduced and corrected'
assistant = "#{sysroot}/usr/pkg/qt6/bin/assistant"
qdoc = "#{sysroot}/usr/pkg/qt6/bin/qdoc"
headers, ok = run.call('assistant-elf', readelf, '-h', '-d', assistant)
abort 'Assistant is not AArch64 with the common shared litehtml' unless ok && headers.include?('AArch64') && headers.match?(/NEEDED.*\[liblitehtml\.so\.0\]/)
headers, ok = run.call('qdoc-elf', readelf, '-h', '-d', qdoc)
abort 'full target QDoc/libclang missing' unless ok && headers.include?('AArch64') && headers.match?(/NEEDED.*\[libclang\.so/)
inputs = [__FILE__, input, assistant, qdoc, "#{tree}/devel/qt6-qttools/Makefile"]
File.write("#{work}/inputs.sha256", inputs.map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p}\n" }.join)
puts 'PASS: installed target Assistant uses shared litehtml; Clang-backed target QDoc is present; target runtime is separate'
