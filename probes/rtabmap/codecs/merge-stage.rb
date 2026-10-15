# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Refuse to overwrite an unrelated provider.
require 'fileutils'
require 'find'
require 'digest'
source, target, receipt = ARGV
abort 'Usage: merge-stage.rb STAGE_PREFIX TARGET_PREFIX RECEIPT' unless receipt
entries = []
Find.find(source) { |path| entries << path.delete_prefix(source + '/') unless path == source || File.directory?(path) }
entries.each do |relative|
  from = File.join(source, relative)
  to = File.join(target, relative)
  next unless File.exist?(to) || File.symlink?(to)
  identical = if File.symlink?(from) && File.symlink?(to)
                File.readlink(from) == File.readlink(to)
              elsif File.file?(from) && File.file?(to) && !File.symlink?(from) && !File.symlink?(to)
                Digest::SHA256.file(from).hexdigest == Digest::SHA256.file(to).hexdigest
              else
                false
              end
  abort "Refusing to replace existing provider file: #{to}" unless identical
end
entries.each do |relative|
  from = File.join(source, relative)
  to = File.join(target, relative)
  next if File.exist?(to) || File.symlink?(to)
  FileUtils.mkdir_p(File.dirname(to))
  File.symlink?(from) ? File.symlink(File.readlink(from), to) : FileUtils.copy_file(from, to, true)
end
File.write(receipt, entries.sort.join("\n") + "\n")
