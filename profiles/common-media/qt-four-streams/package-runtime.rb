#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Prepare only the amd64 raster/video runtime. This is not a desktop SDK package.
# All six producer builds must finish before this helper is used.
require 'json'
require 'digest'
require 'fileutils'
require 'open3'
require 'etc'

work, stage, sysroot, output, pkg_create = ARGV
abort 'Usage: package-runtime.rb WORK AMD64_STAGE SYSROOT NEW_OUTPUT [HOST_PKG_CREATE]' unless
  (4..5).cover?(ARGV.length) && ARGV.all? { |path| path.start_with?('/') }
[work, stage, sysroot].each { |path| abort 'Missing input directory: ' + path unless File.directory?(path) }
work, stage, sysroot = [work, stage, sysroot].map { |path| File.realpath(path) }
output = File.expand_path(output)
abort 'Output already exists' if File.exist?(output) || File.symlink?(output)
abort 'Unsafe metadata path' if ARGV.any? { |path| path.match?(/[\r\n]/) }
ports = File.expand_path('../../..', __dir__)
graphics = ports + '/profiles/common-graphics/recipes/'
toolkit = ports + '/probes/plasma-mobile/toolkit/recipes/'
config = {
  'png' => ['png-cpu-runtime-1.6.59', 'libpng-1.6.59', graphics + 'graphics/png', 'png-[0-9]*'],
  'freetype' => ['freetype2-cpu-runtime-2.14.3nb1', 'freetype-2.14.3', graphics + 'graphics/freetype2', 'freetype2-[0-9]*'],
  'harfbuzz' => ['harfbuzz-cpu-runtime-14.6.0nb1', 'harfbuzz-14.6.0', graphics + 'fonts/harfbuzz', 'harfbuzz-[0-9]*'],
  'qtbase' => ['qt6-qtbase-cpu-runtime-6.12.0nb3', 'qtbase-everywhere-src-6.12.0', toolkit + 'x11/qt6-qtbase', 'qt6-qtbase-[0-9]*'],
  'qtshadertools' => ['qt6-qtshadertools-cpu-runtime-6.12.0', 'qtshadertools-everywhere-src-6.12.0', toolkit + 'graphics/qt6-qtshadertools', 'qt6-qtshadertools-[0-9]*'],
  'qtmultimedia' => ['qt6-qtmultimedia-cpu-runtime-6.12.0nb2', 'qtmultimedia-everywhere-src-6.12.0', toolkit + 'multimedia/qt6-qtmultimedia', 'qt6-qtmultimedia-[0-9]*']
}
sysroot_info = JSON.parse(File.read(sysroot + '/EMBERBSD-PORTS-SYSROOT.json'))
base_source = sysroot_info.fetch('base_source_revision')
abort 'Unidentified base or compiler' unless base_source.match?(/\A[0-9a-f]{40}\z/) && sysroot_info.fetch('compiler').include?('GCC16.2.0 x86_64--netbsd')
pins = %w[profiles/common-graphics/sources.tsv probes/plasma-mobile/toolkit/sources.tsv].flat_map do |path|
  File.readlines(ports + '/' + path).reject { |line| line.start_with?('#') }.map { |line| line.chomp.split("\t") }
end
readelf = ENV.fetch('READELF', 'readelf')
elf_cache = {}
elf = lambda do |path|
  real = File.realpath(path)
  elf_cache[real] ||= begin
    header = File.binread(real, 20)
    abort 'Not an amd64 shared ELF: ' + path unless header.byteslice(0, 4) == "\x7fELF".b &&
      header.getbyte(4) == 2 && header.getbyte(5) == 1 && header.byteslice(16, 4).unpack('v2') == [3, 62]
    dynamic, error, status = Open3.capture3(readelf, '-d', real)
    abort 'ELF inspection failed: ' + error unless status.success?
    needed = dynamic.scan(/\(NEEDED\).*\[([^\]]+)\]/).flatten
    abort 'Invalid ELF dependency' unless needed.all? { |name| name.match?(/\A[A-Za-z0-9_.+-]+\z/) }
    rpaths = dynamic.scan(/\((?:RUNPATH|RPATH)\).*\[([^\]]*)\]/).flatten.flat_map { |value| value.split(':') }
    abort 'Host or unrecognized RPATH: ' + path unless rpaths.all? { |value| value == '/usr/pkg' || value.start_with?('/usr/pkg/', '/usr/lib/', '/lib/') }
    { soname: dynamic[/\(SONAME\).*\[([^\]]+)\]/, 1], needed: needed, rpaths: rpaths }
  end
