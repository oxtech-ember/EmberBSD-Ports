#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Prepare real tests without target build tools.
require 'digest'
require 'json'
require 'open3'
require 'rbconfig'
abort 'Usage: wayland-runtime.rb WRKSRC SYSROOT NATIVE_SCANNER TARGET_NM TARGET_READELF NEW_WORK' unless ARGV.size == 6
source, sysroot, scanner, nm, readelf = ARGV.first(5).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'New absolute output required.' unless ARGV.last.start_with?('/') && !File.exist?(work) && !File.symlink?(work)
Dir.mkdir(work)
commands = []
run = lambda do |name, env, argv|
  out, err, status = Open3.capture3(env, *argv)
  File.write(work + '/' + name + '.stdout', out)
  File.write(work + '/' + name + '.stderr', err)
  commands << {name: name, argv: argv, status: status.exitstatus}
  File.write(work + '/commands.json', JSON.pretty_generate(commands) + "\n")
  abort name + ' failed: ' + err unless status.success?
  out + err
end
abort 'Wrong native scanner release.' unless run.call('scanner-version', {}, [scanner, '--version']).strip == 'wayland-scanner 1.26.0'
header = File.binread(sysroot + '/usr/pkg/lib/libwayland-client.so', 64)
machine = header.byteslice(18, 2)&.unpack1('v')
target = {183 => 'aarch64', 62 => 'amd64'}[machine]
abort 'Unsupported installed Wayland ELF.' unless target
helper = File.expand_path('../cross/prepare-wayland-tests.rb', __dir__)
bundle = work + '/bundle'
run.call('prepare-runtime', {}, [RbConfig.ruby, helper, '--runtime', '--target', target, source, sysroot, bundle])
entries = File.readlines(bundle + '/tests.tsv', chomp: true).map { |l| l.split("\t") }
abort 'Runtime selection changed.' unless entries.size == 24 && entries.all? { |e| e.size == 4 && e[2..] == ['elf', '30'] }
abort 'Scanner entered runtime closure.' unless File.readlines(bundle + '/runtime.sha256').size == 4 && !File.read(bundle + '/runtime.sha256').include?('scanner')
abort 'Excluded source invocations lost.' unless File.readlines(bundle + '/host-tests.tsv').map { |l| l.split("\t").first }.sort == %w[scanner-test wayland-egl-symbols-check]
# Target executables use ordinary installed search paths. Do not edit their ELF
# bytes or inject a loader override to make the guest accept build-tree paths.
rpaths = {}
entries.each do |name, path, _kind, _timeout|
  dynamic = run.call(name + '-elf', {}, [readelf, '-d', bundle + '/' + path])
  paths = dynamic.scan(/\((?:RPATH|RUNPATH)\).*\[([^\]]*)\]/).flatten.flat_map { |p| p.split(':') }
  abort 'Unexpected target test runtime search path: ' + name unless paths.all? { |p| %w[/usr/pkg/lib /usr/pkg/gcc16/lib].include?(p) }
  rpaths[name] = paths
end
Dir.mkdir(work + '/scanner-output')
run.call('native-scanner-golden', {
  'TEST_DATA_DIR' => source + '/tests/data', 'TEST_OUTPUT_DIR' => work + '/scanner-output',
  'SED' => '/usr/bin/sed', 'WAYLAND_SCANNER' => scanner
}, ['/bin/sh', source + '/tests/scanner-test.sh'])
run.call('target-egl-symbols', {
  'WAYLAND_EGL_LIB' => sysroot + '/usr/pkg/lib/libwayland-egl.so', 'NM' => nm
}, ['/bin/sh', source + '/egl/wayland-egl-symbols-check'])
inputs = [helper, File.expand_path('../cross/run-wayland-tests.sh', __dir__),
          source + '/output/meson-info/intro-tests.json', source + '/tests/scanner-test.sh',
          source + '/egl/wayland-egl-symbols-check', scanner, nm, readelf]
File.write(work + '/result.json', JSON.pretty_generate({
  scope: 'Actual native scanner golden and target SDK symbol checks; 24 target runtime invocations prepared, not executed.',
  target: target, runtime_invocations: 24, separate_host_checks: 2,
  input_sha256: inputs.to_h { |p| [p, Digest::SHA256.file(p).hexdigest] },
  target_rpaths: rpaths, bundle_manifest: Digest::SHA256.file(bundle + '/artifacts.sha256').hexdigest
}) + "\n")
puts 'PASS: 24 real runtime test ELFs prepared; actual native scanner and target EGL symbols checked.'
