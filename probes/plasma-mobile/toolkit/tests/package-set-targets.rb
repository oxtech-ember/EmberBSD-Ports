#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Real package fixtures for target selection.
require 'digest'
require 'fileutils'
require 'open3'
require 'rbconfig'

abort 'Usage: package-set-targets.rb NEW_OUTPUT' unless ARGV.length == 1
work = File.expand_path(ARGV.first)
Dir.mkdir(work)
create = ENV.fetch('PKG_CREATE', 'pkg_create')
info = ENV.fetch('PKG_INFO', 'pkg_info')
admin = ENV.fetch('PKG_ADMIN', 'pkg_admin')
tar = ENV.fetch('BSDTAR', 'bsdtar')
auditor = File.expand_path('../cross/prepare-package-set.rb', __dir__)
installer = File.expand_path('../cross/install-package-set.sh', __dir__)
environment = { 'PKG_INFO' => info, 'PKG_ADMIN' => admin, 'BSDTAR' => tar }
count = 0

run = lambda do |*command|
  output, error, status = Open3.capture3(*command)
  raise "Command failed: #{command.inspect}\n#{output}#{error}" unless status.success?
  output
end
metadata = lambda do |arch|
  "OPSYS=NetBSD\nOS_VERSION=11.0\nMACHINE_ARCH=#{arch}\nOBJECT_FMT=ELF\n"
end
# Header-only ELF fixtures are never executed. Test the declared machine,
# class and byte order independently from truthful pkgtools MD5 metadata.
elf = lambda do |machine, klass = 2, endian = 1|
  header = "\0".b * 64
  header[0, 7] = "\x7fELF".b + [klass, endian, 1].pack('C*')
  header[18, 2] = [machine].pack('v')
  header
end
fixture = lambda do |name, arch, machines, database_arch = nil, archive_arch = {}|
  directory = File.join(work, name)
  payload = File.join(directory, 'payload')
  database = File.join(directory, 'pkgdb')
  archives = File.join(directory, 'archives')
  FileUtils.mkdir_p([File.join(payload, 'share'), database, archives])
  File.write(File.join(directory, 'comment'), "Target fixtures\n")
  File.write(File.join(directory, 'description'), "Header-only package fixtures; no target execution.\n")
  File.write(File.join(directory, 'build-info'), metadata.call(arch))
  %w[target-leaf-1.0 target-root-1.0].each_with_index do |package, index|
    File.write(File.join(directory, 'build-info'), metadata.call(archive_arch.fetch(package, arch)))
    File.binwrite(File.join(payload, "share/#{package}"), machines[index])
    plist = File.join(directory, 'plist')
    File.write(plist, "share/#{package}\n")
    command = [create, '-p', payload, '-I', '/usr/pkg', '-f', plist,
               '-c', File.join(directory, 'comment'), '-d', File.join(directory, 'description'),
               '-B', File.join(directory, 'build-info')]
    command += ['-P', 'target-leaf>=1.0'] if index == 1
    archive = File.join(archives, "#{package}.tgz")
    run.call(*command, archive)
    installed = File.join(database, package)
    Dir.mkdir(installed)
    run.call(tar, '-tf', archive).lines.map(&:chomp).grep(/^\+/).each do |entry|
      File.binwrite(File.join(installed, entry), run.call(tar, '-xOf', archive, entry))
    end
  end
  database_arch&.each do |package, wrong|
    File.write(File.join(database, package, '+BUILD_INFO'), metadata.call(wrong))
  end
  list = File.join(directory, 'archives.txt')
  File.write(list, Dir[File.join(archives, '*.tgz')].sort.join("\n") + "\n")
  [directory, database, list]
end
audit = lambda do |name, arch, payloads, target, expected = nil, database_arch = nil|
  directory, database, index = fixture.call(name, arch, payloads, database_arch)
  destination = File.join(directory, 'set')
  arguments = target ? ['--target', target] : []
  output, error, status = Open3.capture3(environment, RbConfig.ruby, auditor,
                                      *arguments, database, index, destination, 'target-root-1.0')
  File.write(File.join(directory, 'audit.log'), output + error)
  if expected
    raise "#{name} did not reject #{expected}: #{output}#{error}" if status.success? || !(output + error).include?(expected)
    raise 'Failed target audit published output' if File.exist?(destination)
  else
    raise "#{name} failed: #{output}#{error}" unless status.success?
    raise 'Target receipt differs' unless File.binread(File.join(destination, 'target.txt')) == metadata.call(arch)
    verify = ['sh', installer, *arguments, '--verify-only', destination]
    output, error, status = Open3.capture3(environment, *verify)
    raise "#{name} host verification failed: #{output}#{error}" unless status.success?
    File.write(File.join(directory, 'verify.log'), output + error)
  end
  count += 1
  puts "PASS: #{name}"
  destination
