#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); actual pkgsrc metadata and staging contracts.
require 'digest'
require 'fileutils'
require 'find'
require 'json'
require 'open3'
require 'timeout'

abort 'Usage: wayland-package-split.rb PKGSRC MAKECONF WRKSRC COMPLETE_DESTDIR NEW_WORK' unless ARGV.size == 5
source, makeconf, pristine = ARGV.first(3).map { |p| File.realpath(p) }
complete = File.realpath(ARGV[3])
work = File.expand_path(ARGV.last)
abort 'New absolute output directory required.' unless ARGV.last.start_with?('/') && !File.exist?(work)
profile = File.expand_path('..', __dir__)
FileUtils.mkdir_p(work + '/pkgsrc/devel')
tree = work + '/pkgsrc'
Dir.children(source).reject { |n| n.start_with?('.') || n == 'devel' }.each do |name|
  File.symlink(source + '/' + name, tree + '/' + name)
end
Dir.children(source + '/devel').reject { |n| %w[wayland wayland-devel wayland-split-consumer].include?(n) }.each do |name|
  File.symlink(source + '/devel/' + name, tree + '/devel/' + name)
end
commands = []
run = lambda do |label, argv, expected = true|
  output = ''
  status = nil
  Open3.popen2e(*argv, pgroup: true) do |input, stream, process|
    input.close
    reader = Thread.new { stream.read }
    begin
      status = Timeout.timeout(30) { process.value }
    rescue Timeout::Error
      Process.kill('KILL', -process.pid) rescue Errno::ESRCH
      process.value
    ensure
      output = reader.value
    end
  end
  File.write(work + '/' + label + '.log', output)
  commands << { label: label, argv: argv, status: status&.exitstatus }
  File.write(work + '/commands.json', JSON.pretty_generate(commands) + "\n")
  abort label + ': query exceeded 30 seconds' unless status
  abort label + ': unexpected status: ' + output unless status.success? == expected
  output
end
%w[wayland wayland-devel].each do |name|
  run.call('copy-' + name, ['cp', '-RL', profile + '/../../pkgsrc/devel/' + name, tree + '/devel/' + name])
end
bmake = ENV.fetch('BMAKE', 'bmake')
common = [bmake, 'MAKECONF=' + makeconf, 'WRKOBJDIR=' + work + '/objects',
          'PACKAGES=' + work + '/packages', 'DISTDIR=' + work + '/distfiles',
          'CAT=/bin/cat', 'SED=/usr/bin/sed', 'TEST=/bin/test', 'MKDIR=/bin/mkdir -p',
          'FIND=/usr/bin/find', 'INSTALL_DATA_DIR=/usr/bin/install -d',
          'INSTALL_DATA=/usr/bin/install -m 644', 'PERL5=' + ENV.fetch('PERL', '/usr/bin/perl')]
query = lambda do |label, package, args|
  run.call(label, common + ['-C', tree + '/devel/' + package] + args)
end
cross = ['USE_CROSS_COMPILE=yes']
plist = lambda do |label, package, args|
  directory = work + '/' + label
  query.call(label, package, args + ['WRKDIR=' + directory, 'plist'])
  File.readlines(directory + '/.PLIST_nokeywords', chomp: true).reject(&:empty?)
end
runtime = plist.call('runtime', 'wayland', cross)
sdk = plist.call('sdk', 'wayland-devel', cross)
owner = tree + '/devel/wayland'
full = plist.call('full', 'wayland', cross + ['PLIST_SRC=' + owner + '/PLIST'])
native = plist.call('native', 'wayland', ['USE_CROSS_COMPILE=no'])
licenses = %w[share/licenses/wayland/COPYING]
expected_runtime = %w[client cursor server].flat_map { |name|
  ["lib/libwayland-#{name}.so", "lib/libwayland-#{name}.so.0", "lib/libwayland-#{name}.so.0.26.0"]
} + %w[lib/libwayland-egl.so lib/libwayland-egl.so.1 lib/libwayland-egl.so.1.26.0] + licenses
abort 'Wrong runtime ownership.' unless runtime.sort == expected_runtime.sort
abort 'Partitions overlap or omit full entries.' unless (runtime & sdk).empty? && (runtime + sdk).sort == full.sort
abort 'Native full manifest changed.' unless native.size == 35 && (native + licenses).sort == full.sort
%w[bin/wayland-scanner include/wayland-client.h include/wayland-server.h lib/pkgconfig/wayland-client.pc lib/pkgconfig/wayland-scanner.pc share/wayland/wayland.xml].each do |path|
  abort 'SDK lost required interface: ' + path unless sdk.include?(path)
