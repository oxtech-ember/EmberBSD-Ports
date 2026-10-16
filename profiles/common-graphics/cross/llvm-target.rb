# SPDX-License-Identifier: BSD-2-Clause
# Validate generated LLVM target facts. This never supplies query answers.
require 'json'

module EmberGraphicsLLVM
  module_function

  def for_processor(processor)
    case processor
    when 'aarch64' then {processor: processor, backend: 'aarch64', machine: 183}
    when 'x86_64' then {processor: processor, backend: 'x86', machine: 62}
    else raise ArgumentError, 'target must be configured for NetBSD/aarch64 or NetBSD/x86_64'
    end
  end

  def for_triple(triple)
    match = triple.to_s.match(/\A(aarch64|x86_64)-(?:unknown)?-netbsd(?:11(?:\.[0-9]+)*)?\z/)
    raise ArgumentError, 'unsupported NetBSD LLVM target triple' unless match
    for_processor(match[1])
  end

  def validate(cache, definitions, components)
    raise ArgumentError, 'target must be configured for NetBSD/aarch64 or NetBSD/x86_64' unless cache['CMAKE_SYSTEM_NAME'] == 'NetBSD'
    if cache.key?('CMAKE_SYSTEM_VERSION') && !cache['CMAKE_SYSTEM_VERSION'].match?(/\A11(?:\.[0-9]+)*\z/)
      raise ArgumentError, 'target metadata must use the NetBSD 11 ABI'
    end
    spec = for_processor(cache['CMAKE_SYSTEM_PROCESSOR'])
    %w[LLVM_HOST_TRIPLE LLVM_DEFAULT_TARGET_TRIPLE].each do |key|
      triple = JSON.parse(definitions.fetch(key))
      raise ArgumentError, "inconsistent or non-NetBSD target #{key}" unless triple == cache[key] && for_triple(triple) == spec
    end
    names = %w[bitwriter engine mcdisassembler mcjit core executionengine scalaropts transformutils instcombine native orcjit] + [spec.fetch(:backend)]
    names.each do |name|
      raise ArgumentError, "missing target LLVM component: #{name}" unless components.match?(/\{ "#{Regexp.escape(name)}",/)
    end
    backend = Regexp.escape(spec.fetch(:backend))
    raise ArgumentError, 'native LLVM component disagrees with target processor' unless components.match?(/\{ "native", nullptr, true, \{"#{backend}"\} \}/)
    spec
  rescue KeyError, JSON::ParserError => error
    raise ArgumentError, "invalid generated LLVM target metadata: #{error.message}"
  end

  def validate_elf(header, spec)
    unless header && header.bytesize >= 20 && header.byteslice(0, 6) == "\x7fELF\x02\x01".b && header.byteslice(16, 4).unpack('v2') == [3, spec.fetch(:machine)]
      raise ArgumentError, 'LLVM library is not shared little-endian ELF64 for the selected target'
    end
    true
  end
end
