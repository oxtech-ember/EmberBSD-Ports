#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Audit and copy a target runtime package closure.
require 'digest'
require 'fileutils'
require 'open3'
require 'optparse'
require 'rubygems/package'
require 'tmpdir'

# TarReader needs a position even when libarchive writes to a non-seekable pipe.
class TarStream
  attr_reader :pos
  def initialize(io)
    @io = io
    @pos = 0
  end
  def read(length = nil)
    data = @io.read(length)
    @pos += data.bytesize if data
    data
  end
  def eof?
    @io.eof?
  end
end

def check(condition, message)
  raise message unless condition
end

TARGETS = {
  'aarch64' => { arch: 'aarch64', machine: 183 },
  'amd64' => { arch: 'x86_64', machine: 62 }
}.freeze

def target_metadata(build, context, target)
  { 'OPSYS' => 'NetBSD', 'OS_VERSION' => '11.0',
    'MACHINE_ARCH' => target.fetch(:arch), 'OBJECT_FMT' => 'ELF' }.each do |key, value|
    check(build.lines.grep(/^#{key}=/) == ["#{key}=#{value}\n"], "Wrong target #{key} in #{context}")
  end
end

def relative_name(name)
  name = name.delete_prefix('./').delete_suffix('/')
  check(!name.empty? && !name.start_with?('/') && !name.match?(/[\x00-\x1f\x7f]/) &&
        name.split('/').none? { |part| ['', '.', '..'].include?(part) }, "Invalid archive path: #{name.inspect}")
  name
end

def package_manifest(contents)
  files = {}
  metadata = ['+CONTENTS']
  lines = contents.lines.map(&:chomp)
  i = 0
  while i < lines.length
    line = lines[i]
    if line == '@ignore'
      i += 1
      ignored = lines.fetch(i)
      metadata << relative_name(ignored) if ignored.start_with?('+')
    elsif !line.empty? && !line.start_with?('@')
      name = relative_name(line)
      check(!files.key?(name), "Duplicate manifest file: #{name}")
      comment = lines[i + 1]
      match = /\A@comment (MD5:([0-9a-f]{32})|Symlink:(.*))\z/.match(comment.to_s)
      check(match, "Missing file digest or symlink target: #{name}")
      files[name] = match[2] ? [:file, match[2]] : [:symlink, match[3]]
      i += 1
    end
    i += 1
  end
  check(metadata.uniq.length == metadata.length, 'Duplicate metadata entry in manifest')
  [files, metadata]
end

# PAX records use byte counts, not newline splitting. Paths and links can be long.
def pax_records(data)
  values = {}
  until data.empty?
    match = /\A([1-9][0-9]*) /.match(data)
    check(match, 'Malformed PAX record length')
    length = Integer(match[1])
    check(length <= data.bytesize && length > match[0].bytesize + 2, 'Truncated PAX record')
    record = data.byteslice(match[0].bytesize, length - match[0].bytesize)
    check(record.end_with?("\n") && record.include?('='), 'Malformed PAX value')
    key, value = record.delete_suffix("\n").split('=', 2)
    check(!key.start_with?('GNU.sparse') && key != 'SCHILY.realsize', 'Sparse package members are unsupported')
    values[key] = value
    data = data.byteslice(length..)
  end
  values
end

def archive_members(tar, path, target)
  members = {}
  global = {}
  local = {}
  # libarchive validates the input and emits PAX tar; no file is extracted.
  Open3.popen3(tar, '-cf', '-', '--format=pax', "@#{path}") do |input, stream, error, process|
    input.close
    errors = Thread.new { error.read }
    begin
      Gem::Package::TarReader.new(TarStream.new(stream)) do |reader|
        reader.each do |entry|
          type = entry.header.typeflag
          if ['x', 'g'].include?(type)
            check(entry.size <= 1_048_576, 'Oversized PAX header')
            records = pax_records(entry.read)
            if type == 'g'
              records.each { |key, value| value.empty? ? global.delete(key) : global[key] = value }
            else
              local.merge!(records)
            end
            next
          end
          attributes = global.merge(local).reject { |_key, value| value.empty? }
          local = {}
          check(!attributes.key?('size') || Integer(attributes['size']) == entry.size, 'Unsupported PAX size override')
          name = relative_name(attributes.fetch('path', entry.full_name).b)
          link = attributes.fetch('linkpath', entry.header.linkname).b
          check(!members.key?(name), "Duplicate archive member: #{name}")
          case type
          when '0', ''
            md5 = Digest::MD5.new
            data = name.start_with?('+') ? ''.b : nil
            header = ''.b
            while (chunk = entry.read(1_048_576)) && !chunk.empty?
              md5.update(chunk)
              header << chunk.byteslice(0, 64 - header.bytesize) if header.bytesize < 64
              data << chunk if data
              check(!data || data.bytesize <= 16_777_216, "Oversized package metadata: #{name}")
            end
            check(entry.bytes_read == entry.size, "Truncated archive member: #{name}")
            if header.start_with?("\x7fELF".b)
              check(header.bytesize == 64, "Truncated ELF header: #{name}")
              check(header.getbyte(4) == 2, "Unsupported ELF class: #{name}")
              check(header.getbyte(5) == 1, "Unsupported ELF byte order: #{name}")
              machine = header.byteslice(18, 2).unpack1('v')
              check(machine == target.fetch(:machine), "Wrong ELF machine #{machine}: #{name}")
            end
            members[name] = [:file, md5.hexdigest, data]
          when '1'
            members[name] = [:hardlink, relative_name(link)]
          when '2'
            members[name] = [:symlink, link]
          when '5'
            members[name] = [:directory]
          else
            raise "Unsupported archive member type #{type.inspect}: #{name}"
          end
        end
      end
      # Drain padding so the producer can finish and report archive errors.
      stream.read(1_048_576) until stream.eof?
      check(process.value.success?, "Cannot read archive #{path}: #{errors.value}")
    ensure
      stream.close unless stream.closed?
      errors.join
    end
  end
  check(local.empty?, 'PAX header has no following member')
  members
end

def audit_archive(tar, path, expected, files, target)
  members = archive_members(tar, path, target)
  build = members.fetch('+BUILD_INFO', [])[2]
  check(build, "Missing regular +BUILD_INFO: #{path}")
  target_metadata(build, path, target)
  expected.each do |name, bytes|
    check(members[name]&.first == :file && members[name][2] == bytes, "Archive metadata mismatch #{name}: #{path}")
  end
  resolve = lambda do |name, seen|
    check(!seen.include?(name), "Hardlink cycle: #{name}")
    member = members[name]
    check(member, "Missing archive member: #{name}")
    member.first == :hardlink ? resolve.call(member[1], seen + [name]) : member
  end
  files.each do |name, wanted|
    actual = resolve.call(name, [])
    check(actual[0, 2] == wanted, "Archive payload mismatch #{name}: #{path}")
  end
  allowed = (files.keys + expected.keys).to_h { |name| [name, true] }
  members.each do |name, member|
    next if allowed.include?(name)
    next if member.first == :directory && files.keys.any? { |file| file.start_with?("#{name}/") }
    raise "Unlisted archive member #{name}: #{path}"
  end
end

Signal.trap('TERM') { raise Interrupt, 'Package audit interrupted' }

begin
  target_name = 'aarch64'
  target_seen = false
  options = OptionParser.new do |parser|
    parser.banner = 'Usage: prepare-package-set.rb [--target aarch64|amd64] PKGDB ARCHIVE_PATHS NEW_OUTPUT ROOT_PACKAGE...'
    parser.on('--target TARGET') do |name|
      check(!target_seen, 'Duplicate target option')
      check(TARGETS.key?(name), "Unsupported target: #{name}")
      target_name = name
      target_seen = true
    end
  end
  options.order!
  target = TARGETS.fetch(target_name)
  check(ARGV.length >= 4, options.banner)
  pkgdb, index, output, *roots = ARGV
  check(roots.uniq.length == roots.length, 'Duplicate root package')
  pkgdb = File.realpath(pkgdb)
  output = File.expand_path(output)
  check(!File.exist?(output) && !File.symlink?(output), 'Output already exists')
  info = ENV.fetch('PKG_INFO', 'pkg_info')
  tar = ENV.fetch('BSDTAR', 'bsdtar')
  version, error, status = Open3.capture3(tar, '--version')
  check(status.success? && version.include?('libarchive'), "Use bsdtar/libarchive: #{error}")
  archives = File.readlines(index, chomp: true).reject(&:empty?).map { |path| File.expand_path(path) }
                 .group_by { |path| File.basename(path, '.tgz') }
  cache = {}
  packages = {}
  snapshots = {}
  manifests = {}
  order = []
  visit = lambda do |name|
    check(/\A[a-zA-Z0-9][a-zA-Z0-9_.+\-]*-[0-9][a-zA-Z0-9_.+\-]*\z/.match?(name), "Invalid package name: #{name}")
    return if packages[name] == :done
    check(packages[name] != :active, "Runtime dependency cycle at #{name}")
    packages[name] = :active
    contents = File.binread(File.join(pkgdb, name, '+CONTENTS'))
    check(contents.lines.grep(/^@name /) == ["@name #{name}\n"], "Package identity mismatch: #{name}")
    files, metadata = package_manifest(contents)
    manifests[name] = files
    snapshots[name] = metadata.to_h { |entry| [entry, File.binread(File.join(pkgdb, name, entry))] }
    check(snapshots[name].fetch('+CONTENTS') == contents, "Installed manifest changed during read: #{name}")
    target_metadata(snapshots[name].fetch('+BUILD_INFO'), "installed #{name}", target)
    contents.lines.grep(/^@pkgdep /).each do |line|
      pattern = line.delete_prefix('@pkgdep ').strip
      selected = cache[pattern] ||= begin
        out, err, result = Open3.capture3(info, '-K', pkgdb, '-e', pattern)
        names = out.lines.map(&:strip)
        check(result.success? && names.length == 1, "Unresolved or ambiguous dependency #{name}: #{pattern}: #{err}")
        names.first
      end
      visit.call(selected)
    end
    packages[name] = :done
    order << name
  end
  roots.each { |name| visit.call(name) }
  # Only a complete, verified directory is renamed to the advertised output.
  staging = Dir.mktmpdir(".#{File.basename(output)}-", File.dirname(output))
  FileUtils.mkdir(File.join(staging, 'packages'))
  hashes = []
  order.each do |name|
    expected = snapshots[name].fetch('+CONTENTS')
    candidates = (archives[name] || []).select { |path| File.file?(path) }
    candidates = candidates.uniq { |path| stat = File.stat(path); [stat.dev, stat.ino] }
    accepted = false
    failures = []
    candidates.each do |original|
      data, _err, result = Open3.capture3(tar, '-xOf', original, '+CONTENTS')
      next unless result.success? && data == expected
      destination = File.join(staging, 'packages', "#{name}.tgz")
      digest = Digest::SHA256.file(original).hexdigest
      FileUtils.cp(original, destination)
      check(Digest::SHA256.file(destination).hexdigest == digest, "Archive changed during copy: #{name}")
      begin
        audit_archive(tar, destination, snapshots.fetch(name), manifests.fetch(name), target)
      rescue StandardError => error
        failures << "#{original}: #{error.message}"
        next
      end
      hashes << "#{digest}  packages/#{name}.tgz\n"
      accepted = true
      break
    end
    reason = if failures.empty?
               "No archive with the installed manifest: #{name} (#{candidates.length} candidates)"
             else
               "No verified archive for #{name}:\n#{failures.join("\n")}"
             end
    check(accepted, reason)
  end
  snapshots.each do |name, metadata|
    metadata.each do |entry, bytes|
      check(File.binread(File.join(pkgdb, name, entry)) == bytes, "Installed metadata changed during audit: #{name}/#{entry}")
    end
  end
  File.write(File.join(staging, 'packages.sha256'), hashes.join)
  File.write(File.join(staging, 'install-order.txt'), order.map { |name| "#{name}.tgz\n" }.join)
  File.write(File.join(staging, 'roots.txt'), roots.join("\n") + "\n")
  File.write(File.join(staging, 'target.txt'), "OPSYS=NetBSD\nOS_VERSION=11.0\nMACHINE_ARCH=#{target.fetch(:arch)}\nOBJECT_FMT=ELF\n")
  check(!File.exist?(output) && !File.symlink?(output), 'Output appeared during audit')
  File.rename(staging, output)
  staging = nil
  puts "PASS: #{order.length} NetBSD 11.0/#{target_name} packages; archived payload, ELF headers, metadata and copied SHA256 verified"
  puts "Package files: #{output}"
rescue Interrupt
  warn 'FAIL: package audit interrupted'
  exit 130
rescue StandardError => error
  warn "FAIL: #{error.message}"
  exit 1
ensure
  FileUtils.remove_entry(staging) if defined?(staging) && staging && File.directory?(staging)
end
