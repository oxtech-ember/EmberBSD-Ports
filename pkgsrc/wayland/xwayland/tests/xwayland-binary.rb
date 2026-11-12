#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check that Xwayland names only target paths.
abort 'Usage: xwayland-binary.rb XWAYLAND [PREFIX]' unless [1, 2].include?(ARGV.size)
path = File.expand_path(ARGV[0])
prefix = ARGV[1] || '/usr/pkg'
data = File.binread(path)
abort "Not an ELF file: #{path}" unless data.start_with?("\x7fELF".b)
strings = data.scan(/[\x20-\x7e]{4,}/n).map { |s| s.force_encoding('BINARY') }
failures = []

# No build machine or sysroot path may reach the binary.
forbidden = %r{/Volumes/|/Users/|/home/|sysroot|stages/|work\.NetBSD|pkgsrc-objects|\.buildlink|\.cwrapper}
strings.grep(forbidden).each { |s| failures << "build machine path: #{s[0, 120]}" }

# DRI_DRIVER_PATH is a C string literal. Every driver directory the binary can
# search must be the target one; a sysroot prefix is the defect being tested.
dri = strings.select { |s| s.end_with?('/lib/dri') || s.end_with?('/lib/dri/') }.uniq
failures << 'DRI_DRIVER_PATH is missing' unless dri.include?("#{prefix}/lib/dri")
dri.each { |s| failures << "unexpected DRI path: #{s}" unless s == "#{prefix}/lib/dri" }
raise 'The DRI path must be a separate NUL-terminated literal' unless data.include?("\0#{prefix}/lib/dri\0".b) || failures.any?

# The other installed-location paths of this recipe.
["#{prefix}/share/X11/xkb", "#{prefix}/bin"].each do |expected|
  failures << "missing target path #{expected}" unless data.include?(expected.b)
end

if failures.empty?
  puts "PASS: #{path} names only #{prefix} paths (DRI_DRIVER_PATH=#{prefix}/lib/dri)"
else
  failures.each { |f| warn "FAIL: #{f}" }
  exit 1
end
