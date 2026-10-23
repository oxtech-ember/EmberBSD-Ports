#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Run the real Library before and after its patch.
set -eu
[ "$#" = 4 ] || {
    echo "Usage: $0 FCITX_SOURCE NATIVE_BUILD FCITX_RECIPE NEW_OUTPUT" >&2
    exit 2
}
: "${RUBY:=ruby}"
for path in "$@"; do
    case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2 ;; esac
done
source=$1 build=$2 recipe=$3 out=$4
mkdir "$out"
mkdir -p "$out/patched/src/lib/fcitx-utils"
cp "$source/src/lib/fcitx-utils/library.cpp" "$out/patched/src/lib/fcitx-utils/library.cpp"
patch -d "$out/patched" -p0 -F0 < "$recipe/patches/patch-src_lib_fcitx-utils_library.cpp" \
    > "$out/patch.log" 2>&1
"$RUBY" - "$source" "$build" "$recipe" "$out" <<'RUBY'
require 'json'
require 'shellwords'
source, build, recipe, out = ARGV
record = JSON.parse(File.read(build + '/compile_commands.json')).find do |item|
  item.fetch('file').end_with?('/src/lib/fcitx-utils/library.cpp')
end
abort 'The native build has no library.cpp compilation command' unless record
base_args = Shellwords.split(record.fetch('command'))
compiler = base_args.shift
index = base_args.index('-o')
abort 'Unexpected compilation command' unless index && base_args.include?('-c')
base_args.slice!(index, 2)
base_args.delete('-c')
base_args.delete(record.fetch('file'))
# A relocated translation unit still needs its original quoted header directory.
base_args += ['-iquote', File.dirname(record.fetch('file'))]
library = build + '/lib/libFcitx5Utils.a'
abort 'The prepared native static Utils library is missing' unless File.file?(library)
intl = File.readlines(build + '/CMakeCache.txt').map do |line|
  match = /^LibIntl_LIBRARY:[^=]+=(.*)$/.match(line)
  match && match[1]
end.compact.first
libraries = [library]
libraries << intl if intl && !intl.empty? && !intl.end_with?('-NOTFOUND')
export_flag = RUBY_PLATFORM.include?('darwin') ? '-Wl,-export_dynamic' : '-Wl,--export-dynamic'
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
  file = state == 'original' ? source + '/src/lib/fcitx-utils/library.cpp' : out + '/patched/src/lib/fcitx-utils/library.cpp'
  object = out + '/' + state + '.o'
  compile = [compiler, *base_args, '-c', file, '-o', object]
  abort "#{state} compilation failed" unless run_record(compile, out, out + '/' + state + '-compile') == 0
  commands << {'directory' => out, 'arguments' => compile, 'file' => file, 'output' => object}
  executable = out + '/' + state
  link = [compiler, *base_args, recipe + '/tests/library-find-data.cpp', object, *libraries, export_flag, '-o', executable]
  abort "#{state} link failed" unless run_record(link, out, out + '/' + state + '-link') == 0
  # Use the matching compiler/runtime when the native build is instrumented.
  # No leak checking or Valgrind pass is implied by ASan/UBSan execution.
  ENV['ASAN_OPTIONS'] = 'halt_on_error=1'
  ENV['UBSAN_OPTIONS'] = 'halt_on_error=1:print_stacktrace=1'
  result = run_record([executable, out], out, out + '/' + state + '-run')
  log = File.read(out + '/' + state + '-run.log')
  if state == 'original'
    expected = log.include?('FAIL: missing magic result=1 callback=1') ||
               log.match?(/runtime error: applying non-zero offset .* to null pointer/)
    abort 'The original source did not reproduce the expected defect' unless result != 0 && expected
  else
    abort 'The patched Library regression failed' unless result == 0 && log.include?('PASS: file magic, loaded symbol, missing magic')
  end
end
File.write(out + '/compile_commands.json', JSON.pretty_generate(commands) + "\n")
puts 'PASS: original missing-signature defect; fixed file, loaded-symbol and missing-signature cases'
puts 'Only Library and the regression were rebuilt. This is not full Fcitx or target acceptance.'
RUBY
