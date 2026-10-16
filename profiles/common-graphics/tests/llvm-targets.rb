#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Exercise generated target metadata and ELF-header guards without LLVM builds.
require 'json'
require_relative '../cross/llvm-target'

def check(name)
  abort "FAIL: #{name}" unless yield
  puts "PASS: #{name}"
end

def reject(name)
  yield
  abort "FAIL: accepted #{name}"
rescue ArgumentError
  puts "PASS: rejects #{name}"
end

%w[aarch64 x86_64].each do |cpu|
  triple = "#{cpu}-unknown-netbsd"
  backend, elf_machine = cpu == 'aarch64' ? ['aarch64', 183] : ['x86', 62]
  cache = {'CMAKE_SYSTEM_NAME' => 'NetBSD', 'CMAKE_SYSTEM_PROCESSOR' => cpu,
           'LLVM_HOST_TRIPLE' => triple, 'LLVM_DEFAULT_TARGET_TRIPLE' => triple}
  definitions = cache.select { |key, _| key.start_with?('LLVM_') }.transform_values { |value| JSON.generate(value) }
  components = (%w[bitwriter engine mcdisassembler mcjit core executionengine scalaropts transformutils instcombine native orcjit] + [backend]).map { |name| "{ \"#{name}\", nullptr, true, {\"#{name == 'native' ? backend : ''}\"} }" }.join("\n")
  spec = EmberGraphicsLLVM.validate(cache, definitions, components)
  check("#{cpu} metadata binds its own native backend") { spec.fetch(:backend) == backend && spec.fetch(:machine) == elf_machine }
  header = "\x7fELF\x02\x01".b.ljust(16, "\0") + [3, elf_machine].pack('v2')
  check("#{cpu} target DSO header accepted") { EmberGraphicsLLVM.validate_elf(header, spec) }
  reject("#{cpu} mixed ELF architecture") { EmberGraphicsLLVM.validate_elf(header[0, 18] + [cpu == 'aarch64' ? 62 : 183].pack('v'), spec) }
  reject("#{cpu} mixed generated triple") { EmberGraphicsLLVM.validate(cache, definitions.merge('LLVM_HOST_TRIPLE' => JSON.generate('riscv64-unknown-netbsd')), components) }
  reject("#{cpu} foreign target OS") { EmberGraphicsLLVM.validate(cache.merge('CMAKE_SYSTEM_NAME' => 'Darwin'), definitions, components) }
  reject("#{cpu} wrong native backend") { EmberGraphicsLLVM.validate(cache, definitions, components.sub("{\"#{backend}\"}", '{"riscv"}')) }
end
reject('unsupported processor') { EmberGraphicsLLVM.for_processor('riscv64') }
reject('foreign receipt triple') { EmberGraphicsLLVM.for_triple('x86_64-unknown-linux-gnu') }
puts 'PASS: actual target metadata and mixed-architecture guards; no LLVM compilation or runtime acceptance'
