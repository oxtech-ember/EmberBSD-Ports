#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Real release patches and bounded cross links.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
abort 'Usage: webkit-source.rb PINNED_PKGSRC ARCHIVE TARGET_CXX SYSROOT NEW_OUTPUT' unless ARGV.size == 5
pkgsrc, archive, cxx, sysroot, output = ARGV.map { |path| File.expand_path(path) }
abort 'Input paths must not contain shell/CMake metacharacters.' unless
  [pkgsrc, archive, cxx, sysroot, output].all? { |path| path.match?(%r{\A[-+A-Za-z0-9_./]+\z}) }
abort 'DIGEST must name one executable.' unless ENV.fetch('DIGEST').match?(%r{\A[-+A-Za-z0-9_./]+\z})
abort 'Output must be new.' if File.exist?(output) || File.symlink?(output)
root = File.expand_path('../../..', __dir__)
abort 'Repository path must not contain CMake metacharacters.' unless root.match?(%r{\A[-+A-Za-z0-9_./]+\z})
recipe = root + '/pkgsrc/www/webkit-gtk41'
expected = 'ea0bbb02dbdbc596874a4e7ad35b66645b3e0a232bd0e4081de5ed92eb0a397d'
abort 'Wrong official WebKitGTK2.54.1 archive.' unless Digest::SHA256.file(archive).hexdigest == expected
Dir.mkdir(output)
commands = []
run = lambda do |name, argv, input: '', success: true, environment: {}|
  stdout, stderr, status = Open3.capture3(environment, *argv, stdin_data: input)
  File.write(output + '/' + name + '.log', stdout + stderr)
  commands << {name: name, argv: argv, environment: environment, exit: status.exitstatus}
  File.write(output + '/commands.json', JSON.pretty_generate(commands) + "\n")
  raise name unless status.success? == success
  stdout + stderr
end
pin = run.call('gitlink', ['git', '-C', root, 'ls-files', '--stage', 'upstream/pkgsrc']).split[1]
raise 'Wrong pkgsrc checkout.' unless run.call('pkgsrc-head', ['git', '-C', pkgsrc, 'rev-parse', 'HEAD']).strip == pin
patches = Dir[recipe + '/patches/patch-*'].sort
run.call('patch-checksums', ['awk', '-f', pkgsrc + '/mk/checksum/checksum.awk', '--', '-p', recipe + '/distinfo', *patches],
         environment: {'DIGEST' => ENV.fetch('DIGEST')})
paths = patches.flat_map { |path| File.readlines(path).grep(/^\+\+\+ /).map { |line| line.split[1] } }.uniq
raise 'Unsafe patch path.' unless paths.all? { |path| path.start_with?('Source/') && !path.split('/').include?('..') }
paths += %w[Source/cmake/VersioningUtils.cmake Source/cmake/OptionsGTK.cmake Source/cmake/WebKitCompilerFlags.cmake]
run.call('extract', ['tar', '-xJf', archive, '-C', output, *paths.uniq.map { |path| 'webkitgtk-2.54.1/' + path }])
source = output + '/webkitgtk-2.54.1'
arm = 'Source/JavaScriptCore/assembler/ARM64Assembler.h'
original_arm = File.read(source + '/' + arm)
patches.each do |path|
  run.call(File.basename(path), ['patch', '-f', '-p0', '-F', '0', '-d', source], input: File.read(path))
end
version_calls = File.read(source + '/Source/cmake/OptionsGTK.cmake')
                    .scan(/CALCULATE_LIBRARY_VERSIONS_FROM_LIBTOOL_TRIPLE\((WEBKIT|JAVASCRIPTCORE) (\d+) (\d+) (\d+)\)/)
raise 'Changed ABI version declaration shape.' unless version_calls.size == 4
cmake = "include(\"#{source}/Source/cmake/VersioningUtils.cmake\")\n"
version_calls.each_with_index do |(name, current, revision, age), i|
  cmake += "CALCULATE_LIBRARY_VERSIONS_FROM_LIBTOOL_TRIPLE(#{name} #{current} #{revision} #{age})\n"
  cmake += "file(APPEND \"#{output}/abi.txt\" \"#{i}=\${#{name}_VERSION}\\n\")\n"
end
File.write(output + '/versions.cmake', cmake)
run.call('versions', [ENV.fetch('CMAKE', 'cmake'), '-P', output + '/versions.cmake'])
versions = File.readlines(output + '/abi.txt', chomp: true).map { |line| line.split('=').last }
%w[libwebkit2gtk-4.1 libjavascriptcoregtk-4.1 libwebkitgtk-6.0 libjavascriptcoregtk-6.0].zip(versions).each_with_index do |(name, version), i|
  plist = File.read(File.dirname(recipe) + '/webkit-gtk' + (i < 2 ? '41' : '60') + '/PLIST')
  raise 'PLIST library version disagrees with upstream CMake.' unless plist.lines.map(&:chomp).include?('lib/' + name + '.so.' + version)
