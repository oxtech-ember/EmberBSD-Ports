#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Test actual pkgsrc PLIST libtool expansion.
require 'fileutils'
require 'open3'

abort 'usage: cross-sort.rb PREPARED_PKGSRC CROSS_MAKECONF NEW_WORK' unless ARGV.length == 3
tree, config = ARGV.first(2).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
Dir.mkdir(work)
make = ENV.fetch('BMAKE', 'bmake')
FileUtils.cp(File.expand_path('../cross/mk.conf', __dir__), work + '/cross.mk.conf')
text = File.read(config)
line = /^\.include "[^"]*\/EMBERBSD-CROSS-MK\.CONF"$/
abort 'expected exactly one common cross profile include' unless text.scan(line).length == 1
text = text.sub(line, ".include \"#{work}/cross.mk.conf\"")
text += "\nWRKOBJDIR=#{work}/objects\nPACKAGES=#{work}/packages\n"
File.write(work + '/mk.conf', text)
prefix = work + '/stage/usr/pkg'
FileUtils.mkdir_p(prefix + '/lib')
# These are PLIST parser inputs, not executable ELF or target acceptance.
%w[libsortcheck.so.1.0 libsortcheck.so.1 libsortcheck.so libsortcheck.a].each do |name|
  File.write(prefix + '/lib/' + name, "PLIST fixture only\n")
end
File.write(prefix + '/lib/libsortcheck.la', <<~LA)
  # libsortcheck.la - a libtool library file
  dlname='libsortcheck.so.1'
  library_names='libsortcheck.so.1.0 libsortcheck.so.1 libsortcheck.so'
  old_library='libsortcheck.a'
  installed=yes
  libdir='/usr/pkg/lib'
LA
File.write(work + '/PLIST', "lib/libsortcheck.la\n")
File.write(work + '/extra.mk', <<~MK)
  cross-sort-locale:
  \t@printf '%s\\n' "$$LC_ALL" > #{work}/child-locale.txt
  \t@printf '%s\\n' a B A b | ${SORT} > #{work}/child-sort.txt
MK
base = [make, '-C', tree + '/devel/pkgconf', '-f', 'Makefile', '-f', work + '/extra.mk', 'MAKECONF=' + work + '/mk.conf', 'DESTDIR=' + work + '/stage', 'PLIST_SRC=' + work + '/PLIST']
run = lambda do |name, *args|
  out, err, status = Open3.capture3({'LC_ALL' => 'en_US.UTF-8'}, *base, *args)
  File.write(work + '/' + name + '.stdout', out)
  File.write(work + '/' + name + '.stderr', err)
  abort "real pkgsrc command failed: #{name}: #{err}" unless status.success?
  out
end
vars = %w[PLIST TOOLS_SORT TOOLS_PLATFORM.sort LC_ALL]
values = run.call('metadata', *vars.flat_map { |v| ['-V', '${' + v + '}'] }).lines.map(&:chomp)
abort 'unexpected query output' unless values.length == vars.length
v = vars.zip(values).to_h
run.call('plist', v.fetch('PLIST'), 'cross-sort-locale')
actual = File.readlines(v.fetch('PLIST')).map(&:chomp).reject { |p| p.start_with?('@') || p.empty? }
expected = %w[lib/libsortcheck.la lib/libsortcheck.a lib/libsortcheck.so lib/libsortcheck.so.1 lib/libsortcheck.so.1.0]
check = lambda do |name, condition|
  abort "FAIL: #{name}" unless condition
  puts "PASS: #{name}"
end
check.call('actual pkgsrc PLIST retains all libtool shared and static payloads', actual.sort == expected.sort)
check.call('TOOLS_SORT is the selected single executable', v.fetch('TOOLS_SORT') == '/usr/bin/sort' && v.fetch('TOOLS_PLATFORM.sort') == '/usr/bin/sort')
check.call('cross MAKECONF exports C collation despite the non-C caller', v.fetch('LC_ALL') == 'C' && File.read(work + '/child-locale.txt') == "C\n")
check.call('ordinary make child sort uses deterministic C byte order', File.read(work + '/child-sort.txt') == "A\nB\na\nb\n")
puts 'PASS: actual PLIST/libtool and child-locale contracts; no target build or execution'
