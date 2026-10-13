#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Test the actual XKB parser before and after its patch.
set -eu
[ "$#" = 5 ] || {
    echo "Usage: $0 FCITX_SOURCE NATIVE_BUILD FCITX_RECIPE EXPAT_PREFIX NEW_OUTPUT" >&2
    exit 2
}
: "${RUBY:=ruby}"
for path in "$@"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2 ;; esac
done
source=$1 build=$2 recipe=$3 expat=$4 out=$5
mkdir "$out"
mkdir -p "$out/patched/src/im/keyboard"
cp "$source/src/im/keyboard/xkbrules.cpp" "$out/patched/src/im/keyboard/xkbrules.cpp"
patch -d "$out/patched" -p0 -F0 < "$recipe/patches/patch-src_im_keyboard_xkbrules.cpp" \
    > "$out/patch.log" 2>&1
"$RUBY" - "$source" "$build" "$recipe" "$expat" "$out" <<'RUBY'
require 'json'
require 'shellwords'
source, build, recipe, expat, out = ARGV
record = JSON.parse(File.read(build + '/compile_commands.json')).find do |item|
  item.fetch('file').end_with?('/src/lib/fcitx-utils/stringutils.cpp')
end
abort 'The native build has no stringutils.cpp compilation command' unless record
args = Shellwords.split(record.fetch('command'))
compiler = args.shift
index = args.index('-o')
abort 'Unexpected compilation command' unless index && args.include?('-c')
args.slice!(index, 2)
args.delete('-c')
args.delete(record.fetch('file'))
args += ['-I' + source + '/src/im/keyboard', '-I' + expat + '/include']
library = build + '/lib/libFcitx5Utils.a'
expat_library = expat + '/lib/libexpat.a'
abort 'Prepared native Utils or Expat library is missing' unless [library, expat_library].all? { |p| File.file?(p) }
intl = File.readlines(build + '/CMakeCache.txt').map do |line|
  match = /^LibIntl_LIBRARY:[^=]+=(.*)$/.match(line)
  match && match[1]
end.compact.first
libraries = [library, expat_library]
libraries << intl if intl && !intl.empty? && !intl.end_with?('-NOTFOUND')
File.write(out + '/native-input-command.txt', record.fetch('command') + "\n")
commands = []
def run_record(command, directory, stem)
  File.write(stem + '.command', Shellwords.join(command) + "\n")
  system(*command, chdir: directory, out: stem + '.log', err: stem + '.log')
  state = $?
  result = state.exitstatus || 128 + state.termsig
  File.write(stem + '.status', result.to_s + "\n")
  result
end
%w[original fixed].each do |state|
  parser = state == 'original' ? source + '/src/im/keyboard/xkbrules.cpp' : out + '/patched/src/im/keyboard/xkbrules.cpp'
  sources = [parser, source + '/src/im/keyboard/xmlparser.cpp', recipe + '/tests/xkbrules.cpp']
  objects = sources.map do |file|
    object = out + '/' + state + '-' + File.basename(file) + '.o'
    # The regression and parser have the same basename; keep their objects distinct.
    object = out + '/' + state + '-test.o' if file == sources.last
    command = [compiler, *args, '-c', file, '-o', object]
    abort "#{state} compilation failed: #{file}" unless run_record(command, out, object + '-compile') == 0
    commands << {'directory' => out, 'arguments' => command, 'file' => file, 'output' => object}
    object
  end
  executable = out + '/' + state
  abort "#{state} link failed" unless run_record([compiler, *args, *objects, *libraries, '-o', executable], out, out + '/' + state + '-link') == 0
  ENV['ASAN_OPTIONS'] = 'halt_on_error=1'
  ENV['UBSAN_OPTIONS'] = 'halt_on_error=1:print_stacktrace=1'
  result = run_record([executable, out + '/' + state + '-fixtures'], out, out + '/' + state + '-run')
  log = File.read(out + '/' + state + '-run.log')
  if state == 'original'
    abort 'The original source did not reproduce missing models' unless result == 1 && log.include?('FAIL: missing models after merge')
  else
    abort 'The fixed XKB regression failed' unless result == 0 && log.include?('PASS: models, groups, options, parse order, attributes and repeat lifecycle')
  end
end
File.write(out + '/compile_commands.json', JSON.pretty_generate(commands) + "\n")
puts 'PASS: original missing models; fixed models, groups, ordering and lifecycle'
puts 'Only the XKB parser, XML parser and regression were rebuilt. No target acceptance is implied.'
RUBY
