#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); real Abseil CMake metadata regression.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'

abort 'Usage: abseil-metadata.rb ARCHIVE TARGET_TOOLCHAIN NATIVE_CXX NEW_WORK' unless ARGV.length == 4
archive, toolchain, native_cxx = ARGV.take(3).map { |p| File.realpath(p) }
work = File.expand_path(ARGV[3])
abort 'Output exists.' if File.exist?(work) || File.symlink?(work)
abort 'Wrong Abseil archive.' unless Digest::SHA256.file(archive).hexdigest == 'f7e05179df39c45434cad433f5783840bb3788ef322976f9138bc6b72b3a107d'
root = File.expand_path('../../..', __dir__)
recipe = root + '/profiles/common-build-tools/recipes/devel/abseil'
patches = Dir.glob(recipe + '/patches/patch-*').sort
fix = recipe + '/patches/patch-absl_debugging_CMakeLists.txt'
abort 'Expected six source patches.' unless patches.size == 6 && patches.include?(fix)
FileUtils.mkdir_p(work)
commands = []
run = lambda do |name, argv, env = {}, success = true|
  stdout, stderr, status = Open3.capture3({ 'LC_ALL' => 'C' }.merge(env), *argv)
  File.write(work + '/' + name + '.stdout', stdout)
  File.write(work + '/' + name + '.stderr', stderr)
  commands << { name: name, argv: argv, status: status.exitstatus }
  File.write(work + '/commands.json', JSON.pretty_generate(commands) + "\n")
  abort "Unexpected #{name} status #{status.exitstatus}" unless status.success? == success
  stdout + stderr
end
run.call('extract', ['tar', '-xzf', archive, '-C', work])
baseline = work + '/baseline'
File.rename(work + '/abseil-cpp-20260817.0', baseline)
(patches - [fix]).each_with_index do |patch, i|
  run.call("base-patch-#{i}", ['patch', '-f', '-p0', '-F', '0', '-d', baseline, '-i', patch])
end
patched = work + '/patched'
FileUtils.cp_r(baseline, patched)
run.call('metadata-patch', ['patch', '-f', '-p0', '-F', '0', '-d', patched, '-i', fix])
cmake = ENV.fetch('CMAKE', 'cmake')
common = ['-G', 'Ninja', '-DCMAKE_INSTALL_PREFIX=/usr/pkg', '-DCMAKE_INSTALL_LIBDIR=lib',
          '-DCMAKE_CXX_STANDARD=17', '-DCMAKE_BUILD_TYPE=Release', '-DABSL_BUILD_TESTING=OFF',
          '-DABSL_ENABLE_INSTALL=ON', '-DBUILD_SHARED_LIBS=ON']
target_env = %w[LIBRARY_PATH CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH OBJC_INCLUDE_PATH].to_h { |n| [n, nil] }
%w[native target].each do |kind|
  [baseline, patched].each do |source|
    name = kind + '-' + File.basename(source)
    options = kind == 'native' ? ["-DCMAKE_CXX_COMPILER=#{native_cxx}"] : ["-DCMAKE_TOOLCHAIN_FILE=#{toolchain}"]
    run.call(name, [cmake, '-S', source, '-B', work + '/' + name] + common + options,
             kind == 'target' ? target_env : {})
  end
end
read_pc = lambda do |name|
  Dir.glob(work + '/' + name + '/lib/pkgconfig/*.pc').to_h { |p| [File.basename(p), File.binread(p)] }
end
native_before, native_after = %w[native-baseline native-patched].map { |n| read_pc.call(n) }
abort 'Native pkg-config changed.' unless !native_before.empty? && native_before == native_after
target_before, target_after = %w[target-baseline target-patched].map { |n| read_pc.call(n) }
abort 'Missing target pkg-config output.' unless target_before.keys.sort == target_after.keys.sort && !target_before.empty?
cache = File.read(work + '/target-baseline/CMakeCache.txt')
execinfo = cache[/^EXECINFO_LIBRARY:FILEPATH=(.+)$/, 1]
abort 'Target baseline did not discover real execinfo.' unless execinfo && File.file?(execinfo)
abort 'Baseline does not reproduce the absolute library path.' unless target_before.fetch('absl_stacktrace.pc').include?(execinfo)
abort 'Patched metadata lacks execinfo.' unless target_after.fetch('absl_stacktrace.pc').match?(/\s-lexecinfo(?:\s|$)/)
changed = target_before.keys.select { |n| target_before[n] != target_after[n] }
abort 'Unexpected target metadata change.' unless changed == ['absl_stacktrace.pc']
abort 'Host metadata path retained.' if target_after.values.any? { |s| s.include?(work) || s.include?(File.dirname(execinfo)) }
system_file = Dir.glob(work + '/target-patched/CMakeFiles/*/CMakeSystem.cmake').fetch(0)
system_text = File.read(system_file)
abort 'Not a real NetBSD cross configuration.' unless system_text.include?('set(CMAKE_SYSTEM_NAME "NetBSD")') && system_text.include?('set(CMAKE_CROSSCOMPILING "TRUE")')
# Check static export semantics too. This configures real targets but builds none.
run.call('target-static', [cmake, '-S', patched, '-B', work + '/target-static'] + common +
         ["-DCMAKE_TOOLCHAIN_FILE=#{toolchain}", '-DBUILD_SHARED_LIBS=OFF'], target_env)
exports = Dir.glob(work + '/target-static/CMakeFiles/Export/**/abslTargets.cmake')
abort 'Static exported dependency missing.' unless exports.size == 1 && File.read(exports[0]).include?('$<LINK_ONLY:') && File.read(exports[0]).include?(':-lexecinfo>>')
abort 'Static export retains sysroot library.' if File.read(exports[0]).include?(execinfo)
# A real library copy in an unsearched directory must fail. This is an input
# rejection fixture; it is never installed or used as a runtime provider.
FileUtils.mkdir_p(work + '/nonstandard')
foreign = work + '/nonstandard/libexecinfo.so'
FileUtils.cp(execinfo, foreign)
message = run.call('target-nonstandard', [cmake, '-S', patched, '-B', work + '/target-nonstandard'] + common +
                   ["-DCMAKE_TOOLCHAIN_FILE=#{toolchain}", "-DEXECINFO_LIBRARY=#{foreign}"], target_env, false)
abort 'Wrong rejection reason.' unless message.include?('Cross execinfo must be in a compiler implicit library directory')
File.write(work + '/result.json', JSON.pretty_generate({
  scope: 'Actual upstream configure and generated metadata; no package install or target execution.',
  native_pc_identical: native_before.size, target_pc_compared: target_before.size,
  target_changed_pc: changed, discovered_execinfo: execinfo, static_execinfo_preserved: true,
  nonstandard_rejected: true, inputs: ([archive, toolchain] + patches).to_h { |p| [p, Digest::SHA256.file(p).hexdigest] }
}) + "\n")
puts "PASS: #{native_before.size} unchanged native pc files; target execinfo link and static export preserved; nonstandard provider rejected."
