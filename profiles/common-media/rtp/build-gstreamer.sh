#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Selected CPU RTP SDK, not the desktop profile.
set -eu
exec ruby - "$0" "$@" <<'RUBY'
require 'digest'
require 'fileutils'
require 'find'
require 'json'
require 'open3'
require 'shellwords'

script = File.realpath(ARGV.shift)
usage = 'Usage: build-gstreamer.sh native ARCHIVES WORK PREFIX | cross ARCHIVES WORK STAGE SYSROOT TARGET GCC_PREFIX'
mode = ARGV.shift
abort usage unless (mode == 'native' && ARGV.size == 3) || (mode == 'cross' && ARGV.size == 6)
archives, work, output, sysroot, target, compiler = ARGV.map { |v| File.expand_path(v) }
target = ARGV[4] if mode == 'cross'
abort 'Use paths without whitespace or shell metacharacters' unless [archives, work, output, sysroot, compiler].compact.all? { |path| path.match?(/\A[a-zA-Z0-9_.+\/-]+\z/) }
ports = File.expand_path('../../..', File.dirname(script))
media = File.join(ports, 'profiles/common-media')
graphics = File.join(ports, 'profiles/common-graphics')
pkgsrc = File.join(ports, 'pkgsrc')
jobs = Integer(ENV.fetch('JOBS', '2'))
abort 'JOBS must be positive' unless jobs.positive?
native_prefix = mode == 'native' ? output : File.expand_path(ENV.fetch('NATIVE_PREFIX'))
prefix = mode == 'native' ? output : '/usr/pkg'
FileUtils.mkdir_p(work)
FileUtils.mkdir_p(output)
environment = {'PATH' => native_prefix + '/bin:' + ENV.fetch('PATH')}
if mode == 'cross'
  abort 'Unsupported target' unless %w[aarch64--netbsd x86_64--netbsd].include?(target)
  abort 'Missing target sysroot' unless File.file?(File.join(sysroot, 'usr/include/sys/types.h'))
  cc = File.join(compiler, 'bin', target + '-gcc')
  cxx = File.join(compiler, 'bin', target + '-g++')
  ar = File.join(compiler, 'bin', target + '-ar')
  ranlib = File.join(compiler, 'bin', target + '-ranlib')
  strip = File.join(compiler, 'bin', target + '-strip')
  environment.merge!('PKG_CONFIG_PATH' => '', 'PKG_CONFIG_SYSROOT_DIR' => sysroot,
    'PKG_CONFIG_LIBDIR' => [sysroot + '/usr/pkg/lib/pkgconfig', sysroot + '/usr/pkg/lib/ffmpeg9/pkgconfig', sysroot + '/usr/lib/pkgconfig'].join(':'))
else
  cc = ENV.fetch('CC', 'gcc')
  cxx = ENV.fetch('CXX', 'g++')
  ar = ENV.fetch('AR', 'ar')
  ranlib = ENV.fetch('RANLIB', 'ranlib')
  strip = ENV.fetch('STRIP', 'strip')
  environment['PKG_CONFIG_PATH'] = [prefix + '/lib/pkgconfig', prefix + '/lib/ffmpeg9/pkgconfig', ENV['PKG_CONFIG_PATH']].compact.join(':')
end
environment.merge!('CC' => cc, 'CXX' => cxx, 'AR' => ar, 'RANLIB' => ranlib, 'STRIP' => strip)
rpath = mode == 'native' ? [prefix + '/lib', prefix + '/lib/ffmpeg9', '/usr/local/lib64'] : ['/usr/pkg/lib', '/usr/pkg/lib/ffmpeg9', '/usr/pkg/gcc16/lib']
cflags = ['-O2', '-g']
ldflags = rpath.map { |v| '-Wl,-rpath,' + v }
if mode == 'cross'
  cflags += ['--sysroot=' + sysroot, '-I' + sysroot + '/usr/pkg/include']
  ldflags += ['--sysroot=' + sysroot, '-L' + sysroot + '/usr/pkg/lib', '-L' + sysroot + '/usr/pkg/gcc16/lib', '-Wl,-rpath-link,' + sysroot + '/usr/pkg/lib', '-Wl,-rpath-link,' + sysroot + '/usr/pkg/lib/ffmpeg9', '-Wl,-rpath-link,' + sysroot + '/usr/pkg/gcc16/lib']
