#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Bundle existing upstream target tests.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'

abort 'Usage: prepare.rb SOURCE_WITH_OUTPUT SYSROOT NEW_OUTPUT' unless ARGV.size == 3
source, sysroot, output = ARGV.map { |path| File.expand_path(path) }
reader = ENV.fetch('READELF')
final_paths = [output, output + '.tar.gz', output + '.tar.gz.sha256']
raise 'Output exists' if final_paths.any? { |path| File.exist?(path) || File.symlink?(path) }
staging = output + '.preparing'
Dir.mkdir(staging)
build = File.join(source, 'output')
binaries = %w[unit-tests-utils unit-tests-ei unit-tests-eis unit-tests-oeffis eierpecken test-build-libei test-build-libeis test-build-cxx-libei test-build-cxx-libeis]

def readelf(reader, *arguments)
  text, error, status = Open3.capture3(reader, *arguments)
  raise "readelf failed: #{error}" unless status.success?
  text
end

archive = output + '.tar.gz.preparing'
owned_archive = false
begin
  archive_file = File.open(archive, File::WRONLY | File::CREAT | File::EXCL, 0o600)
  owned_archive = true
  %w[bin lib fixtures metadata].each { |dir| Dir.mkdir(File.join(staging, dir)) }
  commands = JSON.parse(File.read(File.join(build, 'compile_commands.json')))
  %w[LIBEI LIBEIS].each do |name|
    target_directory = "test-build-cxx-#{name.downcase}.p"
    matches = commands.select { |entry| entry.fetch('output', '').split('/').include?(target_directory) }
    raise "Missing target C++ configuration for #{name}" unless matches.size == 1
    command = matches.first['command'] || matches.first.fetch('arguments').join(' ')
    raise "C++ header check is disabled for #{name}" unless command.include?("-DINCLUDE_#{name}=1")
  end
  queue = []
  binaries.each do |name|
    input = File.join(build, 'test', name)
    header = readelf(reader, '-h', input)
    segments = readelf(reader, '-lW', input)
    raise "Not AArch64 ELF64: #{name}" unless header.match?(/Class:\s+ELF64/) && header.match?(/Machine:\s+AArch64/)
    raise "Wrong target interpreter: #{name}" unless segments.include?('[Requesting program interpreter: /libexec/ld.elf_so]')
    target = File.join(staging, 'bin', name)
    FileUtils.copy_file(input, target, true)
    queue << target
  end
  %w[libei libeis liboeffis].each do |name|
    input = File.join(build, 'src', name + '.so.1.6.0')
    target = File.join(staging, 'lib', name + '.so.1')
    FileUtils.copy_file(input, target, true)
    queue << target
  end
  directories = [File.join(build, 'src'), File.join(sysroot, 'usr/pkg/lib'), File.join(sysroot, 'usr/pkg/gcc16/lib')]
  base_directories = [File.join(sysroot, 'lib'), File.join(sysroot, 'usr/lib')]
  seen = {}
  base = {}
  until queue.empty?
    input = queue.shift
    next if seen[input]
    seen[input] = true
    header = readelf(reader, '-h', input)
    raise "Wrong library ABI: #{input}" unless header.match?(/Class:\s+ELF64/) && header.match?(/Machine:\s+AArch64/)
    dynamic = readelf(reader, '-dW', input)
    File.write(File.join(staging, 'metadata', File.basename(input) + '.dynamic'), dynamic)
    dynamic.scan(/\(NEEDED\).*\[([^\]]+)\]/).flatten.each do |name|
      raise "Unsafe library name: #{name}" unless name.match?(/\A[a-zA-Z0-9_.+-]+\z/)
      bundled = File.join(staging, 'lib', name)
      next if File.file?(bundled)
      original = directories.map { |dir| File.join(dir, name) }.find { |path| File.file?(path) }
      if original
        FileUtils.copy_file(original, bundled, true)
        queue << bundled
      else
        original = base_directories.map { |dir| File.join(dir, name) }.find { |path| File.file?(path) }
        raise "Missing dependency: #{name}" unless original
        base[name] = Digest::SHA256.file(original).hexdigest
      end
    end
  end
  FileUtils.copy_file(File.join(__dir__, 'run.sh'), File.join(staging, 'run.sh'))
  FileUtils.copy_file(File.join(source, 'COPYING'), File.join(staging, 'COPYING'))
  %w[protocol.xml protocol.dtd].each { |name| FileUtils.copy_file(File.join(source, 'proto', name), File.join(staging, 'fixtures', name)) }
  FileUtils.copy_file(File.join(build, 'meson-info/intro-tests.json'), File.join(staging, 'metadata/upstream-tests.json'))
  FileUtils.copy_file(File.join(build, 'meson-info/intro-compilers.json'), File.join(staging, 'metadata/compilers.json'))
  File.write(File.join(staging, 'metadata/base-libraries.json'), JSON.pretty_generate(base))
  File.write(File.join(staging, 'metadata/limits.txt'), "Prepared only; target execution has not run.\nRequires matched EmberBSD AArch64 base, sh, timeout, sha256, and ldd.\nPython portal/scanner tests and a real compositor are outside this bundle.\n")
  files = Dir.glob(staging + '/**/*').select { |path| File.file?(path) }.sort
  File.write(File.join(staging, 'SHA256SUMS'), files.map { |path| "#{Digest::SHA256.file(path).hexdigest}  #{path.delete_prefix(staging + '/')}\n" }.join)
  ok = system('/usr/bin/tar', '-czf', '-', '-C', staging, '.', out: archive_file)
  archive_file.close
  raise 'Archive creation failed' unless ok
  archive_hash = Digest::SHA256.file(archive).hexdigest
  File.rename(staging, output)
  File.rename(archive, output + '.tar.gz')
  File.write(output + '.tar.gz.sha256', archive_hash + "\n")
  puts "PREPARED: #{binaries.size} compiled upstream binaries; target execution is pending"
ensure
  FileUtils.remove_entry(staging) if File.directory?(staging)
  archive_file.close if archive_file && !archive_file.closed?
  File.unlink(archive) if owned_archive && (File.exist?(archive) || File.symlink?(archive))
end
