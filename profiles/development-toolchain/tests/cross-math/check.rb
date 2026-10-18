#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Run real target probes; never execute ELF.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'

abort 'Usage: check.rb TARGET EXPORTED_PKGSRC GCC_ARCHIVE GCC16_PREFIX SYSROOT NEW_WORK' unless ARGV.length == 6
target, tree, archive, prefix, sysroot, work = ARGV
triplet = {'aarch64' => 'aarch64--netbsd', 'amd64' => 'x86_64--netbsd'}.fetch(target) { abort 'Unknown target' }
[tree, archive, prefix, sysroot, work].each do |path|
  abort 'Absolute simple paths required' unless path.match?(%r{\A/[A-Za-z0-9_./-]+\z}) && !path.split('/').include?('..')
end
abort 'NEW_WORK already exists' if File.exist?(work) || File.symlink?(work)
here = File.realpath(__dir__)
profile = File.expand_path('../..', here)
gcc = prefix + '/bin/' + triplet + '-gcc'
cxx = prefix + '/bin/' + triplet + '-g++'
make = ENV.fetch('GNU_MAKE', '/usr/bin/make')
env = ENV.keys.grep(/\A(?:ac_cv_|glibcxx_cv_|gcc_cv_)/).to_h { |key| [key, nil] }
%w[CC CXX CFLAGS CXXFLAGS CPPFLAGS LDFLAGS LIBS CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH LIBRARY_PATH GCC_EXEC_PREFIX COMPILER_PATH CONFIG_SITE].each { |key| env[key] = nil }
env['LC_ALL'] = 'C'
env['PATH'] = prefix + '/bin:' + ENV.fetch('PATH')
capture = lambda do |*args|
  out, err, status = Open3.capture3(env, *args)
  abort "Input command failed: #{args.first}: #{err}" unless status.success?
  out
end
abort 'GCC16 required' unless capture.call(gcc, '-dumpfullversion').strip == '16.2.0' && capture.call(gcc, '-dumpmachine').strip == triplet
abort 'GNU make required' unless capture.call(make, '--version').start_with?('GNU Make ')
names = File.read(here + '/imports.cc').scan(/^auto address_(\w+) =/).flatten
abort 'Expected 43 independent names' unless names.length == 43 && names.uniq.length == 43
FileUtils.mkdir_p(work)
results = []
run = lambda do |label, command, expected = 0, directory = work, extra = {}|
  out, err, status = Open3.capture3(env.merge(extra), *command, chdir: directory)
  File.write(work + '/' + label + '.stdout', out)
  File.write(work + '/' + label + '.stderr', err)
  results << {name: label, argv: command, directory: directory, environment: extra,
              exit: status.exitstatus, signal: status.termsig,
              stdout_sha256: Digest::SHA256.hexdigest(out), stderr_sha256: Digest::SHA256.hexdigest(err)}
  File.write(work + '/results.json', JSON.pretty_generate(results) + "\n")
  abort "Unexpected result: #{label}: #{status.exitstatus.inspect}" unless status.exitstatus == expected && status.termsig.nil?
  [out, err]
