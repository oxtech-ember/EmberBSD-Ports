#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), real pkgtools provider transition fixture.
require 'fileutils'
require 'open3'
abort 'Usage: llvm-lit-ownership.rb HOST_PKGTOOLS_DIRECTORY NEW_WORK' unless ARGV.size == 2
tools, work = ARGV.map { |arg| File.expand_path(arg) }
Dir.mkdir(work)
root = File.join(work, 'root')
FileUtils.mkdir_p(root)
log = File.open(File.join(work, 'commands.log'), 'w')
run = lambda do |expected, *args|
  output, status = Open3.capture2e(*args)
  log.puts(args.inspect, output, "status=#{status.exitstatus}")
  log.flush
  abort "Unexpected command result: #{args.inspect}\n#{output}" unless status.success? == expected
  output
end
File.write(File.join(work, 'comment'), 'LLVM Python ownership fixture')
File.write(File.join(work, 'description'), 'Test data; this package is not a compiler.')
File.write(File.join(work, 'build-info'), "OPSYS=NetBSD\nOS_VERSION=11.0\nMACHINE_ARCH=aarch64\nOBJECT_FMT=ELF\n")
packages = {}
old = 'py314-llvm-lit-23.1.3'
new = 'py315-llvm-lit-23.1.3nb1'
consumer = 'llvm-python-consumer-1.0'
replacement = 'llvm-python-consumer-1.0nb1'
[[old, nil, false], [new, nil, true], [consumer, old, false], [replacement, new, false]].each do |name, dependency, conflict|
  stage = File.join(work, name)
  FileUtils.mkdir_p(File.join(stage, 'bin'))
  relative = dependency ? 'bin/compiler-fixture' : 'bin/lit'
  File.write(File.join(stage, relative), dependency ? 'compiler payload retained' : name)
  plist = "@cwd /usr/pkg\n@name #{name}\n"
  plist += "@pkgdep #{dependency}\n" if dependency
  plist += "@pkgcfl py[0-9]*-llvm-lit-[0-9]*\n" if conflict
  plist += "#{relative}\n"
  File.write(File.join(stage, 'plist'), plist)
  packages[name] = File.join(work, name + '.tgz')
  run.call(true, File.join(tools, 'pkg_create'), '-p', stage, '-I', '/usr/pkg', '-f', File.join(stage, 'plist'), '-c', File.join(work, 'comment'), '-d', File.join(work, 'description'), '-B', File.join(work, 'build-info'), packages.fetch(name))
end
add = lambda { |name, expected = true| run.call(expected, File.join(tools, 'pkg_add'), '-U', '-I', '-P', root, '-K', '/usr/pkg/pkgdb', '-m', 'NetBSD/aarch64 11.0', packages.fetch(name)) }
delete = lambda do |name, force, expected = true|
  args = [File.join(tools, 'pkg_delete'), '-D', '-P', root, '-K', '/usr/pkg/pkgdb']
  args << '-f' if force
  run.call(expected, *args, name)
end
add.call(old)
add.call(consumer)
add.call(new, false)
abort 'Conflict overwrote launcher' unless File.read(File.join(root, 'usr/pkg/bin/lit')) == old
delete.call(old, false, false)
abort 'Compiler disappeared' unless File.read(File.join(root, 'usr/pkg/bin/compiler-fixture')) == 'compiler payload retained'
delete.call(old, true)
add.call(new)
add.call(replacement)
abort 'Wrong new launcher' unless File.read(File.join(root, 'usr/pkg/bin/lit')) == new
required = File.read(File.join(root, 'usr/pkg/pkgdb', new, '+REQUIRED_BY')).lines.map(&:chomp)
abort 'Wrong new reverse dependency' unless required == [replacement]
# Repeat the same provider-first sequence with the retained rollback archives.
delete.call(new, true)
add.call(old)
add.call(consumer)
abort 'Rollback lost compiler' unless File.read(File.join(root, 'usr/pkg/bin/compiler-fixture')) == 'compiler payload retained'
abort 'Rollback lost provider' unless File.read(File.join(root, 'usr/pkg/bin/lit')) == old
required = File.read(File.join(root, 'usr/pkg/pkgdb', old, '+REQUIRED_BY')).lines.map(&:chomp)
abort 'Wrong rollback reverse dependency' unless required == [consumer]
puts 'PASS: rejected co-installation, guarded removal, provider replacement, retained compiler and package rollback.'
