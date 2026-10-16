#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Real amd64 inputs and labelled foreign fixtures.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'rbconfig'
abort 'usage: wayland-targets.rb CONFIGURED_WAYLAND SYSROOT NEW_WORK' unless ARGV.length == 3
source, sdk = ARGV.first(2).map { |p| File.realpath(p) }
work = File.expand_path(ARGV[2])
abort 'new absolute work required' unless ARGV[2].start_with?('/') && !File.exist?(work)
Dir.mkdir(work)
helper = File.expand_path('../cross/prepare-wayland-tests.rb', __dir__)
run = lambda do |label, arguments, accepted|
  out, status = Open3.capture2e(RbConfig.ruby, helper, *arguments)
  File.write(work + '/' + label + '.log', out)
  abort label + ' unexpected preparation status: ' + out unless status.success? == accepted
  out
end
actual = work + '/actual-amd64'
run.call('actual-amd64', ['--target', 'amd64', source, sdk, actual], true)
abort 'amd64 target marker missing' unless File.read(actual + '/target.txt') == "amd64\n"
abort 'upstream invocations changed' unless File.readlines(actual + '/tests.tsv').length == 26
hashes = File.read(actual + '/artifacts.sha256')
abort 'target marker not bound by artifact hashes' unless hashes.include?(Digest::SHA256.file(actual + '/target.txt').hexdigest + '  target.txt')
run.call('default-refuses-amd64', [source, sdk, work + '/default-refuses'], false)
%w[unknown duplicate missing-value].each do |label|
  args = case label
         when 'unknown' then ['--target', 'riscv64']
         when 'duplicate' then ['--target', 'amd64', '--target', 'amd64']
         else ['--target']
         end
  run.call(label, [*args, source, sdk, work + '/reject-' + label], false)
end
# These ELF headers are source-contract fixtures. They are never executed.
fixture = work + '/arm-source'
fixture_sdk = work + '/arm-sdk'
FileUtils.mkdir_p([fixture + '/output/meson-info', fixture + '/tests/data'])
FileUtils.cp(source + '/COPYING', fixture)
FileUtils.cp(source + '/output/meson-info/intro-projectinfo.json', fixture + '/output/meson-info')
header = "\x7fELF".b + [2, 1, 1, 0].pack('C*') + "\0".b * 56
header[18, 2] = [183].pack('v')
tests = JSON.parse(File.read(source + '/output/meson-info/intro-tests.json'))
tests.each do |test|
  path = test.fetch('cmd').fetch(0).sub(source, fixture)
  FileUtils.mkdir_p(File.dirname(path))
  script = path == fixture + '/tests/scanner-test.sh' || path == fixture + '/egl/wayland-egl-symbols-check'
  File.binwrite(path, script ? "#!/bin/sh\nexit 99\n" : header)
  test['cmd'] = [path]
end
File.write(fixture + '/output/meson-info/intro-tests.json', JSON.generate(tests))
FileUtils.mkdir_p(fixture + '/output/tests')
File.binwrite(fixture + '/output/tests/exec-fd-leak-checker', header)
%w[bin/wayland-scanner lib/libwayland-client.so lib/libwayland-server.so lib/libwayland-cursor.so lib/libwayland-egl.so].each do |path|
  FileUtils.mkdir_p(File.dirname(fixture_sdk + '/usr/pkg/' + path))
  File.binwrite(fixture_sdk + '/usr/pkg/' + path, header)
end
run.call('arm-default-fixture', [fixture, fixture_sdk, work + '/arm-default'], true)
abort 'default ARM target marker changed' unless File.read(work + '/arm-default/target.txt') == "aarch64\n"
run.call('amd64-refuses-arm-fixture', ['--target', 'amd64', fixture, fixture_sdk, work + '/foreign-arm'], false)
exe = fixture + '/output/tests/exec-fd-leak-checker'
File.binwrite(exe, header.byteslice(0, 20))
run.call('truncated-helper', [fixture, fixture_sdk, work + '/truncated'], false)
File.binwrite(exe, header)
foreign = header.dup
foreign[18, 2] = [62].pack('v')
File.binwrite(exe, foreign)
run.call('foreign-helper', [fixture, fixture_sdk, work + '/foreign-helper'], false)
File.binwrite(exe, header)
provider = fixture_sdk + '/usr/pkg/lib/libwayland-client.so'
{'foreign-runtime' => foreign, 'wrong-class' => header.dup, 'wrong-endian' => header.dup}.each do |label, bytes|
  bytes.setbyte(4, 1) if label == 'wrong-class'
  bytes.setbyte(5, 2) if label == 'wrong-endian'
  File.binwrite(provider, bytes)
  run.call(label, [fixture, fixture_sdk, work + '/reject-' + label], false)
end
File.binwrite(provider, header)
tests.first['timeout'] = 31
File.write(fixture + '/output/meson-info/intro-tests.json', JSON.generate(tests))
run.call('changed-timeout', [fixture, fixture_sdk, work + '/timeout'], false)
# Guard-only runner checks on the host. The fake uname is explicit fixture
# metadata and cannot establish target execution or installed-package success.
FileUtils.mkdir_p(work + '/fixture-bin')
uname = work + '/fixture-bin/uname'
File.write(uname, "#!/bin/sh\ncase \"$1\" in -s) echo NetBSD;; -p) echo aarch64;; *) exit 2;; esac\n")
File.chmod(0755, uname)
runner = actual + '/run-wayland-tests.sh'
[['foreign-uname', ['--target', 'amd64']], ['default-target-mismatch', []],
 ['duplicate-runner', ['--target', 'amd64', '--target', 'amd64']],
 ['unknown-runner', ['--target', 'riscv64']]].each do |label, options|
  result = work + '/result-' + label
  out, status = Open3.capture2e({'PATH' => work + '/fixture-bin:/usr/bin:/bin'}, '/bin/sh', runner, *options, result)
  File.write(work + '/' + label + '.log', out)
  abort label + ' did not reject before output creation' unless status.exitstatus == 2 && !File.exist?(result)
end
puts 'PASS: actual amd64 suite input, explicit target marker, all 26 invocations and bound hashes'
puts 'PASS: AArch64 default source fixture; foreign ELF, truncated helper, changed timeout and invalid CLI rejected'
puts 'PASS: runner refuses wrong target/uname and invalid CLI before output creation (host guard fixtures only)'
puts 'SCOPE: actual test payload preparation; no target test execution or package mutation'
