#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted reproducible host-only vendor preparation.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'rubygems/package'
require 'zlib'

module CssVendor
  class Error < StandardError; end
  SOURCE_SHA = '97bf4670e565bf43ae77348af74a38c1b432fc5dfa47ab15c375e04331fdb8e1'.freeze
  SOURCE_PAX_COMMENT = "52 comment=d7bd0b6a6ca1db88a8189aee81498f194f1e45a5\n".freeze
  LOCK_SHA = 'd2fa05be2697e96e1c2f11dfa361266938ea75c6eb6977d8d292f288ed79d031'.freeze
  RUST_COMMIT = 'b940084d7eb6a299eb4bfeb8e34901bc051e7ac4'.freeze
  ARCHIVE = 'cxx-rust-cssparser-vendor-1.1.0-r1.tar'.freeze
  module_function

  def need(condition, message)
    raise Error, message unless condition
  end

  def safe_name(name)
    need(!name.start_with?('/') && name.split('/').none? { |p| p == '..' || p.empty? } && !name.include?("\0"), 'Unsafe archive path')
    name
  end

  # The hash-pinned GitHub archive has this one global commit comment.
  # Accept its exact bytes, without interpreting any PAX path/link directives.
  def pinned_source_metadata(type, name, payload)
    need(type == 'g' && name == 'pax_global_header' && payload == SOURCE_PAX_COMMENT, 'Unsupported source PAX metadata')
    {'type' => type, 'name' => name, 'payload' => payload}
  end

  # This parser deliberately accepts only the pinned registry closure. The CLI
  # additionally checks the complete upstream lock file before parsing it.
  def lock_packages(text)
    need(text.match?(/^version = 4$/), 'Expected Cargo.lock version 4')
    result = text.split(/^\[\[package\]\]\s*$/).drop(1).filter_map do |section|
      fields = section.scan(/^(name|version|source|checksum) = "([^"]+)"$/).to_h
      next unless fields.key?('source')
      need(fields['source'] == 'registry+https://github.com/rust-lang/crates.io-index', 'Unreviewed dependency source')
      need(fields['name'].to_s.match?(/\A[A-Za-z0-9_-]+\z/) && fields['version'].to_s.match?(/\A[0-9][A-Za-z0-9.+-]*\z/) && fields['checksum'].to_s.match?(/\A[0-9a-f]{64}\z/), 'Invalid locked crate identity/checksum')
      fields.reject { |key, _| key == 'source' }
    end
    need(!result.empty? && result.map { |p| [p['name'], p['version']] }.uniq.length == result.length, 'Empty or duplicate crate closure')
    result
  end

  def paths(root)
    Dir.glob(root + '/**/*', File::FNM_DOTMATCH).reject { |p| ['.', '..'].include?(File.basename(p)) }.sort.each do |path|
      need(!File.symlink?(path) && (File.file?(path) || File.directory?(path)), 'Symlink or special file in source tree')
    end
  end

  def audit(vendor, cache, packages)
    expected = packages.map { |p| p.fetch('name') + '-' + p.fetch('version') }.sort
    need(Dir.children(vendor).sort == expected, 'Vendor crate closure differs from Cargo.lock')
    licenses = 0
    packages.each do |package|
      name = package.fetch('name') + '-' + package.fetch('version')
      root = vendor + '/' + name
      need(File.directory?(root) && !File.symlink?(root), 'Invalid vendor crate directory')
      files = paths(root).select { |path| File.file?(path) }
      metadata = JSON.parse(File.read(root + '/.cargo-checksum.json'))
      need(metadata['package'] == package.fetch('checksum'), 'Vendor package checksum mismatch')
      actual = files.reject { |path| path == root + '/.cargo-checksum.json' }.to_h { |path| [path.delete_prefix(root + '/'), Digest::SHA256.file(path).hexdigest] }
      need(actual == metadata['files'], 'Incomplete or changed vendor file checksums')
      archives = Dir.glob(cache + '/*/' + name + '.crate')
      need(archives.length == 1 && !File.symlink?(archives.first) && Digest::SHA256.file(archives.first).hexdigest == package.fetch('checksum'), 'Registry archive does not match Cargo.lock')
      original_files = {}
      Zlib::GzipReader.open(archives.first) do |gzip|
        Gem::Package::TarReader.new(gzip) do |tar|
          tar.each do |entry|
            relative = safe_name(entry.full_name.sub(%r{/\z}, ''))
            need(relative == name || relative.start_with?(name + '/'), 'Registry crate has a foreign root')
            need(entry.file? || entry.directory?, 'Registry crate contains a special file')
            next unless entry.file?
            content = entry.read
            target = vendor + '/' + relative
            need(File.file?(target) && File.binread(target) == content, 'Original registry source/license was changed or omitted')
            original_files[relative.delete_prefix(name + '/')] = Digest::SHA256.hexdigest(content)
            licenses += 1 if File.basename(relative).match?(/\A(?:LICENSE|COPYING|NOTICE)(?:[._-].*)?\z/i)
          end
        end
      end
      need(original_files == actual, 'Vendor file set differs from original registry archive')
    end
    {'crates' => packages.length, 'license_files' => licenses}
  rescue JSON::ParserError, Errno::ENOENT => error
    raise Error, error.message
  end

  def pack(vendor, output)
    old_epoch = ENV['SOURCE_DATE_EPOCH']
    need(File.directory?(vendor) && !File.symlink?(vendor), 'Invalid vendor root')
    entries = [vendor] + paths(vendor)
    ENV['SOURCE_DATE_EPOCH'] = '0'
    File.open(output, File::WRONLY | File::CREAT | File::EXCL, 0644) do |io|
      io.binmode
      Gem::Package::TarWriter.new(io) do |tar|
        entries.each do |path|
          name = safe_name('vendor' + path.delete_prefix(vendor))
          if File.directory?(path)
            tar.mkdir(name, 0755)
          else
            mode = File.stat(path).mode & 0111 == 0 ? 0644 : 0755
            tar.add_file_simple(name, mode, File.size(path)) { |destination| File.open(path, 'rb') { |source| IO.copy_stream(source, destination) } }
          end
        end
      end
    end
    File.open(output, 'rb') do |io|
      Gem::Package::TarReader.new(io) do |tar|
        tar.each do |entry|
          h = entry.header
          need(h.uid == 0 && h.gid == 0 && h.uname == 'wheel' && h.gname == 'wheel' && h.mtime == 0 && h.magic == 'ustar' && h.version == 0, 'RubyGems USTAR metadata contract changed')
        end
      end
    end
  ensure
    ENV['SOURCE_DATE_EPOCH'] = old_epoch
  end

  def run(source_archive, host, work)
    [source_archive, host, work].each { |path| need(path.start_with?('/'), 'Absolute paths required') }
    need(Digest::SHA256.file(source_archive).hexdigest == SOURCE_SHA, 'Upstream archive checksum mismatch')
    rustc = host + '/bin/rustc'
    cargo = host + '/bin/cargo'
    rust, status = Open3.capture2(rustc, '-vV')
    need(status.success? && rust.lines.include?("commit-hash: #{RUST_COMMIT}\n") && rust.lines.include?("release: 1.99.0\n"), 'Official shared native Rust 1.99.0 required')
    native = rust[/^host: (\S+)$/, 1]
    need(native && !native.end_with?('-netbsd'), 'Build-host Rust provider required')
    cargo_version, status = Open3.capture2(cargo, '-V')
    need(status.success? && cargo_version.start_with?('cargo 1.99.0 '), 'Matching native Cargo 1.99.0 required')
    need(!File.exist?(work) && !File.symlink?(work), 'Work directory must be new')
    Dir.mkdir(work, 0700)
    source_root = work + '/cxx-rust-cssparser-1.1.0'
    source_metadata = []
    Zlib::GzipReader.open(source_archive) do |gzip|
      Gem::Package::TarReader.new(gzip) do |tar|
        tar.each do |entry|
          if ['g', 'x'].include?(entry.header.typeflag)
            need(source_metadata.empty?, 'Duplicate source PAX metadata')
            source_metadata << pinned_source_metadata(entry.header.typeflag, entry.full_name, entry.read)
            next
          end
          relative = safe_name(entry.full_name.sub(%r{/\z}, ''))
          need(relative == 'cxx-rust-cssparser-1.1.0' || relative.start_with?('cxx-rust-cssparser-1.1.0/'), 'Unexpected source root')
          destination = work + '/' + relative
          if entry.directory?
            FileUtils.mkdir_p(destination)
          else
            need(entry.file?, 'Source symlinks/special files are not supported')
            FileUtils.mkdir_p(File.dirname(destination))
            File.binwrite(destination, entry.read)
            File.chmod(entry.header.mode & 0111 == 0 ? 0644 : 0755, destination)
          end
        end
      end
    end
    need(source_metadata.length == 1, 'Pinned source PAX metadata missing')
    File.write(work + '/source-metadata.json', JSON.pretty_generate(source_metadata) + "\n")
    lock = File.read(source_root + '/rust/Cargo.lock')
    need(Digest::SHA256.hexdigest(lock) == LOCK_SHA, 'Upstream Cargo.lock checksum mismatch')
    packages = lock_packages(lock)
    manifest = packages.map { |p| [p.fetch('name'), p.fetch('version'), p.fetch('checksum')].join("\t") }.join("\n") + "\n"
    manifest_path = File.expand_path('vendor-crates.tsv', __dir__)
    need(File.binread(manifest_path) == manifest, 'Reviewed registry closure differs from Cargo.lock')
    cargo_home = work + '/cargo-home'
    vendor = work + '/vendor'
    env = {'CARGO_HOME' => cargo_home, 'RUSTC' => rustc, 'RUSTFLAGS' => nil, 'CARGO_ENCODED_RUSTFLAGS' => nil, 'RUSTC_WRAPPER' => nil, 'RUSTC_WORKSPACE_WRAPPER' => nil, 'RUSTUP_TOOLCHAIN' => nil}
    File.open(work + '/cargo-vendor.config', 'wb') do |output|
      File.open(work + '/cargo-vendor.log', 'wb') do |log|
        ok = system(env, cargo, 'vendor', '--locked', '--versioned-dirs', '--manifest-path', source_root + '/rust/Cargo.toml', vendor, chdir: work, out: output, err: log)
        need(ok, 'Cargo vendor failed; inspect cargo-vendor.log')
      end
    end
    need(File.read(source_root + '/rust/Cargo.lock') == lock, 'Cargo changed the upstream lock')
    result = audit(vendor, cargo_home + '/registry/cache', packages)
    archive = work + '/' + ARCHIVE
    pack(vendor, archive)
    receipt = result.merge('scope' => 'host-derived-cssparser-vendor-r1', 'source_sha256' => SOURCE_SHA, 'source_metadata' => source_metadata, 'lock_sha256' => LOCK_SHA, 'closure_sha256' => Digest::SHA256.hexdigest(manifest), 'helper_sha256' => Digest::SHA256.file(__FILE__).hexdigest, 'rustc' => rust, 'cargo' => cargo_version.strip, 'ruby' => RUBY_DESCRIPTION, 'rubygems' => Gem::VERSION, 'archive' => ARCHIVE, 'archive_sha256' => Digest::SHA256.file(archive).hexdigest, 'archive_size' => File.size(archive))
    File.write(work + '/receipt.json', JSON.pretty_generate(receipt) + "\n")
    puts archive
  end
end

if $PROGRAM_NAME == __FILE__
  begin
    CssVendor.need(ARGV.length == 3, 'Usage: vendor.rb UPSTREAM_ARCHIVE NATIVE_HOST_PREFIX NEW_WORK_DIRECTORY')
    CssVendor.run(*ARGV)
  rescue CssVendor::Error, SystemCallError, Gem::Package::Error, Zlib::Error => error
    warn error.message
    exit 1
  end
end
