#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); actual pkgsrc metadata and staging contracts.
require 'digest'
require 'fileutils'
require 'find'
require 'json'
require 'open3'
require 'timeout'

abort 'Usage: protobuf-package-split.rb PKGSRC MAKECONF PRISTINE_PROTOBUF NEW_WORK' unless ARGV.size == 4
source, makeconf, pristine = ARGV.first(3).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'New absolute output directory required.' unless ARGV.last.start_with?('/') && !File.exist?(work)
profile = File.expand_path('..', __dir__)
FileUtils.mkdir_p(work + '/pkgsrc/devel')
tree = work + '/pkgsrc'
Dir.children(source).reject { |n| n.start_with?('.') || n == 'devel' }.each do |name|
  File.symlink(source + '/' + name, tree + '/' + name)
end
Dir.children(source + '/devel').reject { |n| %w[protobuf protobuf-devel protobuf-split-consumer].include?(n) }.each do |name|
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
%w[protobuf protobuf-devel].each do |name|
  run.call('copy-' + name, ['cp', '-RL', profile + '/recipes/devel/' + name, tree + '/devel/' + name])
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
runtime = plist.call('runtime', 'protobuf', cross)
sdk = plist.call('sdk', 'protobuf-devel', cross)
owner = tree + '/devel/protobuf'
full = plist.call('full', 'protobuf', cross + ['PLIST_SRC=' + owner + '/PLIST'])
native = plist.call('native', 'protobuf', ['USE_CROSS_COMPILE=no'])
licenses = %w[share/licenses/protobuf/LICENSE share/licenses/protobuf/utf8_range-LICENSE]
expected_runtime = %w[protobuf-lite protobuf protoc utf8_range utf8_validity].flat_map { |name|
  ["lib/lib#{name}.so", "lib/lib#{name}.so.36.2.0"]
} + licenses
abort 'Wrong runtime ownership.' unless runtime.sort == expected_runtime.sort
abort 'Partitions overlap or omit full entries.' unless (runtime & sdk).empty? && (runtime + sdk).sort == full.sort
abort 'Native full manifest changed.' unless native.size == 351 && (native + licenses).sort == full.sort
%w[bin/protoc bin/protoc-gen-upb include/google/protobuf/message.h lib/libupb.a lib/cmake/protobuf/protobuf-config.cmake lib/pkgconfig/protobuf.pc].each do |path|
  abort 'SDK lost required interface: ' + path unless sdk.include?(path)
end
%w[protobuf protobuf-devel].each do |name|
  identity = query.call(name + '-identity', name, cross + ['-V', '${PKGNAME}', '-V', '${PKG_FAIL_REASON}']).lines
  abort 'Wrong package identity or failure reason.' unless identity[0].strip == name + '-36.2nb1' && identity.drop(1).join.strip.empty?
end
abort 'Native identity changed.' unless query.call('native-name', 'protobuf', ['USE_CROSS_COMPILE=no', '-V', '${PKGNAME}']).strip == 'protobuf-36.2'
sdk_fields = query.call('sdk-metadata', 'protobuf-devel', cross + ['-V', '${DEPENDS}', '-V', '${DISTINFO_FILE}', '-V', '${PATCHDIR}', '-V', '${FILESDIR}'])
abort 'SDK lost exact runtime or source owner.' unless sdk_fields.include?('protobuf-36.2nb1:../../devel/protobuf') && %w[distinfo patches files].all? { |p| sdk_fields.include?(owner + '/' + p) }
FileUtils.mkdir_p(tree + '/devel/protobuf-split-consumer')
File.write(tree + '/devel/protobuf-split-consumer/Makefile', <<~MAKE)
  DISTNAME= protobuf-split-contract-1
  CATEGORIES= devel
  COMMENT= Protobuf buildlink source contract fixture
  LICENSE= 2-clause-bsd
  META_PACKAGE= yes
  .include "../../mk/bsd.prefs.mk"
  .include "../../devel/protobuf/buildlink3.mk"
  .include "../../devel/protobuf/host-protoc.mk"
  .include "../../mk/bsd.pkg.mk"
