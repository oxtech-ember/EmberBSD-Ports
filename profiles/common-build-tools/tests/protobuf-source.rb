#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); ordinary package source and host-tool checks.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'

abort 'Usage: protobuf-source.rb EXPORTED_PKGSRC MAKECONF DISTFILES HOST_PROTOC NEW_WORK' unless ARGV.length == 5
tree, makeconf, distfiles, protoc = ARGV.take(4).map { |path| File.realpath(path) }
work = File.expand_path(ARGV[4])
abort 'Use absolute portable paths.' unless [tree, makeconf, distfiles, protoc, work].all? { |p| p.match?(%r{\A/[A-Za-z0-9_./-]+\z}) }
abort 'Output exists.' if File.exist?(work) || File.symlink?(work)
root = File.expand_path('../../..', __dir__)
probe = root + '/probes/kicad/protobuf'
archive = distfiles + '/protobuf-36.2.tar.gz'
File.readlines(probe + '/sources.sha256').each do |line|
  sha, name = line.split
  abort "Wrong archive #{name}" unless Digest::SHA256.file(distfiles + '/' + name).hexdigest == sha
end
local = Dir.glob(probe + '/patches/patch-*').sort
patches = Dir.glob(tree + '/devel/protobuf/patches/patch-*').sort
abort 'Expected six materialized patches.' unless patches.size == 6 && patches.all? { |p| File.file?(p) && !File.symlink?(p) }
local.each { |p| abort "Changed patch #{p}" unless File.binread(p) == File.binread(tree + '/devel/protobuf/patches/' + File.basename(p)) }
FileUtils.mkdir_p(work + '/package')
commands = []
run = lambda do |name, argv, env = {}, expected = 0|
  stdout, stderr, status = Open3.capture3({ 'LC_ALL' => 'C' }.merge(env), *argv)
  File.write(work + '/' + name + '.stdout', stdout)
  File.write(work + '/' + name + '.stderr', stderr)
  commands << { name: name, argv: argv, status: status.exitstatus }
  File.write(work + '/commands.json', JSON.pretty_generate(commands) + "\n")
  abort "Unexpected #{name} status #{status.exitstatus}" unless expected == :nonzero ? !status.success? : status.exitstatus == expected
  stdout
end
bmake = ENV.fetch('BMAKE', 'bmake')
make = [bmake, '-C', tree + '/devel/protobuf', "MAKECONF=#{makeconf}",
        "WRKDIR=#{work}/package", "WRKOBJDIR=#{work}/objects", "PACKAGES=#{work}/packages",
        "DISTDIR=#{distfiles}", '_PKGSRC_BARRIER=yes']
metadata = %w[PKGNAME PKG_FAIL_REASON WRKSRC CONFIGURE_ARGS CMAKE_CONFIGURE_ARGS DEPENDS TOOL_DEPENDS USE_CROSS_COMPILE OPSYS].to_h do |name|
  [name, run.call('metadata-' + name, make + ['show-var', "VARNAME=#{name}"]).strip]
end
cross_split = metadata['USE_CROSS_COMPILE'].downcase == 'yes' && metadata['OPSYS'] == 'NetBSD'
expected_name = cross_split ? 'protobuf-36.2nb1' : 'protobuf-36.2'
abort 'Wrong recipe metadata.' unless metadata['PKGNAME'] == expected_name && metadata['PKG_FAIL_REASON'].empty?
abort 'Non-private source path.' unless metadata['WRKSRC'] == work + '/package/protobuf-36.2'
%w[-Dprotobuf_LOCAL_DEPENDENCIES_ONLY=ON -Dprotobuf_BUILD_SHARED_LIBS=ON].each do |flag|
  abort "Missing #{flag}" unless Shellwords.split(metadata['CMAKE_CONFIGURE_ARGS']).include?(flag)
end
run.call('archive-checksum', make + ['checksum'])
run.call('extract', ['tar', '-xzf', archive, '-C', work + '/package'])
run.call('pkgsrc-patch', make + ['do-pkgsrc-patch'])
FileUtils.mkdir_p(work + '/probe/downloads')
%w[protobuf-36.2.tar.gz abseil-cpp-20260817.0.tar.gz].each do |name|
  FileUtils.cp(distfiles + '/' + name, work + '/probe/downloads/' + name)
end
run.call('probe-prepare', ['sh', probe + '/build.sh', 'prepare'],
         { 'PROTOBUF_WORK' => work + '/probe', 'PKGSRC_BASE' => tree })
expected = work + '/probe/protobuf-36.2'
actual = metadata['WRKSRC']
# Compare release inputs, not implementation-specific GNU/BSD patch backups.
# Real upstream .orig files, if any, remain in this archive-derived list.
listed = run.call('archive-file-list', ['tar', '-tzf', archive]).lines.map(&:strip)
files = listed.filter_map do |entry|
  abort 'Unexpected archive path.' unless entry.start_with?('protobuf-36.2/')
  path = expected + '/' + entry.delete_prefix('protobuf-36.2/')
  path if File.file?(path)