end
safe_relative = lambda do |path|
  abort 'Invalid payload path: ' + path if path.empty? || path.start_with?('/') || path.split('/').include?('..') || path.match?(/[\s\x00]/)
  path
end

# Validate complete producer receipts and canonical pins before creating output.
packages = config.map do |component, (name, source_name, recipe, conflict)|
  revision = File.read(recipe + '/Makefile')[/^PKGREVISION\s*=\s*([0-9]+)/, 1].to_i
  expected_suffix = revision.positive? ? 'nb' + revision.to_s : ''
  abort 'Runtime package revision is stale: ' + component unless name[/nb[0-9]+\z/].to_s == expected_suffix
  build = work + '/build-amd64/' + component
  receipt = JSON.parse(File.read(build + '/PASS.json'))
  abort 'Incomplete or foreign producer: ' + component unless receipt.fetch('mode') == 'amd64' &&
    receipt.fetch('component') == component && receipt.fetch('install_prefix') == '/usr/pkg' && File.realpath(receipt.fetch('stage')) == stage
  fingerprint = JSON.parse(File.read(work + '/source/' + component + '.json'))
  patches = Dir[recipe + '/patches/*'].sort.to_h { |path| [File.basename(path), Digest::SHA256.file(path).hexdigest] }
  pin = pins.find { |row| row[1] == source_name + '.tar.xz' }
  abort 'Producer source inputs changed: ' + component unless pin && fingerprint == receipt.fetch('source') &&
    fingerprint.fetch('archive_sha256') == pin[2] && fingerprint.fetch('patches') == patches
  manifest = component == 'harfbuzz' ? build + '/meson-logs/install-log.txt' : build + '/install_manifest.txt'
  files = File.readlines(manifest, chomp: true).reject { |line| line.empty? || line.start_with?('#') }.filter_map do |path|
    relative = if path.start_with?(stage + '/usr/pkg/')
                 path.delete_prefix(stage + '/usr/pkg/')
               elsif path.start_with?('/usr/pkg/')
                 path.delete_prefix('/usr/pkg/')
               else
                 abort 'Foreign install manifest path: ' + path
               end
    safe_relative.call(relative)
    input = stage + '/usr/pkg/' + relative
    next if File.directory?(input)
    abort 'Missing producer output: ' + input unless File.file?(input) || File.symlink?(input)
    runtime_library = relative.match?(%r{\A(?:lib/|qt6/lib/|qt6/plugins/).*\.so(?:\.[0-9.]+)?\z})
    runtime_data = relative.start_with?('qt6/resources/', 'qt6/translations/', 'qt6/fonts/', 'qt6/lib/fonts/', 'share/fonts/') ||
      (relative.start_with?('qt6/plugins/') && relative.end_with?('.json'))
    next unless runtime_library || runtime_data
    # Unversioned linker symlinks are development files. Plugin files remain.
    next if File.symlink?(input) && relative.end_with?('.so') && !relative.start_with?('qt6/plugins/')
    if runtime_library
      real = File.realpath(input)
      abort 'Library symlink leaves staging prefix' unless real.start_with?(stage + '/usr/pkg/')
      elf.call(input)
    elsif File.symlink?(input)
      abort 'Runtime-data symlinks require an explicit rule'
    end
    relative
  end.uniq.sort
  abort 'No shared runtime libraries: ' + component unless files.any? { |path| !File.symlink?(stage + '/usr/pkg/' + path) && path.include?('.so') }
  files.each do |relative|
    input = stage + '/usr/pkg/' + relative
    next unless File.symlink?(input)
    resolved = File.realpath(input).delete_prefix(stage + '/usr/pkg/')
    abort 'Symlink target is not in runtime payload: ' + relative unless files.include?(resolved)
  end
  { key: component, name: name, source_dir: work + '/source/' + source_name, source: fingerprint,
    install_manifest_sha256: Digest::SHA256.file(manifest).hexdigest, files: files, conflict: conflict }
end