MAKE
fields = query.call('consumer-dependencies', 'protobuf-split-consumer', cross + ['-V', '${BUILD_DEPENDS}', '-V', '${DEPENDS}', '-V', '${TOOL_DEPENDS}']).lines
abort 'SDK is not target build-only.' unless fields[0].include?('protobuf-devel>=36.2nb1:') && !fields[1].include?('protobuf-devel') && fields[1].include?('protobuf>=36.2nb1:')
abort 'Default native generator dependency changed.' unless fields[2].include?('protobuf-36.2{,nb[0-9]*}:../../devel/protobuf') && !fields[2].include?('protobuf-devel')
negatives = [
  ['wrong-part', 'protobuf', cross + ['PROTOBUF_PACKAGE_PART=devel']],
  ['wrong-revision', 'protobuf', cross + ['PKGREVISION=2']],
  ['wrong-role', 'protobuf', cross + ['EMBERBSD_PROTOBUF_DEVEL=yes']],
  ['wrong-sdk-role', 'protobuf-devel', cross + ['EMBERBSD_PROTOBUF_DEVEL=no']],
  ['unsupported-architecture', 'protobuf', cross + ['CROSS_MACHINE_ARCH=i386']],
  ['native-sdk', 'protobuf-devel', ['USE_CROSS_COMPILE=no']]
]
negatives.each do |label, package, args|
  abort 'Invalid role accepted: ' + label if query.call(label, package, args + ['-V', '${PKG_FAIL_REASON}']).strip.empty?
end
['', '/'].each_with_index do |destination, index|
  run.call("unsafe-destdir-#{index}", common + ['-C', owner] + cross +
    ['WRKDIR=' + work + "/unsafe-destdir-#{index}", 'DESTDIR=' + destination,
     'protobuf-select-stage'], false)
end
# Labelled text fixtures test exact file ownership, not target execution.
original = work + '/full-stage'
prefix = original + '/usr/pkg'
full.each do |path|
  FileUtils.mkdir_p(File.dirname(prefix + '/' + path))
  File.write(prefix + '/' + path, "source-contract fixture: #{path}\n")
end
licenses.zip(%w[LICENSE third_party/utf8_range/LICENSE]).each do |destination, input|
  FileUtils.cp(pristine + '/' + input, prefix + '/' + destination)
  File.chmod(0644, prefix + '/' + destination)
end
%w[protobuf-lite protobuf protoc utf8_range utf8_validity].each do |name|
  path = prefix + "/lib/lib#{name}.so"
  File.unlink(path)
  File.symlink("lib#{name}.so.36.2.0", path)
end
File.chmod(0555, prefix + '/lib/libprotobuf.so.36.2.0')
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
  package = part == 'runtime' ? 'protobuf' : 'protobuf-devel'
  query.call(part + '-select', package, cross + ['WRKDIR=' + work + '/' + part + '-select', 'WRKSRC=' + pristine, 'DESTDIR=' + destination, 'protobuf-select-stage'])
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
    path = stage + '/lib/libprotobuf.so'
    File.unlink(path)
    File.symlink(name == 'escaping-link' ? '../../../outside' : '../bin/protoc', path)
  when 'part' then part = 'unsupported'
  end
  unchanged = fingerprint.call(stage)
  run.call('reject-' + name, [ENV.fetch('PERL', '/usr/bin/perl'), helper, part, stage, *lists], false)
  abort 'Rejected input changed stage: ' + name unless fingerprint.call(stage) == unchanged
end
File.write(work + '/result.json', JSON.pretty_generate({
  scope: 'Actual pkgsrc metadata and labelled staging fixtures; no package compilation, installation or target execution.',
  runtime_entries: runtime.size, sdk_entries: sdk.size, native_entries: native.size,
  exhaustive_disjoint: true, native_full_preserved: true, role_negatives: negatives.map(&:first),
  unsafe_destdir_negatives: ['', '/'],
  payload_negatives: %w[missing unknown overlap union selected symlink-parent escaping-link runtime-sdk-link part],
  licenses: %w[LICENSE third_party/utf8_range/LICENSE].to_h { |p| [p, Digest::SHA256.file(pristine + '/' + p).hexdigest] }
}) + "\n")
puts 'PASS: real runtime/SDK pkgsrc ownership, native package, host generator, stage bytes and rejection controls.'