end
%w[wayland wayland-devel].each do |name|
  identity = query.call(name + '-identity', name, cross + ['-V', '${PKGNAME}', '-V', '${PKG_FAIL_REASON}']).lines
  abort 'Wrong package identity or failure reason.' unless identity[0].strip == name + '-1.26.0nb2' && identity.drop(1).join.strip.empty?
end
abort 'Native identity changed.' unless query.call('native-name', 'wayland', ['USE_CROSS_COMPILE=no', '-V', '${PKGNAME}']).strip == 'wayland-1.26.0nb2'
sdk_fields = query.call('sdk-metadata', 'wayland-devel', cross + ['-V', '${DEPENDS}', '-V', '${DISTINFO_FILE}', '-V', '${PATCHDIR}', '-V', '${FILESDIR}'])
abort 'SDK lost exact runtime or source owner.' unless sdk_fields.include?('wayland-1.26.0nb2:../../devel/wayland') && %w[distinfo patches files].all? { |p| sdk_fields.include?(owner + '/' + p) }
FileUtils.mkdir_p(tree + '/devel/wayland-split-consumer')
File.write(tree + '/devel/wayland-split-consumer/Makefile', <<~MAKE)
  DISTNAME= wayland-split-contract-1
  CATEGORIES= devel
  COMMENT= Wayland buildlink source contract fixture
  LICENSE= 2-clause-bsd
  META_PACKAGE= yes
  .include "../../mk/bsd.prefs.mk"
  .include "../../devel/wayland/buildlink3.mk"

  .include "../../mk/bsd.pkg.mk"
MAKE
fields = query.call('consumer-dependencies', 'wayland-split-consumer', cross + ['-V', '${BUILD_DEPENDS}', '-V', '${DEPENDS}', '-V', '${TOOL_DEPENDS}']).lines
abort 'SDK is not target build-only.' unless fields[0].include?('wayland-devel>=1.26.0nb2:') && !fields[1].include?('wayland-devel') && fields[1].include?('wayland>=1.26.0nb2:')
# Remove only the explicit external scanner choice. Both recipes must request
# the full native provider, not recurse into target wayland-devel.
File.write(work + '/default-scanner.conf', ".include \"#{makeconf}\"\n.undef EMBERBSD_WAYLAND_SCANNER\n")
%w[wayland wayland-devel].each do |package|
  native_tools = query.call(package + '-native-scanner', package,
    cross + ['MAKECONF=' + work + '/default-scanner.conf', '-V', '${TOOL_DEPENDS}'])
  abort 'Default native generator dependency changed.' unless native_tools.include?('wayland-1.26.0{,nb[0-9]*}:../../devel/wayland') && !native_tools.include?('wayland-devel')
end
negatives = [
  ['wrong-part', 'wayland', cross + ['WAYLAND_PACKAGE_PART=devel']],
  ['wrong-revision', 'wayland', cross + ['PKGREVISION=1']],
  ['wrong-role', 'wayland', cross + ['EMBERBSD_WAYLAND_DEVEL=yes']],
  ['wrong-sdk-role', 'wayland-devel', cross + ['EMBERBSD_WAYLAND_DEVEL=no']],
  ['unsupported-architecture', 'wayland', cross + ['CROSS_MACHINE_ARCH=i386']],
  ['native-sdk', 'wayland-devel', ['USE_CROSS_COMPILE=no']]
]
negatives.each do |label, package, args|
  abort 'Invalid role accepted: ' + label if query.call(label, package, args + ['-V', '${PKG_FAIL_REASON}']).strip.empty?
end
['', '/'].each_with_index do |destination, index|
  run.call("unsafe-destdir-#{index}", common + ['-C', owner] + cross +
    ['WRKDIR=' + work + "/unsafe-destdir-#{index}", 'DESTDIR=' + destination,
     'wayland-select-stage'], false)
