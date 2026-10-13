# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EmberBSD contributors. AI-assisted validation.
require 'digest'
require 'json'

module Idfwdf
  UPSTREAM_HEADER = '329700660db533589188cf6610cb0641ba181292eda65f57fe73ace7e1f2ff46'.freeze
  OLD_ADDRESS = "   PVR_IDFWDF_DATA_ADDR_LO,\n".freeze
  NEW_ADDRESS = "   /* The sampler occupies four shared-register dwords. */\n   PVR_IDFWDF_DATA_ADDR_LO = 8,\n".freeze

  def self.patched_header(path)
    text = File.read(path)
    original = text.sub(NEW_ADDRESS, OLD_ADDRESS)
    raise 'unrecognized Mesa 26.2.4 shared header' unless Digest::SHA256.hexdigest(original) == UPSTREAM_HEADER
    original.sub(OLD_ADDRESS, NEW_ADDRESS)
  end

  def self.file_record(path)
    { 'path' => File.realpath(path), 'sha256' => Digest::SHA256.file(path).hexdigest }
  end

  def self.verify_file(entry)
    raise 'missing artifact provenance' unless entry.is_a?(Hash) && entry['path'].is_a?(String) && entry['sha256'].is_a?(String)
    path = File.realpath(entry['path'])
    raise "artifact hash mismatch: #{path}" unless Digest::SHA256.file(path).hexdigest == entry['sha256']
    path
  end

  # Inspect compiler IR from spirv-dis. Names identify the original intrinsic.
  # Register numbers and constant IDs come from the actual module.
  def self.check_spirv(text)
    names = text.scan(/OpName\s+(%\S+)\s+"([^"]+)"/).to_h
    constants = text.scan(/(%\S+)\s+=\s+OpConstant\s+%\S+\s+(\d+)/).to_h.transform_values(&:to_i)
    impl = names.key('__clang_ocl_kern_imp_cs_idfwdf_common')
    raise 'IDFWDF implementation missing' unless impl
    body = text[/^#{Regexp.escape(impl)}\s+=\s+OpFunction\b.*?OpFunctionEnd/m]
    raise 'IDFWDF function body missing' unless body
    scalar = []
    vector = []
    body.scan(/OpFunctionCall\s+%\S+\s+(%\S+)\s+(%\S+)\s+(%\S+)/).each do |callee, slot, offset|
      next unless %w[nir_load_preamble__1 nir_load_preamble__4].include?(names[callee])
      raise 'nonconstant or nonzero shared-register offset' unless constants[offset] == 0 && constants.key?(slot)
      (names[callee] == 'nir_load_preamble__1' ? scalar : vector) << constants[slot]
    end
    raise "old or unknown IDFWDF scalar layout: #{scalar.inspect}" unless scalar == [8, 9]
    raise "unknown IDFWDF descriptors: #{vector.inspect}" unless vector == [0, 4]
    { 'scalar_slots' => scalar, 'vector_slots' => vector, 'layout_dwords' => 10 }
  end

  SHADER_NAMES = {
    'probe' => 'cs_probe_store_0_common',
    'store' => 'cs_store_sr_1024_common_0_common',
    'load' => 'cs_load_sr_256_common_0_common',
    'idfwdf' => 'cs_idfwdf_common_0_common'
  }.freeze

  def self.shaders(table)
    SHADER_NAMES.transform_values do |symbol|
      match = table.match(/static const uint32_t #{symbol}\[(\d+)\] = \{(.*?)\};/m)
      raise "missing #{symbol}" unless match
      words = match[2].scan(/0x[0-9a-fA-F]+/)
      raise "word count mismatch in #{symbol}" unless words.size == match[1].to_i
      words.map { |word| word.to_i(16) }.pack('V*')
    end
  end

  # Check the real SPIR-V control-flow edge and the single global store.
  # Reject new compiler shapes until this bounded proof can model them.
  def self.check_probe(text)
    names = text.scan(/OpName\s+(%\S+)\s+"([^"]+)"/).to_h
    constants = text.scan(/(%\S+)\s+=\s+OpConstant\s+%\S+\s+(\d+)/).to_h.transform_values(&:to_i)
    impl = names.key('__clang_ocl_kern_imp_cs_probe_store')
    raise 'bounded store implementation missing' unless impl
    body = text[/^#{Regexp.escape(impl)}\s+=\s+OpFunction\b.*?OpFunctionEnd/m]
    raise 'bounded store body missing' unless body
    defs = {}; writes = {}; edges = {}; stores = []; dma = []; terminals = {}; locations = {}; branches = []
    block = nil; entry = nil
    pure = %w[OpFunction OpLabel OpVariable OpLoad OpINotEqual OpFunctionCall OpCompositeConstruct OpCompositeInsert OpVectorShuffle OpBitcast]
    body.each_line.with_index do |line, position|
      line = line.strip
      if (match = line.match(/^(%\S+) = (Op\w+)(.*)$/))
        id, op, rest = match.captures
        raise "unsupported probe operation: #{op}" unless pure.include?(op)
        if op == 'OpLabel'
          raise 'unterminated basic block' if block && !terminals[block]
          block = id; entry ||= id; edges[id] = []
        elsif op != 'OpFunction'
          raise 'instruction outside a live block' unless block && !terminals[block]
        end
        args = rest.split
        if op == 'OpFunctionCall'
          callee = names[args[1]]
          raise 'unbounded probe function call' unless %w[nir_load_instance_num_pco nir_dma_st_pco__1].include?(callee)
          dma << [block, args[2], args[3]] if callee == 'nir_dma_st_pco__1'
        end
        raise 'nonlocal probe variable' if op == 'OpVariable' && args[1] != 'Function'
        defs[id] = [op, args]; locations[id] = [block, position]
      elsif line.start_with?('OpStore ')
        raise 'store outside a live block' unless block && !terminals[block]
        args = line.split
        writes[args[1]] ||= []
        writes[args[1]] << [args[2], block, position]
        stores << [block, args[1], args[2]]
      elsif line.start_with?('OpBranchConditional ', 'OpBranch ') || line == 'OpReturn'
        raise 'terminator outside a live block' unless block && !terminals[block]
        args = line.split
        edges[block] = args[0] == 'OpBranchConditional' ? args[2, 2] : args[0] == 'OpBranch' ? [args[1]] : []
        branches << [block, args[1], args[2], args[3]] if args[0] == 'OpBranchConditional'
        terminals[block] = true
      elsif line.start_with?('OpSelectionMerge ')
        raise 'merge outside a live block' unless block && !terminals[block]
      elsif line != 'OpFunctionEnd'
        raise "unsupported probe instruction: #{line}"
      end
    end
    raise 'unterminated final block' unless block && terminals[block]
    raise 'branch target missing' unless edges.values.flatten.all? { |target| edges.key?(target) }
    visited = []
    acyclic = lambda do |current, path|
      raise 'probe contains a loop' if path.include?(current)
      return if visited.include?(current)
      edges.fetch(current).each { |target| acyclic.call(target, path + [current]) }
      visited << current
    end
    acyclic.call(entry, [])
    instance = defs.find { |_, (op, a)| op == 'OpFunctionCall' && names[a[1]] == 'nir_load_instance_num_pco' }&.first
    compare = defs.find { |_, (op, a)| op == 'OpINotEqual' && a[1] == instance && constants[a[2]] == 0 }&.first
    raise 'explicit nonzero-instance guard missing' unless instance && compare
    branch = branches.find { |_, condition, _, _| condition == compare }
    raise 'instance guard does not control a branch' unless branch
    guard_block, _, reject_edge, accept_edge = branch
    composites = text.scan(/(%\S+)\s+=\s+OpConstantComposite\s+(%\S+)\s+([^\n]+)/).to_h { |id, type, values| [id, [type, values.split]] }
    undef_types = text.scan(/(%\S+)\s+=\s+OpUndef\s+(%\S+)/).to_h
    vector_types = text.scan(/(%\S+)\s+=\s+OpTypeVector\s+(%\S+)\s+(\d+)/).to_h { |id, component, count| [id, [component, count.to_i]] }
    integer_widths = text.scan(/(%\S+)\s+=\s+OpTypeInt\s+(\d+)\s+[01]/).to_h
    pointer_types = text.scan(/(%\S+)\s+=\s+OpTypePointer\s+(\w+)\s+(%\S+)/).to_h { |id, storage, type| [id, [storage, type]] }
    local_pointer = lambda do |id, seen = []|
      raise 'cyclic local pointer' if seen.include?(id)
      op, args = defs[id]
      raise 'unsupported local pointer' unless args
      storage, type = pointer_types[args[0]]
      raise 'nonlocal pointer type' unless storage == 'Function'
      if op == 'OpVariable'
        raise 'nonlocal variable' unless args[1] == 'Function'
        id
      elsif op == 'OpBitcast'
        source_type = pointer_types.fetch(defs.fetch(args[1])[1][0])
        src_component, src_count = vector_types[source_type[1]]
        dst_component, dst_count = vector_types[type]
        unless source_type[0] == 'Function' && src_component == dst_component &&
            integer_widths[src_component] == '32' && [3, 4].include?(src_count) && [3, 4].include?(dst_count)
          raise 'unsupported local vector pointer cast'
        end
        local_pointer.call(args[1], seen + [id])
      else
        raise 'unsupported local pointer expression'
      end
    end
    local_writes = {}
    stores.each do |stored_block, dst, value|
      variable = local_pointer.call(dst)
      local_writes[variable] ||= []
      writes.fetch(dst).each { |entry| local_writes[variable] << entry unless local_writes[variable].include?(entry) }
    end
    evaluate = lambda do |id, seen = []|
      raise 'cyclic constant expression' if seen.include?(id)
      return constants[id] if constants.key?(id)
      recurse = ->(child) { evaluate.call(child, seen + [id]) }
      if composites.key?(id)
        return composites[id][1].map { |child| recurse.call(child) }
      end
      return Array.new(vector_types.fetch(undef_types[id])[1]) if undef_types.key?(id)
      op, args = defs[id]
      case op
      when 'OpLoad'
        values = local_writes[local_pointer.call(args[1])]
        raise 'nonconstant probe local' unless values&.size == 1
        value, written_block, written_at = values.first
        loaded_block, loaded_at = locations.fetch(id)
        raise 'probe local write does not precede its load' unless written_block == loaded_block && written_at < loaded_at
        vector = recurse.call(value)
        component, width = vector_types[args[0]]
        unless vector.is_a?(Array) && integer_widths[component] == '32' && [2, 3, 4].include?(width)
          raise 'unsupported local load type'
        end
        Array.new(width) { |index| vector[index] }
      when 'OpCompositeConstruct'
        args[1..].flat_map { |child| recurse.call(child) }
      when 'OpCompositeInsert'
        vector = recurse.call(args[2]).dup
        index = Integer(args[3], 10)
        raise 'unsupported composite insertion' unless args.size == 4 && vector.is_a?(Array) && index >= 0 && index < vector.size
        vector[index] = recurse.call(args[1])
        vector
      when 'OpVectorShuffle'
        vector = recurse.call(args[1]) + recurse.call(args[2])
        args[3..].map do |index|
          index = Integer(index, 10)
          next nil if index == 0xffffffff # SPIR-V undefined component; never a proven DMA argument.
          raise 'unsupported shuffle index' unless index >= 0 && index < vector.size
          vector[index]
        end
      else
        raise 'nonconstant DMA store argument'
      end
    end
    raise 'probe must have one DMA dword store' unless dma.size == 1
    target_block, data, flags = dma.first
    data_type = composites[data]&.first || defs[data]&.last&.first
    component, width = vector_types[data_type]
    raise 'DMA store is not three 32-bit dwords' unless width == 3 && integer_widths[component] == '32'
    raise 'wrong DMA output or flags' unless evaluate.call(data) == [0, 0x80, 0x13579bdf] && constants[flags] == 0
    reachable = lambda do |from, removed = nil|
      pending = [from]; seen = []
      until pending.empty?
        current = pending.pop
        next if seen.include?(current)
        seen << current
        edges.fetch(current, []).each { |to| pending << to unless removed == [current, to] }
      end
      seen
    end
    raise 'nonzero lane can reach the output' if reachable.call(reject_edge).include?(target_block)
    raise 'zero lane cannot reach the output' unless reachable.call(accept_edge).include?(target_block)
    raise 'output bypasses the lane guard' if reachable.call(entry, [guard_block, accept_edge]).include?(target_block)
    { 'instance' => 0, 'address' => '0x8000000000', 'value' => '0x13579bdf', 'bytes' => 4 }
  end

  def self.verify_receipt(path, table = nil)
    receipt = JSON.parse(File.read(path))
    raise 'unverified shader ABI receipt' unless receipt['schema'] == 'ember-pco-usclib-v1' &&
      receipt['idfwdf'] == { 'scalar_slots' => [8, 9], 'vector_slots' => [0, 4], 'layout_dwords' => 10 }
    files = receipt.fetch('files')
    files.each_value { |entry| verify_file(entry) }
    raise 'generated table differs from compiler receipt' if table && File.realpath(table) != verify_file(files.fetch('programs'))
    text = File.read(verify_file(files.fetch('spirv_text')))
    check_spirv(text)
    raise 'probe proof mismatch' unless receipt['probe'] == check_probe(text)
    header = File.read(verify_file(files.fetch('shared_header')))
    raise 'compiler header is not the shared patched ABI' unless header == patched_header(files.fetch('shared_header').fetch('path'))
    receipt
  end
end