end
files.each do |path|
  relative = path.delete_prefix(expected + '/')
  abort "Prepared source differs: #{relative}" unless File.file?(actual + '/' + relative) && File.binread(path) == File.binread(actual + '/' + relative)
end

# A new fixture recipe exercises the real exported fragment without dependency
# installation. The default path is metadata-only; the positive external tool
# is the real accepted native executable supplied by the caller.
# Keep the supplied export unchanged. The private source view shares its
# read-only recipes and framework, except for this one synthetic consumer.
host_tree = work + '/host-tree'
FileUtils.mkdir_p(host_tree + '/devel')
Dir.children(tree).reject { |n| n == 'devel' }.each { |n| File.symlink(tree + '/' + n, host_tree + '/' + n) }
Dir.children(tree + '/devel').each { |n| File.symlink(tree + '/devel/' + n, host_tree + '/devel/' + n) }
fixture = host_tree + '/devel/ember-protobuf-host-check'
abort 'Fixture recipe exists.' if File.exist?(fixture) || File.symlink?(fixture)
FileUtils.mkdir_p(fixture)
File.write(fixture + '/Makefile', <<~MAKE)
  DISTNAME=ember-protobuf-host-check-1
  CATEGORIES=devel
  USE_LANGUAGES=
  NO_BUILD=yes
  .include "../../devel/protobuf/host-protoc.mk"
  .include "../../mk/bsd.pkg.mk"
MAKE
host_make = [bmake, '-C', fixture, "MAKECONF=#{makeconf}", "WRKDIR=#{work}/host-work", '_PKGSRC_BARRIER=yes']
default = run.call('host-default-dependency', host_make + ['show-var', 'VARNAME=TOOL_DEPENDS'])
abort 'Missing actual default native dependency.' unless Shellwords.split(default).include?('protobuf-36.2{,nb[0-9]*}:../../devel/protobuf')
sha = Digest::SHA256.file(protoc).hexdigest
explicit = ["EMBERBSD_BUILD_PROTOC=#{protoc}", "EMBERBSD_BUILD_PROTOC_SHA256=#{sha}"]
selected = run.call('host-explicit-dependency', host_make + explicit + ['show-var', 'VARNAME=TOOL_DEPENDS'])
abort 'Explicit provider retains recursive host dependency.' if selected.include?('protobuf-36.2')
run.call('host-real-positive', host_make + explicit + ['protobuf-host-tool-check'])
run.call('host-wrong-hash', host_make + ["EMBERBSD_BUILD_PROTOC=#{protoc}", 'EMBERBSD_BUILD_PROTOC_SHA256=' + '0' * 64, 'protobuf-host-tool-check'], {}, :nonzero)
run.call('host-malformed-hash', host_make + ["EMBERBSD_BUILD_PROTOC=#{protoc}", 'EMBERBSD_BUILD_PROTOC_SHA256=xyz', 'protobuf-host-tool-check'], {}, :nonzero)
missing = run.call('host-missing-hash', host_make + ["EMBERBSD_BUILD_PROTOC=#{protoc}", 'show-var', 'VARNAME=PKG_FAIL_REASON'])
abort 'Missing hash not rejected.' unless missing.include?('EMBERBSD_BUILD_PROTOC_SHA256')
# This negative executable deliberately has the wrong version. It cannot satisfy
# the positive test and is never used as a package or generator provider.
wrong = work + '/wrong-version'
File.write(wrong, "#!/bin/sh\nprintf '%s\\n' 'libprotoc 36.1'\n")
File.chmod(0755, wrong)
run.call('host-wrong-version', host_make + ["EMBERBSD_BUILD_PROTOC=#{wrong}", "EMBERBSD_BUILD_PROTOC_SHA256=#{Digest::SHA256.file(wrong).hexdigest}", 'protobuf-host-tool-check'], {}, :nonzero)
File.write(wrong, "#!/bin/sh\nprintf '%s\\n' 'libprotoc 36.2'\nexit 1\n")
run.call('host-failed-version-command', host_make + ["EMBERBSD_BUILD_PROTOC=#{wrong}", "EMBERBSD_BUILD_PROTOC_SHA256=#{Digest::SHA256.file(wrong).hexdigest}", 'protobuf-host-tool-check'], {}, :nonzero)
File.write(work + '/result.json', JSON.pretty_generate({
  scope: 'Actual pkgsrc checksum/patch and host-protoc checks; no package install or target execution.',
  metadata: metadata, compared_source_files: files.size, host_protoc: protoc, host_protoc_sha256: sha,
  inputs: (patches + [tree + '/devel/protobuf/Makefile', tree + '/devel/protobuf/host-protoc.mk', archive, makeconf]).to_h { |p| [p, Digest::SHA256.file(p).hexdigest] }
}) + "\n")
puts "PASS: protobuf 36.2 metadata, six patches, #{files.size} source files and real host-protoc selection."
