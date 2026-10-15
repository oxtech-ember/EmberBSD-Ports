#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted derived vendor source regression.
require 'tmpdir'
require 'fileutils'
require 'digest'
require 'json'
require 'zlib'
require 'rubygems/package'
require 'open3'
require 'rbconfig'
helper = File.expand_path('../files/vendor.rb', __dir__)
abort 'FAIL: reproducible vendor helper is missing' unless File.file?(helper)
require helper
def expect_failure(reason)
  begin
    yield
  rescue CssVendor::Error
    return
  end
  abort 'FAIL: accepted ' + reason
end
pax_comment = "52 comment=d7bd0b6a6ca1db88a8189aee81498f194f1e45a5\n"
pax_metadata = {'type' => 'g', 'name' => 'pax_global_header', 'payload' => pax_comment}
abort 'FAIL: pinned commit comment provenance changed' unless CssVendor.pinned_source_metadata('g', 'pax_global_header', pax_comment) == pax_metadata
[
  ['x', 'pax_global_header', pax_comment],
  ['g', 'foreign_header', pax_comment],
  ['g', '../pax_global_header', pax_comment],
  ['g', 'pax_global_header', pax_comment.sub('d7bd', '0000')],
  ['g', 'pax_global_header', pax_comment.chomp],
  ['g', 'pax_global_header', pax_comment + "20 path=../escape\n"],
  ['g', 'pax_global_header', "20 linkpath=/escape\n"],
  ['g', 'pax_global_header', "20 path=/escape\n"]
].each do |type, name, payload|
  expect_failure('unreviewed PAX type, name or payload') { CssVendor.pinned_source_metadata(type, name, payload) }
end
Dir.mktmpdir('ember-css-vendor-', '/tmp') do |work|
  vendor = work + '/vendor'
  crate = vendor + '/fixture-1.0.0'
  cache = work + '/cache/index'
  FileUtils.mkdir_p([crate + '/src', cache])
  files = {'LICENSE-MIT' => "MIT license fixture\n", 'src/lib.rs' => "pub fn fixture() {}\n"}
  files.each { |name, data| File.write(crate + '/' + name, data) }
  archive = cache + '/fixture-1.0.0.crate'
  Zlib::GzipWriter.open(archive) do |gzip|
    gzip.mtime = 0
    Gem::Package::TarWriter.new(gzip) do |tar|
      files.each do |name, data|
        tar.add_file_simple('fixture-1.0.0/' + name, 0644, data.bytesize) { |io| io.write(data) }
      end
    end
  end
  checksum = Digest::SHA256.file(archive).hexdigest
  packages = [{'name' => 'fixture', 'version' => '1.0.0', 'checksum' => checksum}]
  sums = files.transform_values { |data| Digest::SHA256.hexdigest(data) }
  metadata = {'package' => checksum, 'files' => sums.dup}
  File.write(crate + '/.cargo-checksum.json', JSON.generate(metadata))
  result = CssVendor.audit(vendor, work + '/cache', packages)
  abort 'FAIL: original crate license not retained' unless result.fetch('license_files') == 1
  ENV['SOURCE_DATE_EPOCH'] = '1234'
  CssVendor.pack(vendor, work + '/first.tar')
  abort 'FAIL: caller epoch changed' unless ENV['SOURCE_DATE_EPOCH'] == '1234'
  FileUtils.chmod_R(0700, vendor)
  files.each_key { |name| File.chmod(0600, crate + '/' + name) }
  File.chmod(0600, crate + '/.cargo-checksum.json')
  File.utime(Time.at(1234567), Time.at(1234567), crate + '/src/lib.rs')
  CssVendor.pack(vendor, work + '/second.tar')
  abort 'FAIL: archive depends on metadata or invocation time' unless File.binread(work + '/first.tar') == File.binread(work + '/second.tar')
  File.open(work + '/first.tar', 'rb') do |archive_io|
    Gem::Package::TarReader.new(archive_io) do |tar|
      tar.each do |entry|
        h = entry.header
        abort 'FAIL: noncanonical USTAR metadata' unless h.uid == 0 && h.gid == 0 && h.mtime == 0 && h.magic == 'ustar'
        abort 'FAIL: unstable file modes' unless h.mode == (entry.directory? ? 0755 : 0644)
      end
    end
  end
  abort 'FAIL: host tar cannot read canonical archive' unless system('tar', '-tf', work + '/first.tar', out: File::NULL)
  File.symlink('src/lib.rs', crate + '/link')
  expect_failure('vendor symlink') { CssVendor.audit(vendor, work + '/cache', packages) }
  File.unlink(crate + '/link')
  FileUtils.mkdir_p(vendor + '/foreign-1.0.0')
  expect_failure('foreign crate directory') { CssVendor.audit(vendor, work + '/cache', packages) }
  Dir.rmdir(vendor + '/foreign-1.0.0')
  File.chmod(0755, crate + '/src/lib.rs')
  CssVendor.pack(vendor, work + '/executable.tar')
  File.open(work + '/executable.tar', 'rb') do |io|
    Gem::Package::TarReader.new(io) do |tar|
      tar.each do |entry|
        next unless entry.full_name.end_with?('/src/lib.rs')
        abort 'FAIL: executable bit omitted' unless entry.header.mode == 0755
      end
    end
  end
  File.write(crate + '/unexpected', 'extra')
  expect_failure('unrecorded vendored file') { CssVendor.audit(vendor, work + '/cache', packages) }
  File.unlink(crate + '/unexpected')
  File.write(crate + '/LICENSE-MIT', "changed license\n")
  metadata['files']['LICENSE-MIT'] = Digest::SHA256.file(crate + '/LICENSE-MIT').hexdigest
  File.write(crate + '/.cargo-checksum.json', JSON.generate(metadata))
  expect_failure('license changed together with its local checksum') { CssVendor.audit(vendor, work + '/cache', packages) }
  File.write(crate + '/LICENSE-MIT', files.fetch('LICENSE-MIT'))
  metadata['files']['LICENSE-MIT'] = sums.fetch('LICENSE-MIT')
  File.write(crate + '/.cargo-checksum.json', JSON.generate(metadata))
  File.open(archive, 'ab') { |io| io.write('corrupt') }
  expect_failure('crate archive differs from lock checksum') { CssVendor.audit(vendor, work + '/cache', packages) }
  lock = "version = 4\n[[package]]\nname = \"fixture\"\nversion = \"1.0.0\"\nsource = \"registry+https://github.com/rust-lang/crates.io-index\"\nchecksum = \"#{checksum}\"\n"
  abort 'FAIL: original lock closure not parsed' unless CssVendor.lock_packages(lock) == packages
  expect_failure('unchecksummed registry crate') { CssVendor.lock_packages(lock.sub(/^checksum.*\n/, '')) }
  expect_failure('unreviewed git dependency') { CssVendor.lock_packages(lock.sub('registry+https://github.com/rust-lang/crates.io-index', 'git+https://example.invalid/crate')) }
  expect_failure('duplicate crate identity') { CssVendor.lock_packages(lock + lock.sub(/^version = 4\n/, '')) }
  expect_failure('unsafe archive path') { CssVendor.safe_name('vendor/../escape') }
