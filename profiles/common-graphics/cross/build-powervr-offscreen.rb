#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'
abort 'usage: build-powervr-offscreen.rb CROSS_TOOLS SYSROOT SPIRV_TOOLS NEW_WORK' unless ARGV.size == 4
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
repository, status = Open3.capture2e('git', '-C', __dir__, 'rev-parse', '--show-toplevel')
abort 'Build from a clean Ports checkout' unless status.success?
repository = repository.strip
revision, status = Open3.capture2e('git', '-C', repository, 'rev-parse', 'HEAD')
abort 'Cannot read Ports revision' unless status.success?
changes, status = Open3.capture2e('git', '-C', repository, 'status', '--porcelain')
abort 'Build from a clean committed Ports checkout' unless status.success? && changes.empty?
FileUtils.mkdir_p(work)
commands = []
run = lambda do |name, argv|
  commands << argv
  out, err, status = Open3.capture3(*argv)
  File.write(work + '/' + name + '.log', out + err)
  File.write(work + '/' + name + '.command', Shellwords.join(argv) + "\n")
  abort "Failed: #{name}" unless status.success?
end
header = "/* Generated from validated public SPIR-V assembly. */\n"
shaders = %w[vertex fragment].map do |stage|
  shader = __dir__ + '/powervr-offscreen-' + stage + '.spvasm'
  run.call(stage + '-assemble', [assembler, '--target-env', 'vulkan1.2', shader, '-o', work + '/' + stage + '.spv'])
  run.call(stage + '-validate', [validator, '--target-env', 'vulkan1.2', work + '/' + stage + '.spv'])
  words = File.binread(work + '/' + stage + '.spv')
  abort 'Invalid SPIR-V word stream' unless words.size >= 20 && words.size % 4 == 0 && words.unpack1('V') == 0x07230203
  header += "static const uint32_t #{stage}_shader[] = {\n" + words.unpack('V*').each_slice(6).map { |a| "\t" + a.map { |v| format('0x%08xU', v) }.join(', ') + ',' }.join("\n") + "\n};\n"
  shader
end
File.write(work + '/powervr-offscreen-shaders.h', header)
source = __dir__ + '/powervr-offscreen.c'
command = [cc, "--sysroot=#{sysroot}", '-std=c11', '-D_NETBSD_SOURCE', '-O2', '-g', '-MD', '-MF', work + '/consumer.d', '-Wall', '-Wextra', '-Werror', "-I#{sysroot}/usr/pkg/include", "-I#{work}", source,
           "-L#{sysroot}/usr/pkg/lib", '-lvulkan', '-Wl,-rpath,/usr/pkg/lib', '-Wl,-z,relro,-z,now', '-o', work + '/powervr-offscreen']
run.call('build', command)
run.call('compiler-specs', [cc, '-dumpspecs'])
dependencies = File.read(work + '/consumer.d').gsub(/\\\n/, ' ').split(': ', 2).last
abort 'Missing compiler dependency list' unless dependencies
headers = Shellwords.split(dependencies).map { |p| File.realpath(p) }.uniq
startup = %w[crt0.o crti.o crtbegin.o crtend.o crtn.o libc.so libgcc.a libgcc_s.so].map do |name|
  path, status = Open3.capture2e(cc, "--sysroot=#{sysroot}", '-print-file-name=' + name)
  abort 'Cannot resolve linker input: ' + name unless status.success? && File.file?(path.strip)
  File.realpath(path.strip)
end
base_inputs = (startup + [sysroot + '/libexec/ld.elf_so']).uniq
FileUtils.cp(__dir__ + '/run-powervr-offscreen.sh', work)
inputs = [cc, assembler, validator, source, *shaders, __FILE__, __dir__ + '/run-powervr-offscreen.sh', sysroot + '/usr/pkg/include/vulkan/vulkan_core.h', sysroot + '/usr/pkg/lib/libvulkan.so', *headers, *base_inputs]
receipt = {schema: 'ember-powervr-offscreen-1', revision: revision.strip, commands: commands,
  sysroot_scope: 'Hashes cover actual compile dependencies and selected base/link inputs. They are not a complete sysroot manifest or proof of its source revision.',
  base_inputs: base_inputs, inputs: inputs.uniq.to_h { |p| [p, Digest::SHA256.file(p).hexdigest] },
  outputs: %w[powervr-offscreen vertex.spv fragment.spv powervr-offscreen-shaders.h].to_h { |n| [n, Digest::SHA256.file(work + '/' + n).hexdigest] },
  scope: 'Cross-build and SPIR-V validation only. Physical geometry, fragment, transfer, and pixel acceptance remain separate.'}
File.write(work + '/receipt.json', JSON.pretty_generate(receipt) + "\n")
puts "Built target offscreen check: #{work}"
