#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). No actual provider is modified by this check.
require 'fileutils'
require 'open3'
abort 'usage: rust-target-paths.rb NEW_WORK' unless ARGV.size == 1
root = File.expand_path(ARGV[0])
abort 'new absolute work required' unless ARGV[0].start_with?('/') && !File.exist?(root)
%w[host tools/bin gcc/bin sysroot build].each { |p| FileUtils.mkdir_p(root + '/' + p) }
File.write(root + '/gcc/bin/aarch64--netbsd-gcc', '# fixture: never executed')
File.symlink('../../gcc/bin/aarch64--netbsd-gcc', root + '/tools/bin/aarch64--netbsd-gcc')
helper = File.expand_path('../../../pkgsrc/lang/rust-std-aarch64-netbsd/files/target-std.sh', __dir__)
call = lambda do |source, work|
  Open3.capture2e('/bin/sh', helper, 'preflight', source, work, root + '/host', root + '/tools', root + '/sysroot')
end
out, status = call.call(root + '/build', root + '/build')
abort "disjoint fixture rejected: #{out}" unless status.success?
%w[host tools gcc sysroot].each do |name|
  path = root + '/' + name + '/must-stay-empty'
  Dir.mkdir(path)
  [path, root + '/' + name].each do |overlap|
    [[overlap, root + '/build'], [root + '/build', overlap]].each do |source, work|
      out, status = call.call(source, work)
      abort "overlap not rejected: #{name}" if status.success? || !out.include?('overlaps an input provider')
      abort "input modified: #{name}" unless Dir.empty?(path)
    end
  end
end
File.symlink(root + '/host', root + '/host-alias')
out, status = call.call(root + '/build', root + '/host-alias/must-stay-empty')
abort 'symlink alias bypassed guard' if status.success? || !out.include?('overlaps an input provider')
out, status = call.call(root + '/build', root)
abort 'nested provider bypassed guard' if status.success? || !out.include?('input provider is inside work/source')
puts 'PASS: disjoint preflight; source/work overlaps, provider roots, GCC facade, symlink alias and nested provider rejected before writes'
