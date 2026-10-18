#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Real accepted-tool integrity regression.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'

abort 'usage: llvm-config-seal.rb ACCEPTED_WORK ORIGINAL_MANIFEST_SHA256 SEALED_WORK TARGET_REFERENCE NEW_WORK' unless ARGV.length == 5
old, original_hash, sealed, reference, work = ARGV
[old, sealed, reference].each { |p| abort 'absolute input required' unless p.start_with?('/') && File.directory?(p) }
abort 'NEW_WORK must be new and absolute' unless work.start_with?('/') && !File.exist?(work)
FileUtils.mkdir_p(work)
sealer = File.expand_path('../cross/seal-llvm-config.rb', __dir__)
comparer = File.expand_path('../cross/compare-llvm-config.rb', __dir__)

$count = 0
def check(name)
  abort "FAIL: #{name}" unless yield
  $count += 1
  puts "PASS: #{name}"
end

def run(log, *command)
  out, err, status = Open3.capture3(*command)
  File.write(log, out + err)
  [out, err, status]
end

def hash_file(path)
  Digest::SHA256.file(path).hexdigest
end

check('caller anchor agrees with the original manifest') { hash_file("#{old}/inputs.sha256") == original_hash }
r = JSON.parse(File.read("#{old}/receipt.json"))
native_files = r['native_runtime'] ? r.fetch('native_runtime').fetch('files').map { |file| file.fetch('path') } : []
check('unchanged compiled executable, historical receipt, manifest and launcher') do
  { 'bin/llvm-config.real' => 'bin/llvm-config.real', 'receipt.json' => 'receipt.json',
    'provenance/receipt.json' => 'receipt.json', 'provenance/inputs.sha256' => 'inputs.sha256',
    'provenance/original-launcher' => 'bin/llvm-config' }.all? { |new_path, original_path| File.binread("#{sealed}/#{new_path}") == File.binread("#{old}/#{original_path}") }
end
unless native_files.empty?
  check('Linux sealer preserves every native loader/runtime file byte for byte') do
    native_files.all? { |path| File.binread("#{old}/#{path}") == File.binread("#{sealed}/#{path}") }
  end
end
check('16 real queries agree with freshly captured target executable') do
  _, _, status = run("#{work}/target-agreement.log", 'ruby', comparer, sealed, reference)
  status.success?
end
check('upstream still rejects unknown components') do
  out, err, status = run("#{work}/unknown-component.log", "#{sealed}/bin/llvm-config", '--libs', 'ember_unknown_component')
  !status.success? && out.empty? && err.include?('unknown component')
end
seal = JSON.parse(File.read("#{sealed}/seal.json"))
check('all original inputs have explicit classes and observations') do
  rows = seal.fetch('observed_inputs')
  rows.length == File.readlines("#{old}/inputs.sha256").length &&
    rows.all? { |row| %w[accepted-local-artifact target-report-metadata installed-target-input historical-build-input].include?(row['classification']) } &&
    rows.select { |row| row['state'] != 'match' }.all? { |row| row['classification'] == 'historical-build-input' }
end
check('sealed runtime receipt has no temporary source/build dependency') do
  r = JSON.parse(File.read("#{old}/receipt.json"))
  paths = File.readlines("#{sealed}/inputs.sha256").map { |line| line.chomp.split(/  /, 2)[1] }
  paths.select { |p| p.start_with?('/') }.all? { |p| p.start_with?(r.fetch('target_prefix') + '/') }
end
# Each case copies only the small helper, not LLVM sources or libraries.
(%w[metadata/BuildVariables.inc bin/llvm-config.real receipt.json] + native_files).each_with_index do |path, i|
  fixture = "#{work}/original-drift-#{i}"
  FileUtils.cp_r(old, fixture)
  File.open("#{fixture}/#{path}", 'a') { |f| f.write('changed accepted artifact') }
  check("sealing rejects original #{path} drift") do
    _, err, status = run("#{work}/original-drift-#{i}.log", 'ruby', sealer, fixture, original_hash, "#{work}/rejected-#{i}")
    !status.success? && (err.include?('mismatch') || err.include?('retained native runtime changed'))
  end
  FileUtils.rm_r(fixture)
