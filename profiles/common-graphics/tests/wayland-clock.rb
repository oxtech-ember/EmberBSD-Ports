#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted). Extract actual WSI source.
require 'fileutils'
require 'open3'
require 'shellwords'
abort 'Usage: wayland-clock.rb MESA_SOURCE NEW_WORK' unless ARGV.size == 2
source = File.realpath(ARGV[0])
work = File.expand_path(ARGV[1])
abort 'Use a new absolute work directory' unless ARGV[1].start_with?('/') && !File.exist?(work)
FileUtils.mkdir_p(work)
text = File.read(source + '/src/vulkan/wsi/wsi_common_wayland.c')
functions = %w[clock_id_to_vk_time_domain vk_time_domain_to_clock_id].map do |name|
    match = text.match(/static [^\n]+\n#{name}\([^\n]+\)\n\{.*?\n\}/m)
    abort "Missing WSI function: #{name}" unless match
    match[0]
end
# Keep the actual admission expression. Its enclosing case exits on rejection.
admission = text.match(/if \(clock_id != CLOCK_MONOTONIC.*?\)\n\s+break;/m)
abort 'Missing presentation clock admission' unless admission
functions << "static bool\npresentation_clock_supported(clockid_t clock_id)\n{\n" +
    admission[0].sub('break;', 'return false;') + "\nreturn true;\n}\n"
File.write(work + '/wayland-clock-source.h', functions.join("\n\n") + "\n")
flags = %w[-std=c11 -D_POSIX_C_SOURCE=200809L -O1 -g -Wall -Wextra -Werror]
flags += %w[-fsanitize=address,undefined -fno-omit-frame-pointer] if ENV['SANITIZERS'] == 'yes'
cc = Shellwords.split(ENV.fetch('CC', 'cc'))
fixture = File.dirname(File.realpath(__FILE__)) + '/wayland-clock.c'
[[], ['-DTEST_RAW_CLOCK']].each_with_index do |extra, index|
    argv = [*cc, *flags, *extra, '-I' + source + '/include', '-I' + work, fixture, '-o', work + "/check-#{index}"]
    out, status = Open3.capture2e(*argv)
    File.write(work + "/compile-#{index}.log", out)
    abort "Clock profile #{index} cannot compile: #{out}" unless status.success?
    out, status = Open3.capture2e(work + "/check-#{index}")
    File.write(work + "/run-#{index}.log", out)
    abort out unless status.success?
    puts out
end
