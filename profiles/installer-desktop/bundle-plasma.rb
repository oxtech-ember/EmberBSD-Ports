#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Audit an amd64 Plasma set for installation media.
require 'digest'
require 'fiddle'
require 'fileutils'
require 'json'
require 'open3'
require 'rbconfig'
require 'tmpdir'

MANIFESTS = %w[packages.sha256 install-order.txt roots.txt target.txt].freeze
PROGRAMS = %w[startplasma-wayland kwin_wayland plasmashell Xwayland dbus-run-session].freeze
INSTALLER_LIMIT = 512 * 1024 * 1024

def check(condition, message)
  raise message unless condition
end

def run!(environment, *command)
  output, error, status = Open3.capture3(environment, *command)
  check(status.success?, "Command failed: #{File.basename(command.first)}\n#{output}#{error}")
  output
end

def fingerprint(directory)
  packages = File.join(directory, 'packages')
  check(File.directory?(packages) && !File.symlink?(packages), 'Missing regular packages directory')
  names = Dir.children(packages).sort
  check(!names.empty?, 'Empty package set')
  names.each do |name|
    check(/\A[A-Za-z0-9][A-Za-z0-9_.+\-]*-[0-9][A-Za-z0-9_.+\-]*\.tgz\z/.match?(name), 'Unsafe package filename')
  end
  (MANIFESTS + names.map { |name| "packages/#{name}" }).to_h do |relative|
    path = File.join(directory, relative)
    check(File.file?(path) && !File.symlink?(path), "Missing regular #{relative}")
    [relative, Digest::SHA256.file(path).hexdigest]
  end
end

# The destination must not appear between a Ruby existence check and rename.
# These native operations reject an existing file, directory or symlink atomically.
def publish_directory(source, destination)
  library = Fiddle::Handle::DEFAULT
  if RUBY_PLATFORM.include?('darwin')
    function = Fiddle::Function.new(library['renamex_np'],
                                   [Fiddle::TYPE_VOIDP, Fiddle::TYPE_VOIDP, Fiddle::TYPE_INT], Fiddle::TYPE_INT)
    result = function.call(source, destination, 0x00000004) # RENAME_EXCL
  elsif RUBY_PLATFORM.include?('linux')
    function = Fiddle::Function.new(library['renameat2'],
                                   [Fiddle::TYPE_INT, Fiddle::TYPE_VOIDP, Fiddle::TYPE_INT,
                                    Fiddle::TYPE_VOIDP, Fiddle::TYPE_INT], Fiddle::TYPE_INT)
    result = function.call(-100, source, -100, destination, 1) # AT_FDCWD, RENAME_NOREPLACE
  else
    raise 'Atomic no-replace publication requires macOS or Linux'
  end
  raise SystemCallError.new('Cannot publish bundle output', Fiddle.last_error) unless result.zero?
end

def source_revision
  revision, _error, status = Open3.capture3('git', '-C', __dir__, 'rev-parse', 'HEAD')
  return nil unless status.success?
  changes, _error, status = Open3.capture3('git', '-C', __dir__, 'status', '--porcelain')
  { 'revision' => revision.strip, 'working_tree_clean' => status.success? && changes.empty? }
rescue Errno::ENOENT
  nil
end

def installed_files(contents, archive)
  files = {}
  cwd = nil
  lines = contents.lines.map(&:chomp)
  index = 0
  while index < lines.length
    line = lines[index]
    if line == '@ignore'
      index += 1
    elsif line.start_with?('@cwd ')
      cwd = line.delete_prefix('@cwd ')
    elsif !line.empty? && !line.start_with?('@')
      check(cwd&.start_with?('/'), 'Package has no absolute installation prefix')
      path = File.expand_path(line, cwd)
      link = lines[index + 1].to_s[/\A@comment Symlink:(.*)\z/, 1]
      check(!files.key?(path), "Duplicate installed path: #{path}")
      files[path] = { archive: archive, member: line, symlink: link }
    end
    index += 1
  end
  files
end

