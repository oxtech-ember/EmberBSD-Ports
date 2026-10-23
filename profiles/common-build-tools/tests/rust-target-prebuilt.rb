#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check the prebuilt std contract without a build.
require 'digest'
require 'fileutils'
require 'open3'
abort 'Usage: rust-target-prebuilt.rb READ_ELF STD_ARCHIVE NEW_WORK' unless ARGV.length == 3
readelf, archive, work = ARGV.map { |path| File.expand_path(path) }
abort 'Archive SHA256 differs from the release manifest' unless
  Digest::SHA256.file(archive).hexdigest == '97569760ad6e042d56ccdac2fd295df8a10351403b9bbca2a19567f8ed6ae46b'
Dir.mkdir(work)
work = File.realpath(work)
source = File.join(work, 'rust-std-1.99.1-x86_64-unknown-netbsd')
output, error, status = Open3.capture3('tar', '-xf', archive, '-C', work)
abort output + error unless status.success?
host = File.join(work, 'host')
stage = File.join(work, 'stage')
FileUtils.mkdir_p([File.join(host, 'bin'), stage])
FileUtils.cp_r(File.join(source, 'rust-std-x86_64-unknown-netbsd/lib'), stage)
File.write(File.join(host, 'bin/rustc'), <<~SH)
  #!/bin/sh
  set -eu
  if [ "$1" = -vV ]; then
      echo "rustc ${FIXTURE_VERSION:-1.99.1} (58cf8f9c3 2026-10-13)"
      echo 'commit-hash: 58cf8f9c35b355199727627d07ae34a4e2846d67'
      echo 'host: aarch64-apple-darwin'
      exit
  fi
  printf '%s\n' "$@" > "$FIXTURE_LOG"
  [ "${FIXTURE_REJECT_METADATA:-0}" = 0 ] || { echo 'E0514 fixture: incompatible metadata' >&2; exit 1; }
  while [ "$#" -gt 0 ]; do
      if [ "$1" = -o ]; then printf 'metadata boundary fixture' > "$2"; exit; fi
      shift
  done
  exit 1
SH
File.chmod(0755, File.join(host, 'bin/rustc'))
helper = File.expand_path('../../../pkgsrc/lang/rust-std-x86_64-netbsd/files/check.sh', __dir__)
count = 0
check = lambda do |name, expected = nil, extra = {}|
  output_dir = File.join(work, name)
  output, error, status = Open3.capture3({ 'FIXTURE_LOG' => File.join(work, 'compiler-args') }.merge(extra),
                                       'sh', helper, host, source, stage, output_dir, readelf)
  File.write(File.join(work, "#{name}.log"), output + error)
  if expected
    abort "#{name} accepted invalid input: #{output}#{error}" if status.success? || !(output + error).include?(expected)
  else
    abort "#{name} failed: #{output}#{error}" unless status.success?
    args = File.readlines(File.join(work, 'compiler-args'), chomp: true)
    abort 'Wrong metadata target or sysroot' unless args.include?('x86_64-unknown-netbsd') && args.include?(stage)
    abort 'Metadata check attempted linking' unless args.include?('--emit=metadata') && !args.include?('link')
  end
  count += 1
  puts "PASS: #{name}"
end
check.call('official-elf-and-component')
check.call('foreign-compiler', 'official Rust 1.99.1 required', { 'FIXTURE_VERSION' => '1.98.0' })
check.call('incompatible-metadata', 'E0514', { 'FIXTURE_REJECT_METADATA' => '1' })
component = File.join(stage, 'lib/rustlib/x86_64-unknown-netbsd/lib')
core = Dir[File.join(component, 'libcore-*.rmeta')].fetch(0)
original = File.binread(core)
File.binwrite(core, original + 'corrupt')
check.call('changed-payload', 'target component differs from the upstream payload')
File.binwrite(core, original)
File.unlink(core)
check.call('missing-metadata', 'target component manifest differs')
File.binwrite(core, original)
File.write(File.join(component, 'extra'), 'unlisted')
check.call('extra-payload', 'target component manifest differs')
File.unlink(File.join(component, 'extra'))
shared = Dir[File.join(component, 'libstd-*.so')].fetch(0)
source_shared = File.join(source, 'rust-std-x86_64-unknown-netbsd/lib/rustlib/x86_64-unknown-netbsd/lib', File.basename(shared))
original = File.binread(shared)
wrong = original.dup
wrong[18, 2] = [183].pack('v')
[shared, source_shared].each { |path| File.binwrite(path, wrong) }
check.call('foreign-elf', 'target std must be x86_64 ELF64')
[shared, source_shared].each { |path| File.binwrite(path, original) }
[['foreign-needed', 'libc.so.12', 'libc.so.99', 'unexpected target std providers'],
 ['foreign-rpath', '$ORIGIN/../lib', '$ORIGIN/../bad', 'unexpected official target std RPATH']].each do |name, from, to, expected|
  wrong = original.sub(from, to)
  abort 'Missing ELF string mutation' if wrong == original
  [shared, source_shared].each { |path| File.binwrite(path, wrong) }
  check.call(name, expected)
  [shared, source_shared].each { |path| File.binwrite(path, original) }
end
puts "PASS: #{count} upstream component and real ELF checks; compiler boundary fixtures do not prove Rust metadata acceptance"