end
aarch = elf.call(183)
amd = elf.call(62)
arm_set = audit.call('aarch64-default', 'aarch64', [aarch, aarch], nil)
audit.call('aarch64-explicit', 'aarch64', [aarch, aarch], 'aarch64')
amd_set = audit.call('amd64-explicit', 'x86_64', [amd, amd], 'amd64')
audit.call('amd64-data-package', 'x86_64', ["data only\n", amd], 'amd64')
audit.call('amd64-wrong-root-elf', 'x86_64', [amd, aarch], 'amd64', 'Wrong ELF machine')
audit.call('amd64-wrong-dependency-elf', 'x86_64', [aarch, amd], 'amd64', 'Wrong ELF machine')
audit.call('aarch64-wrong-elf', 'aarch64', [amd, aarch], nil, 'Wrong ELF machine')
audit.call('amd64-wrong-class', 'x86_64', [elf.call(62, 1), amd], 'amd64', 'Unsupported ELF class')
audit.call('amd64-wrong-endian', 'x86_64', [elf.call(62, 2, 2), amd], 'amd64', 'Unsupported ELF byte order')
audit.call('amd64-truncated-elf', 'x86_64', ["\x7fELF".b, amd], 'amd64', 'Truncated ELF header')
audit.call('amd64-wrong-root-metadata', 'x86_64', [amd, amd], 'amd64', 'Wrong target MACHINE_ARCH',
           { 'target-root-1.0' => 'aarch64' })
audit.call('amd64-wrong-dependency-metadata', 'x86_64', [amd, amd], 'amd64', 'Wrong target MACHINE_ARCH',
           { 'target-leaf-1.0' => 'aarch64' })
%w[unknown missing empty repeated].each do |name|
  options = case name
            when 'unknown' then ['--target', 'riscv64']
            when 'missing' then ['--target']
            when 'empty' then ['--target', '']
            else ['--target', 'amd64', '--target', 'aarch64']
            end
  [[RbConfig.ruby, auditor], ['sh', installer]].each do |command|
    output, error, status = Open3.capture3(environment, *command, *options)
    raise "Accepted #{name} target: #{output}#{error}" if status.success?
    count += 1
  end
end
[['--target', 'amd64', arm_set], ['--target', 'aarch64', amd_set], [amd_set]].each do |arguments|
  output, error, status = Open3.capture3(environment, 'sh', installer, *arguments)
  raise 'Mismatched target receipt accepted' if status.success? || !(output + error).include?('Target receipt mismatch')
  count += 1
end
host_bin = File.join(work, 'host-bin')
Dir.mkdir(host_bin)
File.write(File.join(host_bin, 'uname'), <<~SH)
  #!/bin/sh
  case "$1" in -s) echo NetBSD;; -p) echo "$FIXTURE_ARCH";; *) exit 1;; esac
SH
File.chmod(0755, File.join(host_bin, 'uname'))
[[arm_set, nil, 'x86_64', 'Installation requires aarch64'],
 [arm_set, 'amd64', 'x86_64', 'Target receipt mismatch'],
 [amd_set, 'amd64', 'aarch64', 'Installation requires x86_64']].each_with_index do |(bundle, target, host_arch, expected), index|
  options = target ? ['--target', target] : []
  log = File.join(work, "wrong-host-#{index}-install.log")
  env = environment.merge('PATH' => "#{host_bin}:#{ENV.fetch('PATH')}", 'FIXTURE_ARCH' => host_arch)
  output, error, status = Open3.capture3(env, 'sh', installer, *options, '--install', bundle, log)
  raise "Wrong-host install did not reject #{expected}: #{output}#{error}" if status.success? || !(output + error).include?(expected)
  raise 'Wrong-host installation created a log' if File.exist?(log)
  count += 1
end
# A forged marker must not hide ARM package metadata in an amd64 closure.
directory, = fixture.call('installer-mixed-archive', 'x86_64', [amd, amd], nil,
                          { 'target-leaf-1.0' => 'aarch64' })
mixed = File.join(directory, 'set')
Dir.mkdir(mixed)
FileUtils.cp_r(File.join(directory, 'archives'), File.join(mixed, 'packages'))
File.write(File.join(mixed, 'target.txt'), metadata.call('x86_64'))
File.write(File.join(mixed, 'install-order.txt'), "target-leaf-1.0.tgz\ntarget-root-1.0.tgz\n")
File.write(File.join(mixed, 'roots.txt'), "target-root-1.0\n")
File.write(File.join(mixed, 'packages.sha256'), Dir[File.join(mixed, 'packages', '*.tgz')].sort.map do |path|
  "#{Digest::SHA256.file(path).hexdigest}  packages/#{File.basename(path)}\n"
end.join)
output, error, status = Open3.capture3(environment, 'sh', installer, '--target', 'amd64', mixed)
raise 'Foreign archive metadata accepted by installer' if status.success? || !(output + error).include?('Package is not the prepared EmberBSD ABI')
count += 1
File.write(File.join(amd_set, 'target.txt'), metadata.call('x86_64') + "MACHINE_ARCH=x86_64\n")
output, error, status = Open3.capture3(environment, 'sh', installer, '--target', 'amd64', amd_set)
raise 'Duplicate receipt fields accepted' if status.success? || !(output + error).include?('Target receipt mismatch')
count += 1
puts "PASS: #{count} target selection, real pkgtools closure, ELF header and host verification checks; no target execution"
