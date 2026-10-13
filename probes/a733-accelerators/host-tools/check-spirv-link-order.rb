#!/usr/bin/env ruby
# SPDX-License-Identifier: MIT
# EmberBSD, AI-assisted. Exercise the real SPIRV-Tools linker and validator.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'

abort 'usage: check-spirv-link-order.rb TOOLS_BIN NEW_OUTPUT [--expect-invalid]' unless
  ARGV.length.between?(2, 3) && (ARGV.length == 2 || ARGV[2] == '--expect-invalid')
tools, output = ARGV.take(2).map { |p| File.expand_path(p) }
expect_invalid = ARGV[2] == '--expect-invalid'
abort 'Output already exists' if File.exist?(output)
names = %w[spirv-as spirv-link spirv-val spirv-dis]
names.each { |n| abort "Missing #{n}" unless File.executable?(File.join(tools, n)) }
FileUtils.mkdir_p(output)
commands = []
run = lambda do |name, *args|
  command = [File.join(tools, name), *args]
  text, status = Open3.capture2e(*command)
  commands << { argv: command, status: status.exitstatus, output: text }
  [text, status.success?]
end
checked = lambda do |name, *args|
  text, ok = run.call(name, *args)
  abort "#{name} failed: #{text}" unless ok
  text
end

make_module = lambda do |imports, definitions|
  all = imports + definitions.keys
  text = "OpCapability Addresses\nOpCapability Linkage\nOpCapability Kernel\n" \
    "OpMemoryModel Physical64 OpenCL\n"
  all.each { |n| text << "OpName %#{n} \"#{n}\"\n" }
  imports.each { |n| text << "OpDecorate %#{n} LinkageAttributes \"#{n}\" Import\n" }
  definitions.each_key { |n| text << "OpDecorate %#{n} LinkageAttributes \"#{n}\" Export\n" }
  text << "%void = OpTypeVoid\n%fn = OpTypeFunction %void\n"
  imports.each { |n| text << "%#{n} = OpFunction %void None %fn\nOpFunctionEnd\n" }
  definitions.each do |n, callee|
    text << "%#{n} = OpFunction %void None %fn\n%label_#{n} = OpLabel\n"
    text << "%call_#{n} = OpFunctionCall %void %#{callee}\n" if callee
    text << "OpReturn\nOpFunctionEnd\n"
  end
  text
end
modules = {
  'a' => make_module.call(%w[ia1 ia2], { 'fa' => 'ia1' }),
  'b' => make_module.call(%w[ib1 ib2], { 'fb' => 'ib2' }),
  'definitions' => make_module.call([], { 'ia1' => nil, 'ia2' => nil, 'ib1' => nil, 'ib2' => nil }),
  'only_imports' => make_module.call(%w[ic1 ic2], {})
}
modules.each do |name, text|
  path = File.join(output, name)
  File.write(path + '.spvasm', text)
  checked.call('spirv-as', '--target-env', 'spv1.3', path + '.spvasm', '-o', path + '.spv')
  checked.call('spirv-val', '--target-env', 'spv1.3', path + '.spv')
end
cases = [
  [%w[a b], %w[ia1 ia2 ib1 ib2 fa fb]],
  [%w[b a], %w[ib1 ib2 ia1 ia2 fb fa]],
  [%w[a only_imports b], %w[ia1 ia2 ic1 ic2 ib1 ib2 fa fb]],
  [%w[a b definitions], %w[fa fb ia1 ia2 ib1 ib2]],
  [%w[definitions], %w[ia1 ia2 ib1 ib2]]
]
invalid = 0
cases.each_with_index do |(inputs, expected), index|
  binary = File.join(output, "linked-#{index}.spv")
  checked.call('spirv-link', '--target-env', 'spv1.3', '--create-library',
    '--allow-partial-linkage', *inputs.map { |n| File.join(output, n + '.spv') }, '-o', binary)
  validation, valid = run.call('spirv-val', '--target-env', 'spv1.3', binary)
  if !valid && expect_invalid && index < 3 &&
      validation.include?('Function declarations must appear before function definitions')
    invalid += 1
    next
  end
  abort "Invalid linked module #{index}: #{validation}" unless valid
  disassembly = checked.call('spirv-dis', '--no-header', '--raw-id', binary)
  File.write(binary + '.txt', disassembly)
  symbols = disassembly.scan(/OpName %(\d+) "([^"]+)"/).to_h
  order = disassembly.scan(/%(\d+) = OpFunction /).flatten.map { |id| symbols.fetch(id) }
  abort "Function order #{order.inspect}, expected #{expected.inspect}" unless order == expected
  if index < 3
    calls = disassembly.scan(/OpFunctionCall %\d+ %(\d+)/).flatten.map { |id| symbols.fetch(id) }
    expected_calls = inputs.reject { |n| n == 'only_imports' }.map { |n| n == 'a' ? 'ia1' : 'ib2' }
    abort 'Imported call targets changed' unless calls == expected_calls
  end
end
abort "Expected three causal validator failures, got #{invalid}" if expect_invalid && invalid != 3
receipt = { expected_invalid: expect_invalid, causal_failures: invalid, cases: cases.length,
  tools: names.to_h { |n| [n, Digest::SHA256.file(File.join(tools, n)).hexdigest] }, commands: commands }
File.write(File.join(output, 'receipt.json'), JSON.pretty_generate(receipt) + "\n")
puts "PASS: #{cases.length} linker order cases; #{invalid} expected baseline failures"
