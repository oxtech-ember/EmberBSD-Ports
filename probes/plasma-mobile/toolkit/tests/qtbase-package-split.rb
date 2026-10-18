#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Real pkgsrc PLIST contracts, without a Qt build.
require 'fileutils'
require 'digest'
require 'find'
require 'open3'
require 'shellwords'
require 'timeout'

abort 'Usage: qtbase-package-split.rb PKGSRC HOST_PREFIX CROSS_TOOLS SYSROOT HOST_QT NEW_WORK' unless ARGV.length == 6
source, host, tools, sysroot, qt = ARGV.first(5).map { |path| File.realpath(path) }
work = File.expand_path(ARGV.last)
abort 'new absolute work directory required' unless ARGV.last.start_with?('/') && !File.exist?(work)
FileUtils.mkdir_p(work)
tree = work + '/pkgsrc'
Dir.mkdir(tree)
toolkit = File.expand_path('..', __dir__)
# Other recipes and the actual pkgsrc framework remain read-only. Only these
# two recipes can write local files; WRKDIR and the package database are private.
Dir.children(source).reject { |name| name.start_with?('.') }.each do |name|
  if %w[x11 devel meta-pkgs].include?(name)
    Dir.mkdir(tree + '/' + name)
    Dir.children(source + '/' + name).each do |package|
      next if name == 'x11' && %w[qt6-qtbase qt6-qtbase-devel].include?(package)
      if name == 'meta-pkgs' && package == 'qt6'
        FileUtils.cp_r(source + '/meta-pkgs/qt6', tree + '/meta-pkgs/qt6')
        FileUtils.cp(toolkit + '/shared/meta-pkgs/qt6/Makefile.common', tree + '/meta-pkgs/qt6/Makefile.common')
      else
        File.symlink(source + '/' + name + '/' + package, tree + '/' + name + '/' + package)
      end
    end
  else
    File.symlink(source + '/' + name, tree + '/' + name)
  end
end
%w[qt6-qtbase qt6-qtbase-devel].each do |name|
  recipe = toolkit + '/recipes/x11/' + name
  FileUtils.cp_r(recipe, tree + '/x11/' + name) if File.directory?(recipe)
end
File.write(work + '/mk.conf', <<~MAKE)
  .include "#{host}/etc/mk.conf"
  WRKOBJDIR= #{work}/objects
  PACKAGES= #{work}/packages
  PKG_DBDIR= #{work}/pkgdb
  CXXFLAGS= -O2
MAKE
bmake = ENV.fetch('BMAKE', host + '/bin/bmake')
common = [bmake, 'MAKECONF=' + work + '/mk.conf', 'AWK=' + host + '/bin/nawk',
  'CAT=/bin/cat', 'SED=/usr/bin/sed', 'TEST=/bin/test', 'MKDIR=/bin/mkdir -p',
  'PERL5=' + host + '/bin/perl', 'FIND=/usr/bin/find', 'LN=/bin/ln',
  'INSTALL_DATA_DIR=/usr/bin/install -d',
  'X11_TYPE=modular', 'PLATFORM_SUPPORTS_WAYLAND=no',
  'EMBERBSD_QT_HOST_PATH=' + qt]
# Cache actual SDK lookup results rather than repeating xcrun --no-cache for
# every make parse. Missing SDK tools retain the framework's empty result.
%w[m4 yacc].each do |tool|
  path, error, status = Open3.capture3('/usr/bin/xcrun', '--find', tool)
  File.write(work + '/xcrun-' + tool + '.log', path + error)
  common << 'OSX_PATH_TO_' + tool.upcase + '=' + (status.success? ? path.strip : '')
end
cross = ['USE_CROSS_COMPILE=yes', 'CROSS_OPSYS=NetBSD', 'CROSS_OS_VERSION=11.0',
  'CROSS_OPSYS_VERSION=110000', 'CROSS_MACHINE_ARCH=x86_64', 'CROSS_LOWER_OPSYS=netbsd',
  'CROSS_LOWER_OPSYS_VERSUFFIX=', 'CROSS_LOWER_OS_VARIANT=', 'CROSS_LOWER_VARIANT_VERSION=',
  'CROSS_LOWER_VENDOR=', 'CROSS_OBJECT_FMT=ELF', 'CROSS_LOCALBASE=/usr/pkg',
  'CROSS_DESTDIR=' + sysroot, 'TOOLDIR=' + tools, 'CROSS_PKG_TOOLS_BIN=' + host + '/sbin']