end
machine = run.call('compiler-target', [cxx, '-dumpmachine']).strip
raise 'This actual cache-flush regression requires AArch64.' unless machine.match?(/\Aaarch64-(unknown)?-netbsd/)
raise 'Wrong Clang release.' unless run.call('compiler-version', [cxx, '--version']).include?('clang version 23.')
triplet = 'aarch64--netbsd'
flags = ['--sysroot=' + sysroot]
environment = %w[LIBRARY_PATH CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH].to_h { |name| [name, nil] }
readelf = File.dirname(cxx) + '/' + triplet + '-readelf'
link = []
gi_project = output + '/gi-project'
Dir.mkdir(gi_project)
File.write(gi_project + '/CMakeLists.txt', "cmake_minimum_required(VERSION 3.20)\nproject(RealWebKitFindGI NONE)\nset(ENABLE_INTROSPECTION ON)\ninclude(\"#{source}/Source/cmake/FindGI.cmake\")\n")
gi_base = [ENV.fetch('CMAKE', 'cmake'), '-S', gi_project, '-DCMAKE_SYSTEM_NAME=NetBSD', '-DCMAKE_SYSTEM_PROCESSOR=aarch64']
log = run.call('gi-missing-elf-reader', gi_base + ['-B', output + '/gi-missing-reader'],
               success: false, environment: {'GI_CROSS_LAUNCHER' => nil})
raise 'Wrong GI reader refusal.' unless log.include?('Cross introspection requires an absolute GI_LDD_WRAPPER')
log = run.call('gi-missing-launcher', gi_base + ['-B', output + '/gi-missing-launcher',
               '-DGI_LDD_WRAPPER=' + root + '/pkgsrc/devel/gobject-introspection/files/elf-needed.sh'],
               success: false, environment: {'GI_CROSS_LAUNCHER' => nil})
raise 'Wrong GI launcher refusal.' unless log.include?('Cross introspection requires a real GI_CROSS_LAUNCHER')
{'original' => original_arm, 'patched' => File.read(source + '/' + arm)}.each do |mode, text|
  function = text[/    static void cacheFlush\(void\* code, size_t size\)\n    \{.*?\n    \}/m]
  raise 'Upstream cacheFlush boundary changed.' unless function
  unit = "#include <cstddef>\n#ifndef __NetBSD__\n#error Actual NetBSD compiler required\n#endif\n#define OS_NETBSD 1\n#define OS(feature) OS_##feature\nstruct ActualUpstreamCacheFlush {\n" + function + "\n};\nint main() { char code[16]{}; ActualUpstreamCacheFlush::cacheFlush(code, sizeof code); }\n"
  path = output + '/cache-' + mode + '.cpp'
  File.write(path, unit)
  log = run.call('cache-' + mode, [cxx, *flags, '-std=c++23', path, *link, '-o', output + '/cache-' + mode],
                 success: mode == 'patched', environment: environment)
  raise 'Wrong original failure.' if mode == 'original' && !log.include?('The cacheFlush support is missing on this platform.')
end
elf = run.call('cache-elf', [readelf, '-h', '-Ws', output + '/cache-patched'])
raise 'Target cache builtin was not linked.' unless elf.include?('AArch64') && elf.include?('__clear_cache')
atomic = File.read(source + '/Source/cmake/WebKitCompilerFlags.cmake')[/set\(ATOMIC_TEST_SOURCE \[=\[\n(.*?)\n    \]=\]\)/m, 1]
raise 'Upstream atomic test boundary changed.' unless atomic
File.write(output + '/atomic.cpp', atomic + "\n")
checker = recipe + '/files/check-atomic.sh'
cmake = source + '/Source/cmake/WebKitCompilerFlags.cmake'
run.call('atomic-provider', ['sh', checker, sysroot, triplet, readelf, cmake, cxx, *flags], environment: environment)
run.call('atomic-wrong-target', ['sh', checker, sysroot, 'x86_64--netbsd', readelf, cmake, cxx, *flags], success: false, environment: environment)
run.call('atomic-no-library', [cxx, *flags, '-std=c++23', output + '/atomic.cpp', *link, '-o', output + '/atomic'], environment: environment)
elf = run.call('atomic-elf', [readelf, '-h', '-d', '-Ws', output + '/atomic'])
raise 'Wrong target atomic closure.' unless elf.include?('AArch64') && !elf.include?('libatomic') && elf !~ /UND.* __atomic_/
inputs = [__FILE__, archive, cxx, checker, recipe + '/distinfo'] + patches
File.write(output + '/result.json', JSON.pretty_generate({
  scope: 'Actual release patch/checksum and CMake ABI checks; extracted real cache/atomic source target links. No full WebKit compile, package or target execution.',
  inputs: inputs.to_h { |path| [path, Digest::SHA256.file(path).hexdigest] },
  versions: versions, commands: commands
}) + "\n")
puts 'PASS: release patches, actual ABI declarations, AArch64 cache-flush and inline atomic links.'
