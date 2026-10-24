#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Host source-contract fixtures, not NetBSD execution or Qt/KConfig acceptance.
require 'tmpdir'
require 'fileutils'
require 'open3'
root = File.expand_path('../../..', __dir__)
kconfig = root + '/probes/plasma-mobile/toolkit/tests/kconfig-consumer/build.sh'
capture = root + '/profiles/common-graphics/cross/record-llvm-config.sh'
readelf = ENV.fetch('READELF') { abort 'Set READELF to the real host-executable cross readelf' }
abort 'READELF must be an absolute executable' unless readelf.start_with?('/') && File.executable?(readelf)
def script(path, text)
  File.write(path, "#!/bin/sh\nset -eu\n" + text)
  File.chmod(0755, path)
end
def check(command, env, success, reason)
  stdout, stderr, status = Open3.capture3(env, *command)
  abort "FAIL: #{reason}: #{stdout}#{stderr}" unless status.success? == success
end
Dir.mktmpdir('ember-acceptance-targets-', '/tmp') do |work|
  bin = work + '/bin'
  tools = work + '/tools'
  seed = work + '/seed'
  FileUtils.mkdir_p([bin, tools + '/bin', seed + '/usr/pkg/qt6/bin', seed + '/usr/lib'])
  # Valid minimal ELF64 executable headers; no target payload is executed.
  elf = lambda do |machine|
    "\x7fELF\x02\x01\x01".b.ljust(16, "\0") + [2, machine, 1].pack('vvV') + "\0" * 24 + [0, 64, 0, 0, 0, 0, 0].pack('Vvvvvvv')
  end
  {'aarch64' => 183, 'amd64' => 62}.each { |name, machine| File.binwrite(work + '/' + name + '.elf', elf.call(machine)) }
  script(bin + '/cmake', 'cp "$FIXTURE_ELF" "$2/kconfig-consumer"' + "\n")
  script(seed + '/usr/pkg/qt6/bin/qt-cmake', 'printf "%s\n" "$@" > "$FIXTURE_TRACE"' + "\n")
  script(bin + '/uname', 'case "$1" in -s) echo "${FIXTURE_OS:-NetBSD}";; -p) echo "$FIXTURE_CPU";; -a) echo "NetBSD source-contract fixture";; *) exit 96;; esac' + "\n")
  script(bin + '/sha256', 'shasum -a 256 "$2" | cut -d " " -f 1' + "\n")
  # A controlled query script stands in for target llvm-config. The diagnostic
  # boundary reads its companion real ELF header with the selected readelf.
  script(bin + '/readelf', 'exec "$FIXTURE_READELF" "$1" "$2.elf"' + "\n")
  script(work + '/llvm-config', 'case "$1" in --host-target) echo "$FIXTURE_LLVM_TRIPLE";; --version) echo 23.1.4;; *) echo fixture;; esac' + "\n")
  env = {'PATH' => bin + ':' + ENV.fetch('PATH'), 'CMAKE' => bin + '/cmake', 'NINJA' => '/usr/bin/true', 'PKG_CONFIG' => '/usr/bin/true', 'FIXTURE_READELF' => readelf, 'READELF' => bin + '/readelf', 'FIXTURE_TRACE' => work + '/cmake.args'}
  %w[aarch64 amd64].each do |target|
    cpu, triplet = target == 'amd64' ? ['x86_64', 'x86_64--netbsd'] : ['aarch64', 'aarch64--netbsd']
    selected = env.merge('FIXTURE_ELF' => work + '/' + target + '.elf', 'FIXTURE_CPU' => cpu, 'FIXTURE_LLVM_TRIPLE' => cpu + '-unknown-netbsd')
    script(tools + '/bin/' + triplet + '-g++', "case \"$1\" in -dumpmachine) echo #{triplet};; -dumpfullversion) echo 16.2.0;; *) exit 96;; esac\n")
    if target == 'amd64' && ENV['CROSS_TEST_TOOLS']
      File.unlink(tools + '/bin/' + triplet + '-g++')
      File.symlink(ENV.fetch('CROSS_TEST_TOOLS') + '/bin/' + triplet + '-g++', tools + '/bin/' + triplet + '-g++')
    end
    File.symlink(readelf, tools + '/bin/' + triplet + '-readelf')
    FileUtils.cp(selected.fetch('FIXTURE_ELF'), seed + '/usr/lib/libc.so.12')
    args = [tools, seed, work, work, work + '/consumer-' + target]
    check(['sh', kconfig, '--target', target, *args], selected, true, target + ' consumer selection')
    abort 'FAIL: consumer target receipt changed' unless File.read(args.last + '/target.txt').include?("triplet=#{triplet}\n")
    configured = File.readlines(work + '/cmake.args', chomp: true)
    abort 'FAIL: mixed consumer compiler/processor/CRT selection' unless configured.include?('-DCMAKE_SYSTEM_PROCESSOR=' + cpu) && configured.include?('-DCMAKE_CXX_COMPILER=' + tools + '/bin/' + triplet + '-g++') && configured.include?("-DCMAKE_CXX_FLAGS=-B#{seed}/usr/pkg/gcc16/lib/gcc/#{triplet}/16.2.0/")
    check(['sh', kconfig, '--target', target, *args], selected, false, 'existing consumer output')
    if target == 'aarch64'
      check(['sh', kconfig, *args[0...-1], work + '/default-consumer'], selected, true, 'default AArch64 consumer')
    end
    compiler = tools + '/bin/' + triplet + '-g++'
    File.rename(compiler, compiler + '.good')
    ['foreign--netbsd:16.2.0', triplet + ':15.2.0'].each_with_index do |identity, index|
      wrong_triplet, wrong_version = identity.split(':')
      script(compiler, "case \"$1\" in -dumpmachine) echo #{wrong_triplet};; -dumpfullversion) echo #{wrong_version};; *) exit 96;; esac\n")
      refused = work + '/wrong-compiler-' + target + index.to_s
      check(['sh', kconfig, '--target', target, *args[0...-1], refused], selected, false, 'compiler target/version mismatch')
      abort 'FAIL: rejected compiler created output' if File.exist?(refused)
    end
    File.unlink(compiler)
    File.rename(compiler + '.good', compiler)
    foreign = target == 'amd64' ? 'aarch64' : 'amd64'
    check(['sh', kconfig, '--target', target, *args[0...-1], work + '/foreign-consumer-' + target], selected.merge('FIXTURE_ELF' => work + '/' + foreign + '.elf'), false, 'foreign consumer ELF')
    FileUtils.cp(work + '/' + foreign + '.elf', seed + '/usr/lib/libc.so.12')
    refused = work + '/foreign-seed-' + target
    check(['sh', kconfig, '--target', target, *args[0...-1], refused], selected, false, 'foreign seed ELF')
    abort 'FAIL: foreign seed created output' if File.exist?(refused)
    FileUtils.cp(selected.fetch('FIXTURE_ELF'), seed + '/usr/lib/libc.so.12')
    FileUtils.cp(selected.fetch('FIXTURE_ELF'), work + '/llvm-config.elf')
    output = work + '/reference-' + target
    check(['sh', capture, '--target', target, work + '/llvm-config', output], selected, true, target + ' target-capture contract')
    abort 'FAIL: target capture not complete' unless File.read(output + '/status').strip == 'complete'
    abort 'FAIL: capture target receipt changed' unless File.read(output + '/target.txt').include?("triplet=#{triplet}\n")
    if target == 'aarch64'
      check(['sh', capture, work + '/llvm-config', work + '/default-reference'], selected, true, 'default AArch64 capture')
    end
    check(['sh', capture, '--target', target, work + '/llvm-config', work + '/gnu-triple-' + target], selected.merge('FIXTURE_LLVM_TRIPLE' => triplet + '11.0'), true, 'selected GNU NetBSD11 triple')
    check(['sh', capture, '--target', target, work + '/llvm-config', output], selected, false, 'existing reference output')
    {'foreign uname' => {'FIXTURE_CPU' => foreign == 'amd64' ? 'x86_64' : 'aarch64'}, 'foreign OS' => {'FIXTURE_OS' => 'Darwin'}, 'foreign LLVM triple' => {'FIXTURE_LLVM_TRIPLE' => 'riscv64-unknown-netbsd'}, 'foreign ABI' => {'FIXTURE_LLVM_TRIPLE' => cpu + '-unknown-netbsd10'}, 'malformed ABI' => {'FIXTURE_LLVM_TRIPLE' => cpu + '-unknown-netbsd11.bad'}}.each do |reason, changed|
      refused = work + '/refused-' + target + '-' + reason.tr(' ', '-')
      check(['sh', capture, '--target', target, work + '/llvm-config', refused], selected.merge(changed), false, reason)
      abort 'FAIL: rejected target identity created output' if File.exist?(refused)
    end
    FileUtils.cp(work + '/' + foreign + '.elf', work + '/llvm-config.elf')
    refused = work + '/foreign-llvm-' + target
    check(['sh', capture, '--target', target, work + '/llvm-config', refused], selected, false, 'foreign LLVM ELF')
    abort 'FAIL: foreign LLVM ELF created output' if File.exist?(refused)
    puts "PASS: #{target} consumer/capture source contracts and foreign input guards"
  end
  [kconfig, capture].each do |entrypoint|
    positional = entrypoint == kconfig ? [tools, seed, work, work, work + '/invalid-output'] : [work + '/llvm-config', work + '/invalid-reference']
    [%w[--target riscv64], %w[--target], %w[--target amd64 --target aarch64], %w[--unknown], %w[--kernel]].each do |flags|
      check(['sh', entrypoint, *flags, *positional], env.merge('kernel_allowed' => 'yes'), false, 'invalid target arguments')
    end
  end
end
puts 'PASS: source-contract fixtures with real ELF inspection; no Qt build, NetBSD execution or VM acceptance'