end
environment.merge!('CFLAGS' => cflags.join(' '), 'CXXFLAGS' => cflags.join(' '), 'LDFLAGS' => ldflags.join(' '))

def run!(env, argv, log, cwd = nil)
  FileUtils.mkdir_p(File.dirname(log))
  File.open(log, 'a') do |stream|
    stream.puts('$ ' + argv.shelljoin)
    stream.flush
    options = {out: stream, err: stream}
    options[:chdir] = cwd if cwd
    status = Process.wait2(Process.spawn(env, *argv, **options)).last
    abort "Command failed (#{status.exitstatus}); see #{log}" unless status.success?
  end
end

pins = {}
[media + '/sources.tsv', graphics + '/sources.tsv', ports + '/profiles/common-build-tools/sources.tsv'].each do |manifest|
  File.readlines(manifest, chomp: true).each do |line|
    next if line.empty? || line.start_with?('#')
    fields = line.split("\t")
    recipe, archive, sha256, url = fields
    recipe, archive, sha256, url = nil, *fields if fields.size == 3
    pins[archive] = {'recipe' => recipe, 'sha256' => sha256, 'url' => url, 'manifest' => manifest}
  end
end
ffi_recipe = File.join(pkgsrc, 'devel/libffi')
ffi_hash = File.read(ffi_recipe + '/distinfo')[/^SHA512 \(libffi-3\.8\.0\.tar\.gz\) = ([0-9a-f]{128})$/, 1]
abort 'Unexpected pinned libffi source' unless ffi_hash
pins['libffi-3.8.0.tar.gz'] = {'sha512' => ffi_hash, 'recipe' => 'devel/libffi',
  'url' => pins.fetch('libffi-3.8.0.tar.gz').fetch('url')}

prepare = lambda do |name, archive, recipe|
  base = File.join(work, name)
  source = File.join(base, 'source')
  logs = File.join(base, 'logs')
  FileUtils.mkdir_p(logs)
  pin = pins.fetch(archive)
  archive_path = File.join(archives, archive)
  algorithm = pin.key?('sha256') ? Digest::SHA256 : Digest::SHA512
  expected = pin.fetch(pin.key?('sha256') ? 'sha256' : 'sha512')
  abort 'Source checksum mismatch: ' + archive unless algorithm.file(archive_path).hexdigest == expected
  patch_inputs = []
  if recipe
    info = File.read(recipe + '/distinfo')
    info.scan(/^SHA1 \((patch-[^)]+)\) = ([0-9a-f]{40})$/).sort.each do |patch, sha1|
      path = recipe + '/patches/' + patch
      filtered = File.binread(path).lines.reject { |line| line.match?(/[$]NetBSD.*/) }.join
      abort 'Patch checksum mismatch: ' + path unless Digest::SHA1.hexdigest(filtered) == sha1
      patch_inputs << {'name' => patch, 'sha1_rcs_filtered' => sha1, 'sha256' => Digest::SHA256.file(path).hexdigest, 'selected' => true}
    end
  end
  receipt = {'archive' => archive, 'sha256' => Digest::SHA256.file(archive_path).hexdigest, 'patches' => patch_inputs}
  receipt_path = base + '/source-inputs.json'
  if File.exist?(receipt_path)
    abort 'Source inputs changed; use a new work directory' unless JSON.parse(File.read(receipt_path)) == receipt
  else
    abort 'Source directory exists without its receipt' if File.exist?(source)
    FileUtils.mkdir_p(source)
    run!({}, ['tar', '-xf', archive_path, '--strip-components=1', '-C', source], logs + '/extract.log')
    patch_inputs.select { |input| input.fetch('selected') }.each do |input|
      File.open(recipe + '/patches/' + input.fetch('name')) do |input_stream|
        File.open(logs + '/patch.log', 'a') do |stream|
          status = Process.wait2(Process.spawn('patch', '-f', '-N', '-F', '0', '-p0', '-d', source, in: input_stream, out: stream, err: stream)).last
          abort 'Canonical patch failed; see ' + logs + '/patch.log' unless status.success?
        end
      end
    end
    # Preserve the owning recipe's explicit build-host Python substitution.
    if name == 'glib'
      python, status = Open3.capture2('sh', '-c', 'command -v python3')
      abort 'Missing native upstream Python generator' unless status.success?
      ['meson.build'].each do |file|
        path = source + '/' + file
        File.write(path, File.read(path).gsub('@TOOL_PYTHONBIN@', python.strip))
      end
    end
    File.write(receipt_path, JSON.pretty_generate(receipt) + "\n")
  end
  [base, source, logs]