end
run.call('source', ['sh', profile + '/bootstrap/prepare-source.sh', tree, archive, work + '/src'])
source = work + '/src'
baseline = work + '/baseline'
FileUtils.mkdir_p(baseline + '/libstdc++-v3')
FileUtils.cp(source + '/libstdc++-v3/configure', baseline + '/libstdc++-v3/configure')
patch = tree + '/lang/gcc16/patches/patch-libstdc++-v3_configure_math'
run.call('baseline-configure', ['patch', '-f', '-R', '-F', '0', '-p0', '-i', patch], 0, baseline)
flags = ["--sysroot=#{sysroot}", "-B#{sysroot}/usr/pkg/gcc16/lib/gcc/#{triplet}/16.2.0/", "-B#{sysroot}/usr/pkg/gcc16/lib/"]
tools = %w[ar as ld nm objcopy objdump ranlib readelf strip].to_h { |name| [name.upcase, prefix + '/bin/' + triplet + '-' + name] }
build_triplet = capture.call('sh', source + '/config.guess').strip
gthreads = work + '/build/' + triplet + '/libgcc'
FileUtils.mkdir_p(gthreads)
rule = File.read(source + '/libgcc/Makefile.in')[/^gthr-default\.h: \$\(srcdir\)\/\$\(thread_header\)\n\t-\$\(LN_S\) \$< \$@\n/]
abort 'Upstream gthread rule changed' unless rule
File.write(work + '/gthreads.mk', rule)
run.call('gthreads', [make, '-f', work + '/gthreads.mk', 'srcdir=' + source + '/libgcc', 'thread_header=gthr-posix.h', 'LN_S=ln -s', 'gthr-default.h'], 0, gthreads)
configure_args = ["--srcdir=#{source}/libstdc++-v3", "--build=#{build_triplet}", "--host=#{triplet}", "--target=#{triplet}",
                  "--with-cross-host=#{build_triplet}", "--with-target-subdir=#{triplet}", '--prefix=/usr/pkg/gcc16',
                  '--libdir=/usr/pkg/gcc16/lib', '--with-toolexeclibdir=/usr/pkg/gcc16/lib', '--with-gxx-include-dir=/usr/pkg/gcc16/include/c++',
                  "--with-sysroot=#{sysroot}", '--with-gnu-as', '--with-gnu-ld', "--with-as=#{tools['AS']}", "--with-ld=#{tools['LD']}",
                  '--disable-multilib', '--enable-shared', '--enable-threads=posix', '--enable-long-long', '--disable-libssp',
                  '--disable-libstdcxx-pch', '--disable-nls', '--disable-year2038', '--cache-file=/dev/null']
configure_env = tools.merge('CC' => [gcc, *flags].join(' '), 'CXX' => [gcc, *flags, '-shared-libgcc', '-nostdinc++'].join(' '),
                            'CFLAGS' => '-O2', 'CXXFLAGS' => '-O2', 'CPPFLAGS' => '',
                            'LDFLAGS' => "-L#{sysroot}/usr/pkg/gcc16/lib -Wl,-rpath,/usr/pkg/gcc16/lib -Wl,-z,relro")
configure = lambda do |name, script, overrides = {}|
  directory = work + '/build/' + triplet + '/libstdc++-' + name
  FileUtils.mkdir_p(directory)
  run.call('configure-' + name, [script, *configure_args], 0, directory, configure_env.merge(overrides))
  directory
end
base = configure.call('base', baseline + '/libstdc++-v3/configure')
current = configure.call('current', source + '/libstdc++-v3/configure')
[base, current].each { |dir| run.call('headers-' + File.basename(dir), [make, '-C', 'include', 'all'], 0, dir) }
compile_args = lambda do |dir|
  [cxx, *flags, '-nostdinc++', '-I' + dir + '/include/' + triplet, '-I' + dir + '/include', '-I' + source + '/libstdc++-v3/libsupc++', '-std=gnu++23']
end
fixture = here + '/imports.cc'
run.call('global-declarations', [*compile_args.call(base), '-DGLOBAL_MATH_NAMES', '-c', fixture, '-o', work + '/globals.o'])
_, error = run.call('std-imports-before', [*compile_args.call(base), '-fsyntax-only', fixture], 1)
abort 'Baseline failed for an unrelated reason' unless error.include?('not a member')
run.call('std-imports', [*compile_args.call(current), '-Wall', '-Wextra', '-Werror', '-c', fixture, '-o', work + '/imports.o'])
symbols = capture.call(tools['NM'], '-u', work + '/imports.o').lines.map { |line| line.split.last }
abort 'Missing literal math relocations' unless (names - symbols).empty?
link = ['-L' + sysroot + '/usr/pkg/gcc16/lib', '-Wl,-rpath,/usr/pkg/gcc16/lib', '-Wl,-rpath-link,' + sysroot + '/usr/lib', '-lm']
run.call('std-link', [cxx, *flags, work + '/imports.o', *link, '-o', work + '/math-consumer'])
module_inputs = %w[std.cc std.compat.cc].to_h do |name|
  [name, File.binread(source + '/libstdc++-v3/src/c++23/' + name + '.in') + File.binread(source + '/libstdc++-v3/src/c++23/std-clib.cc.in')]
