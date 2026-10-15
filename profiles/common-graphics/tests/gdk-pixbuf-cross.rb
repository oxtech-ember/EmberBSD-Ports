#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise patched Meson selection and installed build rules.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
abort 'Usage: gdk-pixbuf-cross.rb BUILT_SOURCE HOST_PREFIX CROSS_CC NEW_WORK' unless ARGV.size == 4
source, host, cc = ARGV.first(3).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'new absolute work required' unless ARGV.last.start_with?('/') && !File.exist?(work)
FileUtils.mkdir_p(work + '/source/build-aux')
root = File.read(source + '/meson.build')
start = root.index("if meson.is_cross_build() and meson.get_external_property('emberbsd_gi_cross'") or abort 'missing native Python selection'
finish = root.index("\nendif", start) or abort 'missing Python selection end'
root = root[start..finish + 6]
selection = File.read(source + '/gdk-pixbuf/meson.build')
start = selection.index('emberbsd_gi_cross =') or abort 'missing GI selection'
finish = selection.index('  gdkpixbuf_gir =', start) or abort 'missing GI selection end'
selection = selection[start...finish] + "endif\n"
File.write(work + '/source/meson.options', "option('introspection', type: 'feature', value: 'enabled')\n")
File.write(work + '/source/build-aux/gen-thumbnailer.py', "#!/usr/bin/env python3\n")
File.chmod(0755, work + '/source/build-aux/gen-thumbnailer.py')
File.write(work + '/source/meson.build', "project('pixbuf-tool-selection', 'c')\n" + root + selection + <<~MESON)
  if emberbsd_gi_cross
    message('native scanner: ' + gir.full_path())
    message('native compiler: ' + gir_compiler.full_path())
    message('native python: ' + gen_thumbnailer[0].full_path())
  else
    message('ordinary generator: ' + gen_thumbnailer.full_path())
  endif
  message('scanner arguments: ' + ' '.join(gir_args))
MESON
helper = File.expand_path('../recipes/graphics/gdk-pixbuf2/files/target-tools.rb', __dir__)
needed = File.expand_path('../recipes/devel/gobject-introspection/files/elf-needed.sh', __dir__)
properties = "emberbsd_gi_cross = true\nemberbsd_pixbuf_python = '#{host}/bin/python3.15'\nemberbsd_gi_ldd_wrapper = '#{needed}'\nemberbsd_pixbuf_runner = ['#{RbConfig.ruby}', '#{helper}']\n"
binaries = "[binaries]\nc = '#{cc}'\ng-ir-scanner = '/usr/bin/false'\n"
machine = "[host_machine]\nsystem = 'netbsd'\ncpu_family = 'aarch64'\ncpu = 'aarch64'\nendian = 'little'\n"
File.write(work + '/cross.ini', binaries + machine)
File.write(work + '/enabled.ini', binaries + machine + "[properties]\n" + properties)
File.write(work + '/native.ini', "[binaries]\nc = '/usr/bin/cc'\ng-ir-scanner = '#{host}/bin/g-ir-scanner'\ng-ir-compiler = '#{host}/bin/g-ir-compiler'\n[properties]\n" + properties)
%w[native default-cross enabled-cross].each do |mode|
  args = [host + '/bin/meson', 'setup', work + '/' + mode, work + '/source', '--native-file', work + '/native.ini']
  args += ['--cross-file', work + (mode == 'default-cross' ? '/cross.ini' : '/enabled.ini')] unless mode == 'native'
  out, status = Open3.capture2e({'PATH' => host + '/bin:/usr/bin:/bin', 'CC' => nil, 'CFLAGS' => nil, 'LDFLAGS' => nil}, *args)
  File.write(work + '/' + mode + '.log', out)
  abort "#{mode} failed: #{out}" unless status.success?
  if mode == 'enabled-cross'
    %w[scanner compiler].each { |tool| abort "wrong native #{tool}" unless out.include?("native #{tool}: #{host}/bin/g-ir-#{tool}") }
    abort 'wrong native Python' unless out.include?('native python: ' + host + '/bin/python3.15')
    abort 'ELF inspection missing' unless out.include?('--use-ldd-wrapper=')
  else
    abort 'ordinary generator changed' unless out.include?('ordinary generator: ' + work + '/source/build-aux/gen-thumbnailer.py')
    abort 'unexpected ELF inspection' if out.include?('--use-ldd-wrapper=')
  end
end
# Fail closed when explicitly selected native Python is absent.
bad = File.read(work + '/enabled.ini').sub(host + '/bin/python3.15', work + '/missing-python')
File.write(work + '/missing.ini', bad)
out, status = Open3.capture2e(host + '/bin/meson', 'setup', work + '/missing', work + '/source', '--native-file', work + '/native.ini', '--cross-file', work + '/missing.ini')
File.write(work + '/missing.log', out)
abort 'missing native Python was accepted' if status.success? || !out.include?('missing-python')
targets = JSON.parse(File.read(source + '/output/meson-info/intro-targets.json'))
%w[GdkPixbuf-2.0 GdkPixdata-2.0].each do |namespace|
  %w[gir typelib].each do |ext|
    target = targets.find { |t| t.fetch('name') == namespace + '.' + ext } or abort 'missing metadata target'
    command = target.fetch('target_sources').flat_map { |s| s.fetch('compiler', []) }
    expected = host + '/bin/g-ir-' + (ext == 'gir' ? 'scanner' : 'compiler')
    abort 'wrong actual native generator' unless command.any? { |p| File.exist?(p) && File.realpath(p) == File.realpath(expected) }
    abort 'empty metadata output' unless File.size?(source + '/output/gdk-pixbuf/' + namespace + '.' + ext)
  end
end
thumbnail = File.read(source + '/output/thumbnailer/gdk-pixbuf-thumbnailer.thumbnailer')
%w[image/png image/jpeg image/tiff image/x-tga image/x-icns].each { |type| abort "thumbnail MIME missing: #{type}" unless thumbnail.include?(type + ';') }
File.write(work + '/inputs.sha256', [__FILE__, source + '/meson.build', source + '/gdk-pixbuf/meson.build', source + '/output/build.ninja'].map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p}\n" }.join)
puts 'PASS: native/default paths preserved, explicit native generators, missing Python rejected, all metadata and thumbnail outputs present'
