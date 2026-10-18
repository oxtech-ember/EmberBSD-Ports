#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Real pkgsrc tool routing and upstream lexer.
require 'digest'
require 'fileutils'
require 'find'
require 'json'
require 'open3'
require 'shellwords'

abort 'Usage: gi-native-flex.rb PKGSRC MAKECONF NEW_WORK' unless ARGV.size == 3
source, config = ARGV.first(2).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'New absolute output required' unless ARGV.last.start_with?('/') && !File.exist?(work) && !File.symlink?(work)
profile = File.expand_path('..', __dir__)
recipe = profile + '/recipes/devel/gobject-introspection'
bmake = ENV.fetch('BMAKE', 'bmake')
Dir.mkdir(work)
commands = []
run = lambda do |label, argv, env = {}|
  out, err, status = Open3.capture3(env, *argv)
  File.write(work + '/' + label + '.stdout', out)
  File.write(work + '/' + label + '.stderr', err)
  commands << {name: label, argv: argv, status: status.exitstatus}
  File.write(work + '/commands.json', JSON.pretty_generate(commands) + "\n")
  abort label + ' failed: ' + err unless status.success?
  out
end
views = {}
%w[before after].each do |variant|
  tree = work + '/' + variant + '/pkgsrc'
  FileUtils.mkdir_p(tree + '/devel')
  Dir.children(source).reject { |n| n.start_with?('.') || n == 'devel' }.each { |n| File.symlink(source + '/' + n, tree + '/' + n) }
  Dir.children(source + '/devel').reject { |n| n == 'gobject-introspection' }.each { |n| File.symlink(source + '/devel/' + n, tree + '/devel/' + n) }
  run.call(variant + '-copy', ['cp', '-RL', recipe, tree + '/devel/gobject-introspection'])
  views[variant] = tree + '/devel/gobject-introspection'
end
first = <<~'MAKE'
  # The lexer supplies yywrap itself; Flex is a native generator, not target libfl.
  TOOL_DEPENDS+=	flex>=2.5.4a:../../devel/flex
  TOOLS_PLATFORM.flex=	${TOOLBASE}/bin/flex
MAKE
# These are literal Makefile tabs, not an escaped diagnostic representation.
first = first.gsub('\\t', "\t")
last = <<~'MAKE'

  .if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${_TOOLS_USE_PKGSRC.flex:Uyes:tl} != "no"
  PKG_FAIL_REASON+= "GI cross builds require installed native Flex satisfying FLEX_REQD=${FLEX_REQD} at ${TOOLBASE}/bin/flex"
  .endif
MAKE
makefile = views.fetch('before') + '/Makefile'
body = File.read(makefile)
abort 'Unexpected source repair' unless body.scan(first).size == 1 && body.end_with?(last)
File.write(makefile, body.sub(first, '').delete_suffix(last))
fields = %w[PKGNAME PKG_FAIL_REASON BUILD_DEPENDS DEPENDS TOOL_DEPENDS TOOLS_PATH.flex _TOOLS_USE_PKGSRC.flex _TOOLS_VERSION.flex FLEX_REQD TOOLBASE CROSS_DESTDIR TOOLDIR MACHINE_GNU_PLATFORM WRKDIR TOOLS_DIR PKG_CC CWRAPPERS_CONFIG_DIR WRAPPER_BINDIR]
args = lambda do |variant|
  [bmake, '-C', views.fetch(variant), 'MAKECONF=' + config,
   'WRKOBJDIR=' + work + '/' + variant + '/objects', 'PACKAGES=' + work + '/packages', 'MAKE_JOBS=1']
end
query = lambda do |label, variant, extra|
  lines = run.call(label, args.call(variant) + extra + fields.flat_map { |f| ['-V', '${' + f + '}'] }).lines.map(&:strip)
  abort 'Unexpected metadata output' unless lines.size == fields.size
  fields.zip(lines).to_h
end
before = query.call('before-cross', 'before', [])
after = query.call('after-cross', 'after', [])
abort 'Missing real baseline target Flex dependency' unless before.fetch('BUILD_DEPENDS').split.any? { |p| p.start_with?('flex>=') }
abort 'Target Flex remains' if %w[BUILD_DEPENDS DEPENDS].any? { |k| after.fetch(k).split.any? { |p| p.start_with?('flex>=') } }
abort 'Native dependency missing' unless after.fetch('TOOL_DEPENDS').split.include?('flex>=2.5.4a:../../devel/flex')
abort 'Native Flex version routing failed' unless after.fetch('PKG_FAIL_REASON').empty? && after.fetch('_TOOLS_USE_PKGSRC.flex') == 'no' && after.fetch('TOOLS_PATH.flex') == after.fetch('TOOLBASE') + '/bin/flex'
%w[PKGNAME DEPENDS].each { |k| abort 'Unrelated metadata changed' unless before.fetch(k) == after.fetch(k) }
native_before = query.call('before-native', 'before', ['USE_CROSS_COMPILE=no'])
native_after = query.call('after-native', 'after', ['USE_CROSS_COMPILE=no'])
%w[PKGNAME PKG_FAIL_REASON BUILD_DEPENDS DEPENDS TOOL_DEPENDS TOOLS_PATH.flex _TOOLS_USE_PKGSRC.flex _TOOLS_VERSION.flex].each { |k| abort 'Native metadata changed: ' + k unless native_before.fetch(k) == native_after.fetch(k) }
{'missing-tool' => ['TOOLS_PLATFORM.flex=' + work + '/absent-flex'], 'wrong-tool' => ['TOOLS_PLATFORM.flex=/usr/bin/false'], 'higher-version' => ['FLEX_REQD=999']}.each do |label, flags|
  bad = query.call(label, 'after', flags)
  abort 'Invalid native Flex accepted: ' + label unless bad.fetch('PKG_FAIL_REASON').include?('GI cross builds require installed native Flex')
