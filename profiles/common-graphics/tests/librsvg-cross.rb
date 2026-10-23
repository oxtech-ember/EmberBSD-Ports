#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise actual source guards and generated rules.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'

abort 'Usage: librsvg-cross.rb BUILT_SOURCE HOST_PREFIX CROSS_CC NEW_WORK' unless ARGV.size == 4
source, host, cc = ARGV.first(3).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'new absolute work required' unless ARGV.last.start_with?('/') && !File.exist?(work)
FileUtils.mkdir_p(work + '/source')
# Removing only the new canonical include mapping must reproduce the scanner's
# missing-header failure even though the target header is installed.
wrkdir = File.dirname(source)
cross_file = File.read(wrkdir + '/.meson_cross')
sysroot = File.realpath(cross_file[/^sys_root = '([^']+)'$/, 1] || abort('missing sysroot'))
mapping = "transform=I:#{sysroot}/usr/pkg:#{wrkdir}/.buildlink\n"
config = File.read(wrkdir + '/.cwrapper/config/cc')
abort 'canonical buildlink mapping absent' unless config.include?(mapping)
%w[good missing-map].each do |mode|
  dir = work + '/wrapper-' + mode
  FileUtils.mkdir_p(dir)
  File.write(dir + '/cc', mode == 'good' ? config : config.sub(mapping, ''))
  out, err, status = Open3.capture3({'CWRAPPERS_CONFIG_DIR' => dir},
    wrkdir + '/.cwrapper/bin/cc', '-E', '-x', 'c', '-I' + sysroot + '/usr/pkg/include/cairo', '-',
    stdin_data: "#include <cairo.h>\n")
  File.write(work + '/wrapper-' + mode + '.log', "exit=#{status.exitstatus}\nstdout_sha256=#{Digest::SHA256.hexdigest(out)}\n" + err)
  if mode == 'good'
    abort 'canonical target headers still rejected' unless status.success?
  else
    abort 'missing-map control failed at another oracle' if status.success? || !err.include?('cairo.h: No such file or directory')
  end
end
root = File.read(source + '/meson.build')
start = root.index('# The Ports recipe validates') or abort 'cross fragment missing'
finish = root.index('build_vala =', start) or abort 'cross guard end missing'
fragment = root[start...finish]
rsvg = File.read(source + '/rsvg/meson.build')
start = rsvg.index('  if emberbsd_gi_cross') or abort 'scanner arguments missing'
finish = rsvg.index('  rsvg_gir = gnome.generate_gir(', start) or abort 'scanner fragment end missing'
fragment += rsvg[start...finish]
pixbuf = File.read(source + '/gdk-pixbuf-loader/meson.build')
start = pixbuf.index("prefix = get_option('prefix')") or abort 'pixbuf directory fragment missing'
finish = pixbuf.index('pixbufloader = custom_target(', start) or abort 'pixbuf fragment end missing'
fragment += "pixbuf_dep = dependency('fixture-pixbuf')\n" + pixbuf[start...finish]
File.write(work + '/fixture-pixbuf.pc', "Name: fixture-pixbuf\nDescription: install path fixture\nVersion: 1\ngdk_pixbuf_moduledir=/lookup-sysroot/usr/pkg/lib/loaders\n")
File.write(work + '/source/meson.options', "option('introspection', type: 'feature', value: 'enabled')\n")
File.write(work + '/source/meson.build', <<~MESON + fragment + <<~MESON)
  project('librsvg-cross-selection', 'c')
  host_system = host_machine.system()
  gi_dep = dependency('gobject-introspection-1.0')
  gir_args = []
MESON
  message('explicit cross path: ' + emberbsd_gi_cross.to_string())
  message('scanner arguments: ' + ' '.join(gir_args))
  message('module install path: ' + pixbuf_module_dir)