cross << 'USE_PKGSRC_GCC_RUNTIME=no'
run = lambda do |label, package, *arguments|
  command = [*common, '-C', tree + '/x11/' + package, *arguments]
  output = ''
  status = nil
  Open3.popen2e(*command, pgroup: true) do |input, stream, process|
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
  abort label + ': bounded source query exceeded 30 seconds' unless status
  abort label + ': ' + output unless status.success?
  output
end
plist = lambda do |label, package, *mode|
  directory = work + '/' + label
  run.call(label, package, *mode, 'WRKDIR=' + directory, 'plist')
  File.readlines(directory + '/.PLIST_nokeywords', chomp: true).reject(&:empty?)
end
runtime = plist.call('runtime', 'qt6-qtbase', *cross)
abort 'runtime PLIST still contains target SDK or generators' if runtime.any? { |path| path.start_with?('qt6/include/') || path.end_with?('.cmake') || %w[qt6/bin/qmake qt6/libexec/moc qt6/libexec/rcc qt6/libexec/uic].include?(path) }
abort 'runtime qtpaths missing' unless %w[qt6/bin/qtpaths qt6/bin/qtpaths6].all? { |path| runtime.include?(path) }
abort 'runtime package identity was not revised' unless run.call('runtime-name', 'qt6-qtbase', *cross, '-V', '${PKGNAME}').strip == 'qt6-qtbase-6.12.0nb2'
abort 'SDK recipe missing' unless File.directory?(tree + '/x11/qt6-qtbase-devel')
sdk = plist.call('devel', 'qt6-qtbase-devel', *cross)
abort 'SDK scanner fix lacks a revised identity' unless run.call('devel-name', 'qt6-qtbase-devel', *cross, '-V', '${PKGNAME}').strip == 'qt6-qtbase-devel-6.12.0nb3'
abort 'SDK PLIST lost the CMake/generator contract' unless %w[qt6/bin/qmake qt6/libexec/moc qt6/libexec/rcc qt6/libexec/uic qt6/lib/cmake/Qt6/Qt6Config.cmake].all? { |path| sdk.include?(path) }
abort 'partition overlaps' unless (runtime & sdk).empty?
owner = tree + '/x11/qt6-qtbase'
full_dir = work + '/full'
run.call('full', 'qt6-qtbase', *cross, 'WRKDIR=' + full_dir, 'PLIST=' + full_dir + '/.PLIST',
  'PLIST_SRC=' + owner + '/PLIST.NetBSD ' + owner + '/PLIST', 'plist')
full = File.readlines(full_dir + '/.PLIST_nokeywords', chomp: true).reject(&:empty?)
abort 'expanded partition union differs from full pkgsrc PLIST' unless (runtime + sdk).sort == full.sort
helper = owner + '/files/select-package-stage.pl'
abort 'stage partition helper missing' unless File.file?(helper)
native = plist.call('native', 'qt6-qtbase', 'USE_CROSS_COMPILE=no', 'PKGSRC_COMPILER=clang',
  'CC=/usr/bin/clang', 'CXX=/usr/bin/clang++', 'USE_NATIVE_GCC=no', 'USE_PKGSRC_GCC=no')
abort 'native full SDK behavior changed' unless native.include?('qt6/bin/qmake') && native.any? { |path| path.start_with?('qt6/include/') }
reasons = run.call('devel-metadata', 'qt6-qtbase-devel', *cross, '-V', '${PKG_FAIL_REASON}', '-V', '${DEPENDS}', '-V', '${DISTINFO_FILE}', '-V', '${PATCHDIR}')
abort 'SDK source owner, exact runtime or platform contract differs' unless reasons.lines.first.strip.empty? && reasons.include?('qt6-qtbase-6.12.0nb2:') && reasons.include?(owner + '/distinfo') && reasons.include?(owner + '/patches')
FileUtils.mkdir_p(tree + '/devel/qtbase-split-consumer')
File.write(tree + '/devel/qtbase-split-consumer/Makefile', <<~MAKE)
  DISTNAME= qtbase-split-contract-1
  CATEGORIES= devel
  COMMENT= Qtbase buildlink source contract fixture
  LICENSE= 2-clause-bsd
  META_PACKAGE= yes
  .include "../../mk/bsd.prefs.mk"
  .include "../../x11/qt6-qtbase/buildlink3.mk"
  .include "../../mk/bsd.pkg.mk"