def executable_provider(files, path, tar, environment)
  visited = []
  loop do
    check(!visited.include?(path), "Plasma program symlink cycle: #{path}")
    visited << path
    entry = files[path]
    check(entry, "Missing Plasma program: #{path}")
    if entry[:symlink]
      path = File.expand_path(entry[:symlink], File.dirname(path))
      next
    end
    listing = run!(environment, tar, '-tvf', entry.fetch(:archive), '--', entry.fetch(:member)).lines
    check(listing.length == 1, "Ambiguous Plasma program archive entry: #{path}")
    mode = listing.first.byteslice(0, 10)
    executable = mode&.match?(/\A[-h][rwxStTs-]{9}\z/) && [3, 6, 9].any? { |index| 'xst'.include?(mode[index]) }
    check(executable, "Plasma program is not executable: #{path}")
    return File.basename(entry.fetch(:archive), '.tgz')
  end
end

Signal.trap('TERM') { raise Interrupt, 'Bundle interrupted' }
begin
  check(ARGV.length == 2, 'Usage: bundle-plasma.rb AMD64_PACKAGE_SET NEW_OUTPUT')
  source = File.realpath(ARGV[0])
  output = File.expand_path(ARGV[1])
  check(!File.exist?(output) && !File.symlink?(output), 'Output already exists')
  parent = File.realpath(File.dirname(output))
  output = File.join(parent, File.basename(output))
  check(!output.start_with?(source + '/'), 'Output must be outside the source package set')
  source_hashes = fingerprint(source)
  python = ENV.fetch('PYTHON', 'python3')
  sdk = ENV.fetch('EMBERBSD_SDK_SOURCE')
  check(sdk.start_with?('/'), 'SDK source must be an absolute path')
  sdk = File.realpath(sdk)
  tar = ENV.fetch('BSDTAR', 'bsdtar')
  environment = { 'BSDTAR' => tar, 'COPYFILE_DISABLE' => '1', 'TAR_OPTIONS' => nil }
  check(run!(environment, tar, '--version').include?('libarchive'), 'Use bsdtar/libarchive')
  cross = File.expand_path('../../probes/plasma-mobile/toolkit/cross', __dir__)
  installer = File.join(cross, 'install-package-set.sh')
  auditor = File.join(cross, 'prepare-package-set.py')
  workspace = Dir.mktmpdir(".#{File.basename(output)}-", parent)
  snapshot = File.join(workspace, 'snapshot')
  FileUtils.mkdir_p(File.join(snapshot, 'packages'))
  source_hashes.each_key { |relative| FileUtils.cp(File.join(source, relative), File.join(snapshot, relative)) }
  check(fingerprint(snapshot) == source_hashes, 'Source changed while copying the package set')
  run!(environment, 'sh', installer, '--target', 'amd64', '--verify-only', snapshot)

  # Recreate only metadata, never extract or execute package payloads/scripts.
  database = File.join(workspace, 'pkgdb')
  Dir.mkdir(database)
  order = File.readlines(File.join(snapshot, 'install-order.txt'), chomp: true)
  contents = {}
  order.each do |archive|
    path = File.join(snapshot, 'packages', archive)
    plist = run!(environment, tar, '-xOf', path, '+CONTENTS')
    name = archive.delete_suffix('.tgz')
    directory = File.join(database, name)
    Dir.mkdir(directory)
    metadata = ['+CONTENTS']
    lines = plist.lines.map(&:chomp)
    lines.each_with_index { |line, index| metadata << lines.fetch(index + 1) if line == '@ignore' && lines.fetch(index + 1).start_with?('+') }
    metadata.each do |entry|
      check(/\A\+[A-Za-z0-9_.-]+\z/.match?(entry), 'Unsafe package metadata name')
      File.binwrite(File.join(directory, entry), entry == '+CONTENTS' ? plist : run!(environment, tar, '-xOf', path, entry))
    end
    contents[archive] = plist
  end
  roots = File.readlines(File.join(snapshot, 'roots.txt'), chomp: true)
  index = File.join(workspace, 'archives.txt')
  File.write(index, order.map { |name| File.join(snapshot, 'packages', name) + "\n" }.join)
  verified = File.join(workspace, 'verified')
  # A failed auditor can retain a producer with unproven ownership. Keep its
  # entire workspace even if its quarantine marker could not be written.
  audit_incomplete = true
  run!(environment, python, '-B', '-I', '-S', auditor, '--sdk-source', sdk,
       '--target', 'amd64', database, index, verified, *roots)
  audit_incomplete = false
  check(File.readlines(File.join(verified, 'install-order.txt'), chomp: true).sort == order.sort,
        'Package set contains archives outside its root dependency closure')

  files = {}
  order.each do |archive|
    installed_files(contents.fetch(archive), File.join(verified, 'packages', archive)).each do |path, entry|
      check(!files.key?(path), "Overlapping package payload: #{path}")
      files[path] = entry
    end
  end
  programs = PROGRAMS.to_h { |name| [name, executable_provider(files, "/usr/pkg/bin/#{name}", tar, environment)] }
  payload = File.join(workspace, 'payload')
  Dir.mkdir(payload)
  File.rename(File.join(verified, 'packages'), File.join(payload, 'All'))
  File.chmod(0755, File.join(payload, 'All'))
  packages = order.sort.map do |name|
    path = File.join(payload, 'All', name)
    File.chmod(0644, path)
    { 'file' => name, 'bytes' => File.size(path), 'sha256' => Digest::SHA256.file(path).hexdigest,
      'sha512' => Digest::SHA512.file(path).hexdigest }
  end
  File.write(File.join(payload, 'ROOTS'), roots.join("\n") + "\n")
  File.write(File.join(payload, 'SHA512'), packages.map { |package| "SHA512 (#{package.fetch('file')}) = #{package.fetch('sha512')}\n" }.join)
  File.write(File.join(payload, 'PROFILE'), "plasma\n")
  # The snapshot is redundant after the full audit. Keep only the verified copy.
  FileUtils.remove_entry(snapshot)
  result = File.join(workspace, 'result')
  Dir.mkdir(result)
  archive = File.join(result, 'desktop-plasma.tar.xz')
  run!(environment, tar, '--no-xattrs', '--no-acls', '--no-fflags', '--format=pax',
       '--uid', '0', '--gid', '0', '--uname', 'root', '--gname', 'wheel',
       '-cJf', archive, '-C', payload, 'All', 'ROOTS', 'SHA512', 'PROFILE')
  bytes = File.size(archive)
  checksum = Digest::SHA512.file(archive).hexdigest
  File.write(File.join(result, 'SHA512'), "SHA512 (desktop-plasma.tar.xz) = #{checksum}\n")
  provenance = {
    'format' => 'emberbsd-installer-plasma-v1', 'profile' => 'plasma',
    'target' => { 'OPSYS' => 'NetBSD', 'OS_VERSION' => '11.0', 'MACHINE_ARCH' => 'x86_64', 'OBJECT_FMT' => 'ELF' },
    'source_sha256' => source_hashes, 'roots' => roots, 'packages' => packages, 'required_programs' => programs,
    'producer' => source_revision,
    'tools_sha256' => [__FILE__, installer, auditor].to_h { |path| [File.basename(path), Digest::SHA256.file(path).hexdigest] },
    'bundle' => { 'file' => 'desktop-plasma.tar.xz', 'bytes' => bytes, 'sha512' => checksum },
    'installer_capacity' => { 'limit_bytes' => INSTALLER_LIMIT, 'fits_current_limit' => bytes <= INSTALLER_LIMIT },
    'validation' => 'Fresh native verify-only and full metadata, payload digest and target ELF audit; no target execution'
  }
  File.write(File.join(result, 'PROVENANCE.json'), JSON.pretty_generate(provenance) + "\n")
  check(fingerprint(source) == source_hashes, 'Source package set changed during bundle preparation')
  publish_directory(result, output)
  puts "SHA512 (desktop-plasma.tar.xz) = #{checksum}"
  puts "Bundle bytes: #{bytes}; current installer limit: #{INSTALLER_LIMIT}; fits: #{bytes <= INSTALLER_LIMIT}"
  puts 'Bundle exceeds the current installer capacity; OS capacity acceptance is required.' if bytes > INSTALLER_LIMIT
  puts "Prepared Plasma bundle: #{output}"
rescue Interrupt
  warn 'FAIL: Plasma bundle interrupted'
  exit 130
rescue StandardError => error
  warn "FAIL: #{error.message}"
  exit 1
ensure
  if defined?(workspace) && workspace && File.directory?(workspace)
    if defined?(audit_incomplete) && audit_incomplete
      warn "Retained incomplete auditor workspace: #{workspace}"
    else
      FileUtils.remove_entry(workspace)
    end
  end
end
