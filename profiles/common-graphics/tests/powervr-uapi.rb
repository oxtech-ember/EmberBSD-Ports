#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted). Target ABI data, not Linux execution.
require 'fileutils'
require 'open3'
require 'json'
require 'shellwords'
abort 'Usage: powervr-uapi.rb UPSTREAM_MESA PATCHED_MESA CROSS_CC SYSROOT NEW_WORK' unless ARGV.size == 5
upstream, patched, cc, sysroot = ARGV.first(4).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'Use a new absolute work directory' unless ARGV.last.start_with?('/') && !File.exist?(work)
FileUtils.mkdir_p(work)
old = File.read(upstream + '/include/drm-uapi/pvr_drm.h')
current = File.read(patched + '/include/drm-uapi/pvr_drm.h')
expected = old.sub("#include <linux/const.h>\n#include <linux/types.h>\n\n", '').gsub(/_BITULL\((\d+)\)/, '(1ULL << \1)')
abort 'Unexpected UAPI change' unless current == expected && current != old
# This is an explicit constant-expression model. It does not replace the failed
# unmodified EmberBSD compile or claim a Linux target compile.
model = old.sub("#include <linux/const.h>\n#include <linux/types.h>", '#define _BITULL(nr) (1ULL << (nr))')
{'original' => old, 'model' => model, 'patched' => current}.each do |name, text|
    FileUtils.mkdir(work + '/' + name)
    File.write(work + '/' + name + '/pvr_drm.h', text)
end
clean = old.gsub(%r{/\*.*?\*/}m, '')
expressions = []
clean.scan(/^struct (drm_pvr_\w+) \{(.*?)^\};/m).each do |type, body|
    expressions += ["sizeof(struct #{type})", "_Alignof(struct #{type})"]
    body.split(';').each do |statement|
        statement = statement.strip
        next if statement.empty?
        member = statement.match(/\A(?:__u(?:8|16|32|64)|__s(?:8|16|32|64)|struct drm_pvr_\w+)\s+(\w+)(?:\[\d+\])?\z/)
        abort "Unparsed UAPI field: #{statement}" unless member
        expressions << "offsetof(struct #{type}, #{member[1]})"
    end
end
old.scan(/^#define (DRM_PVR_\w+) _BITULL\((\d+)\)$/).each do |name, _bit|
    expressions += [name, "sizeof(#{name})"]
end
expressions += old.scan(/^#define (DRM_IOCTL_PVR_\w+) /).flatten
abort 'Incomplete UAPI description' unless expressions.size > 200
source = "#include <stddef.h>\n#include \"pvr_drm.h\"\n" +
    "const unsigned long long pvr_abi[] __attribute__((section(\".pvr_abi\"), used)) = {\n" +
    expressions.map { |e| "    #{e}," }.join("\n") + "\n};\n"
File.write(work + '/abi.c', source)
File.write(work + '/expressions.json', JSON.pretty_generate(expressions) + "\n")
objcopy = ENV.fetch('OBJCOPY', cc.sub(/gcc\z/, 'objcopy'))
commands = []
%w[original model patched].each do |name|
    argv = [cc, '--sysroot=' + sysroot, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
            '-I' + work + '/' + name, '-I' + patched + '/include/drm-uapi',
            '-c', work + '/abi.c', '-o', work + '/' + name + '.o']
    out, status = Open3.capture2e(*argv)
    File.write(work + '/' + name + '.log', out)
    commands << {argv: argv, status: status.exitstatus}
    File.write(work + '/commands.json', JSON.pretty_generate(commands) + "\n")
    if name == 'original'
        abort 'Unmodified BSD baseline did not fail on Linux headers' unless !status.success? && out.include?('linux/const.h')
        next
    end
    abort out unless status.success?
    argv = [objcopy, '-O', 'binary', '-j', '.pvr_abi', work + '/' + name + '.o', work + '/' + name + '.bin']
    out, status = Open3.capture2e(*argv)
    commands << {argv: argv, status: status.exitstatus}
    File.write(work + '/commands.json', JSON.pretty_generate(commands) + "\n")
    abort out unless status.success?
end
before = File.binread(work + '/model.bin')
after = File.binread(work + '/patched.bin')
abort 'Target ABI differs or is empty' unless before == after && after.bytesize == expressions.size * 8
puts "PASS: #{expressions.size} target UAPI sizes, alignments, offsets, flag values/widths and ioctl encodings"
puts 'PASS: original EmberBSD header fails; portable header matches the explicit constant-expression model'
