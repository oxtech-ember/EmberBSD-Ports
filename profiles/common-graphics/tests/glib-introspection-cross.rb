#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise the actual GLib Meson selection code.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'

abort 'Usage: glib-introspection-cross.rb BUILT_GLIB_SOURCE HOST_PREFIX CROSS_CC NEW_WORK' unless ARGV.size == 4
source, host, cc = ARGV.first(3).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'new absolute work required' unless ARGV.last.start_with?('/') && !File.exist?(work)
FileUtils.mkdir_p(work)
root = File.read(source + '/meson.build')
start = root.index("gobject_introspection_required_version =") or abort 'missing GI source section'
finish = root.index('glib_exec_preloaded_libs =', start) or abort 'missing GI section end'
fragment = root[start...finish]
compiler = File.read(source + '/girepository/compiler/meson.build')
compiler = compiler[compiler.index('if enable_gir')..] or abort 'missing compiler selection'
native = host + '/bin/gi-compile-repository'
scanner = host + '/bin/g-ir-scanner'
meson = host + '/bin/meson'
%W[#{native} #{scanner} #{meson}].each { |p| abort "missing native tool #{p}" unless File.executable?(p) }
FileUtils.mkdir_p(work + '/source')
File.write(work + '/source/meson.options', "option('introspection', type: 'feature', value: 'enabled')\n")
File.write(work + '/source/compiler.c', "int main(void) { return 42; }\n")
# This real build target is a selection sentinel; it is never executed.
File.write(work + '/source/meson.build', <<~MESON + fragment + compiler + <<~MESON)
  project('glib-introspection-selection', 'c')
  gicompilerepository = executable('target-compiler', 'compiler.c')
MESON
  selected = find_program('g-ir-compiler')
  message('selected compiler: ' + selected.full_path())
  message('cross arguments: ' + ' '.join(gir_args))
MESON
needed = File.expand_path('../../../pkgsrc/devel/gobject-introspection/files/elf-needed.sh', __dir__)
properties = "emberbsd_gi_cross = true\nemberbsd_gi_compiler = '#{native}'\nemberbsd_gi_ldd_wrapper = '#{needed}'\n"
binaries = "[binaries]\nc = '#{cc}'\npkg-config = '#{host}/bin/pkg-config'\n"
machine = "[host_machine]\nsystem = 'netbsd'\ncpu_family = 'aarch64'\ncpu = 'aarch64'\nendian = 'little'\n"
File.write(work + '/cross.ini', binaries + machine)
File.write(work + '/enabled.ini', binaries + machine + "[properties]\n" + properties)
File.write(work + '/native.ini', "[binaries]\nc = '/usr/bin/cc'\ng-ir-scanner = '#{scanner}'\npkg-config = '#{host}/bin/pkg-config'\n[properties]\n" + properties)
env = {'PATH' => host + '/bin:/usr/bin:/bin', 'PKG_CONFIG_SYSROOT_DIR' => '',
       'PKG_CONFIG_PATH' => '', 'PKG_CONFIG_LIBDIR' => host + '/lib/pkgconfig:' + host + '/share/pkgconfig',
       'CC' => nil, 'CFLAGS' => nil, 'LDFLAGS' => nil, 'CPPFLAGS' => nil}
%w[default-cross enabled-cross native].each do |mode|
  args = [meson, 'setup', work + '/' + mode, work + '/source', '--native-file', work + '/native.ini']
  args += ['--cross-file', work + (mode == 'default-cross' ? '/cross.ini' : '/enabled.ini')] unless mode == 'native'
  out, status = Open3.capture2e(env, *args)
  File.write(work + '/' + mode + '.log', out)
  if mode == 'default-cross'
    abort 'default cross guard did not reject' if status.success? || !out.include?('Running binaries on the build host needs to be supported')
  else
    abort "#{mode} configuration failed: #{out}" unless status.success?
    expected = mode == 'native' ? work + '/native/target-compiler' : native
    abort "#{mode} selected wrong compiler" unless out.include?('selected compiler: ' + expected)
    line = out.lines.find { |l| l.include?('cross arguments:') } or abort 'missing selection output'
    abort "#{mode} selected wrong scanner arguments" unless line.include?('--use-ldd-wrapper=') == (mode == 'enabled-cross')
  end
end
# The actual completed package build must use native generators for all seven namespaces.
ninja = File.read(source + '/output/build.ninja')
targets = JSON.parse(File.read(source + '/output/meson-info/intro-targets.json'))
names = %w[GLib-2.0 GLibUnix-2.0 GObject-2.0 GModule-2.0 Gio-2.0 GioUnix-2.0 GIRepository-3.0]
names.each do |name|
  %w[gir typelib].each do |ext|
    stanza = ninja.split("\n\n").find { |s| s.start_with?("build girepository/introspection/#{name}.#{ext}:") }
    abort "missing #{name}.#{ext} rule" unless stanza
    command = stanza.lines.find { |l| l.start_with?(' COMMAND = ') } or abort 'missing command'
    tool = ext == 'gir' ? scanner : native
    target = targets.find { |t| t.fetch('name') == "#{name}.#{ext}" } or abort 'missing Meson target'
    generators = target.fetch('target_sources').flat_map { |s| s.fetch('compiler', []) }
    abort 'wrong generator in actual build' unless generators.any? { |p| p.end_with?(File.basename(tool)) && File.realpath(p) == File.realpath(tool) }
    abort 'missing ELF inspection helper' if ext == 'gir' && !command.include?('--use-ldd-wrapper=')
    abort 'missing output payload' unless File.size?(source + "/output/girepository/introspection/#{name}.#{ext}")
  end
end
inputs = [__FILE__, source + '/meson.build', source + '/girepository/compiler/meson.build', source + '/output/build.ninja']
File.write(work + '/inputs.sha256', inputs.map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p}\n" }.join)
puts 'PASS: default cross refuses; explicit cross selects native tools; native behavior unchanged; all 14 real output rules verified'
