#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted). Exercise the actual C consumer.
require 'fileutils'
require 'json'
require 'digest'
require 'open3'
require 'shellwords'
abort 'usage: powervr-offscreen.rb VULKAN_HEADERS SPIRV_TOOLS NEW_WORK' unless ARGV.size == 3
headers, tools = ARGV.first(2).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'Use a new absolute output directory' unless ARGV.last.start_with?('/') && !File.exist?(work)
FileUtils.mkdir_p(work)
owner = File.realpath(__dir__ + '/../cross')
fixture = __dir__ + '/powervr-offscreen.c'
commands = []
run = lambda do |name, argv, success|
  commands << argv
  out, err, status = Open3.capture3(*argv)
  File.write(work + '/' + name + '.stdout', out)
  File.write(work + '/' + name + '.stderr', err)
  File.write(work + '/' + name + '.command', Shellwords.join(argv) + "\n")
  abort "Unexpected #{name} result: #{status.inspect}" unless !!status.success? == success
  abort "Mutant did not reach a contract assertion: #{name}" if !success && !err.include?('FAIL ')
  puts out.lines.last if success && name == 'check'
end
header = ''
shaders = %w[vertex fragment].map do |stage|
  path = owner + '/powervr-offscreen-' + stage + '.spvasm'
  run.call(stage + '-assemble', [tools + '/bin/spirv-as', '--target-env', 'vulkan1.2', path, '-o', work + '/' + stage + '.spv'], true)
  run.call(stage + '-validate', [tools + '/bin/spirv-val', '--target-env', 'vulkan1.2', work + '/' + stage + '.spv'], true)
  bytes = File.binread(work + '/' + stage + '.spv')
  abort 'Invalid shader word stream' unless bytes.size >= 20 && bytes.size % 4 == 0 && bytes.unpack1('V') == 0x07230203
  header += "static const uint32_t #{stage}_shader[] = {\n" + bytes.unpack('V*').map { |n| format('0x%08xU,', n) }.join("\n") + "\n};\n"
  path
end
File.write(work + '/powervr-offscreen-shaders.h', header)
flags = %w[-std=c11 -O1 -g -Wall -Wextra -Werror]
flags += %w[-fsanitize=address,undefined -fno-omit-frame-pointer] if ENV['SANITIZERS'] == 'yes'
cc = Shellwords.split(ENV.fetch('CC', 'cc'))
compile = lambda { |dir, binary| cc + flags + ['-I' + headers, '-I' + dir, '-I' + work, fixture, '-o', binary] }
run.call('compile', compile.call(owner, work + '/check'), true)
run.call('check', [work + '/check'], true)
source = File.read(owner + '/powervr-offscreen.c')
mutants = {
  'wrong-node' => ['drm.renderMinor != (int64_t)minor(expected)', 'false'],
  'readback' => ['bytes[i] != expected', 'false'],
  'no-invalidate' => ['TRY(vkInvalidateMappedMemoryRanges(device, 1, &range));', '(void)range;'],
  'no-fence-wait' => ['result = vkWaitForFences(device, 1, &fence, VK_TRUE, WAIT_NS);', 'result = VK_SUCCESS;'],
  'wrong-host-barrier' => ['buffer_barrier.dstAccessMask = VK_ACCESS_HOST_READ_BIT;', 'buffer_barrier.dstAccessMask = VK_ACCESS_HOST_WRITE_BIT;'],
  'wrong-row-stride' => ['.bufferRowLength = ROW_PIXELS,', '.bufferRowLength = WIDTH,'],
  'missing-triangle' => ['vkCmdDraw(command, 3, 1, 0, 0);', '(void)pipeline;'],
  'wrong-triangle-oracle' => ['2U * x > y && 2U * x + y < 4U * WIDTH', '2U * x > y && 2U * x + y < 3U * WIDTH']
}
mutants.each do |name, (from, to)|
  abort 'Mutation anchor must be unique: ' + name unless source.scan(from).size == 1
  path = work + '/' + name; FileUtils.mkdir_p(path)
  File.write(path + '/powervr-offscreen.c', source.sub(from, to))
  run.call(name + '-compile', compile.call(path, path + '/check'), true)
  run.call(name, [path + '/check'], false)
end
inputs = [owner + '/powervr-offscreen.c', *shaders, fixture, __FILE__, headers + '/vulkan/vulkan_core.h', tools + '/bin/spirv-as', tools + '/bin/spirv-val']
File.write(work + '/receipt.json', JSON.pretty_generate({schema: 'ember-powervr-offscreen-contract-1', commands: commands,
  inputs: inputs.to_h { |p| [p, Digest::SHA256.file(p).hexdigest] }, mutants: mutants.keys,
  shaders: %w[vertex fragment].to_h { |s| [s, Digest::SHA256.file(work + '/' + s + '.spv').hexdigest] },
  scope: 'Actual C consumer with modeled Vulkan calls and independent pixel data; SPIR-V validation. No shader execution, physical GPU, or driver acceptance.'}) + "\n")
puts 'PASS: eight causal mutants reached contract assertions'
