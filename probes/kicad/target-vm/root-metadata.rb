# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Keep private staging permissions out of the guest root.
module QueryVmRootMetadata
  def self.image_root(source_etc, tools, &run)
    source = source_etc + '/mtree/NetBSD.dist.base'
    roots = File.readlines(source).reject { |line| line.lstrip.start_with?('#') }
                .count { |line| line.split.first == '.' }
    raise ArgumentError, 'Expected one root declaration in the pinned fork mtree source' unless roots == 1
    flat = run.call('root-metadata', tools + '/nbmtree', '-C', '-N', source_etc, '-f', source)
    records = flat.lines.select { |line| line.split.first == '.' }
    expected = %w[type=dir uid=0 gid=0 mode=0755].sort
    unless records.size == 1 && records.first.split.drop(1).sort == expected
      raise ArgumentError, 'Pinned fork root must resolve to root:wheel (0:0), directory mode 0755'
    end
    records.first.chomp + "\n"
  end
end
