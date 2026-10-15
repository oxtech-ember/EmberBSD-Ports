# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Expand the canonical libtool PLIST entry.
require 'find'
component, recipe, stage, receipt = ARGV
abort 'Usage: check-plist.rb png|jpeg RECIPE STAGE_PREFIX RECEIPT' unless receipt
expected = File.readlines(File.join(recipe, 'PLIST'), chomp: true).reject { |line| line.start_with?('@comment') || line.empty? }
if component == 'png'
  text = File.read(File.join(stage, 'lib/libpng16.la'))
  libraries = text[/^library_names='([^']*)'/, 1].split
  archive = text[/^old_library='([^']*)'/, 1]
  expected.concat((libraries + [archive]).map { |name| "lib/#{name}" })
elsif component != 'jpeg'
  abort 'Unknown codec'
end
actual = []
Find.find(stage) { |path| actual << path.delete_prefix(stage + '/') if File.file?(path) || File.symlink?(path) }
missing = expected.uniq.sort - actual.uniq.sort
extra = actual.uniq.sort - expected.uniq.sort
abort "PLIST mismatch: missing=#{missing.inspect}; extra=#{extra.inspect}" unless missing.empty? && extra.empty?
File.write(receipt, actual.uniq.sort.join("\n") + "\n")
puts "PASS #{component}: #{actual.uniq.length} files match the canonical PLIST"