owners = {}
packages.each do |package|
  package[:files].each do |relative|
    path = stage + '/usr/pkg/' + relative
    next unless relative.include?('.so')
    info = elf.call(path)
    [File.basename(relative), info[:soname]].compact.each do |name|
      abort 'Ambiguous library owner: ' + name if owners[name] && owners[name] != package[:name]
      owners[name] = package[:name]
    end
  end
end
external = {
  /\Alib(?:stdc\+\+|gcc_s)\.so/ => 'ember-gcc16-cxx-runtime-16.2.0',
  /\Alibpcre2-/ => 'pcre2-10.49',
  /\Alib(?:glib|gobject|gio|gmodule|gthread)-2\.0\.so/ => 'glib2-cpu-2.90.1',
  /\Alibffi\.so/ => 'libffi-3.8.0nb1',
  /\Alib(?:avcodec|avformat|avutil|avfilter|avdevice|swscale|swresample)\.so/ => 'ffmpeg9-9.0.2nb2',
  /\Alibx265\.so/ => 'x265-4.2', /\Alibxml2\.so/ => 'libxml2-2.15.4nb1'
}
providers = {}
packages.each do |package|
  dependencies = []
  package[:elf] = package[:files].filter_map do |relative|
    next unless relative.include?('.so')
    info = elf.call(stage + '/usr/pkg/' + relative)
    info[:needed].each do |needed|
      owner = owners[needed]
      unless owner
        mapping = external.find { |pattern, _name| needed.match?(pattern) }
        owner = mapping&.last
        roots = owner ? %w[usr/pkg/gcc16/lib usr/pkg/lib usr/pkg/lib/ffmpeg9] : %w[lib usr/lib]
        provider = roots.map { |root| sysroot + '/' + root + '/' + needed }.find { |path| File.file?(path) }
        abort 'Unresolved target dependency: ' + needed unless provider
        abort 'Unregistered selected provider: ' + owner if owner && !sysroot_info.fetch('packages').include?(owner)
        elf.call(provider)
        providers[needed] = { package: owner, base: owner.nil?, path: provider,
                              sha256: Digest::SHA256.file(provider).hexdigest }
      end
      dependencies << owner if owner && owner != package[:name]
    end
    { path: relative, **info }
  end
  package[:deps] = dependencies.uniq.sort
end

if pkg_create
  pkg_create = File.realpath(pkg_create)
  abort 'pkg_create must be a host tool outside target/source roots' if [work, stage, sysroot].any? { |root| pkg_create.start_with?(root + '/') }
  abort 'Host pkg_create is not executable' unless File.executable?(pkg_create)
  header = File.binread(pkg_create, 8)
  abort 'Refusing a NetBSD target ELF as a host tool' if header.start_with?("\x7fELF".b) && header.getbyte(7) == 2
end
archive_user = pkg_create ? Etc.getpwuid(0).name : 'root'
archive_group = pkg_create ? Etc.getgrgid(0).name : 'wheel'
Dir.mkdir(output)
manifest = { schema: 'emberbsd.qt-four-streams.runtime-packages.v1', status: 'preparing', arch: 'amd64',
             prefix: '/usr/pkg', os_source: base_source, compiler: sysroot_info.fetch('compiler'),
             selection: 'Shared raster/video runtime and plugins; no headers, build metadata, tools or compiler.',
             archive_ownership: { uid: 0, gid: 0, user: archive_user, group: archive_group },
             helper_sha256: Digest::SHA256.file(__FILE__).hexdigest, providers: providers, packages: [] }
