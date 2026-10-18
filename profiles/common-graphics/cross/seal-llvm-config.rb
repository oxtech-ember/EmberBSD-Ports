#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Separate accepted build provenance from use.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'
require_relative 'llvm-target'
require_relative 'llvm-native'

def fail!(message)
  abort "seal-llvm-config: #{message}"
end

def digest(path)
  File.file?(path) ? Digest::SHA256.file(path).hexdigest : nil
end

def safe_path?(path)
  !path.match?(/[\s\x00-\x1f]/) && !path.split('/').include?('..')
end

fail!('usage: seal-llvm-config.rb ACCEPTED_WORK ORIGINAL_MANIFEST_SHA256 NEW_WORK') unless ARGV.length == 3
old, expected, work = ARGV
fail!('absolute work directories required') unless [old, work].all? { |p| p.start_with?('/') && safe_path?(p) }
old = File.realpath(old)
work = File.expand_path(work)
fail!('NEW_WORK must not exist or be inside ACCEPTED_WORK') if File.exist?(work) || work.start_with?(old + '/')
manifest_path = "#{old}/inputs.sha256"
fail!('original manifest hash mismatch') unless expected.match?(/\A[0-9a-f]{64}\z/) && digest(manifest_path) == expected
manifest = {}
File.readlines(manifest_path).each do |line|
  match = line.match(/\A([0-9a-f]{64})  (.+)\n\z/)
  fail!('malformed original manifest') unless match && safe_path?(match[2])
  fail!('duplicate original input') if manifest.key?(match[2])
  manifest[match[2]] = match[1]
end
# Authenticate the receipt before using it to classify any absolute path.
fail!('original receipt mismatch') unless manifest['receipt.json'] && digest("#{old}/receipt.json") == manifest['receipt.json']
r = JSON.parse(File.read("#{old}/receipt.json"))
native_platform = r.fetch('native_platform', 'darwin')
fail!('unsupported native platform') unless %w[darwin linux-gnu].include?(native_platform)
paths = %w[source target_build native_build sysroot target_prefix compiler]
paths << 'native_sdk' if native_platform == 'darwin'
paths.each do |key|
  p = r.fetch(key)
  fail!("unsupported receipt path #{key}") unless p.start_with?('/') && safe_path?(p)
end
native_roots = native_platform == 'darwin' ? [r.fetch('native_sdk')] : r.fetch('native_header_roots')
fail!('unsupported native header search roots') unless native_roots.is_a?(Array) && !native_roots.empty? && native_roots.all? { |path| path.is_a?(String) && path != '/' && path.start_with?('/') && safe_path?(path) }
native_runtime = native_platform == 'linux-gnu' ? r.fetch('native_runtime') : nil
fail!('missing native Linux runtime receipt') if native_platform == 'linux-gnu' && !native_runtime.is_a?(Hash)
source, target, native, prefix = r.values_at('source', 'target_build', 'native_build', 'target_prefix')
fail!('requires an accepted installed LLVM 23.1.3 helper') unless r['version'] == '23.1.3' && prefix == r['sysroot'] + '/usr/pkg'
begin
  target_spec = EmberGraphicsLLVM.for_triple(r['target_triple'])
rescue ArgumentError => error
  fail!(error.message)
end
proof = r.fetch('library_proof')
fail!('unsupported historical library proof') unless %w[identical cmake-install-strip].include?(proof['method']) &&
  proof['built_library'] == "#{target}/lib/libLLVM.so" && proof['staged_library'] == "#{prefix}/lib/libLLVM-23.so" &&
  proof['staged_sha256'] == r['staged_library_sha256'] &&
  proof[proof['method'] == 'identical' ? 'built_sha256' : 'reproduced_sha256'] == proof['staged_sha256']

local = %w[metadata/BuildVariables.inc metadata/LibraryDependencies.inc metadata/ExtensionDependencies.inc llvm-config.cpp build-llvm-config.rb llvm-config.d dependencies.command compile.command receipt.json bin/llvm-config.real bin/llvm-config]
local << 'llvm-target.rb' if manifest.key?('llvm-target.rb')
local << 'llvm-native.rb' if manifest.key?('llvm-native.rb')
native_files = native_runtime ? native_runtime.fetch('files').map { |file| file.fetch('path') } : []
if native_runtime
  fail!('missing accepted native inspector') unless manifest.key?('llvm-native.rb')
  fail!('accepted native executable mismatch') unless manifest['bin/llvm-config.real'] && digest("#{old}/bin/llvm-config.real") == manifest['bin/llvm-config.real']
  begin
    fail!('native receipt triples differ') unless native_runtime.fetch('triple') == r.fetch('native_triple')
    EmberGraphicsLLVMNative.verify("#{old}/bin/llvm-config.real", old, native_runtime)
  rescue ArgumentError => error
    fail!(error.message)
  end
  local += native_files
