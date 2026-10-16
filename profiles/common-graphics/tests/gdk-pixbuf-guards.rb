#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Negative controls use the real helper and upstream generator.
require 'fileutils'
require 'json'
require 'open3'
abort 'Usage: gdk-pixbuf-guards.rb BUILT_SOURCE HOST_PYTHON SYSROOT READELF NEW_WORK' unless ARGV.size == 5
arch = ENV.fetch('EMBERBSD_CROSS_ARCH', 'aarch64')
abort 'unsupported target architecture' unless %w[aarch64 x86_64].include?(arch)
source, python, sysroot, readelf = ARGV.first(4).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'new absolute work required' unless ARGV.last.start_with?('/') && !File.exist?(work)
FileUtils.mkdir_p([work + '/build', work + '/cache', work + '/bin'])
helper = File.expand_path('../recipes/graphics/gdk-pixbuf2/files/target-tools.rb', __dir__)
config = {'target' => (arch == 'x86_64' ? 'amd64' : 'aarch64'), 'build_root' => work + '/build', 'cache' => work + '/cache', 'sysroot' => sysroot,
          'readelf' => readelf, 'ssh' => 'unused.invalid', 'library_dirs' => [sysroot + '/usr/pkg/gcc16/lib']}
File.write(work + '/query.json', JSON.pretty_generate(config))
# Any transport during a local refusal is a regression.
File.write(work + '/bin/ssh', "#!/bin/sh\necho unexpected-transport >&2\nexit 97\n")
File.chmod(0755, work + '/bin/ssh')
query = work + '/build/gdk-pixbuf-query-loaders'
printer = work + '/build/gdk-pixbuf-print-mime-types'
mod = work + '/build/libpixbufloader-bmp.so'
FileUtils.cp(source + '/output/gdk-pixbuf/gdk-pixbuf-query-loaders', query)
FileUtils.cp(source + '/output/thumbnailer/gdk-pixbuf-print-mime-types', printer)
FileUtils.cp(source + '/output/gdk-pixbuf/libpixbufloader-bmp.so', mod)
env = {'EMBERBSD_GI_QUERY_CONFIG' => work + '/query.json', 'PATH' => work + '/bin:/usr/bin:/bin', 'LD_LIBRARY_PATH' => nil}
cases = [
  ['unknown-mode', ['--other', query], 'usage:'],
  ['no-modules', ['--loaders', query], 'missing target modules'],
  ['duplicate-modules', ['--loaders', query, mod, mod], 'duplicate target modules'],
  ['outside-binary', ['--loaders', '/usr/bin/true', mod], 'binary outside build root'],
  ['outside-module', ['--loaders', query, '/usr/bin/true'], 'invalid target module'],
  ['wrong-tool', ['--loaders', printer, mod], 'unexpected target tool']
]
cases.each do |name, args, reason|
  out, status = Open3.capture2e(env, RbConfig.ruby, helper, *args)
  File.write(work + '/' + name + '.log', out)
  abort "#{name} not refused" if status.success? || !out.include?(reason) || out.include?('unexpected-transport')
end
FileUtils.cp('/usr/bin/true', mod)
out, status = Open3.capture2e(env, RbConfig.ruby, helper, '--loaders', query, mod)
File.write(work + '/wrong-architecture.log', out)
abort 'host module accepted' if status.success? || !out.include?("not little-endian #{arch} ELF64") || out.include?('unexpected-transport')
# The original upstream script accepted nonzero exit when a printer emitted data.
File.write(work + '/printer', "#!/bin/sh\nprintf 'image/png;'\nexit 7\n")
File.chmod(0755, work + '/printer')
File.write(work + '/input', "Exec=@bindir@/gdk-pixbuf-thumbnailer\nMimeType=@mimetypes@\n")
args = [python, source + '/build-aux/gen-thumbnailer.py', '--printer', work + '/printer',
        '--pixdata', query, '--loaders', work + '/unused-cache', '--bindir', '/usr/pkg/bin', work + '/input', work + '/output']
out, status = Open3.capture2e(*args)
File.write(work + '/printer-failure.log', out)
abort 'printer exit status was lost' unless status.exitstatus == 7 && !File.exist?(work + '/output')
File.write(work + '/printer', "#!/bin/sh\nprintf 'image/png;'\n")
out, status = Open3.capture2e(*args)
File.write(work + '/printer-success.log', out)
abort 'ordinary printer failed' unless status.success? && File.read(work + '/output') == "Exec=/usr/pkg/bin/gdk-pixbuf-thumbnailer\nMimeType=image/png;\n"
puts 'PASS: seven target-tool refusals before SSH; thumbnail printer error preserved and ordinary success unchanged'