end
modules = work + '/modules'; FileUtils.mkdir_p(modules)
module_inputs.each { |name, bytes| File.binwrite(modules + '/' + name, bytes) }
module_flags = ['-fmodules', '-isystem', source + '/libstdc++-v3/include/backward']
run.call('full-std-before', [*compile_args.call(base), *module_flags, '-c', modules + '/std.cc', '-o', modules + '/before.o'], 1, modules)
module_inputs.each_key do |name|
  run.call(name, [*compile_args.call(current), *module_flags, '-c', modules + '/' + name, '-o', modules + '/' + name + '.o'], 0, modules)
  bmi = modules + '/gcm.cache/' + name.delete_suffix('.cc') + '.gcm'
  abort 'Missing real module BMI' unless File.size(bmi) > 1024 && File.size(modules + '/' + name + '.o').positive?
end
{'std' => '-DMATH_STD_MODULE', 'compat' => '-DMATH_COMPAT_MODULE'}.each do |name, selection|
  mode = name == 'compat' ? ['-DGLOBAL_MATH_NAMES'] : []
  run.call('module-import-' + name, [*compile_args.call(current), *module_flags, selection, *mode, fixture,
                                   modules + '/std.cc.o', modules + '/std.compat.cc.o', *link, '-o', modules + '/' + name + '-consumer'], 0, modules)
end
abort 'Module sources were replaced' unless module_inputs.all? { |name, bytes| File.binread(modules + '/' + name) == bytes }
# Fault inputs are private copies. They never modify the selected SDK.
fault_header = work + '/missing-declaration'; FileUtils.mkdir_p(fault_header)
math = File.read(sysroot + '/usr/include/math.h')
abort 'No target acosf declaration' unless math.match?(/\bacosf\b/)
File.write(fault_header + '/math.h', math.gsub(/\bacosf\b/, 'absent_declaration_acosf'))
no_decl = configure.call('missing-declaration', source + '/libstdc++-v3/configure', 'CPPFLAGS' => '-I' + fault_header)
abort 'Missing declaration became available' if File.read(no_decl + '/config.h').match?(/^#define HAVE_ACOSF 1$/)
fault_lib = work + '/missing-symbol'; FileUtils.mkdir_p(fault_lib)
libm = sysroot + '/usr/lib/libm.a'
members = capture.call(tools['NM'], '-A', '--defined-only', libm).lines.filter_map { |line| line[/\A.*:([^:\s]+):.* [TW] acosf\s*$/, 1] }.uniq
abort 'Cannot identify the real acosf archive member' if members.empty?
FileUtils.cp(libm, fault_lib + '/libm.a')
File.chmod(0644, fault_lib + '/libm.a')
run.call('remove-symbol', [tools['AR'], 'd', fault_lib + '/libm.a', *members])
no_symbol = configure.call('missing-symbol', source + '/libstdc++-v3/configure', 'LDFLAGS' => '-L' + fault_lib + ' ' + configure_env.fetch('LDFLAGS'))
abort 'Missing symbol became available' if File.read(no_symbol + '/config.h').match?(/^#define HAVE_ACOSF 1$/)
fault_cap = work + '/missing-capability/' + triplet + '/bits'; FileUtils.mkdir_p(fault_cap)
config = File.read(current + '/include/' + triplet + '/bits/c++config.h')
abort 'Missing positive capability' unless config.sub!(/^#define _GLIBCXX_HAVE_ACOSF 1$/, '/* deliberately absent for the negative test */')
File.write(fault_cap + '/c++config.h', config)
run.call('removed-capability', [*compile_args.call(current).insert(4, '-I' + work + '/missing-capability/' + triplet), '-fsyntax-only', fixture], 1)
File.write(work + '/acceptance.json', JSON.pretty_generate(target: target, names: names, full_modules: module_inputs.transform_values { |bytes| Digest::SHA256.hexdigest(bytes) },
                                                        target_execution: false, package_lifecycle: false, results: results.length) + "\n")
puts "PASS: 43 target math declarations/imports/links, complete std/std.compat and three capability negatives; target execution remains separate."
