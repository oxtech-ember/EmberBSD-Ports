#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted). Use the installed Vulkan loader.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'
abort 'usage: build-powervr-compute.rb CROSS_TOOLS SYSROOT SPIRV_TOOLS NEW_WORK' unless ARGV.size == 4
cross, sysroot, spirv = ARGV.first(3).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'Use a new absolute output directory' unless ARGV.last.start_with?('/') && !File.exist?(work)
cc = cross + '/bin/aarch64--netbsd-gcc'
assembler, validator = %w[spirv-as spirv-val].map { |n| spirv + '/bin/' + n }
abort 'Missing compiler, SPIR-V tools, or Vulkan headers' unless [cc, assembler, validator].all? { |p| File.executable?(p) } && File.file?(sysroot + '/usr/pkg/include/vulkan/vulkan.h')
triple, status = Open3.capture2e(cc, '-dumpmachine')
abort 'Wrong cross compiler' unless status.success? && triple.strip == 'aarch64--netbsd'
version, status = Open3.capture2e(cc, '-dumpfullversion')
abort 'Require the common GCC16' unless status.success? && version.start_with?('16.')
FileUtils.mkdir_p(work)
commands = []
run = lambda do |name, argv|
  commands << argv
  out, err, status = Open3.capture3(*argv)
  File.write(work + '/' + name + '.log', out + err)
  File.write(work + '/' + name + '.command', Shellwords.join(argv) + "\n")
  abort "Failed: #{name}" unless status.success?
end
source = __dir__ + '/powervr-compute.c'
shader = __dir__ + '/powervr-compute.spvasm'
run.call('assemble', [assembler, '--target-env', 'vulkan1.2', shader, '-o', work + '/compute.spv'])
run.call('validate', [validator, '--target-env', 'vulkan1.2', work + '/compute.spv'])
words = File.binread(work + '/compute.spv')
abort 'Invalid SPIR-V word stream' unless words.size >= 20 && words.size % 4 == 0 && words.unpack1('V') == 0x07230203
File.write(work + '/powervr-compute-shader.h', "/* Generated from the validated powervr-compute.spvasm. */\nstatic const uint32_t compute_shader[] = {\n" + words.unpack('V*').each_slice(6).map { |a| "\t" + a.map { |v| format('0x%08xU', v) }.join(', ') + ',' }.join("\n") + "\n};\n")
command = [cc, "--sysroot=#{sysroot}", '-std=c11', '-D_NETBSD_SOURCE', '-O2', '-g', '-Wall', '-Wextra', '-Werror', "-I#{sysroot}/usr/pkg/include", "-I#{work}", source,
           "-L#{sysroot}/usr/pkg/lib", '-lvulkan', '-Wl,-rpath,/usr/pkg/lib', '-Wl,-z,relro,-z,now', '-o', work + '/powervr-compute']
run.call('build', command)
FileUtils.cp(__dir__ + '/run-powervr-compute.sh', work)
inputs = [cc, assembler, validator, source, shader, __FILE__, __dir__ + '/run-powervr-compute.sh', sysroot + '/usr/pkg/include/vulkan/vulkan_core.h', sysroot + '/usr/pkg/lib/libvulkan.so']
receipt = {schema: 'ember-powervr-compute-1', commands: commands,
           inputs: inputs.to_h { |p| [p, Digest::SHA256.file(p).hexdigest] },
           outputs: %w[powervr-compute compute.spv powervr-compute-shader.h].to_h { |n| [n, Digest::SHA256.file(work + '/' + n).hexdigest] },
           scope: 'Target build only. Physical Vulkan device creation, queue submission, and readback require separate acceptance.'}
File.write(work + '/receipt.json', JSON.pretty_generate(receipt) + "\n")
puts "Built target compute check: #{work}"