end

_, meson_source, = prepare.call('meson', 'meson-1.12.1.tar.gz', nil)
meson = ['python3', meson_source + '/meson.py']
crossfile = nil
if mode == 'cross'
  crossfile = work + '/cross.ini'
  quote = ->(value) { "'" + value.gsub("'", "\\\\'") + "'" }
  array = ->(values) { '[' + values.map { |v| quote.call(v) }.join(', ') + ']' }
  cpu = target == 'aarch64--netbsd' ? 'aarch64' : 'x86_64'
  content = "[binaries]\nc = #{quote.call(cc)}\ncpp = #{quote.call(cxx)}\nar = #{quote.call(ar)}\nstrip = #{quote.call(strip)}\npkg-config = 'pkg-config'\n"
  %w[glib-mkenums glib-genmarshal glib-compile-resources gdbus-codegen].each { |name| content += "#{name} = #{quote.call(native_prefix + '/bin/' + name)}\n" }
  content += "[built-in options]\nc_args = #{array.call(cflags)}\ncpp_args = #{array.call(cflags)}\nc_link_args = #{array.call(ldflags)}\ncpp_link_args = #{array.call(ldflags)}\n"
  content += "[properties]\nneeds_exe_wrapper = true\nsys_root = #{quote.call(sysroot)}\ngrowing_stack = false\nhave_c99_snprintf = true\nhave_c99_vsnprintf = true\nhave_strlcpy = true\nhave_unix98_printf = true\n"
  content += "[host_machine]\nsystem = 'netbsd'\ncpu_family = '#{cpu}'\ncpu = '#{cpu}'\nendian = 'little'\n"
  File.write(crossfile, content)
end

