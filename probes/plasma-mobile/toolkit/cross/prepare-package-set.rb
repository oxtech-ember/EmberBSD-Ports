#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Audit and copy a target runtime package closure.
require 'digest'
require 'fileutils'
require 'open3'
require 'optparse'
require 'rubygems/package'
require 'shellwords'
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

# Execution-only desktop images must not inherit the LLVM target SDK from the
# build-host sysroot. This is an explicit LLVM23 manifest, not archive pruning.
def llvm_runtime_payload(name, paths)
  check(!name.match?(/\Allvm-devel-[0-9]/), "LLVM SDK is forbidden in the desktop runtime closure: #{name}")
  check(!name.match?(/\AlibLLVM-[0-9]/), "LLVM legacy provider is forbidden in the desktop runtime closure: #{name}")
  return unless name.match?(/\Allvm-[0-9]/)
  expected = %w[lib/libLLVM.so.23.1 lib/libLLVM-23.so lib/libLLVM.so
                lib/libLTO.so.23.1 lib/libLTO.so lib/libRemarks.so.23.1
                lib/libRemarks.so include/llvm/Support/LICENSE.TXT]
             .map { |path| '/usr/pkg/' + path }
  check(name == 'llvm-23.1.3nb1' && paths.keys.sort == expected.sort,
        "LLVM runtime package has an unprepared identity or SDK/missing payload: #{name}")
end

def relative_name(name)
  name = name.delete_prefix('./').delete_suffix('/')
  check(!name.empty? && !name.start_with?('/') && !name.match?(/[\x00-\x1f\x7f]/) &&
        name.split('/').none? { |part| ['', '.', '..'].include?(part) }, "Invalid archive path: #{name.inspect}")
  name
end

def package_manifest(contents)
  files = {}
  paths = {}
  prefix = nil
  metadata = ['+CONTENTS']
  lines = contents.lines.map(&:chomp)
  i = 0
  while i < lines.length
    line = lines[i]
    if line.start_with?('@cwd ')
      prefix = line.delete_prefix('@cwd ')
      check(prefix.start_with?('/'), "Relative package prefix: #{prefix}")
    elsif line == '@ignore'
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
      check(prefix, "Missing package prefix: #{name}")
      paths[File.join(prefix, name)] = true
      i += 1
    end
    i += 1
  end
  check(metadata.uniq.length == metadata.length, 'Duplicate metadata entry in manifest')
  [files, metadata, paths]
end

# pkg_add checks REQUIRES before extracting this package, including replacements.
# Metadata must exclude the package's own payload and name real providers.
def library_metadata(build, paths, context)
  build.each_line do |line|
    if line.start_with?('PROVIDES=')
      path = line.delete_prefix('PROVIDES=').chomp
      check(paths.key?(path), "PROVIDES is absent from the manifest: #{path}: #{context}")
    elsif line.start_with?('REQUIRES=')
      path = line.delete_prefix('REQUIRES=').chomp
      check(!paths.key?(path), "REQUIRES names the package's own payload: #{path}: #{context}")
    end
  end
end

# These are executable substitutions in pkgsrc's mk/pkginstall templates.
# Inspect serialized values, including helper scripts stored in here-documents.
# This is a portability check, not a shell parser or an execution sandbox.
SCRIPT_HELPERS = %w[
  AWK BASENAME CAT CHGRP CHMOD CHOWN CMP CP DIRNAME ECHO ECHO_N EGREP EXPR
  FALSE FIND GREP GROUPADD GTAR HEAD ID INSTALL_INFO LINKFARM LN LS MKDIR MV
  PERL5 PKG_ADMIN PKG_INFO PW PWD_CMD RM RMDIR SED SETENV SH SORT SU TEST
  TOUCH TR TRUE USERADD XARGS RCD_SCRIPTS_SHELL PKG_USER_SHELL
  LDCONFIG_ADD_CMD LDCONFIG_REMOVE_CMD TTF_INDEX_CMD TYPE1_INDEX_CMD
  TYPE1_POSTINDEX_CMD MKFONTDIR GTK2_UPDATE_ICON_CACHE GTK3_UPDATE_ICON_CACHE
].freeze

