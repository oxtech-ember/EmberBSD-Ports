#!/usr/bin/env ruby
# Verify the real prebuilt provider without rewriting Mach-O load commands.
require 'digest'
require 'fileutils'
require 'open3'

abort 'usage: rust-darwin.rb ORIGINAL_HOST_RUST STAGED_HOST_RUST NEW_WORK' unless ARGV.size == 3
original, staged = ARGV.first(2).map { |p| File.realpath(p) }
work = File.expand_path(ARGV[2])
abort 'new absolute work directory required' unless ARGV[2].start_with?('/') && !File.exist?(work)
parent = File.realpath(File.dirname(work))
abort 'work overlaps an input' if [original, staged].any? { |p| parent == p || parent.start_with?(p + '/') }
Dir.mkdir(work)
env = {'DYLD_LIBRARY_PATH' => nil, 'DYLD_FRAMEWORK_PATH' => nil, 'DYLD_INSERT_LIBRARIES' => nil}
run = lambda do |name, *args|
  output, status = Open3.capture2e(env, *args)
  File.write(File.join(work, name + '.log'), output)
  abort "#{name} failed" unless status.success?
  output
end
version = run.call('version', File.join(staged, 'bin/rustc'), '-vV')
abort 'official Rust 1.99 macOS/AArch64 required' unless version.lines.first.chomp == 'rustc 1.99.1 (58cf8f9c3 2026-10-13)' &&
  version.include?("host: aarch64-apple-darwin\n")
relative = %w[bin/rustc bin/cargo lib/libLLVM.dylib] +
  Dir.glob('lib/librustc_driver-*.dylib', base: original) +
  Dir.glob('lib/rustlib/aarch64-apple-darwin/lib/libstd-*.dylib', base: original)
abort 'unexpected upstream component layout' unless relative.size == 5
hashes = relative.to_h do |p|
  hash = Digest::SHA256.file(File.join(original, p)).hexdigest
  abort "rewritten provider: #{p}" unless Digest::SHA256.file(File.join(staged, p)).hexdigest == hash
  [p, hash]
end
File.write(File.join(work, 'providers.sha256'), hashes.map { |p, h| "#{h}  #{p}\n" }.join)
# Reproduce the old absolute install-name failure on a disposable real DSO.
std = relative.find { |p| p.include?('/libstd-') }
control = File.join(work, 'legacy-libstd.dylib')
FileUtils.cp(File.join(original, std), control)
name = File.join(work, 'prefix-' + 'x' * 120, std)
output, status = Open3.capture2e('install_name_tool', '-id', name, control)
File.write(File.join(work, 'legacy-rewrite.log'), output)
abort 'legacy load-command overflow was not reproduced' if status.success? || !output.include?('larger updated load commands do not fit')
source = File.expand_path('../../../probes/rust-cross-std/runtime.rs', __dir__)
FileUtils.cp(source, File.join(work, 'runtime.rs'))
binary = File.join(work, 'native-consumer')
run.call('compile', File.join(staged, 'bin/rustc'), '--sysroot', staged, '--edition=2024', File.join(work, 'runtime.rs'), '-o', binary)
run.call('runtime', binary)
run.call('cargo', File.join(staged, 'bin/cargo'), '-V')
relative.each do |p|
  [original, staged].each do |root|
    abort "input changed: #{root}/#{p}" unless Digest::SHA256.file(File.join(root, p)).hexdigest == hashes[p]
  end
end
puts 'PASS: unchanged Mach-O providers, real legacy overflow, relocated rustc/cargo and native thread/TLS/unwind consumer'
