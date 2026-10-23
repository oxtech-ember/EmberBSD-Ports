#!/usr/bin/env ruby
# SPDX-License-Identifier: MIT
require 'digest'; require 'fileutils'; require 'json'; require 'open3'; require 'shellwords'
abort "Usage: #{$PROGRAM_NAME} MESA_ARCHIVE GCC_TOOLS SYSROOT LLD_SPECS MESON NINJA NEW_OUTPUT" unless ARGV.size == 7
archive, tools, sysroot, specs, meson, ninja, work = ARGV.map { |p| File.expand_path(p) }
abort 'Output exists' if File.exist?(work)
recipe = File.expand_path('../../../../pkgsrc/graphics/MesaLib', __dir__)
distinfo = File.read(recipe + '/distinfo')
expected = distinfo[/^SHA512 \(mesa-26\.2\.4\.tar\.xz\) = (\h+)$/, 1]
abort 'Source archive mismatch' unless expected && Digest::SHA512.file(archive).hexdigest == expected
FileUtils.mkdir_p(work)
def run(command, log, **options)
 out, err, status = Open3.capture3(*command, **options)
 File.write(log, command.shelljoin + "\n" + out + err + "\nexit=#{status.exitstatus}\n")
 abort "Command failed: #{log}" unless status.success?
 out
