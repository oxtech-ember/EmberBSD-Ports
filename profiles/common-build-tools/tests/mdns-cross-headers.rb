#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise the actual pkgsrc metadata parser.
require 'fileutils'
require 'open3'
abort 'Usage: mdns-cross-headers.rb NEW_WORK' unless ARGV.length == 1
root = File.expand_path('../../..', __dir__)
work = File.expand_path(ARGV.fetch(0))
abort 'Output already exists' if File.exist?(work)
FileUtils.mkdir_p(work)
source = File.read("#{root}/upstream/pkgsrc/net/mDNSResponder/builtin.mk")
patch = File.read("#{root}/profiles/common-build-tools/patches/pkgsrc-cross-packages.patch")
hunk = patch[/^--- a\/net\/mDNSResponder\/builtin\.mk\n.*?(?=^--- a\/|\z)/m]
abort 'Missing mDNSResponder patch' unless hunk
FileUtils.mkdir_p("#{work}/patched/net/mDNSResponder")
File.write("#{work}/patched/net/mDNSResponder/builtin.mk", source)
log, result = Open3.capture2e('patch', '-f', '-N', '-F', '0', '-p1', '-d', "#{work}/patched", stdin_data: hunk)
File.write("#{work}/patch.log", log)
abort 'Patch failed' unless result.success?
header = "#{work}/native/dns_sd.h"
sysroot = "#{work}/sysroot"
FileUtils.mkdir_p([File.dirname(header), File.dirname(sysroot + header)])
File.write(header, "#define _DNS_SD_H 2120100\n")
File.write(sysroot + header, "#define _DNS_SD_H 16610000\n")
[ ['before', source], ['after', File.read("#{work}/patched/net/mDNSResponder/builtin.mk")] ].each do |name, text|
  # find-files.mk has already selected a logical header name. Preserve the
  # complete production version parser and override only that discovery input.
  text = text.lines.reject { |l| l.match?(/^\s*\.include /) }.join
  File.write("#{work}/#{name}.mk", text)
end
make = ENV.fetch('BMAKE', 'bmake')
[ ['before', 'yes', '212.1'], ['after', 'yes', '2559.1.1'], ['after', 'no', '212.1'] ].each do |name, cross, expected|
  output, result = Open3.capture2e(make, '-r', '-m', '/', '-f', "#{work}/#{name}.mk",
    "SED=/usr/bin/sed", "H_DNSSD=#{header}", "CROSS_DESTDIR=#{sysroot}",
    "USE_CROSS_COMPILE=#{cross}", 'USE_BUILTIN.mDNSResponder=yes', '-v', 'BUILTIN_VERSION.mDNSResponder')
  File.write("#{work}/#{name}-#{cross}.log", output)
  abort "Incorrect #{name}/#{cross}: #{output}" unless result.success? && output.strip == expected
end
puts 'PASS: old parser reads the host header; cross fix reads the sysroot; native recursion stays native'
