# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); authenticated link-only runtime hardening.
require_relative 'inheritance'
module GCC16Runtime
  module Relro
    COMPONENTS = {'libgcc' => 'libgcc_s.so.1', 'libgomp' => 'libgomp.so.1.0', 'libatomic' => 'libatomic.so.3.0'}.freeze
    PARENT = %w[inputs.txt stage.sha256 stage.symlinks build-success inheritance.json].freeze
    module_function

    def verify(work, pkgsrc, archive, current, expected_source: SOURCE_SHA256)
      file = work + '/relink.json'
      receipt = JSON.parse(File.read(file))
      raise Invalid, 'Unknown relink format' unless receipt.fetch('format') == 1
      raise Invalid, 'Relink receipt is not pinned' unless File.readlines(work + '/inputs.txt').count("#{Inheritance.hash(file)}  #{file}\n") == 1
      parent_work = File.realpath(receipt.fetch('parent_work'))
      raise Invalid, 'Expected the original completed libstdc++ rebuild' unless File.read(parent_work + '/build-success') == "runtime-libstdcxx-rebuild\n"
      PARENT.each do |name|
        raise Invalid, 'Relink parent receipt changed' unless Inheritance.hash(parent_work + '/' + name) == receipt.fetch('parent_receipts').fetch(name)
      end
      parent = Stage.new(parent_work, pkgsrc, archive, expected_source: expected_source, historical: true).verify
      %w[GCC_RUNTIME_TARGET GCC_RUNTIME_TRIPLET GCC_RUNTIME_LIBRARIES EMBERBSD_SEED_SOURCE].each do |key|
        raise Invalid, 'Relink parent identity changed' unless current[:metadata][key] == parent[:metadata][key]
      end
      backup = receipt.fetch('backup')
      raise Invalid, 'Archived build changed' unless Inheritance.hash(backup.fetch('path')) == backup.fetch('sha256')
      receipt.fetch('inputs').each do |path, sha|
        raise Invalid, 'Relink input changed' unless Inheritance.hash(path) == sha
      end
      old = Inheritance.inventory(parent_work + '/stage')
      expected = old.dup
      commands = JSON.parse(File.read(work + '/commands.json'))
      raise Invalid, 'Unexpected relink component set' unless receipt.fetch('components').keys.sort == COMPONENTS.keys.sort
      COMPONENTS.each do |library, basename|
        relative = 'usr/pkg/gcc16/lib/' + basename
        record = receipt.fetch('components').fetch(library)
        raise Invalid, 'Wrong relink path or original bytes' unless record.fetch('path') == relative && record.fetch('before') == old.fetch(relative).fetch('sha256')
        before = work + '/proof/' + basename + '.baseline'
        after = work + '/proof/' + basename + '.relro'
        raise Invalid, 'Baseline did not reproduce the accepted DSO' unless Inheritance.hash(before) == record.fetch('before')
        raise Invalid, 'Relink output changed or retained old bytes' unless Inheritance.hash(after) == record.fetch('after') && record['after'] != record['before']
        pair = commands.select { |item| item.fetch('component') == library }
        raise Invalid, 'Missing real baseline/final commands' unless pair.size == 2 && pair.map { |item| item.fetch('status') } == [0, 0]
        argv = pair.first.fetch('argv').dup
        index = argv.index('-o')
        raise Invalid, 'Wrong baseline output' unless index && argv[index + 1] == before
        argv[index + 1] = after
        raise Invalid, 'Unexpected link transformation' unless pair.last.fetch('argv') == argv + ['-Wl,-z,relro']
        expected[relative] = old.fetch(relative).merge('sha256' => record.fetch('after'))
      end
      raise Invalid, 'Relink changed an unowned stage file' unless Inheritance.inventory(work + '/stage') == expected
      {'GCC_RUNTIME_BUILD_MODE' => 'libstdcxx-and-runtime-relro-relink',
       'GCC_RUNTIME_RELINK_SHA256' => Inheritance.hash(file),
       'GCC_RUNTIME_LOCALE_INPUTS_SHA256' => receipt['parent_receipts']['inputs.txt']}
    rescue KeyError, JSON::ParserError => e
      raise Invalid, "Invalid relink receipt: #{e.message}"
    end
  end
end
