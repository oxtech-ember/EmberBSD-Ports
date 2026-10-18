#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Build real before/after GCC conversion objects.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'
abort 'Usage: build.rb PKGSRC GCC_ARCHIVE TARGET_CXX SYSROOT NEW_OUTPUT' unless ARGV.length == 5
pkgsrc, archive, target_cxx, sysroot, output = ARGV.map { |path| File.expand_path(path) }
abort "Input paths must not contain shell metacharacters" unless
  [pkgsrc, archive, target_cxx, sysroot, output].all? { |path| path.match?(%r{\A[-+A-Za-z0-9_./]+\z}) }
digest = ENV.fetch("DIGEST", "digest")
abort "DIGEST must name one executable" unless digest.match?(%r{\A[-+A-Za-z0-9_./]+\z})
root = File.expand_path('../../../..', __dir__)
abort 'Output must be new' if File.exist?(output) || File.symlink?(output)
native = Shellwords.split(ENV.fetch('NATIVE_CXX'))
memcheck = Shellwords.split(ENV.fetch('MEMCHECK', 'valgrind'))
abort 'NATIVE_CXX must name a genuine native GCC16 command' if native.empty?
expected = File.readlines(root + '/profiles/development-toolchain/sources.tsv', chomp: true)
               .map { |line| line.split("\t") }.find { |row| row[0, 2] == ['gcc', '16.2.0'] }
abort 'GCC archive checksum mismatch' unless expected && Digest::SHA256.file(archive).hexdigest == expected[3]
Dir.mkdir(output)
commands = []
run = lambda do |name, arguments, input: nil, environment: {}|
  stdout, stderr, status = Open3.capture3(environment, *arguments, stdin_data: input.to_s)
  File.write(output + '/' + name + '.log', stdout + stderr)
  commands << {name: name, command: arguments, environment: environment, exit: status.exitstatus}
  File.write(output + '/commands.json', JSON.pretty_generate(commands) + "\n")
  raise "Failed #{name}; see its retained log" unless status.success?
  stdout
end
pin = run.call('pkgsrc-gitlink', ['git', '-C', root, 'ls-files', '--stage', 'upstream/pkgsrc']).split[1]
raise 'Pinned pkgsrc checkout differs' unless run.call('pkgsrc-head', ['git', '-C', pkgsrc, 'rev-parse', 'HEAD']).strip == pin
triplet = run.call('target-triple', [target_cxx, '-dumpmachine']).strip
raise 'Unsupported target' unless %w[aarch64--netbsd x86_64--netbsd].include?(triplet)
raise 'Target must be GCC16.2.0' unless run.call('target-version', [target_cxx, '-dumpfullversion']).strip == '16.2.0'
raise 'Native must be GCC16.2.0' unless run.call('native-version', native + ['-dumpfullversion']).strip == '16.2.0'
recipe = output + '/recipe'
Dir.mkdir(recipe)
run.call('recipe-export', ['git', '-C', pkgsrc, 'archive', '-o', output + '/recipe.tar', pin,
                         'lang/gcc16', 'lang/gcc16-libs', 'lang/gcc16-libjit'])
run.call('recipe-extract', ['tar', '-xf', output + '/recipe.tar', '-C', recipe])
patches = %w[pkgsrc-gcc16.2.patch strict-tests.patch gcc-tsvc-netbsd.patch gcc-modules-fallocate.patch gcc-netbsd-locale.patch]
patches.each do |name|
  run.call('recipe-' + name, ['patch', '-f', '-E', '-p1', '-F', '0', '-d', recipe],
           input: File.read(root + '/profiles/development-toolchain/patches/' + name))
end
patch = recipe + '/lang/gcc16/patches/patch-libstdc++-v3_config_locale_generic_c__locale'
run.call('pkgsrc-checksum', ['awk', '-f', pkgsrc + '/mk/checksum/checksum.awk', '--', '-p',
                           recipe + '/lang/gcc16/distinfo', patch],
         environment: {'DIGEST' => digest})