end
local += %w[strip.command strip.log] if proof['method'] == 'cmake-install-strip'
local.each do |p|
  fail!("accepted local artifact mismatch: #{p}") unless manifest[p] && digest("#{old}/#{p}") == manifest[p]
end
metadata_names = %w[include/llvm/Config/llvm-config.h include/llvm/Config/config.h include/llvm/Config/abi-breaking.h tools/llvm-config/BuildVariables.inc tools/llvm-config/LibraryDependencies.inc tools/llvm-config/ExtensionDependencies.inc]
classes = local.to_h { |p| [p, 'accepted-local-artifact'] }
metadata_names.each { |p| classes["#{target}/#{p}"] = 'target-report-metadata' }
%w[llvm-config.h abi-breaking.h].each { |p| classes["#{prefix}/include/llvm/Config/#{p}"] = 'installed-target-input' }
classes[proof.fetch('staged_library')] = 'installed-target-input'
# These exact files were build inputs, not runtime dependencies of the compiled
# upstream tool. Their observed state is retained, never called revalidated.
historical = ["#{target}/CMakeCache.txt", "#{native}/CMakeCache.txt", proof.fetch('built_library'), r.fetch('compiler'),
              "#{source}/tools/llvm-config/llvm-config.cpp", "#{native}/bin/llvm-config"]
historical += %w[llvm-config.h config.h abi-breaking.h].map { |p| "#{native}/include/llvm/Config/#{p}" }
historical += %w[LLVMTargetParser LLVMSupport LLVMDemangle].map { |p| "#{native}/lib/lib#{p}.a" }
historical += r.fetch('native_system_libraries', []).select { |arg| arg.start_with?('/') }
if native_runtime
  native_runtime.fetch('files').each do |file|
    path = file.fetch('source')
    fail!('unsupported native runtime source path') unless path.start_with?('/') && safe_path?(path)
    fail!('native runtime source hash differs from original manifest') unless manifest[path] == file.fetch('sha256')
    historical << path
  end
  native_runtime.fetch('tools').each do |path, hash|
    fail!('unsupported native audit-tool source path') unless path.start_with?('/') && safe_path?(path)
    fail!('native audit-tool hash differs from original manifest') unless manifest[path] == hash
    historical << path
  end
end
if proof['method'] == 'cmake-install-strip'
  fail!('unsupported strip proof paths') unless proof['strip'].start_with?('/') && safe_path?(proof['strip']) && proof['install_script'] == "#{target}/tools/llvm-shlib/cmake_install.cmake"
  historical += [proof.fetch('strip'), proof.fetch('install_script')]
end
# The authenticated dependency file defines the precise native header set;
# merely living somewhere in the source/build tree is not a classification.
depfile = File.read("#{old}/llvm-config.d").gsub("\\\n", ' ')
fail!('unsupported dependency file') unless depfile.start_with?('llvm-config:')
compile_sources = r.fetch('command').select { |arg| arg.end_with?('/llvm-config.cpp') }
fail!('unsupported recorded helper compile command') unless compile_sources.length == 1
compile_work = File.dirname(compile_sources.first)
fail!('unsupported recorded helper work path') unless compile_work.start_with?('/') && safe_path?(compile_work) &&
  r['command'].include?("-I#{compile_work}/metadata") && r['command'].last == "#{compile_work}/bin/llvm-config.real"
deps = Shellwords.split(depfile.sub(/\Allvm-config:\s*/, ''))
deps.each do |p|
  if p.start_with?(compile_work + '/')
    fail!("unknown local compile dependency: #{p}") unless local.include?(p.delete_prefix(compile_work + '/'))
    next
  end
  header = p.start_with?(source + '/include/') || p.start_with?(native + '/include/')
  sdk = native_roots.any? { |root| p.start_with?(root + '/') }
  fail!("unclassified compile dependency: #{p}") unless safe_path?(p) && (header || sdk)
  historical << p