end
if (archive = ENV['CSSPARSER_UPSTREAM_ARCHIVE'])
  abort 'FAIL: original source archive hash' unless Digest::SHA256.file(archive).hexdigest == CssVendor::SOURCE_SHA
  Zlib::GzipReader.open(archive) do |gzip|
    Gem::Package::TarReader.new(gzip) do |tar|
      found = false
      tar.each do |entry|
        next unless entry.full_name == 'cxx-rust-cssparser-1.1.0/rust/Cargo.lock'
        lock = entry.read
        abort 'FAIL: original lock hash' unless Digest::SHA256.hexdigest(lock) == CssVendor::LOCK_SHA
        manifest = CssVendor.lock_packages(lock).map { |p| [p.fetch('name'), p.fetch('version'), p.fetch('checksum')].join("\t") }.join("\n") + "\n"
        abort 'FAIL: reviewed closure differs from original lock' unless File.binread(File.expand_path('../files/vendor-crates.tsv', __dir__)) == manifest
        found = true
      end
      abort 'FAIL: original lock missing' unless found
    end
  end
  Dir.mktmpdir('ember-css-source-cli-', '/tmp') do |work|
    host = work + '/host'
    FileUtils.mkdir_p(host + '/bin')
    File.write(host + '/bin/rustc', <<~SH)
      #!/bin/sh
      [ "$1" = -vV ] || exit 96
      printf '%s\\n' 'rustc 1.99.0 (controlled provider-response fixture)' 'commit-hash: #{CssVendor::RUST_COMMIT}' 'release: 1.99.0' 'host: aarch64-apple-darwin'
    SH
    File.write(host + '/bin/cargo', <<~SH)
      #!/bin/sh
      if [ "$1" = -V ]; then
        printf '%s\\n' 'cargo 1.99.0 (controlled provider-response fixture)'
        exit 0
      fi
      [ "$1" = vendor ] || exit 96
      printf '%s\\n' 'CONTROLLED CARGO BOUNDARY; no native Cargo acceptance' > "$(dirname "$0")/vendor-reached"
      exit 97
    SH
    File.chmod(0755, host + '/bin/rustc', host + '/bin/cargo')
    extraction = work + '/extraction'
    stdout, stderr, status = Open3.capture3(RbConfig.ruby, helper, archive, host, extraction)
    abort "FAIL: actual source CLI did not reach controlled Cargo boundary: #{stderr}" unless status.exitstatus == 1 && stderr.include?('Cargo vendor failed') && File.file?(host + '/bin/vendor-reached')
    abort 'FAIL: extracted original lock changed' unless Digest::SHA256.file(extraction + '/cxx-rust-cssparser-1.1.0/rust/Cargo.lock').hexdigest == CssVendor::LOCK_SHA
    abort 'FAIL: exact source PAX comment was not preserved' unless JSON.parse(File.read(extraction + '/source-metadata.json')) == [pax_metadata]
    abort 'FAIL: controlled Cargo fixture published an artifact' unless stdout.empty? && !File.exist?(extraction + '/receipt.json') && !File.exist?(extraction + '/' + CssVendor::ARCHIVE)
    abort 'FAIL: source archive changed during extraction' unless Digest::SHA256.file(archive).hexdigest == CssVendor::SOURCE_SHA
    changed_archive = work + '/changed-source.tar.gz'
    File.binwrite(changed_archive, File.binread(archive) + 'changed')
    _, stderr, status = Open3.capture3(RbConfig.ruby, helper, changed_archive, host, work + '/untrusted')
    abort 'FAIL: source pin was bypassed before metadata extraction' unless status.exitstatus == 1 && stderr.include?('Upstream archive checksum mismatch') && !File.exist?(work + '/untrusted')
  end
  puts 'PASS: actual pinned upstream archive, Cargo.lock and reviewed 61-crate closure'
  puts 'PASS: actual source CLI extraction reaches controlled Cargo boundary (fixture only; no native Cargo acceptance)'
end
puts 'PASS: exact pinned global PAX comment retained; other PAX types, names and directives rejected'
puts 'PASS: locked crate checksums, complete vendor files/licenses and deterministic readable USTAR'