end
fixture = "#{work}/manifest-fixture"
FileUtils.cp_r(old, fixture)
File.open("#{fixture}/inputs.sha256", 'a') { |f| f.puts(('0' * 64) + '  /tmp/unknown-build-input') }
check('changed original manifest cannot reuse its acceptance anchor') do
  _, err, status = run("#{work}/anchor-negative.log", 'ruby', sealer, fixture, original_hash, "#{work}/wrong-anchor")
  !status.success? && err.include?('original manifest hash mismatch')
end
# This intentionally new fixture anchor tests classification itself. It is
# not represented as accepted provenance and never produces a usable helper.
check('unknown paths cannot become disposable build inputs') do
  _, err, status = run("#{work}/class-negative.log", 'ruby', sealer, fixture, hash_file("#{fixture}/inputs.sha256"), "#{work}/wrong-class")
  !status.success? && err.include?('unclassified original inputs')
end
FileUtils.rm_r(fixture)
FileUtils.cp_r(old, fixture)
removed = "#{r['native_build']}/CMakeCache.txt"
File.write("#{fixture}/inputs.sha256", File.readlines("#{fixture}/inputs.sha256").reject { |line| line.end_with?("  #{removed}\n") }.join)
check('missing required historical classifications cannot be silently dropped') do
  _, err, status = run("#{work}/missing-class-negative.log", 'ruby', sealer, fixture, hash_file("#{fixture}/inputs.sha256"), "#{work}/missing-class")
  !status.success? && err.include?('missing required original inputs')
end
FileUtils.rm_r(fixture)
# Fault-inject a required expected hash, never modify the real target tree.
# The new anchor belongs only to this rejection fixture.
{
  'report-metadata' => "#{r['target_build']}/tools/llvm-config/BuildVariables.inc",
  'target-header' => "#{r['target_prefix']}/include/llvm/Config/llvm-config.h"
}.each do |name, path|
  FileUtils.cp_r(old, fixture)
  lines = File.readlines("#{fixture}/inputs.sha256")
  abort 'fixture path not recorded' unless lines.any? { |line| line.end_with?("  #{path}\n") }
  File.write("#{fixture}/inputs.sha256", lines.map { |line| line.end_with?("  #{path}\n") ? ('0' * 64) + "  #{path}\n" : line }.join)
  check("sealing rejects required #{name} hash mismatch") do
    _, err, status = run("#{work}/#{name}-negative.log", 'ruby', sealer, fixture, hash_file("#{fixture}/inputs.sha256"), "#{work}/wrong-#{name}")
    !status.success? && err.include?('mismatch')
  end
  FileUtils.rm_r(fixture)
end
(%w[bin/llvm-config.real metadata/LibraryDependencies.inc provenance/inputs.sha256 provenance/receipt.json seal.json] + native_files).each_with_index do |path, i|
  clone = "#{work}/sealed-drift-#{i}"
  FileUtils.cp_r(sealed, clone)
  File.open("#{clone}/#{path}", 'a') { |f| f.write('changed sealed artifact') }
  check("query refuses sealed #{path} drift before execution") do
    out, err, status = run("#{work}/sealed-drift-#{i}.log", "#{clone}/bin/llvm-config", '--version')
    !status.success? && out.empty? && err.include?('sealed input receipt changed')
  end
  FileUtils.rm_r(clone)
end
# Redirect one external hash entry to a real copied installed artifact only in
# this host integrity fixture. Do not execute with fabricated target metadata.
%w[include/llvm/Config/llvm-config.h lib/libLLVM-23.so].each_with_index do |path, i|
  clone = "#{work}/installed-drift-#{i}"
  FileUtils.cp_r(sealed, clone)
  installed = "#{r.fetch('target_prefix')}/#{path}"
  copied = "#{work}/installed-artifact-#{i}"
  FileUtils.cp(installed, copied)
  File.write("#{clone}/inputs.sha256", File.read("#{clone}/inputs.sha256").sub("  #{installed}\n", "  #{copied}\n"))
  File.open(copied, 'ab') { |f| f.write('changed installed artifact') }
  check("query rejects actual copied installed #{path} drift") do
    out, err, status = run("#{work}/installed-drift-#{i}.log", "#{clone}/bin/llvm-config", '--version')
    !status.success? && out.empty? && err.include?('sealed input receipt changed')
  end
  FileUtils.rm_r(clone)
  FileUtils.rm(copied)
end
puts "PASS: #{$count} seal/query checks; no LLVM rebuild or target execution."