MESON
needed = File.expand_path('../../../pkgsrc/devel/gobject-introspection/files/elf-needed.sh', __dir__)
native = "[binaries]\nc = '/usr/bin/cc'\npkg-config = '#{host}/bin/pkg-config'\ng-ir-scanner = '#{host}/bin/g-ir-scanner'\ng-ir-compiler = '#{host}/bin/g-ir-compiler'\n"
module_dir = '/usr/pkg/lib/gdk-pixbuf-2.0/2.10.0/loaders'
properties = "[properties]\nemberbsd_gi_cross = true\nemberbsd_gi_ldd_wrapper = '#{needed}'\nemberbsd_pixbuf_module_dir = '#{module_dir}'\n"
cross = "[binaries]\nc = '#{cc}'\npkg-config = '#{host}/bin/pkg-config'\n[host_machine]\nsystem = 'netbsd'\ncpu_family = 'aarch64'\ncpu = 'aarch64'\nendian = 'little'\n"
File.write(work + '/native.ini', native + properties)
File.write(work + '/cross.ini', cross)
File.write(work + '/enabled.ini', cross + properties)
env = {'PATH' => host + '/bin:/usr/bin:/bin', 'PKG_CONFIG_SYSROOT_DIR' => '', 'PKG_CONFIG_PATH' => work,
       'PKG_CONFIG_LIBDIR' => host + '/lib/pkgconfig:' + host + '/share/pkgconfig',
       'CC' => nil, 'CXX' => nil, 'CFLAGS' => nil, 'LDFLAGS' => nil, 'CPPFLAGS' => nil}
%w[default-cross enabled-cross native].each do |mode|
  command = [host + '/bin/meson', 'setup', work + '/' + mode, work + '/source', '--native-file', work + '/native.ini']
  command += ['--cross-file', work + (mode == 'default-cross' ? '/cross.ini' : '/enabled.ini')] unless mode == 'native'
  out, status = Open3.capture2e(env, *command)
  File.write(work + '/' + mode + '.log', out)
  if mode == 'default-cross'
    abort 'default cross guard did not reject' if status.success? || !out.include?('Feature introspection cannot be disabled')
  else
    enabled = mode == 'enabled-cross'
    abort "#{mode} configuration failed: #{out}" unless status.success?
    abort 'incorrect explicit cross selection' unless out.include?("explicit cross path: #{enabled}")
    line = out.lines.find { |l| l.include?('scanner arguments:') } or abort 'no scanner arguments'
    abort 'incorrect scanner argument selection' unless line.include?('--use-ldd-wrapper=') == enabled
    expected_dir = enabled ? module_dir : '/lookup-sysroot/usr/pkg/lib/loaders'
    abort 'incorrect module install path selection' unless out.include?('module install path: ' + expected_dir)
  end
end
targets = JSON.parse(File.read(source + '/output/meson-info/intro-targets.json'))
module_target = targets.find { |t| t.fetch('name') == 'pixbufloader-svg' } or abort 'missing module target'
abort 'module install path contains host sysroot' unless module_target.fetch('install_filename') == [module_dir + '/libpixbufloader_svg.so']
%w[gir typelib].each do |ext|
  target = targets.find { |t| t.fetch('name') == "Rsvg-2.0.#{ext}" } or abort 'missing metadata target'
  tool = host + '/bin/' + (ext == 'gir' ? 'g-ir-scanner' : 'g-ir-compiler')
  commands = target.fetch('target_sources').flat_map { |t| t.fetch('compiler', []) }
  abort 'wrong native generator' unless commands.any? { |p| File.file?(p) && File.realpath(p) == File.realpath(tool) }
  abort 'missing metadata payload' unless File.size?(source + '/output/rsvg/Rsvg-2.0.' + ext)
end
ninja = File.read(source + '/output/build.ninja')
abort 'scanner does not inspect target ELF' unless ninja.include?('--use-ldd-wrapper=')
abort 'target nm not selected' unless ninja.include?('aarch64--netbsd-nm')
%w[rsvg_convert/rsvg-convert gdk-pixbuf-loader/libpixbufloader_svg.so].each do |path|
  abort "missing feature payload: #{path}" unless File.size?(source + '/output/' + path)
end
File.write(work + '/inputs.sha256', [__FILE__, source + '/meson.build', source + '/rsvg/meson.build', source + '/gdk-pixbuf-loader/meson.build', source + '/output/build.ninja'].map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p}\n" }.join)
puts 'PASS: canonical header mapping and negative control; default cross guard retained; explicit native generators and target install path; native behavior retained; full outputs verified'