MAKE
out = run.call('buildlink', '../devel/qtbase-split-consumer', *cross,
  '-V', '${BUILD_DEPENDS}', '-V', '${DEPENDS}')
abort 'SDK was not a separate target build-only dependency' unless out.lines[0].include?('qt6-qtbase-devel>=6.12.0nb3:') && !out.lines[1].include?('qt6-qtbase-devel') && out.lines[1].include?('qt6-qtbase>=6.12.0nb2:')

# These payload bytes are labelled source-contract fixtures, not compiled Qt.
# Exercise the actual normalization/selection targets and preserve every byte
# and symlink that belongs to the selected real pkgsrc manifest.
original = work + '/normalized-full'
prefix = original + '/usr/pkg'
full.each do |path|
  FileUtils.mkdir_p(File.dirname(prefix + '/' + path))
  File.write(prefix + '/' + path, "source-contract fixture: #{path}\n")
end
run.call('normalize-full', 'qt6-qtbase', *cross, 'WRKDIR=' + work + '/normalizer',
  'DESTDIR=' + original, 'qt-target-metadata', 'pkgconfig-link')
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
abort 'full normalized fixture differs from the pkgsrc manifest' unless before.keys.sort == full.sort
%w[runtime devel].each do |part|
  destination = work + '/' + part + '-stage'
  FileUtils.cp_r(original, destination, preserve: true)
  package = part == 'runtime' ? 'qt6-qtbase' : 'qt6-qtbase-devel'
  run.call(part + '-select-stage', package, *cross, 'WRKDIR=' + work + '/' + part + '-select',
    'DESTDIR=' + destination, 'qtbase-select-stage')
  selected = part == 'runtime' ? runtime : sdk
  abort 'selected stage bytes, modes or symlinks changed' unless fingerprint.call(destination + '/usr/pkg') == before.select { |path, _| selected.include?(path) }
end
%w[missing unknown overlap union selected symlink-parent part].each do |case_name|
  destination = work + '/reject-' + case_name
  FileUtils.cp_r(original, destination, preserve: true)
  stage = destination + '/usr/pkg'
  lists = [full_dir + '/.PLIST', work + '/runtime/.PLIST', work + '/devel/.PLIST', work + '/runtime/.PLIST']
  part = 'runtime'
  case case_name
  when 'missing' then File.unlink(stage + '/' + sdk.first)
  when 'unknown' then File.write(stage + '/qt6/bin/unlisted-generator', 'unlisted fixture')
  when 'overlap'
    lists[2] = destination + '/overlap.plist'
    File.write(lists[2], File.read(work + '/devel/.PLIST') + runtime.first + "\n")
  when 'union'
    lists[2] = destination + '/incomplete.plist'
    File.write(lists[2], (sdk.drop(1)).join("\n") + "\n")
  when 'selected' then lists[3] = lists[2]
  when 'symlink-parent'
    outside = destination + '/outside'
    Dir.mkdir(outside)
    File.write(outside + '/preserved', 'outside fixture')
    FileUtils.rm_r(stage + '/qt6/bin')
    File.symlink(outside, stage + '/qt6/bin')
  when 'part' then part = 'unsupported'
  end
  unchanged = fingerprint.call(stage)
  output, status = Open3.capture2e(host + '/bin/perl', helper, part, stage, *lists)
  File.write(work + '/reject-' + case_name + '.log', output)
  abort 'invalid partition was accepted: ' + case_name if status.success?
  abort 'invalid partition changed staging: ' + case_name unless fingerprint.call(stage) == unchanged
end
puts 'PASS: real pkgsrc produces distinct runtime/SDK manifests and a revised runtime identity'
puts 'PASS: native full manifest, exact source/runtime dependencies, exhaustive union and build-only SDK contract'
puts 'PASS: actual full-stage normalizer and partition preserve selected bytes; seven invalid inputs fail before pruning'
puts 'SCOPE: source packaging contract only; no Qt compilation, target file execution or installed Qt acceptance'