begin
  packages.each do |package|
    root = output + '/' + package[:key]
    payload = root + '/stage'
    recipe = root + '/recipe'
    FileUtils.mkdir_p([payload, recipe])
    package[:files].each do |relative|
      source = stage + '/usr/pkg/' + relative
      destination = payload + '/' + relative
      FileUtils.mkdir_p(File.dirname(destination))
      if File.symlink?(source)
        link = File.readlink(source)
        abort 'Absolute runtime symlink' if link.start_with?('/')
        File.symlink(link, destination)
      else
        FileUtils.copy_file(source, destination, true)
      end
    end
    source = package[:source_dir]
    licenses = Dir[source + '/{LICENSES/**/*,LICENSE*,COPYING*,AUTHORS*,docs/FTL.TXT,docs/GPLv2.TXT,src/**/LICENSE*,src/**/COPYING*,src/**/qt_attribution.json}'].select { |path| File.file?(path) && !File.symlink?(path) }.uniq.sort
    abort 'Upstream license files missing: ' + package[:key] if licenses.empty?
    licenses.each do |path|
      relative = path.delete_prefix(source + '/')
      destination = payload + '/share/licenses/' + package[:name] + '/' + relative
      FileUtils.mkdir_p(File.dirname(destination))
      FileUtils.copy_file(path, destination, true)
    end
    notice = payload + '/share/licenses/' + package[:name] + '/SOURCE.json'
    File.write(notice, JSON.pretty_generate(package.slice(:name, :source, :install_manifest_sha256)) + "\n")
    inventory = Dir.glob(payload + '/**/*', File::FNM_DOTMATCH).reject { |path| File.directory?(path) }.map do |path|
      relative = safe_relative.call(path.delete_prefix(payload + '/'))
      stat = File.lstat(path)
      entry = { path: relative, mode: stat.mode & 0o7777 }
      File.symlink?(path) ? entry[:link] = File.readlink(path) : entry[:sha256] = Digest::SHA256.file(path).hexdigest
      entry
    end.sort_by { |entry| entry[:path] }
    File.write(recipe + '/PLIST', inventory.map { |entry| entry[:path] }.join("\n") + "\n")
    File.write(recipe + '/inventory.json', JSON.pretty_generate(inventory) + "\n")
    File.write(recipe + '/DESCR', "Selected #{package[:key]} CPU runtime for four Qt Multimedia streams. No development or desktop package claim.\n")
    info = { 'MACHINE_ARCH' => 'x86_64', 'OPSYS' => 'NetBSD', 'OS_VERSION' => '11.0',
             'PKGPATH' => 'ember-media/qt-four-streams/' + package[:key], 'PKGNAME' => package[:name],
             'CC_VERSION' => 'gcc-16.2.0', 'CXX_VERSION' => 'gcc-16.2.0',
             'BUILD_HOST' => 'Linux-x86_64-cross', 'EMBERBSD_BASE_SOURCE' => base_source,
             'DEPENDS' => package[:deps].join(' '), 'CONFLICTS' => package[:conflict] }
    File.write(recipe + '/build-info.txt', info.map { |key, value| "#{key}=#{value}\n" }.join)
    archive = output + '/' + package[:name] + '.tgz'
    command = [pkg_create || 'pkg_create', '-u', archive_user, '-g', archive_group, '-p', payload, '-I', '/usr/pkg',
               '-c', '-EmberBSD cross-built CPU runtime', '-d', recipe + '/DESCR', '-f', recipe + '/PLIST',
               '-B', recipe + '/build-info.txt', '-P', package[:deps].join(' '), '-C', package[:conflict], archive]
    record = package.reject { |key, _value| %i[files source_dir].include?(key) }.merge(stage: payload, recipe: recipe,
               inventory_sha256: Digest::SHA256.file(recipe + '/inventory.json').hexdigest, pkg_create_command: command)
    manifest[:packages] << record
    if pkg_create
      stdout, stderr, status = Open3.capture3(*command)
      File.write(root + '/pkg-create.log', stdout + stderr)
      record[:pkg_create_exit_status] = status.exitstatus
      raise 'Host pkg_create failed: ' + package[:key] unless status.success? && File.size?(archive)
      record[:archive] = { path: archive, bytes: File.size(archive), sha256: Digest::SHA256.file(archive).hexdigest }
    end
  end
  manifest[:status] = pkg_create ? 'packages-created' : 'payloads-prepared'
  manifest[:note] = 'No package database was modified. Archive acceptance and target lifecycle tests are separate.'
rescue StandardError, SystemExit => error
  manifest[:status] = 'failed'
  manifest[:error] = "#{error.class}: #{error.message}"
  raise
ensure
  File.write(output + '/manifest.json', JSON.pretty_generate(manifest) + "\n")
  File.write(output + '/packages.tsv', manifest[:packages].map { |package| [package[:key], package[:name]].join("\t") }.join("\n") + "\n")
end
puts "Prepared #{packages.length} amd64 runtime payloads; status=#{manifest[:status]}"