def install_script_paths(metadata, context)
  # The package's declared prefix can be outside the default pkgsrc locations.
  # Do not infer target prefixes from executable assignments in the script.
  prefixes = metadata.fetch('+CONTENTS').lines.grep(/^@cwd /).map { |line| line.delete_prefix('@cwd ').strip }
  prefixes += %w[/bin /sbin /usr/bin /usr/sbin /usr/libexec /usr/pkg /usr/local /usr/X11R7]
  host_root = %r{\A/(?:Volumes|Users|Applications|private/(?:tmp|var/folders)|var/folders|opt/homebrew|tmp)(?:/|\z)}
  prefixes.reject! { |prefix| prefix == '/' || prefix.match?(host_root) }
  %w[+INSTALL +DEINSTALL +REQUIRE].each do |name|
    next unless metadata.key?(name)
    metadata.fetch(name).each_line.with_index(1) do |line, number|
      value = nil
      helper = false
      if (match = /^\s*#!\s*(.*)/.match(line))
        value = match[1]
        helper = true
      elsif (match = /^\s*(?:export\s+)?([A-Z][A-Z0-9_]*)=(.*)/.match(line))
        # Shellwords removes quoting but never performs shell expansion.
        helper = SCRIPT_HELPERS.include?(match[1])
        next unless helper || match[2].match?(%r{\A\s*["']?/})
        value = Shellwords.split(match[2]).first
      end
      next unless value
      words = Shellwords.split(value)
      location = "#{context}/#{name}:#{number}"
      words.grep(%r{\A/}).each do |word|
        check(!File.expand_path(word).match?(host_root), "Host path in package script #{location}: #{word}")
      end
      executable = words.first
      next unless executable&.start_with?('/')
      # Normalize dot components before matching paths, without touching the host.
      executable = File.expand_path(executable)
      next unless helper
      check(prefixes.any? { |prefix| executable.start_with?(prefix.delete_suffix('/') + '/') },
            "Non-target executable in package script #{location}: #{executable}")
    end
  end
rescue ArgumentError => error
  raise "Invalid serialized package script in #{context}: #{error.message}"
end

# Match exact package-managed paths. A SONAME alias must be explicit payload;
# a different major version or an unrelated installed sysroot file is not enough.
def package_library_closure(snapshots, payloads)
  providers = payloads.values.flat_map(&:keys).to_h { |path| [path, true] }
  snapshots.each do |name, metadata|
    metadata.fetch('+BUILD_INFO').each_line do |line|
      next unless line.start_with?('REQUIRES=/usr/pkg/')
      path = line.delete_prefix('REQUIRES=').chomp
      check(providers.key?(path), "Package-managed requirement is absent from the set: #{name}: #{path}")
    end
  end
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
  payloads = {}
  order = []
  visit = lambda do |name|
    check(/\A[a-zA-Z0-9][a-zA-Z0-9_.+\-]*-[0-9][a-zA-Z0-9_.+\-]*\z/.match?(name), "Invalid package name: #{name}")
    return if packages[name] == :done
    check(packages[name] != :active, "Runtime dependency cycle at #{name}")
    packages[name] = :active
    contents = File.binread(File.join(pkgdb, name, '+CONTENTS'))
    check(contents.lines.grep(/^@name /) == ["@name #{name}\n"], "Package identity mismatch: #{name}")
    files, metadata, paths = package_manifest(contents)
    llvm_runtime_payload(name, paths)
    manifests[name] = files
    payloads[name] = paths
    snapshots[name] = metadata.to_h { |entry| [entry, File.binread(File.join(pkgdb, name, entry))] }
    check(snapshots[name].fetch('+CONTENTS') == contents, "Installed manifest changed during read: #{name}")
    target_metadata(snapshots[name].fetch("+BUILD_INFO"), "installed #{name}", target)
    library_metadata(snapshots[name].fetch("+BUILD_INFO"), paths, "installed #{name}")
    install_script_paths(snapshots[name], "installed #{name}")
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
  package_library_closure(snapshots, payloads)
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
      begin
        audit_archive(tar, original, snapshots.fetch(name), manifests.fetch(name), target)
      rescue StandardError => error
        failures << "#{original}: #{error.message}"
        next
      end
      FileUtils.cp(original, destination)
      check(Digest::SHA256.file(destination).hexdigest == digest, "Archive changed during copy: #{name}")
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