end
# Original target source directory is stored in the authenticated report data.
original_vars = "#{target}/tools/llvm-config/BuildVariables.inc"
fail!('target report metadata mismatch') unless manifest[original_vars] && digest(original_vars) == manifest[original_vars]
source_match = File.read(original_vars).match(/^#define LLVM_SRC_ROOT (".*")$/)
fail!('missing original target source root') unless source_match
original_source = JSON.parse(source_match[1])
fail!('unsupported original target source path') unless original_source.start_with?('/') && safe_path?(original_source)
historical << "#{original_source}/tools/llvm-config/llvm-config.cpp"
historical.uniq.each { |p| classes[p] ||= 'historical-build-input' }
fail!("unclassified original inputs: #{(manifest.keys - classes.keys).join(', ')}") unless (manifest.keys - classes.keys).empty?
fail!("missing required original inputs: #{(classes.keys - manifest.keys).join(', ')}") unless (classes.keys - manifest.keys).empty?
fail!('library proof differs from original manifest') unless manifest[proof['built_library']] == proof['built_sha256'] && manifest[proof['staged_library']] == proof['staged_sha256']
rows = manifest.map do |p, hash|
  actual = digest(p.start_with?('/') ? p : "#{old}/#{p}")
  state = actual.nil? ? 'missing' : (actual == hash ? 'match' : 'changed')
  fail!("required #{classes.fetch(p)} mismatch: #{p}") if classes[p] != 'historical-build-input' && state != 'match'
  {path: p, classification: classes.fetch(p), expected_sha256: hash, observed_sha256: actual, state: state}
end
library = proof.fetch('staged_library')
fail!('installed shared LLVM resolves outside the target prefix') unless File.realpath(library).start_with?(prefix + '/lib/')
header = File.binread(library, 20)
begin
  EmberGraphicsLLVM.validate_elf(header, target_spec)
rescue ArgumentError => error
  fail!(error.message)
end
# A newly generated guard must not accidentally hide a dynamic native LLVM
# dependency. The accepted helper links its LLVM support archives statically.
if native_runtime
  begin
    linked = EmberGraphicsLLVMNative.verify("#{old}/bin/llvm-config.real", old, native_runtime)
  rescue ArgumentError => error
    fail!(error.message)
  end
else
  linked, error, status = Open3.capture3('/usr/bin/otool', '-L', "#{old}/bin/llvm-config.real")
  fail!("cannot inspect accepted native executable: #{error}") unless status.success?
  linked.lines.drop(1).each do |line|
    p = line.strip.split.first
    fail!("unexpected native runtime dependency: #{p}") unless p && (p.start_with?('/usr/lib/') || p.start_with?('/System/Library/'))
  end
end
FileUtils.mkdir_p("#{work}/provenance")
FileUtils.cp(manifest_path, "#{work}/provenance/inputs.sha256")
local.each do |p|
  next if native_files.include?(p)
  destination = p == 'bin/llvm-config' ? 'provenance/original-launcher' : p
  FileUtils.mkdir_p(File.dirname("#{work}/#{destination}"))
  FileUtils.cp("#{old}/#{p}", "#{work}/#{destination}")
  fail!("copied local artifact changed: #{p}") unless digest("#{work}/#{destination}") == manifest[p]
end
if native_runtime
  begin
    EmberGraphicsLLVMNative.copy("#{old}/bin/llvm-config.real", old, work, native_runtime,
      copied_binary: "#{work}/bin/llvm-config.real")
  rescue ArgumentError => error
    fail!(error.message)
  end
end
FileUtils.cp("#{old}/receipt.json", "#{work}/provenance/receipt.json")
metadata_names.each do |p|
  destination = "#{work}/provenance/target/#{p}"
  FileUtils.mkdir_p(File.dirname(destination))
  FileUtils.cp("#{target}/#{p}", destination)
  fail!("target metadata changed while copying: #{p}") unless digest(destination) == manifest["#{target}/#{p}"]
end
FileUtils.cp(__FILE__, "#{work}/seal-llvm-config.rb")
File.write("#{work}/provenance/native-loader.txt", linked)
File.write("#{work}/seal.json", JSON.pretty_generate({format: 'ember-llvm-config-seal-v1', original_manifest_sha256: expected,
  accepted_executable_sha256: manifest.fetch('bin/llvm-config.real'), original_work: old,
  historical_proof: 'Original strip/build proof is retained as accepted provenance; it is not reproduced by sealing.',
  observed_inputs: rows}) + "\n")
File.write("#{work}/bin/llvm-config", <<~SH)
  #!/bin/sh
  # SPDX-License-Identifier: BSD-2-Clause
  # Integrity guard only; query handling is the unchanged upstream executable.
  set -eu
  base=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
  cd "$base"
  /usr/bin/shasum -a 256 -c inputs.sha256 > /dev/null || {
      echo 'llvm-config: sealed input receipt changed' >&2
      exit 1
  }
  #{EmberGraphicsLLVMNative.launcher(native_runtime)}
SH
File.chmod(0755, "#{work}/bin/llvm-config")
# Preserve all immutable provenance, including observed losses; only installed
# target inputs remain external. Source/build cleanup cannot change queries.
files = Dir.glob("#{work}/**/*").select { |p| File.file?(p) }.sort
runtime = rows.select { |row| row[:classification] == 'installed-target-input' }
runtime.each { |row| fail!("installed input changed while sealing: #{row[:path]}") unless digest(row[:path]) == row[:expected_sha256] }
fail!('original manifest changed while sealing') unless digest(manifest_path) == expected
lines = files.map { |p| "#{digest(p)}  #{p.delete_prefix(work + '/')}\n" }
lines += runtime.map { |row| "#{row[:expected_sha256]}  #{row[:path]}\n" }
File.write("#{work}/inputs.sha256", lines.join)
puts "#{work}/bin/llvm-config"
puts "Same accepted executable; #{rows.count { |row| row[:state] != 'match' }} historical input changes recorded, not revalidated."
