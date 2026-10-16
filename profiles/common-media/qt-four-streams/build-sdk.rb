#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors (AI-assisted).
# Build the explicit raster/video CPU selection with native generators.
require 'json'
require 'digest'
require 'fileutils'
require 'find'
require 'open3'

mode, distfiles, work, prefix, sysroot, host_qt = ARGV
abort 'Usage: build-sdk.rb native|amd64 DISTFILES WORK PREFIX_OR_STAGE [SYSROOT HOST_QT]' unless
  %w[native amd64].include?(mode) && [distfiles, work, prefix].all? { |p| p && p.start_with?('/') }
abort 'Cross build needs SYSROOT and matching HOST_QT' if mode == 'amd64' &&
  ![sysroot, host_qt].all? { |p| p && p.start_with?('/') }
ports = File.expand_path('../../..', __dir__)
toolkit = ports + '/probes/plasma-mobile/toolkit'
jobs = Integer(ENV.fetch('JOBS', '2')); abort 'JOBS must be 1..5' unless (1..5).cover?(jobs)
selected = ENV.fetch('COMPONENTS', 'png,freetype,harfbuzz,qtbase,qtshadertools,qtmultimedia').split(',')
names = {
  'png' => 'libpng-1.6.59.tar.xz', 'freetype' => 'freetype-2.14.3.tar.xz',
  'harfbuzz' => 'harfbuzz-14.6.0.tar.xz', 'pulse' => 'pulseaudio-17.0.tar.xz',
  'sndfile' => 'libsndfile-1.2.2.tar.xz',
  'qtbase' => 'qtbase-everywhere-src-6.12.0.tar.xz',
  'qtshadertools' => 'qtshadertools-everywhere-src-6.12.0.tar.xz',
  'qtmultimedia' => 'qtmultimedia-everywhere-src-6.12.0.tar.xz'
}
abort 'Unknown/duplicate component' unless selected.uniq == selected && selected.all? { |n| names.key?(n) }
abort 'Pulse component is a native Linux control prerequisite' if mode != 'native' && selected.include?('pulse')
inputs = %w[profiles/common-graphics/sources.tsv profiles/common-media/sources.tsv probes/plasma-mobile/toolkit/sources.tsv]
  .flat_map { |p| File.readlines(ports + '/' + p, chomp: true).reject { |l| l.start_with?('#') || l.empty? }.map { |l| l.split("\t") } }
inputs += File.readlines(__dir__ + '/native-sources.tsv', chomp: true).reject { |l| l.start_with?('#') || l.empty? }.map { |l| l.split("\t") }
FileUtils.mkdir_p([work + '/source', work + '/build-' + mode, prefix])
native = mode == 'native'
install_prefix = native ? prefix : '/usr/pkg'
qt_prefix = install_prefix + '/qt6'
env = { 'PKG_CONFIG_PATH' => '', 'BUILD_CC' => '/usr/local/bin/gcc', 'BUILD_CXX' => '/usr/local/bin/g++' }
if native
  env['PKG_CONFIG_LIBDIR'] = ENV.fetch('NATIVE_PKG_CONFIG_LIBDIR', prefix + '/lib/pkgconfig:/usr/lib/x86_64-linux-gnu/pkgconfig:/usr/share/pkgconfig')
else
  env['PKG_CONFIG_SYSROOT_DIR'] = sysroot
  env['PKG_CONFIG_LIBDIR'] = sysroot + '/usr/pkg/lib/pkgconfig:' + sysroot + '/usr/pkg/lib/ffmpeg9/pkgconfig:' + sysroot + '/usr/lib/pkgconfig'
end
def run(env, args, log, dir = nil)
  File.open(log, 'a') do |f|
    f.puts(JSON.generate({ command: args, cwd: dir, environment: env }))
    opts = { out: f, err: [:child, :out] }; opts[:chdir] = dir if dir
    abort 'Command failed; see ' + log unless system(env, *args, **opts)
  end
