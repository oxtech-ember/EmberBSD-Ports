#!/usr/bin/env ruby
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EmberBSD contributors. AI-assisted causal contracts.
require 'fileutils'
require 'open3'
require_relative 'layout'
abort 'usage: check-usclib.rb MESA_SOURCE OLD_SPIRV_TEXT NEW_WORK' unless ARGV.size == 3
mesa, old_path, work = ARGV.map { |p| File.expand_path(p) }
abort 'work already exists' if File.exist?(work)
FileUtils.mkdir_p(work)
checks = 0
reject = lambda do |label, &block|
  begin
    block.call
  rescue RuntimeError, KeyError, Errno::ENOENT
    checks += 1
    next
  end
  abort "accepted #{label}"
end
old = File.read(old_path)
reject.call('actual old shader input') { Idfwdf.check_spirv(old) }
impl = old[/^%__clang_ocl_kern_imp_cs_idfwdf_common = OpFunction.*?OpFunctionEnd/m] or abort 'old shader function missing'
fixed_impl = impl.gsub('%uint_5 %uint_0', '%uint_8 %uint_0').gsub('%uint_6 %uint_0', '%uint_9 %uint_0')
fixed = old.sub(impl, fixed_impl)
raise 'wrong fixed offsets' unless Idfwdf.check_spirv(fixed)['scalar_slots'] == [8, 9]
checks += 1
reject.call('one stale address half') { Idfwdf.check_spirv(fixed.sub('%uint_9 %uint_0', '%uint_6 %uint_0')) }
reject.call('missing entry') { Idfwdf.check_spirv('') }
header = Idfwdf.patched_header(mesa + '/src/imagination/common/pvr_iface.h')
File.write(work + '/pvr_iface.h', header)
raise 'patch is not idempotent' unless Idfwdf.patched_header(work + '/pvr_iface.h') == header
checks += 1
File.write(work + '/unknown.h', header + "/* unpinned change */\n")
reject.call('unrecognized shared header') { Idfwdf.patched_header(work + '/unknown.h') }
# This grammar fixture exercises control-flow rejection, not shader generation.
probe = <<~SPV
  OpName %impl "__clang_ocl_kern_imp_cs_probe_store"
  OpName %instance "nir_load_instance_num_pco"
  OpName %dma "nir_dma_st_pco__1"
  %uint = OpTypeInt 32 0
  %ulong = OpTypeInt 64 0
  %v3uint = OpTypeVector %uint 3
  %zero = OpConstant %uint 0
  %value = OpConstant %uint 324508639
  %hi = OpConstant %uint 128
  %data = OpConstantComposite %v3uint %zero %hi %value
  %impl = OpFunction %void DontInline %signature
  %entry = OpLabel
  %lane = OpFunctionCall %uint %instance
  %other = OpINotEqual %bool %lane %zero
  OpBranchConditional %other %reject %accept
  %reject = OpLabel
  OpReturn
  %accept = OpLabel
  %write = OpFunctionCall %void %dma %data %zero
  OpReturn
  OpFunctionEnd
SPV
expected = { 'instance' => 0, 'address' => '0x8000000000', 'value' => '0x13579bdf', 'bytes' => 4 }
raise 'valid lane guard rejected' unless Idfwdf.check_probe(probe) == expected
checks += 1
{
  'unreachable guard with matching edges' => probe.sub(
    "OpBranchConditional %other %reject %accept",
    "%always = OpINotEqual %bool %zero %zero\nOpBranchConditional %always %reject %accept\n%dead = OpLabel\nOpBranchConditional %other %reject %accept"),
  'store loop' => probe.sub("%write = OpFunctionCall %void %dma %data %zero\nOpReturn", "%write = OpFunctionCall %void %dma %data %zero\nOpBranch %accept"),
  'wrong address' => probe.sub('OpConstant %uint 128', 'OpConstant %uint 129'),
  'wrong value' => probe.sub('324508639', '1'),
  'wrong width' => probe.sub('OpTypeVector %uint 3', 'OpTypeVector %ulong 3'),
  'wrong DMA width' => probe.sub('nir_dma_st_pco__1', 'nir_dma_st_pco__2'),
  'generic store' => probe.sub('%write = OpFunctionCall %void %dma %data %zero', 'OpStore %pointer %value Aligned 4'),
  'wrong DMA flags' => probe.sub('%dma %data %zero', '%dma %data %value'),
  'wrong condition' => probe.sub('OpINotEqual', 'OpIEqual'),
  'nonzero comparison' => probe.sub('OpConstant %uint 0', 'OpConstant %uint 1'),
  'missing instance' => probe.sub('nir_load_instance_num_pco', 'some_other_call'),
  'unguarded store' => probe.sub('OpBranchConditional %other %reject %accept', 'OpBranch %accept'),
  'reversed condition' => probe.sub('%other %reject %accept', '%other %accept %reject'),
  'both lanes write' => probe.sub("%reject = OpLabel\nOpReturn", "%reject = OpLabel\nOpBranch %accept"),
  'switch bypass' => probe.sub("%reject = OpLabel\nOpReturn", "%reject = OpLabel\nOpSwitch %lane %accept 0 %accept"),
  'unbounded call' => probe.sub('%write = OpFunctionCall %void %dma %data %zero', "%side = OpFunctionCall %void %unknown\n%write = OpFunctionCall %void %dma %data %zero"),
  'atomic side effect' => probe.sub('%write = OpFunctionCall %void %dma %data %zero', "%side = OpAtomicIAdd %uint %pointer %zero %zero %value\n%write = OpFunctionCall %void %dma %data %zero"),
  'instruction after return' => probe.sub("%reject = OpLabel\nOpReturn", "%reject = OpLabel\nOpReturn\n%unused = OpLoad %uint %pointer"),
  'two stores' => probe.sub('%write = OpFunctionCall %void %dma %data %zero', "%write = OpFunctionCall %void %dma %data %zero\n%write = OpFunctionCall %void %dma %data %zero")
}.each { |label, text| reject.call(label) { Idfwdf.check_probe(text) } }
File.write(work + '/wrong-receipt.json', JSON.generate({ 'idfwdf_layout_dwords' => 10 }))
reject.call('unsubstantiated layout flag') { Idfwdf.verify_receipt(work + '/wrong-receipt.json') }
entry = Idfwdf.file_record(work + '/pvr_iface.h')
raise 'file proof mismatch' unless Idfwdf.verify_file(entry) == File.realpath(work + '/pvr_iface.h')
checks += 1
File.write(work + '/pvr_iface.h', header + "/* stale input */\n")
reject.call('stale artifact') { Idfwdf.verify_file(entry) }
puts "PASS: #{checks} shader ABI, provenance, and bounded-store proof checks; no GPU execution"