end
# Copies of the genuine completed normal package stage test partitioning.
# These are not new package archives or installed packages.
original = work + '/full-stage'
FileUtils.cp_r(complete, original, preserve: true)
prefix = original + '/usr/pkg'
FileUtils.mkdir_p(prefix + '/share/licenses/wayland')
FileUtils.cp(pristine + '/COPYING', prefix + '/share/licenses/wayland/COPYING')
File.chmod(0644, prefix + '/share/licenses/wayland/COPYING')
fingerprint = lambda do |directory|
  files = {}
  Find.find(directory) do |path|
    next if File.directory?(path) && !File.symlink?(path)
    relative = path.delete_prefix(directory + '/')
    files[relative] = File.symlink?(path) ? ['symlink', File.readlink(path)] : ['file', Digest::SHA256.file(path).hexdigest, File.stat(path).mode & 07777]
  end
  files
end
before = fingerprint.call(prefix)
%w[runtime devel].each do |part|
  destination = work + '/' + part + '-stage'
  FileUtils.cp_r(original, destination, preserve: true)
  package = part == 'runtime' ? 'wayland' : 'wayland-devel'
  query.call(part + '-select', package, cross + ['WRKDIR=' + work + '/' + part + '-select', 'WRKSRC=' + pristine, 'DESTDIR=' + destination, 'wayland-select-stage'])
  selected = part == 'runtime' ? runtime : sdk
  abort 'Selected stage bytes, modes or links changed.' unless fingerprint.call(destination + '/usr/pkg') == before.select { |path, _| selected.include?(path) }
end
helper = owner + '/files/select-package-stage.pl'
%w[missing unknown overlap union selected symlink-parent escaping-link runtime-sdk-link part].each do |name|
  destination = work + '/reject-' + name
  FileUtils.cp_r(original, destination, preserve: true)
  stage = destination + '/usr/pkg'
  lists = [work + '/full/.PLIST', work + '/runtime/.PLIST', work + '/sdk/.PLIST', work + '/runtime/.PLIST']
  part = 'runtime'
  case name
  when 'missing' then File.unlink(stage + '/' + sdk.first)
  when 'unknown' then File.write(stage + '/bin/unlisted-generator', 'unlisted fixture')
  when 'overlap'
    lists[2] = destination + '/overlap.plist'
    File.write(lists[2], File.read(work + '/sdk/.PLIST') + runtime.first + "\n")
  when 'union'
    lists[2] = destination + '/incomplete.plist'
    File.write(lists[2], sdk.drop(1).join("\n") + "\n")
  when 'selected' then lists[3] = lists[2]
  when 'symlink-parent'
    FileUtils.mkdir_p(destination + '/outside')
    File.write(destination + '/outside/preserved', 'outside fixture')
    FileUtils.rm_r(stage + '/include')
    File.symlink(destination + '/outside', stage + '/include')
  when 'escaping-link', 'runtime-sdk-link'
    path = stage + '/lib/libwayland-client.so'
    File.unlink(path)
    File.symlink(name == 'escaping-link' ? '../../../outside' : '../bin/wayland-scanner', path)
  when 'part' then part = 'unsupported'
  end
  unchanged = fingerprint.call(stage)
  run.call('reject-' + name, [ENV.fetch('PERL', '/usr/bin/perl'), helper, part, stage, *lists], false)
  abort 'Rejected input changed stage: ' + name unless fingerprint.call(stage) == unchanged
end
File.write(work + '/result.json', JSON.pretty_generate({
  scope: 'Actual pkgsrc metadata and copied completed package stage; no new package compilation, installation or target execution.',
  source_stage: complete, complete_inventory: before,
  recipe_sha256: Dir.glob(profile + '/../../pkgsrc/devel/wayland{,-devel}/**/*').select { |p| File.file?(p) }.sort.to_h { |p| [p, Digest::SHA256.file(p).hexdigest] },
  runtime_entries: runtime.size, sdk_entries: sdk.size, native_entries: native.size,
  exhaustive_disjoint: true, native_full_preserved: true, role_negatives: negatives.map(&:first),
  unsafe_destdir_negatives: ['', '/'],
  payload_negatives: %w[missing unknown overlap union selected symlink-parent escaping-link runtime-sdk-link part],
  licenses: %w[COPYING].to_h { |p| [p, Digest::SHA256.file(pristine + '/' + p).hexdigest] }
}) + "\n")
puts 'PASS: runtime/SDK pkgsrc ownership, unchanged native metadata, host scanner, actual stage bytes and rejection controls.'