end
paths = %w[src/gallium/targets/dri/meson.build src/gallium/targets/dri/dri.sym.in]
paths.each do |path|
 bytes = run(['tar', '-xOf', archive, 'mesa-26.2.4/' + path], work + '/extract-' + File.basename(path) + '.log')
 %w[baseline fixed].each do |variant|
  target = work + '/' + variant + '/' + path
  FileUtils.mkdir_p(File.dirname(target)); File.write(target, bytes)
 end
 name = 'patch-' + path.gsub('_', '__').tr('/', '_')
 patch = recipe + '/patches/' + name
 expected = distinfo[/^SHA1 \(#{Regexp.escape(name)}\) = (\h+)$/, 1]
 canonical = File.readlines(patch).reject { |line| line.match?(/\$NetBSD.*/) }.join
 abort 'Patch checksum mismatch' unless expected && Digest::SHA1.hexdigest(canonical) == expected
 run(['patch', '-p0', '-i', patch], work + '/patch-' + File.basename(path) + '.log', chdir: work + '/fixed')
end
cc = tools + '/bin/aarch64--netbsd-gcc'; readelf = tools + '/bin/aarch64--netbsd-readelf'
ldflags = ['-specs=' + specs, '-fno-use-linker-plugin', '-Wl,-m,aarch64elf']
receipt = { source_sha512: Digest::SHA512.file(archive).hexdigest, variants: {} }
%w[baseline fixed].product(%w[gnu lld]).each do |variant, linker|
 dir = work + '/' + variant + '-' + linker; FileUtils.mkdir_p(dir)
 script = File.read(work + '/' + variant + '/' + paths[0]).split('libgallium_dri = shared_library(', 2).first
 abort 'Missing actual Meson prefix' unless script.include?('dri_sym = configure_file(')
 map = File.read(work + '/' + variant + '/' + paths[1])
 settings = map.scan(/@([A-Za-z_][A-Za-z_0-9]*)@/).flatten.uniq.map { |key| "sym_config.set('#{key}', '')" }.join("\n")
 File.write(dir + '/dri.sym.in', map)
 symbols = map.lines.filter_map { |line| line[/^\s*([A-Za-z_][A-Za-z_0-9]*);\s*$/, 1] }
 tls = %w[_mesa_glapi_tls_Context _mesa_glapi_tls_Dispatch]
 stub = symbols.map { |name| tls.include?(name) ? "_Thread_local void *#{name};" : "int #{name}(void) { return 42; }" }.join("\n") + "\n"
 File.write(dir + '/stub.c', stub)
 File.write(dir + '/meson_options.txt', "option('unversion-libgallium', type: 'boolean', value: false)\n")
 File.write(dir + '/meson.build', "project('mesa-version-contract', 'c', version: '26.2.4')\ncc = meson.get_compiler('c')\nsym_config = configuration_data()\n#{settings}\nwith_gallium_va = false\nwith_platform_android = false\nwith_glx_read_only_text = true\nwith_ld_version_script = true\nwith_ld_dynamic_list = false\n#{script}\nshared_library(libgallium_name, 'stub.c', link_args: gallium_dri_ld_args, link_depends: gallium_dri_link_depends)\n")
 compiler = [cc, '--sysroot=' + sysroot] + (linker == 'lld' ? ldflags : [])
 quote = ->(value) { "'" + value.gsub('\\', '\\\\').gsub("'", "\\'") + "'" }
 File.write(dir + '/cross.ini', "[binaries]\nc = [#{compiler.map(&quote).join(', ')}]\nar = #{quote.call(tools + '/bin/aarch64--netbsd-ar')}\nstrip = #{quote.call(tools + '/bin/aarch64--netbsd-strip')}\n[host_machine]\nsystem = 'netbsd'\ncpu_family = 'aarch64'\ncpu = 'aarch64'\nendian = 'little'\n[properties]\nneeds_exe_wrapper = true\n")
 run([meson, 'setup', dir + '/build', dir, '--cross-file', dir + '/cross.ini'], dir + '/configure.log')
 run([ninja, '-C', dir + '/build'], dir + '/build.log')
 library = dir + '/build/libgallium-26.2.4.so'
 versions = run([readelf, '--version-info', '--wide', library], dir + '/versions.log')
 exports = run([readelf, '--dyn-syms', '--wide', library], dir + '/exports.log')
 node = versions.include?('Name: libgallium-26.2.4.so')
 versioned = symbols.all? { |name| exports.include?(name + '@@libgallium-26.2.4.so') }
 expected_node = variant == 'fixed' || linker == 'gnu'
 abort "Wrong causal result #{variant}/#{linker}" unless node == expected_node && versioned == expected_node
 receipt[:variants][variant + '-' + linker] = { default_version_node: node, all_exports_versioned: versioned, library_sha256: Digest::SHA256.file(library).hexdigest }
end
# Link a consumer to the old GNU provider. Its version requirement must match
# the fixed LLD provider, not merely an unversioned symbol with the same name.
consumer = work + '/consumer.c'
File.write(consumer, "extern int _mesa_glapi_get_dispatch_table_size(void);\nint main(void) { return _mesa_glapi_get_dispatch_table_size() == 42 ? 0 : 1; }\n")
elf = work + '/old-consumer'
run([cc, '--sysroot=' + sysroot, *ldflags, consumer, work + '/baseline-gnu/build/libgallium-26.2.4.so', '-Wl,-rpath,/usr/pkg/lib', '-Wl,--dynamic-linker,/libexec/ld.elf_so', '-o', elf], work + '/consumer-build.log')
need = run([readelf, '--version-info', '--wide', elf], work + '/consumer-versions.log')
imports = run([readelf, '--dyn-syms', '--wide', elf], work + '/consumer-imports.log')
abort 'Old consumer lacks explicit version requirement' unless need.include?('File: libgallium-26.2.4.so') && need.include?('Name: libgallium-26.2.4.so') && imports.include?('_mesa_glapi_get_dispatch_table_size@libgallium-26.2.4.so')
receipt[:consumer] = { sha256: Digest::SHA256.file(elf).hexdigest, old_gnu_verneed: 'libgallium-26.2.4.so', fixed_lld_verdef_matches: true, target_execution: 'NOT RUN' }
receipt[:scope] = 'Actual Mesa Meson prefix and symbol map; cross ELF ABI contract. No physical runtime claim.'
File.write(work + '/results.json', JSON.pretty_generate(receipt) + "\n")
puts 'PASS: GNU default ABI retained under GNU and LLD; old consumer has matching VERNEED'
