#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual pkgsrc native Autoconf selection.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'pathname'

abort 'Usage: host-autoconf.rb PKGSRC NATIVE_MAKECONF CROSS_MAKECONF HOST_AUTOCONF NEW_WORK' unless ARGV.length == 5
pkgsrc, native, cross, autoconf = ARGV.take(4).map { |p| File.realpath(p) }
work = File.expand_path(ARGV[4])
abort 'Use absolute portable paths.' unless [pkgsrc, native, cross, autoconf, work].all? { |p| p.match?(%r{\A/[A-Za-z0-9_./-]+\z}) }
abort 'Output already exists.' if File.exist?(work) || File.symlink?(work)
FileUtils.mkdir(work)
tools = %w[autoconf autoheader autom4te autoreconf autoscan autoupdate ifnames]
patch = File.expand_path('../patches/pkgsrc-host-autoconf.patch', __dir__)
bmake = ENV.fetch('BMAKE', 'bmake')
commands = []
run = lambda do |name, argv, cwd = nil|
  out, err, status = Open3.capture3({ 'LC_ALL' => 'C' }, *argv, **(cwd ? { chdir: cwd } : {}))
  File.write("#{work}/#{name}.out", out)
  File.write("#{work}/#{name}.err", err)
  commands << { name: name, argv: argv, cwd: cwd, status: status.exitstatus }
  File.write("#{work}/commands.json", JSON.pretty_generate(commands) + "\n")
  abort "Command failed: #{name}" unless status.success?
  out
end
%w[old new].each do |variant|
  tree = "#{work}/#{variant}"
  FileUtils.mkdir_p("#{tree}/devel")
  Dir.children(pkgsrc).each do |name|
    next if %w[mk devel].include?(name)
    File.symlink("#{pkgsrc}/#{name}", "#{tree}/#{name}")
  end
  FileUtils.cp_r("#{pkgsrc}/mk", tree)
  Dir.children("#{pkgsrc}/devel").each do |name|
    if name == 'm4'
      FileUtils.cp_r("#{pkgsrc}/devel/m4", "#{tree}/devel")
      recipe = "#{tree}/devel/m4/Makefile"
      File.write(recipe, "USE_TOOLS+= ${EMBER_TEST_TOOLS}\n" + File.read(recipe))
    else
      File.symlink("#{pkgsrc}/devel/#{name}", "#{tree}/devel/#{name}")
    end
  end
  run.call('patch', ['patch', '-f', '-N', '-F', '0', '-p1', '-d', tree, '-i', patch]) if variant == 'new'
end
configs = { 'native' => native, 'cross' => cross }.to_h do |mode, input|
  path = "#{work}/#{mode}.mk.conf"
  File.write(path, ".include \"#{input}\"\n.undef EMBERBSD_BUILD_AUTOCONF\n.undef TOOLS_DEPENDS.autoconf\n" +
    tools.map { |tool| ".undef TOOLS_PATH.#{tool}\n.undef TOOLS_PLATFORM.#{tool}\n" }.join)
  [mode, path]
end
variables = %w[PKG_FAIL_REASON TOOL_DEPENDS DEPENDS TEST_DEPENDS] + tools.map { |t| "TOOLS_PATH.#{t}" }
results = {}
metadata = lambda do |name, variant, mode, use, opts|
  argv = [bmake, '-C', "#{work}/#{variant}/devel/m4", "MAKECONF=#{configs.fetch(mode)}",
          "WRKDIR=#{work}/objects-#{mode}", "WRKOBJDIR=#{work}/objects-#{mode}",
          "PACKAGES=#{work}/packages", "EMBER_TEST_TOOLS=#{use}"] + opts
  output = run.call(name, argv + variables.flat_map { |v| ['-v', v] })
  values = output.lines.map(&:chomp)
  abort "Unexpected metadata shape: #{name}" unless values.length == variables.length
  results[name] = variables.zip(values).to_h
  [results[name], argv]
