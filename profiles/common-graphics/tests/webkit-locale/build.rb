#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Selected actual Skia translation units.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'
abort 'Usage: build.rb WEBKIT_ARCHIVE TARGET_CXX SYSROOT NEW_OUTPUT' unless ARGV.size == 4
archive, target_cxx, sysroot, output = ARGV.map { |path| File.expand_path(path) }
abort 'Output must be new.' if File.exist?(output) || File.symlink?(output)
abort 'Wrong official WebKitGTK2.54.1 archive.' unless Digest::SHA256.file(archive).hexdigest == 'ea0bbb02dbdbc596874a4e7ad35b66645b3e0a232bd0e4081de5ed92eb0a397d'
root = File.expand_path('../../../..', __dir__)
native = Shellwords.split(ENV.fetch('NATIVE_CXX'))
abort 'NATIVE_CXX must name a genuine compiler.' if native.empty?
Dir.mkdir(output)
commands = []
run = lambda do |name, argv, input: '', environment: {}|
  stdout, stderr, status = Open3.capture3(environment, *argv, stdin_data: input)
  File.write(output + '/' + name + '.log', stdout + stderr)
  commands << {name: name, argv: argv, environment: environment, exit: status.exitstatus}
  File.write(output + '/commands.json', JSON.pretty_generate(commands) + "\n")
  raise name unless status.success?
  stdout
end
raise 'Actual AArch64 GCC16 is required.' unless run.call('target', [target_cxx, '-dumpmachine']).strip == 'aarch64--netbsd'
raise 'GCC16.2 is required.' unless run.call('target-version', [target_cxx, '-dumpfullversion']).strip == '16.2.0' && run.call('native-version', native + ['-dumpfullversion']).strip == '16.2.0'
run.call('extract-skia', ['tar', '-xJf', archive, '-C', output, 'webkitgtk-2.54.1/Source/ThirdParty/skia'])
source = output + '/webkitgtk-2.54.1'
patches = Dir[root + '/pkgsrc/www/webkit-gtk41/patches/patch-Source_ThirdParty_skia*'].sort
raise 'Expected the complete three-patch Skia set.' unless patches.size == 3
patches.each { |path| run.call(File.basename(path), ['patch', '-f', '-p0', '-F', '0', '-d', source], input: File.read(path)) }
source += '/Source/ThirdParty/skia'
units = %w[src/core/SkString.cpp src/core/SkUTF.cpp src/core/SkContainers.cpp src/core/SkDebug.cpp src/core/SkLog.cpp src/ports/SkLog_stdio.cpp src/ports/SkMemory_malloc.cpp src/sksl/SkSLString.cpp src/utils/SkParse.cpp src/utils/SkLogHandler.cpp]
extra = %w[src/sksl/SkSLOutputStream.cpp src/sksl/tracing/SkSLDebugTracePriv.cpp src/utils/SkJSONWriter.cpp]
flags = ['-std=c++23', '-O2', '-g', '-DSK_DEBUG', '-ffunction-sections', '-fdata-sections', '-I' + source, '-pthread']
target = [target_cxx, '--sysroot=' + sysroot, '-B' + sysroot + '/usr/lib/', '-B' + sysroot + '/usr/pkg/gcc16/lib/']
target_environment = %w[LIBRARY_PATH CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH].to_h { |name| [name, nil] }
%w[native target].each do |mode|
  directory = output + '/' + mode
  Dir.mkdir(directory)
  compiler = mode == 'native' ? native : target
  environment = mode == 'native' ? {} : target_environment
  objects = []
  (units + extra).each_with_index do |unit, index|
    object = directory + '/' + index.to_s + '.o'
    run.call(mode + '-' + index.to_s, compiler + flags + ['-c', source + '/' + unit, '-o', object], environment: environment)
    objects << object if index < units.size
  end
  link = mode == 'target' ? ['-L' + sysroot + '/usr/pkg/gcc16/lib', '-Wl,-rpath,/usr/pkg/gcc16/lib', '-Wl,-rpath-link,' + sysroot + '/usr/pkg/gcc16/lib'] : []
  dependencies = mode == 'target' ? ['-MD', '-MF', directory + '/contract.d'] : []
  run.call(mode + '-link', compiler + flags + dependencies + [__dir__ + '/contract.cpp', *objects, '-Wl,--gc-sections', *link, '-o', directory + '/contract'], environment: environment)
end
# Keep system-header dependencies: -MMD would hide the selected C++ locale header.
dependency_file = output + '/target/contract.d'
selected_headers = Shellwords.split(File.read(dependency_file).gsub(/\\\n/, ' ')).select do |path|
  path.end_with?('/bits/c++locale.h')
end
expected_header = sysroot + '/usr/pkg/gcc16/include/c++/aarch64--netbsd/bits/c++locale.h'
raise 'The target compiler did not use the supplied SDK C++ locale header.' unless
  selected_headers.size == 1 && File.realpath(selected_headers.first) == File.realpath(expected_header)
locale = ENV.fetch('COMMA_LOCALE', 'fr_FR.UTF-8')
run.call('native-run', [output + '/native/contract', locale])
run.call('native-memcheck', Shellwords.split(ENV.fetch('MEMCHECK', 'valgrind')) +
         ['--leak-check=full', '--show-leak-kinds=all', '--errors-for-leak-kinds=all', '--error-exitcode=99', output + '/native/contract', locale])
inputs = [__FILE__, __dir__ + '/contract.cpp', archive, target_cxx,
          sysroot + '/usr/pkg/gcc16/include/c++/aarch64--netbsd/bits/c++locale.h',
          sysroot + '/usr/pkg/gcc16/lib/libstdc++.so.7'] + patches
File.write(output + '/result.json', JSON.pretty_generate({
  scope: 'Native selected real Skia APIs, strict native Memcheck, all adapted source units compiled native/target. Target execution and complete WebKit acceptance are separate.',
  target_locale_header: {path: selected_headers.first, realpath: File.realpath(selected_headers.first),
                         dependencies_sha256: Digest::SHA256.file(dependency_file).hexdigest},
  inputs: inputs.to_h { |path| [path, Digest::SHA256.file(path).hexdigest] },
  binaries: %w[native target].to_h { |mode| [mode, Digest::SHA256.file(output + '/' + mode + '/contract').hexdigest] },
  commands: commands
}) + "\n")
puts 'PASS: actual native selected Skia APIs/Memcheck and AArch64 builds. Target runtime verification remains required.'