end
%w[WRKDIR TOOLS_DIR PKG_CC CWRAPPERS_CONFIG_DIR WRAPPER_BINDIR].each do |key|
  raw = after.fetch(key)
  p = File.expand_path(raw)
  abort 'Writable path must be absolute and normalized: ' + key unless raw.start_with?('/') && raw == p
  abort 'Writable path escaped private work: ' + key unless p.start_with?(work + '/after/objects/')
  parent = p
  until parent == work
    abort 'Writable path has symlink ancestor' if File.symlink?(parent)
    parent = File.dirname(parent)
  end
end
info = after.fetch('TOOLBASE') + '/sbin/pkg_info'
admin = after.fetch('TOOLBASE') + '/sbin/pkg_admin'
dependencies = []
%w[TOOL_DEPENDS BUILD_DEPENDS DEPENDS].each do |kind|
  db = kind == 'TOOL_DEPENDS' ? after.fetch('TOOLBASE') + '/pkgdb' : after.fetch('CROSS_DESTDIR') + '/usr/pkg/pkgdb'
  after.fetch(kind).split.uniq.each_with_index do |entry, i|
    pattern = entry.split(':', 2).first
    output = run.call("dependency-#{kind}-#{i}", [info, '-K', db, '-e', pattern])
    names = output.lines.map(&:strip)
    abort 'Empty dependency query: ' + pattern if names.empty?
    contents = names.each_with_index.to_h do |name, j|
      abort 'Unexpected package identity' unless name.match?(/\A[A-Za-z0-9_.+-]+\z/)
      run.call("dependency-match-#{kind}-#{i}-#{j}", [admin, 'pmatch', pattern, name])
      path = db + '/' + name + '/+CONTENTS'
      abort 'Missing real dependency registration: ' + name unless File.file?(path) && File.readlines(path).grep(/^@name /) == ["@name #{name}\n"]
      [name, Digest::SHA256.file(path).hexdigest]
    end
    dependencies << {kind: kind, pattern: pattern, db: db, installed: names, contents_sha256: contents}
  end
end
# All dependencies already exist: these ordinary phases may write only the
# new work tree; they must not bootstrap/install a missing dependency.
run.call('ordinary-patch', args.call('after') + ['patch'])
run.call('ordinary-wrapper', args.call('after') + ['wrapper'])
wrksrc = run.call('wrksrc', args.call('after') + ['-V', '${WRKSRC}']).strip
abort 'Source escaped private work' unless File.realpath(wrksrc).start_with?(work + '/after/objects/')
lexer = wrksrc + '/giscanner/scannerlexer.l'
text = File.read(lexer)
abort 'Upstream yywrap ownership changed' unless text.match?(/static int\s+yywrap \(void\)\s*\{\s*return 1;\s*\}/)
gen = work + '/generated'; Dir.mkdir(gen)
tool = after.fetch('TOOLS_DIR') + '/bin/flex'
run.call('wrapped-flex-version', [tool, '--version'])
run.call('wrapped-bison', [after.fetch('TOOLS_DIR') + '/bin/bison', wrksrc + '/giscanner/scannerparser.y', '--defines=' + gen + '/scannerparser.h', '--output=' + gen + '/scannerparser.c'])
run.call('wrapped-flex', [tool, '-o', gen + '/scannerlexer.c', lexer])
sdk = after.fetch('CROSS_DESTDIR')
compiler = Shellwords.split(after.fetch('PKG_CC'))
target_env = %w[LIBRARY_PATH CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH].to_h { |k| [k, nil] }
run.call('real-target-lexer', compiler + ['-fPIC', '-I' + gen, '-I' + wrksrc + '/giscanner', '-I' + sdk + '/usr/pkg/include/glib-2.0', '-I' + sdk + '/usr/pkg/lib/glib-2.0/include', '-c', gen + '/scannerlexer.c', '-o', gen + '/scannerlexer.o'], target_env)
object = File.binread(gen + '/scannerlexer.o', 20)
machine = {'aarch64--netbsd' => 183, 'x86_64--netbsd' => 62}[after.fetch('MACHINE_GNU_PLATFORM')]
abort 'Wrong generated object ABI' unless machine && object.start_with?("\x7fELF".b) && object.getbyte(4) == 2 && object.getbyte(5) == 1 && object.byteslice(18, 2).unpack1('v') == machine
undefined = run.call('target-undefined', [after.fetch('TOOLDIR') + '/bin/' + after.fetch('MACHINE_GNU_PLATFORM') + '-nm', '-u', gen + '/scannerlexer.o'])
abort 'Generated lexer still needs external yywrap' if undefined.match?(/\byywrap\b/)
inputs = [recipe + '/Makefile', source + '/mk/tools/flex.mk', source + '/mk/tools/replace.mk', source + '/devel/flex/buildlink3.mk', lexer, wrksrc + '/giscanner/meson.build', tool, after.fetch('TOOLS_PATH.flex'), gen + '/scannerlexer.c', gen + '/scannerlexer.o']
File.write(work + '/result.json', JSON.pretty_generate(scope: 'Actual baseline/fixed/native pkgsrc metadata, three invalid-provider refusals, normal private patch/wrapper phases, genuine native Flex/Bison generation and target lexer object with internal yywrap. No package, DB install or VM execution.', before: before, after: after, dependencies: dependencies, input_sha256: inputs.to_h { |p| [p, Digest::SHA256.file(p).hexdigest] }, status: 'PASS') + "\n")
puts 'PASS: native Flex routing, unchanged native metadata, genuine target lexer and ordinary private patch/wrapper phases.'
