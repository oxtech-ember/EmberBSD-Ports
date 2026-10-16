#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Real pkgtools archives; labelled text payloads.
require 'fileutils'
require 'open3'
require 'rbconfig'
abort 'Usage: package-set-llvm.rb HOST_PREFIX NEW_OUTPUT' unless ARGV.length == 2
host = File.realpath(ARGV[0])
work = File.expand_path(ARGV[1])
abort 'new absolute output required' unless ARGV[1].start_with?('/') && !File.exist?(work)
Dir.mkdir(work)
create = host + '/sbin/pkg_create'
info = host + '/sbin/pkg_info'
tar = ENV.fetch('BSDTAR', 'bsdtar')
auditor = File.expand_path('../cross/prepare-package-set.rb', __dir__)
runtime = %w[lib/libLLVM.so.23.1 lib/libLLVM-23.so lib/libLLVM.so lib/libLTO.so.23.1 lib/libLTO.so lib/libRemarks.so.23.1 lib/libRemarks.so include/llvm/Support/LICENSE.TXT]
cases = [
  ['runtime-amd64', 'llvm-23.1.3nb1', runtime, 'amd64', nil],
  ['runtime-aarch64', 'llvm-23.1.3nb1', runtime, 'aarch64', nil],
  ['old-monolith', 'llvm-23.1.3', runtime + ['bin/llvm-config'], 'amd64', 'LLVM runtime'],
  ['dependency-sdk', 'llvm-devel-23.1.3nb1', ['bin/llvm-config'], 'amd64', 'LLVM SDK', true],
  ['dependency-runtime', 'llvm-23.1.3nb1', runtime, 'amd64', nil, true],
  ['sdk', 'llvm-devel-23.1.3nb1', ['bin/llvm-config'], 'amd64', 'LLVM SDK'],
  ['revised-monolith', 'llvm-23.1.3nb1', runtime + ['bin/llvm-config'], 'amd64', 'LLVM runtime'],
  ['header-leak', 'llvm-23.1.3nb1', runtime + ['include/llvm/IR/Module.h'], 'amd64', 'LLVM runtime'],
  ['missing-dso', 'llvm-23.1.3nb1', runtime - ['lib/libLTO.so.23.1'], 'amd64', 'LLVM runtime'],
  ['missing-license', 'llvm-23.1.3nb1', runtime - ['include/llvm/Support/LICENSE.TXT'], 'amd64', 'LLVM runtime'],
  ['legacy-provider', 'libLLVM-13.0.1nb4', ['lib/libLLVM/libLLVM.so.13'], 'amd64', 'LLVM legacy'],
  ['unrelated', 'llvm-helper-1.0', ['share/fixture'], 'amd64', nil]
]
cases.each do |label, package, files, target, rejected, dependency|
  dir = work + '/' + label
  payload = dir + '/payload'
  database = dir + '/pkgdb'
  FileUtils.mkdir_p([payload, database])
  files.each do |name|
    FileUtils.mkdir_p(File.dirname(payload + '/' + name))
    File.write(payload + '/' + name, "Text package policy fixture: #{name}\n")
  end
  File.write(dir + '/plist', files.join("\n") + "\n")
  File.write(dir + '/comment', 'LLVM package role policy fixture')
  File.write(dir + '/description', "Synthetic text, not compiled LLVM or target execution.\n")
  arch = target == 'amd64' ? 'x86_64' : 'aarch64'
  File.write(dir + '/build-info', "OPSYS=NetBSD\nOS_VERSION=11.0\nMACHINE_ARCH=#{arch}\nOBJECT_FMT=ELF\n")
  archive = dir + '/' + package + '.tgz'
  out, err, status = Open3.capture3(create, '-p', payload, '-I', '/usr/pkg', '-f', dir + '/plist', '-c', dir + '/comment', '-d', dir + '/description', '-B', dir + '/build-info', archive)
  abort out + err unless status.success?
  installed = database + '/' + package
  Dir.mkdir(installed)
  listing, err, status = Open3.capture3(tar, '-tf', archive)
  abort err unless status.success?
  listing.lines.map(&:chomp).grep(/^\+/).each do |name|
    bytes, err, status = Open3.capture3(tar, '-xOf', archive, name)
    abort err unless status.success?
    File.binwrite(installed + '/' + name, bytes)
  end
  archives = [archive]
  if dependency
    root = 'desktop-fixture-1.0'
    root_payload = dir + '/root-payload'
    FileUtils.mkdir_p(root_payload + '/share')
    File.write(root_payload + '/share/consumer', 'runtime consumer fixture')
    File.write(dir + '/root-plist', "share/consumer\n")
    root_archive = dir + '/' + root + '.tgz'
    out, err, status = Open3.capture3(create, '-p', root_payload, '-I', '/usr/pkg', '-P', package, '-f', dir + '/root-plist', '-c', dir + '/comment', '-d', dir + '/description', '-B', dir + '/build-info', root_archive)
    abort out + err unless status.success?
    Dir.mkdir(database + '/' + root)
    listing, err, status = Open3.capture3(tar, '-tf', root_archive)
    abort err unless status.success?
    listing.lines.map(&:chomp).select { |name| name.start_with?('+') }.each do |name|
      bytes, err, status = Open3.capture3(tar, '-xOf', root_archive, name)
      abort err unless status.success?
      File.binwrite(database + '/' + root + '/' + name, bytes)
    end
    archives << root_archive
    package = root
  end
  File.write(dir + '/archives', archives.join("\n") + "\n")
  out, err, status = Open3.capture3({'PKG_INFO' => info, 'BSDTAR' => tar}, RbConfig.ruby, auditor, '--target', target, database, dir + '/archives', dir + '/set', package)
  File.write(dir + '/audit.log', out + err)
  if rejected
    abort label + ' accepted a forbidden LLVM package: ' + out + err if status.success? || !(out + err).include?(rejected)
    abort label + ' published a rejected set' if File.exist?(dir + '/set')
  else
    abort label + ': ' + out + err unless status.success?
  end
  puts 'PASS: ' + label
end
puts 'SCOPE: twelve archive/policy fixtures; no LLVM build, target execution or shared pkgdb changes'
