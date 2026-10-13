#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted). Test the actual consumer source.
require 'fileutils'
require 'json'
require 'digest'
require 'open3'
require 'shellwords'
abort 'usage: powervr-compute.rb VULKAN_HEADERS SPIRV_TOOLS NEW_WORK' unless ARGV.size == 3
headers, tools = ARGV.first(2).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'Use a new absolute output directory' unless ARGV.last.start_with?('/') && !File.exist?(work)
FileUtils.mkdir_p(work)
owner = File.realpath(__dir__ + '/../cross')
fixture = __dir__ + '/powervr-compute.c'
commands = []
run = lambda do |name, argv, success|
  commands << argv
  out, err, status = Open3.capture3(*argv)
  File.write(work + '/' + name + '.stdout', out)
  File.write(work + '/' + name + '.stderr', err)
  File.write(work + '/' + name + '.command', Shellwords.join(argv) + "\n")
  abort "Unexpected #{name} result: #{status.inspect}" unless !!status.success? == success
  puts out.lines.last if success && name == 'check'
end
run.call('assemble', [tools + '/bin/spirv-as', '--target-env', 'vulkan1.2', owner + '/powervr-compute.spvasm', '-o', work + '/compute.spv'], true)
run.call('validate', [tools + '/bin/spirv-val', '--target-env', 'vulkan1.2', work + '/compute.spv'], true)
bytes = File.binread(work + '/compute.spv')
abort 'Invalid shader word stream' unless bytes.size >= 20 && bytes.size % 4 == 0 && bytes.unpack1('V') == 0x07230203
File.write(work + '/powervr-compute-shader.h', "static const uint32_t compute_shader[] = {\n" + bytes.unpack('V*').map { |n| format('0x%08xU,', n) }.join("\n") + "\n};\n")
flags = %w[-std=c11 -O1 -g -Wall -Wextra -Werror]
flags += %w[-fsanitize=address,undefined -fno-omit-frame-pointer] if ENV['SANITIZERS'] == 'yes'
cc = Shellwords.split(ENV.fetch('CC', 'cc'))
compile = lambda do |dir, binary|
  cc + flags + ['-I' + headers, '-I' + dir, '-I' + work, fixture, '-o', binary]
end
run.call('compile', compile.call(owner, work + '/check'), true)
run.call('check', [work + '/check'], true)
source = File.read(owner + '/powervr-compute.c')
mutants = {
  'wrong-node' => ['drm.renderMinor != (int64_t)minor(expected)', 'false'],
  'readback' => ['actual != (VALUE ^ i)', 'false'],
  'no-invalidate' => ['TRY(vkInvalidateMappedMemoryRanges(device, 1, &range));', '(void)range;'],
  'no-fence-wait' => ['result = vkWaitForFences(device, 1, &fence, VK_TRUE, WAIT_NS);', 'result = VK_SUCCESS;'],
  'wrong-host-barrier' => ['barrier.dstAccessMask = VK_ACCESS_HOST_READ_BIT;', 'barrier.dstAccessMask = VK_ACCESS_HOST_WRITE_BIT;']
}
mutants.each do |name, (from, to)|
  abort 'Mutation anchor must be unique: ' + name unless source.scan(from).size == 1
  path = work + '/' + name
  FileUtils.mkdir_p(path)
  File.write(path + '/powervr-compute.c', source.sub(from, to))
  run.call(name + '-compile', compile.call(path, path + '/check'), true)
  run.call(name, [path + '/check'], false)
end
inputs = [owner + '/powervr-compute.c', owner + '/powervr-compute.spvasm', fixture, __FILE__, headers + '/vulkan/vulkan_core.h', tools + '/bin/spirv-as', tools + '/bin/spirv-val']
File.write(work + '/receipt.json', JSON.pretty_generate({schema: 'ember-powervr-compute-contract-1', commands: commands,
  inputs: inputs.to_h { |p| [p, Digest::SHA256.file(p).hexdigest] }, mutants: mutants.keys,
  shader_sha256: Digest::SHA256.file(work + '/compute.spv').hexdigest,
  scope: 'Actual C consumer with modeled Vulkan calls; SPIR-V validation; no physical GPU execution.'}) + "\n")
puts 'PASS: five causal mutants failed at runtime'
