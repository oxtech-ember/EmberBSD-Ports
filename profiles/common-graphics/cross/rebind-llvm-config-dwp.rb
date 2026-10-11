#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD. Preserve the verified upstream metadata executable across
# the accepted 23.1.2 -> 23.1.2nb1 DWP-only package update; not a generic reseal.
require 'digest'
require 'fileutils'
require 'json'

OLD_LIBRARY = '42231ed6dbaf213a3a391dff50eb51986b0c8fbb8cff8821c42fa07fbc84b1e6'
NEW_LIBRARY = '59486085a768044e0f1940a067f24be4149c420078ae496972bbea303b7b2eb7'
PACKAGE = 'e677db8bb4a579fc697651025ad3cbdcb27345f56a062f64cac88ac3d259397c'

def digest(path)
  abort "missing regular file: #{path}" unless File.file?(path)
  Digest::SHA256.file(path).hexdigest
end

abort 'usage: rebind-llvm-config-dwp.rb SEALED_TOOL MANIFEST_SHA256 LLVM_NB1_PACKAGE NEW_WORK' unless ARGV.size == 4
source, anchor, package, output = ARGV
abort 'absolute paths required' unless [source, package, output].all? { |p| p.start_with?('/') }
abort 'output already exists' if File.exist?(output) || File.symlink?(output)
source = File.realpath(source)
abort 'output must be outside input' if File.expand_path(output).start_with?(source + '/')
manifest = File.read(source + '/inputs.sha256')
abort 'original manifest anchor mismatch' unless anchor.match?(/\A[0-9a-f]{64}\z/) && Digest::SHA256.hexdigest(manifest) == anchor
abort 'not the accepted LLVM DWP package' unless digest(package) == PACKAGE
entries = manifest.lines.map do |line|
  match = line.match(/\A([0-9a-f]{64})  (.+)\n\z/) or abort 'invalid manifest entry'
  [match[1], match[2]]
end
abort 'duplicate manifest entries' unless entries.map(&:last).uniq.size == entries.size
library = entries.select { |_, p| p.start_with?('/') && p.end_with?('/usr/pkg/lib/libLLVM-23.so') }
abort 'missing unique old library binding' unless library.size == 1 && library[0][0] == OLD_LIBRARY
%w[bin/llvm-config bin/llvm-config.real receipt.json seal.json metadata/BuildVariables.inc metadata/LibraryDependencies.inc metadata/ExtensionDependencies.inc].each do |name|
  abort "missing sealed input: #{name}" unless entries.any? { |_, p| p == name }
end
entries.each do |expected, path|
  absolute = path.start_with?('/') ? path : File.expand_path(path, source)
  abort 'relative input escapes tool directory' unless path.start_with?('/') || absolute.start_with?(source + '/')
  expected = NEW_LIBRARY if path == library[0][1]
  abort "changed input: #{path}" unless digest(absolute) == expected
end
# The accepted package changes only DWP objects and the shared library. Its
# recorded ABI/configuration graph, installed headers and interpreter remain
# covered by the unchanged original manifest. Never substitute query answers.
FileUtils.cp_r(source, output, preserve: true)
File.write(output + '/pre-dwp-inputs.sha256', manifest)
FileUtils.cp(__FILE__, output + '/rebind-llvm-config-dwp.rb')
receipt = {scope: 'Accepted LLVM 23.1.2nb1 DWP-only metadata rebinding',
  original_manifest_sha256: anchor, package_sha256: PACKAGE,
  old_library_sha256: OLD_LIBRARY, library_sha256: NEW_LIBRARY,
  library: library[0][1], proof: 'profiles/common-build-tools/cross/llvm-dwp-tests.md',
  unchanged_inputs: entries.reject { |_, p| p == library[0][1] }.to_h { |sha, path| [path, sha] }}
File.write(output + '/dwp-rebind.json', JSON.pretty_generate(receipt) + "\n")
entries.find { |_, p| p == library[0][1] }[0] = NEW_LIBRARY
%w[pre-dwp-inputs.sha256 rebind-llvm-config-dwp.rb dwp-rebind.json].each do |name|
  entries << [digest(output + '/' + name), name]
end
File.write(output + '/inputs.sha256', entries.map { |sha, p| "#{sha}  #{p}\n" }.join)
puts 'PASS: accepted DWP package/library and all original metadata inputs verified'