source = 'libstdc++-v3/config/locale/generic/'
%w[original patched].each do |mode|
  Dir.mkdir(output + '/' + mode)
end
run.call('source-extract', ['tar', '-xJf', archive, '-C', output + '/original',
                          'gcc-16.2.0/' + source + 'c_locale.h', 'gcc-16.2.0/' + source + 'c_locale.cc'])
FileUtils.cp_r(output + '/original/gcc-16.2.0', output + '/patched/')
run.call('source-patch', ['patch', '-f', '-p0', '-F', '0', '-d', output + '/patched/gcc-16.2.0'],
         input: File.read(patch))
flags = ['--sysroot=' + sysroot, '-B' + sysroot + '/usr/lib/',
         '-B' + sysroot + '/usr/pkg/gcc16/lib/', '-O2', '-g', '-pthread']
target_environment = %w[LIBRARY_PATH CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH].to_h { |name| [name, nil] }
link = ['-L' + sysroot + '/usr/pkg/gcc16/lib', '-Wl,-rpath,/usr/pkg/gcc16/lib',
        '-Wl,-rpath-link,' + sysroot + '/usr/pkg/gcc16/lib']
%w[original patched].each do |mode|
  includes = output + '/' + mode + '-include'
  FileUtils.mkdir_p(includes + '/bits')
  directory = output + '/' + mode + '/gcc-16.2.0/' + source
  FileUtils.cp(directory + 'c_locale.h', includes + '/bits/c++locale.h')
  run.call(mode + '-object', [target_cxx, *flags, '-std=gnu++98', '-I' + includes,
                            '-c', directory + 'c_locale.cc', '-o', output + '/' + mode + '.o'],
           environment: target_environment)
  configurations = %w[c++17 c++20 c++23].map { |standard| [standard, ['-std=' + standard]] }
  configurations += %w[200112L 200809L].map { |level| ['posix-' + level, ['-std=c++20', '-D_POSIX_C_SOURCE=' + level]] }
  configurations.each do |name, extra|
    run.call(mode + '-' + name, [target_cxx, *flags, *extra, '-I' + includes,
                                __dir__ + '/contract.cpp', output + '/' + mode + '.o',
                                *link, '-o', output + '/' + mode + '-' + name],
             environment: target_environment)
  end
  %w[h cc].each do |suffix|
    run.call(mode + '-native-preprocessed-' + suffix,
             native + ['-std=gnu++98', '-x', 'c++', '-E', '-P', directory + 'c_locale.' + suffix,
                       '-o', output + '/' + mode + '-' + suffix + '.ii'])
  end
end
%w[h cc].each do |suffix|
  raise 'Non-NetBSD source changed' unless File.binread(output + '/original-' + suffix + '.ii') ==
                                          File.binread(output + '/patched-' + suffix + '.ii')
end
run.call('native-build', native + ['-std=c++20', '-O2', '-g', '-pthread', __dir__ + '/contract.cpp', '-o', output + '/native'])
run.call('native-run', [output + '/native', ENV.fetch('COMMA_LOCALE', 'fr_FR.UTF-8')])
run.call('native-memcheck', memcheck + ['--leak-check=full', '--show-leak-kinds=all', '--errors-for-leak-kinds=all',
                                     '--error-exitcode=99', output + '/native', ENV.fetch('COMMA_LOCALE', 'fr_FR.UTF-8')])
inputs = [archive, target_cxx, __FILE__, __dir__ + '/contract.cpp', patch] +
         patches.map { |name| root + '/profiles/development-toolchain/patches/' + name }
File.write(output + '/result.json', JSON.pretty_generate({
  scope: 'Actual package/source patch checks and target builds; target execution is not performed. Native contract uses its genuine native runtime.',
  target: triplet, inputs: inputs.to_h { |file| [file, Digest::SHA256.file(file).hexdigest] },
  binaries: %w[original-c++20 patched-c++20 native].to_h { |name| [name, Digest::SHA256.file(output + '/' + name).hexdigest] },
  commands: commands
}) + "\n")
puts 'PASS: real source/package checks, before/after target builds, native semantics and Memcheck. Target execution pending.'