dependency_notices = {}
dependency_notice = lambda do |archive, filename|
  key = [archive, filename]
  next dependency_notices.fetch(key) if dependency_notices.key?(key)
  pin = pins.fetch(archive)
  archive_path = File.join(archives, archive)
  abort 'Dependency source checksum mismatch: ' + archive unless Digest::SHA256.file(archive_path).hexdigest == pin.fetch('sha256')
  listing, error, status = Open3.capture3('tar', '-tf', archive_path)
  abort error unless status.success?
  members = listing.lines.map(&:chomp).select { |name| name.match?(%r{\A[^/]+/#{Regexp.escape(filename)}\z}) }
  abort 'Missing or ambiguous dependency licence: ' + filename unless members.size == 1
  text, error, status = Open3.capture3('tar', '-xOf', archive_path, members.first)
  abort error unless status.success?
  dependency_notices[key] = text
end

configure_installed_test_data = lambda do |base, source|
  next unless mode == 'cross' && File.basename(base) == 'gst-tests'
  archive = 'gst-plugins-good-1.28.8.tar.xz'
  relative = 'tests/check/meson.build'
  original = dependency_notice.call(archive, relative).b
  old = %q{  '-DGST_TEST_FILES_PATH="' + fsmod.as_posix(meson.current_source_dir()) + '/../files"',}
  replacement = %q{  '-DGST_TEST_FILES_PATH="/usr/pkg/share/emberbsd-rtp-tests"',}
  abort 'Unexpected upstream test fixture define' unless original.lines.count { |line| line.chomp == old } == 1
  configured = original.sub(old, replacement)
  path = source + '/' + relative
  current = File.binread(path)
  abort 'Test Meson input differs beyond installed fixture path' unless current == original || current == configured
  backup = base + '/before-installed-test-data/' + relative
  FileUtils.mkdir_p(File.dirname(backup))
  File.binwrite(backup, original) unless File.file?(backup)
  abort 'Original test Meson backup differs' unless File.binread(backup) == original
  fixture_relative = 'tests/files/h265.rtp'
  fixture = dependency_notice.call(archive, fixture_relative).b
  abort 'Upstream RTP fixture differs from verified archive' unless File.binread(source + '/' + fixture_relative) == fixture
  delta = {'path' => relative, 'original_sha256' => Digest::SHA256.hexdigest(original),
    'configured_sha256' => Digest::SHA256.hexdigest(configured),
    'original_define' => old.strip, 'installed_define' => replacement.strip,
    'test_data' => [{'source_path' => fixture_relative,
      'installed_path' => '/usr/pkg/share/emberbsd-rtp-tests/h265.rtp',
      'size' => fixture.bytesize, 'sha256' => Digest::SHA256.hexdigest(fixture)}]}
  receipt = base + '/installed-test-data-config.json'
  abort 'Installed test data configuration changed' if File.file?(receipt) && JSON.parse(File.read(receipt)) != delta
  File.write(receipt, JSON.pretty_generate(delta) + "\n")
  File.binwrite(path, configured) if current != configured
end

# Install notices before the inventory. Verified PASS components use this same
# path, so adding notices does not rebuild their unchanged libraries.
install_notices = lambda do |base, source_base, payload|
  name = File.basename(base)
  source = source_base + '/source'
  inputs = JSON.parse(File.read(source_base + '/source-inputs.json'))
  pin = pins.fetch(inputs.fetch('archive'))
  directory = payload + '/share/licenses/' + name
  FileUtils.mkdir_p(directory)
  File.chmod(0755, payload + '/share/licenses', directory)
  copied = []
  copy = lambda do |relative, text|
    path = directory + '/' + relative
    FileUtils.mkdir_p(File.dirname(path))
    File.binwrite(path, text)
    File.chmod(0644, path)
    copied << {'path' => relative, 'sha256' => Digest::SHA256.hexdigest(text)}
  end
  files = Dir.children(source).select { |file| file.match?(/\A(?:COPYING|LICEN[CS]E|NOTICE|AUTHORS|COPYRIGHT)(?:[._-].*)?\z/i) && File.file?(source + '/' + file) }
  if File.directory?(source + '/LICENSES')
    Find.find(source + '/LICENSES') { |path| files << path.delete_prefix(source + '/') if File.file?(path) }
  end
  abort 'No upstream licence text for ' + name if files.empty?
  files.sort.each do |relative|
    path = File.realpath(source + '/' + relative)
    abort 'Licence symlink escapes its source' unless path.start_with?(File.realpath(source) + '/')
    copy.call(relative, File.binread(path))
  end
  dependencies = []
  if %w[gst-bad gst-libav].include?(name)
    copy.call('dependencies/x265/COPYING', dependency_notice.call('x265_4.2.tar.gz', 'COPYING'))
    dependencies << {'archive' => 'x265_4.2.tar.gz', 'sha256' => pins.fetch('x265_4.2.tar.gz').fetch('sha256'), 'url' => pins.fetch('x265_4.2.tar.gz').fetch('url')}
  end
  if name == 'gst-libav'
    %w[COPYING.GPLv2 COPYING.GPLv3 COPYING.LGPLv2.1 COPYING.LGPLv3 LICENSE.md].each do |file|
      copy.call('dependencies/ffmpeg9/' + file, dependency_notice.call('ffmpeg-9.0.2.tar.xz', file))
    end
    dependencies << {'archive' => 'ffmpeg-9.0.2.tar.xz', 'sha256' => pins.fetch('ffmpeg-9.0.2.tar.xz').fetch('sha256'), 'url' => pins.fetch('ffmpeg-9.0.2.tar.xz').fetch('url')}
  end
  notice = "Original source copyrights and licence texts are retained.\nSOURCE records the verified archive and selected patch inputs.\n"
  notice += "The selected x265 module links x265 4.2 under GPL-2.0-or-later.\nThe upstream x265 plugin reports GPL for this linked module.\n" if name == 'gst-bad'
  if name == 'gst-libav'
    notice += "The wrapper retains its upstream LGPL COPYING text.\nThis profile links FFmpeg 9.0.2 built with --enable-gpl, --enable-version3 and x265.\nThe selected FFmpeg libraries are GPL-3.0-or-later; x265 is GPL-2.0-or-later.\nGST_LIBAV_ENABLE_GPL makes this linked plugin report GPL.\nThe upstream wrapper licence does not describe the complete linked profile.\nDependency COPYING texts are retained below dependencies/.\n"
  end
  copy.call('NOTICE.emberbsd', notice)
  manifest = inputs.merge('component' => name, 'url' => pin.fetch('url'),
    'recipe' => pin['recipe'], 'dependencies' => dependencies,
    'build_helper' => {'path' => script.delete_prefix(ports + '/'), 'sha256' => Digest::SHA256.file(script).hexdigest},
    'extra_cflags' => name == 'gst-libav' ? ['-DGST_LIBAV_ENABLE_GPL=1'] : [],
    'licence_files' => copied)
  if mode == 'cross' && name == 'gst-tests'
    manifest['build_configuration'] = JSON.parse(File.read(base + '/installed-test-data-config.json'))
  end
  copy.call('SOURCE', JSON.pretty_generate(manifest) + "\n")
  Find.find(directory) { |path| File.chmod(0755, path) if File.directory?(path) }
end

normalize_cross_metadata = lambda do |base, payload|
  next if mode != 'cross'
  from = sysroot + prefix
  pattern = /#{Regexp.escape(from)}(?=\/|[\s'"]|\z)/
  receipt_path = base + '/cross-metadata-normalization.json'
  history = File.file?(receipt_path) ? JSON.parse(File.read(receipt_path)).fetch('changes') : []
  validated = []
  Find.find(payload) do |path|
    next unless File.file?(path) && %w[.la .pc .cmake].include?(File.extname(path))
    relative = path.delete_prefix(payload + '/')
    text = File.binread(path)
    normalized = File.extname(path) == '.la' ? text.gsub(pattern, prefix) : text
    forbidden = [work, sysroot, File.dirname(work) + '/', File.dirname(sysroot) + '/', compiler, native_prefix].find { |host_path| normalized.include?(host_path) }
    abort 'Installed metadata retains a host work/sysroot path: ' + relative if forbidden
    if normalized != text
      backup = base + '/before-sysroot-metadata/' + relative
      FileUtils.mkdir_p(File.dirname(backup))
      if File.file?(backup)
        abort 'Existing cross metadata backup differs: ' + relative unless File.binread(backup) == text
      else
        File.binwrite(backup, text)
      end
      change = {'path' => relative, 'before_sha256' => Digest::SHA256.hexdigest(text), 'after_sha256' => Digest::SHA256.hexdigest(normalized)}
      abort 'Cross metadata history differs: ' + relative if history.any? { |entry| entry['path'] == relative && entry != change }
      history << change unless history.include?(change)
      File.binwrite(path, normalized)
    end
    validated << {'path' => relative, 'sha256' => Digest::SHA256.hexdigest(normalized)}
  end
  receipt = {'mapping' => {'from' => from, 'to' => prefix}, 'changes' => history, 'validated_files' => validated}
  File.write(receipt_path, JSON.pretty_generate(receipt) + "\n")
end

normalize_cross_test_rpath = lambda do |base, payload|
  next unless mode == 'cross' && File.basename(base) == 'gst-tests'
  receipt_path = base + '/cross-test-rpath.json'
  history = File.file?(receipt_path) ? JSON.parse(File.read(receipt_path)).fetch('changes') : []
  validated = []
  %w[elements_rtph265 elements_rtpjitterbuffer].each do |name|
    path = payload + '/libexec/emberbsd-rtp-tests/' + name
    before, error, status = Open3.capture3({'LC_ALL' => 'C'}, 'readelf', '-d', path)
    abort error unless status.success?
    values = before.scan(/\((?:RPATH|RUNPATH)\).*?\[([^\]]+)\]/).flatten
    abort 'Missing or ambiguous upstream test runtime path: ' + name unless values.size == 1
    old = values.first
    paths = old.split(':')
    # These upstream test targets are not installed by Meson. Their manual
    # copy retains Meson's automatic build-only dependency path. Apply the
    # same install-time RPATH transition with CMake, using exact known paths.
    build_path = sysroot + prefix + '/lib'
    abort 'Unrecognized upstream test runtime path: ' + name unless (paths - (rpath + [build_path])).empty? && (rpath - paths).empty?
    desired = paths.reject { |entry| entry == build_path }.join(':')
    if desired != old
      before_hash = Digest::SHA256.file(path).hexdigest
      backup = base + '/before-cross-test-rpath/' + before_hash + '/' + name
      FileUtils.mkdir_p(File.dirname(backup))
      FileUtils.cp(path, backup) unless File.file?(backup)
      abort 'Cross test ELF backup differs: ' + name unless Digest::SHA256.file(backup).hexdigest == before_hash
      cmake_script = base + '/cross-test-rpath.cmake'
      File.write(cmake_script, "file(RPATH_CHANGE FILE [[#{path}]] OLD_RPATH [[#{old}]] NEW_RPATH [[#{desired}]])\n")
      run!({}, ['cmake', '-P', cmake_script], base + '/logs/install.log')
      after, error, status = Open3.capture3({'LC_ALL' => 'C'}, 'readelf', '-d', path)
      abort error unless status.success?
      abort 'Unexpected test dynamic-section change: ' + name unless after == before.sub('[' + old + ']', '[' + desired + ']')
      change = {'path' => path.delete_prefix(payload + '/'), 'before_sha256' => before_hash,
        'after_sha256' => Digest::SHA256.file(path).hexdigest, 'from' => old, 'to' => desired}
      history << change unless history.include?(change)
    end
    validated << {'path' => path.delete_prefix(payload + '/'), 'sha256' => Digest::SHA256.file(path).hexdigest,
      'runtime_path' => desired}
  end
  File.write(receipt_path, JSON.pretty_generate({'changes' => history, 'validated_files' => validated}) + "\n")
end

install = lambda do |base, source_base = base|
  payload = File.join(base, 'stage') + prefix
  abort 'Missing staged payload: ' + payload unless File.directory?(payload)
  if mode == 'cross' && File.basename(base) == 'gst-tests'
    fixture_dir = payload + '/share/emberbsd-rtp-tests'
    FileUtils.mkdir_p(fixture_dir)
    FileUtils.install(source_base + '/source/tests/files/h265.rtp', fixture_dir + '/h265.rtp', mode: 0644)
  end
  normalize_cross_test_rpath.call(base, payload)
  normalize_cross_metadata.call(base, payload)
  install_notices.call(base, source_base, payload)
  entries = []
  Find.find(payload) do |path|
    next if path == payload
    relative = path.delete_prefix(payload + '/')
    stat = File.lstat(path)
    entry = {'path' => relative, 'mode' => stat.mode & 07777}
    if stat.symlink?
      entry.merge!('type' => 'link', 'target' => File.readlink(path))
    elsif stat.file?
      entry.merge!('type' => 'file', 'size' => stat.size, 'sha256' => Digest::SHA256.file(path).hexdigest)
    elsif stat.directory?
      entry['type'] = 'directory'
    else
      abort 'Unsupported staged path: ' + path
    end
    entries << entry
  end
  File.write(base + '/installed-files.json', JSON.pretty_generate(entries) + "\n")
  File.write(base + '/PLIST', entries.reject { |e| e['type'] == 'directory' }.map { |e| e['path'] }.sort.join("\n") + "\n")
  destinations = [mode == 'native' ? output : output + prefix]
  destinations << sysroot + prefix if mode == 'cross' && sysroot != output
  destinations.each do |destination|
    FileUtils.mkdir_p(destination)
    run!({}, ['cp', '-a', payload + '/.', destination], base + '/logs/promote.log')
  end
end

# The canonical GLib recipe splits these upstream Python generators into
# glib2-tools. Install the native package separately. Target packages do not
# need Python generators to execute the RTP application.
install_host_tools = lambda do
  next unless mode == 'native'
  base = work + '/glib-tools'
  bin = base + '/stage' + prefix + '/bin'
  FileUtils.mkdir_p(bin)
  %w[glib-genmarshal glib-mkenums].each do |name|
    input = work + '/glib/build/gobject/' + name
    abort 'Missing native GLib generator: ' + input unless File.file?(input)
    FileUtils.install(input, bin + '/' + name, mode: 0755)
  end
  install.call(base, work + '/glib')
end

# Autotools/libtool logs with V=1 contain the compiler invocations that ran.
# Meson writes its own compilation database. Do not infer silent commands.
record_make_commands = lambda do |base|
  log = base + '/logs/build.log'
  next unless File.file?(log)
  commands = File.binread(log).lines.filter_map do |line|
    text = line.strip
    text = text.delete_prefix('libtool: compile:').strip if text.start_with?('libtool: compile:')
    next unless text.match?(/\A\S*(?:gcc|g\+\+|cc|c\+\+)(?:\s|$)/)
    argv = Shellwords.split(text)
    next unless argv.include?('-c') && argv.include?('-o')
    source = argv.find { |value| value.match?(/\.(?:c|cc|cpp|S)$/) }
    next unless source
    {'directory' => base + '/build', 'arguments' => argv,
      'file' => File.expand_path(source, base + '/build'), 'output' => argv[argv.index('-o') + 1]}
  end
  File.write(base + '/build/compile_commands.json', JSON.pretty_generate(commands) + "\n") unless commands.empty?
end

components = [
 ['libffi', 'libffi-3.8.0.tar.gz', ffi_recipe, :configure, ['--disable-multi-os-directory', '--includedir=' + prefix + '/include', '--disable-static']],
 ['pcre2', 'pcre2-10.49.tar.gz', pkgsrc + '/devel/pcre2', :configure, ['--enable-pcre2-16', '--enable-pcre2-32', '--disable-jit', '--disable-static', '--enable-pcre2grep-libz', '--enable-pcre2grep-libbz2']],
 ['glib', 'glib-2.90.1.tar.xz', pkgsrc + '/devel/glib2', :meson, ['-Dtests=false', '-Dinstalled_tests=false', '-Dintrospection=disabled', '-Ddtrace=disabled', '-Dglib_debug=disabled', '-Dlibmount=disabled', '-Dsysprof=disabled', '-Dselinux=disabled', '-Dlibelf=disabled', '-Ddocumentation=false', '-Dman-pages=disabled', '-Dnls=enabled', '-Dlocalstatedir=/var', '-Druntime_dir=/var/run']],
 ['gstreamer', 'gstreamer-1.28.8.tar.xz', pkgsrc + '/multimedia/gstreamer1', :meson, ['-Dtools=enabled', '-Dcheck=enabled', '-Dtests=disabled', '-Dexamples=disabled', '-Dbenchmarks=disabled', '-Dintrospection=disabled', '-Dptp-helper=disabled', '-Dcoretracers=enabled', '-Dnls=enabled']],
 ['gst-base', 'gst-plugins-base-1.28.8.tar.xz', pkgsrc + '/multimedia/gst-plugins1-base', :meson, ['-Dapp=enabled', '-Dvideoconvertscale=enabled', '-Dvideotestsrc=enabled', '-Dtypefind=enabled', '-Drawparse=enabled', '-Dgio=enabled', '-Dgio-typefinder=enabled', '-Dintrospection=disabled', '-Dorc=disabled', '-Dtools=enabled']],
 ['gst-good', 'gst-plugins-good-1.28.8.tar.xz', pkgsrc + '/multimedia/gst-plugins1-good', :meson, ['-Drtp=enabled', '-Drtpmanager=enabled', '-Dudp=enabled']],
 ['gst-bad', 'gst-plugins-bad-1.28.8.tar.xz', pkgsrc + '/multimedia/gst-plugins1-bad', :meson, ['-Dvideoparsers=enabled', '-Dx265=enabled', '-Dgpl=enabled', '-Dintrospection=disabled', '-Dorc=disabled']],
 ['gst-libav', 'gst-libav-1.28.8.tar.xz', pkgsrc + '/multimedia/gst-plugins1-libav', :meson, []],
 # Select this component explicitly. Build the unchanged upstream test units
 # against the installed SDK. Do not rebuild or install another plugin copy.
 ['gst-tests', 'gst-plugins-good-1.28.8.tar.xz', pkgsrc + '/multimedia/gst-plugins1-good', :meson_tests, ['-Drtp=enabled', '-Drtpmanager=enabled', '-Dudp=enabled']]
]
if ENV['COMPONENTS']
  selected = ENV['COMPONENTS'].split(',')
  abort 'COMPONENTS must select known, unique components' if selected.empty? || selected.uniq != selected || (selected - components.map(&:first)).any?
end
components.each do |name, archive, recipe, system, args|
  next if name == 'gst-tests' && !ENV['COMPONENTS']
  next if ENV['COMPONENTS'] && !ENV['COMPONENTS'].split(',').include?(name)
  base, source, logs = prepare.call(name, archive, recipe)
  configure_installed_test_data.call(base, source)
  build = base + '/build'
  stage = base + '/stage'
  identity = {'mode' => mode, 'prefix' => prefix, 'target' => target, 'compiler' => cc, 'arguments' => args, 'rpath' => rpath}
  extra_cflags = name == 'gst-libav' ? ['-DGST_LIBAV_ENABLE_GPL=1'] : []
  identity['extra_cflags'] = extra_cflags unless extra_cflags.empty?
  identity['test_files_path'] = '/usr/pkg/share/emberbsd-rtp-tests' if mode == 'cross' && name == 'gst-tests'
  if File.file?(base + '/PASS.json')
    previous = JSON.parse(File.read(base + '/PASS.json'))
    if previous == identity
      install.call(base)
      install_host_tools.call if name == 'glib'
      record_make_commands.call(base) if system == :configure
      puts 'Verified existing component: ' + name
      next
    end
    if mode == 'cross' && name == 'gst-tests' && previous == identity.reject { |key, _| key == 'test_files_path' }
      saved = base + '/before-installed-test-data'
      old_payloads = %w[elements_rtph265 elements_rtpjitterbuffer].map { |test| 'libexec/emberbsd-rtp-tests/' + test }
    elsif name == 'gst-libav' && previous == identity.reject { |key, _| key == 'extra_cflags' }
      # Retain the old module before selecting the upstream GPL define.
      saved = base + '/before-gpl-metadata'
      abort 'Incomplete existing GPL metadata backup' if File.exist?(saved) && !File.file?(saved + '/MIGRATION.json')
      old_payloads = ['lib/gstreamer-1.0/libgstlibav.so']
    else
      abort 'Build configuration changed; use a new work directory'
    end
    migration = {'before' => previous, 'after' => identity}
    if File.file?(saved + '/MIGRATION.json')
      abort 'Existing build migration backup differs' unless JSON.parse(File.read(saved + '/MIGRATION.json')) == migration
    else
      FileUtils.mkdir_p(saved)
      preserve = lambda do |input, copy|
        if File.file?(copy)
          abort 'Existing migration backup differs: ' + copy unless Digest::SHA256.file(input).hexdigest == Digest::SHA256.file(copy).hexdigest
        else
          FileUtils.cp(input, copy)
        end
      end
      %w[PASS.json PLIST installed-files.json].each { |file| preserve.call(base + '/' + file, saved + '/' + file) if File.file?(base + '/' + file) }
      old_payloads.each do |relative|
        input = stage + prefix + '/' + relative
        copy = saved + '/' + File.basename(relative)
        preserve.call(input, copy)
        abort 'Build migration ELF backup differs' unless Digest::SHA256.file(input).hexdigest == Digest::SHA256.file(copy).hexdigest
      end
      notice = stage + prefix + '/share/licenses/' + name + '/SOURCE'
      preserve.call(notice, saved + '/SOURCE') if File.file?(notice)
      File.write(saved + '/MIGRATION.json', JSON.pretty_generate(migration) + "\n")
    end
  end
  FileUtils.mkdir_p(build)
  if system == :configure
    configure_args = [source + '/configure', '--prefix=' + prefix, '--libdir=' + prefix + '/lib'] + args
    configure_args += ['--host=' + target, '--build=' + `gcc -dumpmachine`.strip] if mode == 'cross'
    run!(environment, configure_args, logs + '/configure.log', build) unless File.file?(build + '/Makefile')
    run!(environment, ['make', 'V=1', '-j' + jobs.to_s], logs + '/build.log', build)
    run!(environment, ['make', 'DESTDIR=' + stage, 'install'], logs + '/install.log', build)
    record_make_commands.call(base)
  else
    common = ['--prefix=' + prefix, '--libdir=lib', '--buildtype=debugoptimized', '--default-library=shared', '--wrap-mode=nofallback', '-Dauto_features=disabled']
    common << '-Dc_args=' + JSON.generate(cflags + extra_cflags) unless extra_cflags.empty?
    if name == 'gst-libav'
      common += ['-Dtests=disabled', '-Ddoc=disabled']
    elsif name.start_with?('gst-')
      common += ['-Dtests=' + (system == :meson_tests ? 'enabled' : 'disabled'), '-Dexamples=disabled', '-Ddoc=disabled', '-Dnls=enabled']
    end
    common += ['--cross-file=' + crossfile] if crossfile
    setup = meson + ['setup', build, source] + common + args
    setup << '--reconfigure' if File.file?(build + '/build.ninja')
    run!(environment, setup, logs + '/configure.log')
    targets = system == :meson_tests ? %w[elements_rtph265 elements_rtpjitterbuffer] : []
    run!(environment, meson + ['compile', '-C', build, '-j', jobs.to_s] + targets, logs + '/build.log')
    if system == :meson_tests
      testbin = stage + prefix + '/libexec/emberbsd-rtp-tests'
      FileUtils.mkdir_p(testbin)
      targets.each { |name| FileUtils.install(build + '/tests/check/' + name, testbin + '/' + name, mode: 0755) }
    else
      run!(environment, meson + ['install', '-C', build, '--destdir=' + stage, '--no-rebuild'], logs + '/install.log')
    end
  end
  install.call(base)
  install_host_tools.call if name == 'glib'
  File.write(base + '/PASS.json', JSON.pretty_generate(identity) + "\n")
  puts 'Built and installed component: ' + name
  $stdout.flush
end
RUBY
