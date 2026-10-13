#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted). Use the common target loader.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'
abort 'usage: build-powervr-enumeration.rb CROSS_TOOLS SYSROOT NEW_WORK' unless ARGV.size == 3
cross, sysroot = ARGV.first(2).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'Use a new absolute output directory' unless ARGV.last.start_with?('/') && !File.exist?(work)
source = File.join(__dir__, 'powervr-enumerate.c')
cc = cross + '/bin/aarch64--netbsd-gcc'
abort 'Missing GCC16 or installed Vulkan loader headers' unless File.executable?(cc) && File.file?(sysroot + '/usr/pkg/include/vulkan/vulkan.h')
triple, status = Open3.capture2e(cc, '-dumpmachine')
abort 'Wrong cross compiler' unless status.success? && triple.strip == 'aarch64--netbsd'
version, status = Open3.capture2e(cc, '-dumpfullversion')
abort 'Require the common GCC16' unless status.success? && version.start_with?('16.')
FileUtils.mkdir_p(work)
command = [cc, "--sysroot=#{sysroot}", '-std=c11', '-D_NETBSD_SOURCE', '-O2', '-g', '-Wall', '-Wextra', '-Werror', "-I#{sysroot}/usr/pkg/include", source,
           "-L#{sysroot}/usr/pkg/lib", '-lvulkan', '-Wl,-rpath,/usr/pkg/lib', '-Wl,-z,relro,-z,now', '-o', work + '/powervr-enumerate']
out, err, status = Open3.capture3(*command)
File.write(work + '/build.log', out + err)
File.write(work + '/build.command', Shellwords.join(command) + "\n")
abort 'Target enumeration consumer build failed' unless status.success?
FileUtils.cp(File.join(__dir__, 'run-powervr-enumeration.sh'), work)
inputs = [cc, source, sysroot + '/usr/pkg/include/vulkan/vulkan_core.h', sysroot + '/usr/pkg/lib/libvulkan.so']
receipt = {schema: 'ember-powervr-enumeration-1', command: command,
           inputs: inputs.to_h { |p| [p, Digest::SHA256.file(p).hexdigest] },
           executable_sha256: Digest::SHA256.file(work + '/powervr-enumerate').hexdigest,
           scope: 'Dynamic installed Vulkan loader; no device creation or GPU submission.'}
File.write(work + '/receipt.json', JSON.pretty_generate(receipt) + "\n")
puts "Built target enumeration check: #{work}"
