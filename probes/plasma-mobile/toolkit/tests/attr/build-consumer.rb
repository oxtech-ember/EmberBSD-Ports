#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Preserve the old libattr consumer boundary.
require 'digest'
require 'json'
require 'open3'
require 'shellwords'
abort 'Usage: build-consumer.rb STAGED_PREFIX OLD_ARCHIVE_PREFIX SYSROOT TOOLS NEW_OUTPUT' unless ARGV.length == 5
staged, old, sysroot, tools, output = ARGV.map { |path| File.expand_path(path) }
Dir.mkdir(output)
source = File.join(__dir__, 'runtime-consumer.c')
gcc = File.join(tools, 'bin/aarch64--netbsd-gcc')
readelf = File.join(tools, 'bin/aarch64--netbsd-readelf')
args = [gcc, "--sysroot=#{sysroot}", "-B#{sysroot}/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/",
        '-std=c11', '-D_NETBSD_SOURCE', '-Wall', '-Wextra', '-Werror', '-O2']
commands = {}
begin
  { 'old' => old, 'fixed' => staged }.each do |kind, prefix|
    command = [*args, "-I#{prefix}/include", '-fsyntax-only', source]
    out, err, status = Open3.capture3(*command)
    commands["headers-#{kind}"] = command
    File.write(File.join(output, "headers-#{kind}.log"), out + err)
    if kind == 'old'
      raise 'Old header did not reproduce the unexpanded EXPORT failure' if status.success? || !err.include?('EXPORT')
    else
      raise err unless status.success?
    end
  end
  libraries = { 'old' => File.join(old, 'lib/libattr.so.1'), 'fixed' => File.join(staged, 'lib/libattr.so.1') }
  exports = {}
  libraries.each do |kind, library|
    dynamic, err, status = Open3.capture3(readelf, '-dW', library)
    raise err unless status.success?
    raise "Changed libattr SONAME: #{kind}" unless dynamic.include?('Library soname: [libattr.so.1]')
    symbols, err, status = Open3.capture3(readelf, '--dyn-syms', '--wide', library)
    raise err unless status.success?
    exports[kind] = symbols.lines.filter_map do |line|
      fields = line.split
      fields[7] if fields.size >= 8 && fields[3] == 'FUNC' && %w[GLOBAL WEAK].include?(fields[4]) && fields[6] != 'UND'
    end.sort
    File.write(File.join(output, "libattr-#{kind}.elf"), dynamic + symbols)
  end
  missing = exports['old'] - exports['fixed']
  raise "Missing exported ABI: #{missing.join(', ')}" unless missing.empty? && !exports['old'].empty?
  binary = File.join(output, 'attr-abi-consumer')
  command = [*args, "-I#{staged}/include", source, "-L#{old}/lib", '-lattr', '-Wl,-rpath,/usr/pkg/lib',
             "-L#{sysroot}/usr/pkg/gcc16/lib", '-Wl,-rpath,/usr/pkg/gcc16/lib', '-o', binary]
  commands['consumer-linked-old-libattr'] = command
  out, err, status = Open3.capture3(*command)
  File.write(File.join(output, 'build.log'), out + err)
  raise err unless status.success?
  dynamic, err, status = Open3.capture3(readelf, '-dW', binary)
  raise err unless status.success? && dynamic.include?('Shared library: [libattr.so.1]')
  File.write(File.join(output, 'consumer.elf'), dynamic)
  File.write(File.join(output, 'sha256.txt'), "#{Digest::SHA256.file(binary).hexdigest}  attr-abi-consumer\n")
  puts "PASS: portable headers, libattr.so.1, #{exports['old'].size} retained exports and old-DSO consumer link"
rescue StandardError => error
  warn error.message
  exit 1
ensure
  File.write(File.join(output, 'commands.json'), JSON.pretty_generate(commands) + "\n")
end