end
toolchain = work + '/build-' + mode + '/toolchain.cmake'
unless native
  gcc = ENV.fetch('GCC_PREFIX', '/workspace/.ember-cloud/amd64/gcc/toolchain')
  File.write(toolchain, <<~CMAKE)
    set(CMAKE_SYSTEM_NAME NetBSD)
    set(CMAKE_SYSTEM_PROCESSOR x86_64)
    set(CMAKE_SYSROOT #{sysroot})
    set(CMAKE_C_COMPILER #{gcc}/bin/x86_64--netbsd-gcc)
    set(CMAKE_CXX_COMPILER #{gcc}/bin/x86_64--netbsd-g++)
    set(CMAKE_C_FLAGS_INIT "-B#{sysroot}/usr/pkg/gcc16/lib/gcc/x86_64--netbsd/16.2.0/ -D_NETBSD_SOURCE")
    set(CMAKE_CXX_FLAGS_INIT "-B#{sysroot}/usr/pkg/gcc16/lib/gcc/x86_64--netbsd/16.2.0/ -isystem #{sysroot}/usr/pkg/gcc16/include/c++ -isystem #{sysroot}/usr/pkg/gcc16/include/c++/x86_64--netbsd -isystem #{sysroot}/usr/pkg/gcc16/include/c++/backward -D_NETBSD_SOURCE")
    set(CMAKE_EXE_LINKER_FLAGS_INIT "-L#{sysroot}/usr/pkg/gcc16/lib -Wl,-rpath,/usr/pkg/gcc16/lib")
    set(CMAKE_SHARED_LINKER_FLAGS_INIT "-L#{sysroot}/usr/pkg/gcc16/lib -Wl,-rpath,/usr/pkg/gcc16/lib")
    set(CMAKE_MODULE_LINKER_FLAGS_INIT "-L#{sysroot}/usr/pkg/gcc16/lib -Wl,-rpath,/usr/pkg/gcc16/lib")
    set(CMAKE_FIND_ROOT_PATH #{sysroot})
    set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
    set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
    set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
    set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
  CMAKE
end
selected.each do |component|
  archive = distfiles + '/' + names.fetch(component)
  row = inputs.find { |i| i[1] == File.basename(archive) }; abort 'Unpinned archive' unless row
  abort 'Archive digest mismatch' unless File.file?(archive) && Digest::SHA256.file(archive).hexdigest == row[2]
  src = work + '/source/' + File.basename(archive).sub(/\.tar\.(xz|gz)\z/, '')
  recipe = case component
           when 'qtbase' then toolkit + '/recipes/x11/qt6-qtbase'
           when 'qtmultimedia' then toolkit + '/recipes/multimedia/qt6-qtmultimedia'
           when 'qtshadertools' then toolkit + '/recipes/graphics/qt6-qtshadertools'
           when 'png' then ports + '/profiles/common-graphics/recipes/graphics/png'
           when 'freetype' then ports + '/profiles/common-graphics/recipes/graphics/freetype2'
           when 'harfbuzz' then ports + '/profiles/common-graphics/recipes/fonts/harfbuzz'
           when 'sndfile' then nil
           else ports + '/profiles/common-media/recipes/audio/pulseaudio'
           end
  patches = recipe ? Dir.glob(recipe + '/patches/*').sort : []
  fingerprint = { archive_sha256: row[2], patches: patches.to_h { |p| [File.basename(p), Digest::SHA256.file(p).hexdigest] } }
  source_receipt = work + '/source/' + component + '.json'
  source_refresh = nil
  File.open(work + '/source/.prepare.lock', 'w') do |lock|
  lock.flock(File::LOCK_EX)
  if File.exist?(source_receipt) && JSON.parse(File.read(source_receipt)) != JSON.parse(JSON.generate(fingerprint))
    backup = ENV['SOURCE_REFRESH_DIR']
    abort 'Changed source inputs; use new WORK or an explicit SOURCE_REFRESH_DIR' unless backup
    abort 'Refresh must select one component and a new directory under WORK/source-history-' unless
      selected.length == 1 && backup.match?(%r{\A#{Regexp.escape(work)}/source-history-[A-Za-z0-9._-]+\z}) &&
      !File.exist?(backup) && !File.symlink?(backup)
    previous = JSON.parse(File.read(source_receipt))
    abort 'Source refresh requires the same upstream archive' unless previous.fetch('archive_sha256') == row[2]
    roots = [src, work + '/build-' + mode + '/' + component]
    active = []
    Dir.glob('/proc/[0-9]*').each do |procdir|
      begin
        paths = [File.readlink(procdir + '/cwd')]
        Dir.children(procdir + '/fd').each do |fd|
          begin
            paths << File.readlink(procdir + '/fd/' + fd)
          rescue Errno::ENOENT, Errno::EACCES
          end
        end
        active << procdir if paths.any? { |p| roots.any? { |root| p == root || p.start_with?(root + '/') } }
        active << procdir if File.readlines(procdir + '/maps').any? { |line| roots.any? { |root| line.include?(root + '/') } }
      rescue Errno::ENOENT, Errno::EACCES
      end
    end
    abort 'Stop users of the source and component build before refresh: ' + active.uniq.join(', ') unless active.empty?
    FileUtils.mkdir_p(backup)
    File.rename(src, backup + '/source')
    File.rename(source_receipt, backup + '/source.json')
    old_pass = work + '/build-' + mode + '/' + component + '/PASS.json'
    FileUtils.cp(old_pass, backup + '/previous-PASS.json') if File.file?(old_pass)
    source_refresh = { backup: backup, previous: previous, next: fingerprint,
                       note: 'Fresh canonical source preparation. Preserve prior objects only through normal CMake/Ninja dependency checks.' }
    File.write(backup + '/refresh.json', JSON.pretty_generate(source_refresh))
  end
  unless File.exist?(source_receipt)
    abort 'Unowned source directory' if File.exist?(src)
    run({}, ['tar', '-xf', archive, '-C', work + '/source'], work + '/source/' + component + '.log')
    patches.each do |p|
      text = File.binread(p).lines.reject { |line| line.match?(/[$]NetBSD.*/) }.join
      expected = File.read(recipe + '/distinfo')[/^SHA1 \(#{Regexp.escape(File.basename(p))}\) = ([0-9a-f]+)$/, 1]
      abort 'Canonical patch digest mismatch: ' + p unless expected && Digest::SHA1.hexdigest(text) == expected
      File.open(p) do |input|
        File.open(work + '/source/' + component + '.log', 'a') do |out|
          abort 'Canonical patch failed: ' + p unless system('patch', '--batch', '--fuzz=0', '-p0', '-d', src, in: input, out: out, err: [:child, :out])
        end
      end
    end
    File.write(source_receipt, JSON.pretty_generate(fingerprint))
  end
  if source_refresh
    changed = []
    Find.find(src) do |path|
      next unless File.file?(path) && !File.symlink?(path)
      relative = path.delete_prefix(src + '/')
      before = source_refresh[:backup] + '/source/' + relative
      if File.file?(before) && Digest::SHA256.file(before).hexdigest == Digest::SHA256.file(path).hexdigest
        stat = File.stat(before)
        File.utime(stat.atime, stat.mtime, path)
        next
      end
      # New or changed inputs must be newer than prior outputs, even when an
      # upstream archive carries old timestamps. Ninja sees the actual change.
      File.utime(Time.now, Time.now, path)
      changed << relative
    end
    source_refresh[:changed_regular_files] = changed
  end
  abort 'Changed source inputs; use new WORK' unless JSON.parse(File.read(source_receipt)) == JSON.parse(JSON.generate(fingerprint))
  end
  build = work + '/build-' + mode + '/' + component
  FileUtils.mkdir_p(build)
  File.write(build + '/source-refresh.json', JSON.pretty_generate(source_refresh)) if source_refresh
  log = build + '/commands.log'
  puts 'Building ' + mode + '/' + component; $stdout.flush
  if %w[harfbuzz pulse].include?(component)
    meson = ENV.fetch('MESON', 'meson')
    args = [meson, 'setup', build, src, '--prefix=' + install_prefix, '--libdir=lib', '--buildtype=release', '--wrap-mode=nodownload']
    if native
      media = ENV.fetch('NATIVE_MEDIA_PREFIX', prefix)
      links = ['-Wl,-rpath,' + prefix + '/lib', '-Wl,-rpath,' + media + '/lib']
      args += ['-Dc_link_args=' + JSON.generate(links), '-Dcpp_link_args=' + JSON.generate(links)]
    end
    if component == 'harfbuzz'
      args += %w[-Dglib=enabled -Dgobject=enabled -Dcairo=disabled -Dicu=disabled -Dfreetype=enabled -Dtests=enabled -Ddocs=disabled -Dutilities=enabled -Dintrospection=disabled -Dchafa=disabled -Dgpu_demo=disabled]
    else
      args += %w[-Ddaemon=false -Dtests=false -Dman=false -Ddoxygen=false -Ddatabase=simple -Ddbus=disabled -Dbluez5=disabled -Dalsa=disabled -Djack=disabled -Dsystemd=disabled -Dudev=disabled -Dopenssl=disabled -Dgstreamer=disabled -Dgtk=disabled -Dx11=disabled -Doss-output=disabled -Dorc=disabled]
    end
    unless native
      cross = build + '/cross.ini'
      gcc = ENV.fetch('GCC_PREFIX', '/workspace/.ember-cloud/amd64/gcc/toolchain')
      File.write(cross, "[binaries]\nc = '#{gcc}/bin/x86_64--netbsd-gcc'\ncpp = '#{gcc}/bin/x86_64--netbsd-g++'\nar = '#{gcc}/bin/x86_64--netbsd-ar'\nstrip = '#{gcc}/bin/x86_64--netbsd-strip'\npkg-config = 'pkg-config'\n[host_machine]\nsystem = 'netbsd'\ncpu_family = 'x86_64'\ncpu = 'x86_64'\nendian = 'little'\n[properties]\nneeds_exe_wrapper = true\nsys_root = '#{sysroot}'\n[built-in options]\nc_args = ['--sysroot=#{sysroot}', '-B#{sysroot}/usr/pkg/gcc16/lib/gcc/x86_64--netbsd/16.2.0/']\ncpp_args = ['--sysroot=#{sysroot}', '-B#{sysroot}/usr/pkg/gcc16/lib/gcc/x86_64--netbsd/16.2.0/', '-isystem', '#{sysroot}/usr/pkg/gcc16/include/c++', '-isystem', '#{sysroot}/usr/pkg/gcc16/include/c++/x86_64--netbsd', '-isystem', '#{sysroot}/usr/pkg/gcc16/include/c++/backward']\nc_link_args = ['--sysroot=#{sysroot}', '-L#{sysroot}/usr/pkg/gcc16/lib', '-Wl,-rpath,/usr/pkg/gcc16/lib', '-Wl,-rpath,/usr/pkg/lib']\ncpp_link_args = ['--sysroot=#{sysroot}', '-L#{sysroot}/usr/pkg/gcc16/lib', '-Wl,-rpath,/usr/pkg/gcc16/lib', '-Wl,-rpath,/usr/pkg/lib']\n")
      args += ['--cross-file=' + cross]
      if component == 'harfbuzz'
        glib_host = ENV.fetch('HOST_GLIB_PREFIX') { abort 'Set HOST_GLIB_PREFIX to matching native GLib generators' }
        %w[glib-mkenums glib-genmarshal].each do |tool|
          abort 'Missing native GLib generator: ' + tool unless File.executable?(glib_host + '/bin/' + tool)
        end
        text = File.read(cross).sub("pkg-config = 'pkg-config'\n", "pkg-config = 'pkg-config'\nglib-mkenums = '#{glib_host}/bin/glib-mkenums'\nglib-genmarshal = '#{glib_host}/bin/glib-genmarshal'\n")
        File.write(cross, text)
      end
    end
    args << '--reconfigure' if File.exist?(build + '/build.ninja')
    run(env, args, log)
    run(env, ['ninja', '-C', build, '-j', jobs.to_s], log)
    run(env.merge(native ? {} : { 'DESTDIR' => prefix }), [meson, 'install', '-C', build, '--no-rebuild'], log)
  else
    args = ['cmake', '-S', src, '-B', build, '-G', 'Ninja', '-DCMAKE_BUILD_TYPE=Release', '-DBUILD_SHARED_LIBS=ON', '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON', '-DCMAKE_INSTALL_PREFIX=' + (component.start_with?('qt') ? qt_prefix : install_prefix), '-DCMAKE_INSTALL_RPATH=' + (native ? [prefix + '/qt6/lib', prefix + '/lib', ENV.fetch('NATIVE_MEDIA_PREFIX', prefix) + '/lib', ENV.fetch('NATIVE_MEDIA_PREFIX', prefix) + '/lib/ffmpeg9'].join(';') : '/usr/pkg/qt6/lib;/usr/pkg/lib;/usr/pkg/lib/ffmpeg9;/usr/pkg/gcc16/lib'), '-DCMAKE_PREFIX_PATH=' + (native ? prefix + '/qt6;' + prefix : sysroot + '/usr/pkg/qt6;' + sysroot + '/usr/pkg')]
    args << '-DCMAKE_TOOLCHAIN_FILE=' + toolchain unless native
    # CMake modules use a separate linker flag cache. Pin their C++ provider
    # explicitly, including when a prior configure initialized an empty cache.
    args << '-DCMAKE_MODULE_LINKER_FLAGS=-L' + sysroot + '/usr/pkg/gcc16/lib -Wl,-rpath,/usr/pkg/gcc16/lib' unless native
    args += ['-DCMAKE_C_COMPILER=/usr/local/bin/gcc', '-DCMAKE_CXX_COMPILER=/usr/local/bin/g++'] if native
    if native && ENV['NATIVE_EXTRA_PREFIX']
      extra = ENV.fetch('NATIVE_EXTRA_PREFIX')
      abort 'Invalid native prerequisite prefix' unless extra.start_with?('/') && !extra.match?(/[;\r\n]/)
      include_dir = extra + '/usr/include'
      library_dir = extra + '/usr/lib/x86_64-linux-gnu'
      abort 'Missing native prerequisite files' unless File.directory?(include_dir) && File.directory?(library_dir)
      env['CPATH'] = include_dir
      env['LIBRARY_PATH'] = library_dir
      %w[EXE SHARED MODULE].each { |kind| args << '-DCMAKE_' + kind + '_LINKER_FLAGS=-L' + library_dir }
      args << '-DCMAKE_INSTALL_RPATH=' + [prefix + '/qt6/lib', prefix + '/lib', ENV.fetch('NATIVE_MEDIA_PREFIX', prefix) + '/lib', ENV.fetch('NATIVE_MEDIA_PREFIX', prefix) + '/lib/ffmpeg9', library_dir].join(';')
    end
    case component
    when 'png' then args += %w[-DPNG_TESTS=ON -DPNG_TOOLS=ON -DPNG_BUILD_ZLIB=OFF -DCMAKE_C_FLAGS=-DPNG_USER_CHUNK_CACHE_MAX=128\ -DPNG_USER_CHUNK_MALLOC_MAX=8000000]
    when 'freetype' then args += %w[-DFT_DISABLE_HARFBUZZ=ON -DFT_DISABLE_BROTLI=ON]
    when 'sndfile' then args += %w[-DENABLE_EXTERNAL_LIBS=OFF -DENABLE_MPEG=OFF -DBUILD_PROGRAMS=OFF -DBUILD_EXAMPLES=OFF -DBUILD_TESTING=ON]
    else
      args += %w[-DQT_BUILD_TESTS=OFF -DQT_BUILD_EXAMPLES=OFF -DBUILD_WITH_PCH=OFF -DCMAKE_DISABLE_PRECOMPILE_HEADERS=ON]
      if component == 'qtbase'
        args += %w[-DQT_QPA_DEFAULT_PLATFORM=vnc -DFEATURE_vnc=ON -DFEATURE_xcb=OFF -DFEATURE_opengl=OFF -DINPUT_opengl=no -DFEATURE_dbus=OFF -DFEATURE_icu=OFF -DFEATURE_fontconfig=OFF -DFEATURE_jpeg=OFF -DFEATURE_system_freetype=ON -DFEATURE_system_harfbuzz=ON -DFEATURE_system_png=ON -DFEATURE_system_pcre2=ON -DFEATURE_sql_mysql=OFF -DFEATURE_sql_psql=OFF -DFEATURE_sql_odbc=OFF]
        args << '-DQT_HOST_PATH=' + host_qt unless native
      else
        args << '-DQT_HOST_PATH=' + host_qt unless native
        if component == 'qtmultimedia'
          args += %w[-DFEATURE_ffmpeg=ON -DQT_DEFAULT_MEDIA_BACKEND=ffmpeg -DFEATURE_gstreamer=OFF -DFEATURE_spatialaudio=OFF -DFEATURE_alsa=OFF -DFEATURE_pipewire=OFF -DFEATURE_vaapi=OFF]
          args << '-DFEATURE_pulseaudio=' + (native ? 'ON' : 'OFF')
        end
      end
    end
    run(env, args, log)
    run(env, ['cmake', '--build', build, '--parallel', jobs.to_s], log)
    run(env.merge(native ? {} : { 'DESTDIR' => prefix }), ['cmake', '--install', build], log)
  end
  unless native
    run({}, ['cp', '-a', prefix + '/usr/pkg/.', sysroot + '/usr/pkg/'], log)
  end
  File.write(build + '/PASS.json', JSON.pretty_generate({ mode: mode, component: component, source: fingerprint, install_prefix: install_prefix, stage: prefix }))
end
