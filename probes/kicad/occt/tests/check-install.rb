#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Execute actual OCCT CMake install fragments.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
abort 'Usage: check-install.rb ORIGINAL_SOURCE PATCHED_SOURCE NEW_WORK' unless ARGV.length == 3
original, patched = ARGV.take(2).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'Use a new absolute output directory.' unless ARGV.last == work && !File.exist?(work) && !File.symlink?(work)
FileUtils.mkdir_p(work)
cmake = ENV.fetch('CMAKE', 'cmake')
records = []
run = lambda do |name, env, argv|
  out, err, status = Open3.capture3(env, *argv)
  File.write(work + '/' + name + '.log', out + err)
  records << { name: name, argv: argv, status: status.exitstatus }
  File.write(work + '/commands.json', JSON.pretty_generate(records) + "\n")
  abort "#{name} failed." unless status.success?
end
{ 'before' => original, 'after' => patched }.each do |variant, source|
  main = File.read(source + '/CMakeLists.txt')
  start = main.index('if (WIN32)' + "\n" + '  set (ADDITIONAL_CUSTOM_CONTENT') or abort 'Missing upstream custom-script block.'
  finish = main.index('if (WIN32)' + "\n" + '  set (THIRDPARTY_DIR_REPLACE', start) or abort 'Missing next upstream block.'
  custom_block = main[start...finish]
  flags_block = main.lines.grep(/^install \(CODE.*(?:TOLOWER|file\(INSTALL FILES).*CMAKE_INSTALL_CONFIG_NAME/).join
  abort 'Missing exact upstream flags install statements.' unless flags_block.lines.length == 2
  project = work + '/' + variant + '/source'
  build = work + '/' + variant + '/build'
  prefix = work + '/' + variant + '/prefix'
  stage = work + '/' + variant + '/stage'
  FileUtils.mkdir_p([project, build, prefix + '/bin', stage])
  # These are installation inputs, not libraries or replacement OCCT code.
  File.write(build + '/custom.sh', "existing build script\n")
  expected = "\nif [ -e \"${aScriptPath}/custom_gcc_64.sh\" ]; then\n  source \"${aScriptPath}/custom_gcc_64.sh\" \"$1\" \"$2\" \nfi"
  File.write(prefix + '/bin/custom.sh', expected)
  sentinel = Digest::SHA256.file(prefix + '/bin/custom.sh').hexdigest
  File.write(build + '/OpenCASCADECompileDefinitionsAndFlags-release.cmake', "set(OCCT_INSTALL_FIXTURE ON)\n")
  File.write(project + '/CMakeLists.txt', <<~CMAKE + custom_block + flags_block)
    cmake_minimum_required(VERSION 3.22)
    project(occt_install_source_contract NONE)
    set(OCCT_ROOT_DIR "#{source}")
    set(OCCT_BINARY_DIR "#{build}")
    set(INSTALL_DIR "#{prefix}")
    set(CMAKE_INSTALL_PREFIX "#{prefix}")
    set(INSTALL_DIR_SCRIPT bin)
    set(INSTALL_DIR_CMAKE lib/cmake/opencascade)
    set(SCRIPT_EXT sh)
    set(SUB_CUSTOM_NAME custom_gcc_64.sh)
    include("#{source}/adm/cmake/occt_macros.cmake")
  CMAKE
  run.call(variant + '-configure', {}, [cmake, '-S', project, '-B', build])
  run.call(variant + '-install', { 'DESTDIR' => stage }, [cmake, '--install', build, '--config', 'Release'])
  abort 'Installed prefix was modified.' unless Digest::SHA256.file(prefix + '/bin/custom.sh').hexdigest == sentinel
  files = Dir.glob(stage + '/**/*', File::FNM_DOTMATCH).select { |p| File.file?(p) }
  expected_flags = stage + prefix + '/lib/cmake/opencascade/OpenCASCADECompileDefinitionsAndFlags-release.cmake'
  abort 'Compile-definitions file escaped the single DESTDIR boundary.' unless files.include?(expected_flags)
  custom = stage + prefix + '/bin/custom.sh'
  if variant == 'before'
    abort 'Baseline unexpectedly installed custom.sh.' if File.exist?(custom)
    abort 'Unexpected baseline payload.' unless files == [expected_flags]
  else
    abort 'Patched custom.sh is missing or incorrect.' unless File.file?(custom) && File.read(custom).include?(expected)
    abort 'Unexpected patched payload.' unless files.sort == [expected_flags, custom].sort
  end
end
puts 'PASS: original custom.sh omission; patched installation; one DESTDIR boundary.'