end
external = ["EMBERBSD_BUILD_AUTOCONF=#{autoconf}"]
%w[native cross].each do |mode|
  old, = metadata.call("#{mode}-ignored-before", 'old', mode, 'autoconf', external)
  fixed, make = metadata.call("#{mode}-selected", 'new', mode, 'autoconf', external)
  abort 'Baseline did not expose the redundant dependency.' unless old['TOOL_DEPENDS'].include?(':../../devel/autoconf')
  abort 'Selected provider has an error.' unless fixed['PKG_FAIL_REASON'].empty?
  abort 'Selected provider still requests an Autoconf package.' if fixed.values_at('TOOL_DEPENDS', 'DEPENDS', 'TEST_DEPENDS').any? { |v| v.include?(':../../devel/autoconf') }
  tools.each do |tool|
    expected = tool == 'autoconf' ? autoconf : "#{File.dirname(autoconf)}/#{tool}"
    abort "Wrong #{tool} selection" unless fixed["TOOLS_PATH.#{tool}"] == expected
  end
  %w[autoconf autoconf:run autoconf:test autoconf213 autoconf269].each do |use|
    opts = use == 'autoconf' ? [] : external
    before, = metadata.call("#{mode}-#{use.tr(':', '-')}-before", 'old', mode, use, opts)
    after, = metadata.call("#{mode}-#{use.tr(':', '-')}-after", 'new', mode, use, opts)
    normalized_before = before.transform_values { |v| v.gsub("#{work}/old/", '%PKGSRC%/') }
    normalized_after = after.transform_values { |v| v.gsub("#{work}/new/", '%PKGSRC%/') }
    abort "Changed default/legacy/runtime/test routing: #{mode}/#{use}" unless normalized_before == normalized_after
  end
  # Invoke actual pkgsrc creation rules only after checking every output path.
  names = %w[WRKDIR TOOLS_DIR WRKLOG] + tools.map { |t| "TOOLS_CMD.#{t}" }
  values = run.call("#{mode}-paths", make + names.flat_map { |v| ['-v', v] }).lines.map(&:chomp)
  abort 'Unexpected path metadata.' unless values.length == names.length
  values.each do |value|
    path = Pathname.new(value).cleanpath.to_s
    base = "#{work}/objects-#{mode}"
    abort "Non-private tool output: #{value}" unless path == base || path.start_with?("#{base}/")
    Pathname.new(path).ascend { |part| abort "Symlink output ancestor: #{part}" if File.symlink?(part) }
  end
  wrappers = values.drop(3)
  run.call("#{mode}-wrappers", make + ['_PKGSRC_BARRIER=yes', 'TOOLS_ALWAYS_WRAP=yes'] + wrappers)
  wrappers.each { |path| run.call("#{mode}-#{File.basename(path)}-version", [path, '--version']) }
  source = "#{work}/source-#{mode}"
  FileUtils.mkdir(source)
  File.write("#{source}/configure.ac", "AC_INIT([ember-host-autoconf], [1.0])\nAC_CONFIG_HEADERS([config.h])\nAC_DEFINE([EMBER_GENERATOR_VALUE], [42], [Generator contract value.])\nAC_OUTPUT\n")
  run.call("#{mode}-autoconf", [wrappers[0]], source)
  run.call("#{mode}-autoheader", [wrappers[1]], source)
  run.call("#{mode}-configure", ['sh', './configure'], source)
  abort 'Generated header is incorrect.' unless File.read("#{source}/config.h").include?('#define EMBER_GENERATOR_VALUE 42')
end
controls = { 'relative' => 'autoconf', 'missing' => "#{work}/missing-autoconf" }
%w[old broken nonexecutable wrong-banner].each do |kind|
  path = "#{work}/#{kind}-autoconf"
  version = kind == 'old' ? '2.72' : '2.73'
  banner = kind == 'wrong-banner' ? "automake (GNU automake) #{version}" : "autoconf (GNU Autoconf) #{version}"
  File.write(path, "#!/bin/sh\nprintf '%s\\n' '#{banner}'\n" + (kind == 'broken' ? "exit 1\n" : ''))
  File.chmod(0o755, path) unless kind == 'nonexecutable'
  controls[kind] = path
end
controls.each do |name, path|
  value, = metadata.call("invalid-#{name}", 'new', 'native', 'autoconf', ["EMBERBSD_BUILD_AUTOCONF=#{path}"])
  abort "Accepted invalid provider: #{name}" unless value['PKG_FAIL_REASON'].include?('EMBERBSD_BUILD_AUTOCONF')
end
value, = metadata.call('required-version', 'new', 'native', 'autoconf', external + ['AUTOCONF_REQD=2.50 99.0'])
abort 'Ignored AUTOCONF_REQD.' unless value['PKG_FAIL_REASON'].include?('Autoconf >=99.0')
%w[missing mismatch failure].each do |kind|
  dir = "#{work}/companion-#{kind}"
  FileUtils.mkdir(dir)
  tools.each { |tool| File.symlink("#{File.dirname(autoconf)}/#{tool}", "#{dir}/#{tool}") unless tool == 'autoheader' }
  unless kind == 'missing'
    File.write("#{dir}/autoheader", "#!/bin/sh\nprintf '%s\\n' 'autoheader (GNU Autoconf) #{kind == 'mismatch' ? '2.72' : '2.73'}'\n" + (kind == 'failure' ? "exit 1\n" : ''))
    File.chmod(0o755, "#{dir}/autoheader")
  end
  value, = metadata.call("invalid-companion-#{kind}", 'new', 'native', 'autoconf', ["EMBERBSD_BUILD_AUTOCONF=#{dir}/autoconf"])
  abort "Accepted invalid companion: #{kind}" unless value['PKG_FAIL_REASON'].include?('matching executable autoheader')
end
File.write("#{work}/result.json", JSON.pretty_generate(
  scope: 'Real native/cross pkgsrc metadata and host tool wrappers; no package installation or target execution.',
  inputs: [native, cross, autoconf, patch].to_h { |p| [p, Digest::SHA256.file(p).hexdigest] }, results: results
) + "\n")
puts 'PASS: explicit native Autoconf, seven real tool wrappers, source regeneration, routing and refusal controls.'
