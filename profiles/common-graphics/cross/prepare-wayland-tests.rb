#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; preserve the actual upstream Meson test selection for a target run.
require 'json'
require 'fileutils'
require 'digest'

usage = "Usage: #{$PROGRAM_NAME} [--target aarch64|amd64] WRKSRC TARGET_SYSROOT NEW_BUNDLE"
target = 'aarch64'
target_seen = false
while ARGV.first&.start_with?('--')
  option = ARGV.shift
  abort usage unless option == '--target' && !target_seen && ARGV.first
  target = ARGV.shift
  target_seen = true
end
machine = { 'aarch64' => 183, 'amd64' => 62 }[target]
abort "Unsupported target: #{target}" unless machine
abort usage unless ARGV.size == 3
verify_elf = lambda do |path|
  header = File.binread(path, 64)
  abort "Expected #{target} ELF64: #{path}" unless header.bytesize == 64 &&
    header.start_with?("\x7fELF".b) && header.getbyte(4) == 2 &&
    header.getbyte(5) == 1 && header.byteslice(18, 2).unpack1('v') == machine
end
source, sysroot = ARGV.take(2).map { |p| File.realpath(p) }
bundle = File.expand_path(ARGV[2])
abort 'Bundle already exists' if File.exist?(bundle) || File.symlink?(bundle)
build = File.join(source, 'output')
info = JSON.parse(File.read(File.join(build, 'meson-info/intro-projectinfo.json')))
abort 'Expected Wayland 1.26.0' unless info.values_at('descriptive_name', 'version') == ['wayland', '1.26.0']
tests = JSON.parse(File.read(File.join(build, 'meson-info/intro-tests.json')))
abort 'Expected all 26 enabled upstream tests' unless tests.size == 26
names = []
entries = tests.map do |test|
  name = test.fetch('name').tr(' ', '-')
  abort "Unsupported test metadata: #{name}" unless name.match?(/\A[a-z0-9-]+\z/) &&
    !names.include?(name) && test.fetch('cmd').size == 1 && test['timeout'] == 30 &&
    test['protocol'] == 'exitcode' && test['workdir'].nil?
  names << name
  input = File.realpath(test.fetch('cmd').first)
  abort "Test escaped source: #{input}" unless input.start_with?(source + '/')
  kind = if input == File.join(source, 'tests/scanner-test.sh')
           'scanner'
         elsif input == File.join(source, 'egl/wayland-egl-symbols-check')
           'symbols'
         else
           verify_elf.call(input)
           'elf'
         end
  relative = "tests/#{File.basename(input)}"
  [input, name, relative, kind, 30]
end
# Validate helpers and installed providers for the same target before output.
verify_elf.call(File.join(build, 'tests/exec-fd-leak-checker'))
runtime_files = %w[bin/wayland-scanner lib/libwayland-client.so lib/libwayland-server.so
                  lib/libwayland-cursor.so lib/libwayland-egl.so]
runtime_files.each { |file| verify_elf.call(File.join(sysroot, 'usr/pkg', file)) }
FileUtils.mkdir_p(File.join(bundle, 'tests'))
FileUtils.cp(File.join(source, 'COPYING'), bundle)
FileUtils.cp(File.join(build, 'meson-info/intro-tests.json'), bundle)
FileUtils.cp(File.join(build, 'meson-info/intro-projectinfo.json'), bundle)
FileUtils.cp_r(File.join(source, 'tests/data'), File.join(bundle, 'tests'))
FileUtils.cp(File.join(__dir__, 'run-wayland-tests.sh'), bundle)

File.write(File.join(bundle, 'target.txt'), target + "\n")
File.open(File.join(bundle, 'tests.tsv'), 'w') do |manifest|
  entries.each do |input, *fields|
    FileUtils.cp(input, File.join(bundle, fields[1]))
    manifest.puts fields.join("\t")
  end
end
FileUtils.cp(File.join(build, 'tests/exec-fd-leak-checker'), File.join(bundle, 'tests'))
File.open(File.join(bundle, 'runtime.sha256'), 'w') do |manifest|
  runtime_files.each do |file|
    relative = "/usr/pkg/#{file}"
    path = File.join(sysroot, relative)
    manifest.puts "#{Digest::SHA256.file(path).hexdigest}  #{relative}"
  end
end
File.open(File.join(bundle, 'artifacts.sha256'), 'w') do |manifest|
  Dir.glob(File.join(bundle, '**/*')).sort.each do |path|
    next unless File.file?(path)
    next if File.basename(path) == 'artifacts.sha256'
    manifest.puts "#{Digest::SHA256.file(path).hexdigest}  #{path.delete_prefix(bundle + '/')}"
  end
end
puts "Prepared #{tests.size} upstream invocations in #{bundle}"
