#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); Redmine plugins in Ports follow the Zeitwerk
# rules that Redmine 7 applies when it eager loads them.
require 'fileutils'
require 'open3'
require 'prism'
require 'rubygems/package'

usage = 'usage: ruby-redmine-plugins-autoload.rb EXPORTED_PKGSRC MAKECONF DISTDIR NEW_WORK (BMAKE)'
abort usage unless ARGV.length == 4 && ENV['BMAKE']
tree, makeconf, distdir = ARGV.take(3).map { |path| File.realpath(path) }
work = File.expand_path(ARGV[3])
abort 'NEW_WORK must be new' if File.exist?(work) || File.symlink?(work)
Dir.mkdir(work)

def vars(tree, makeconf, pkgpath, *names)
  out, err, status = Open3.capture3({ 'MAKECONF' => makeconf }, ENV['BMAKE'],
                                    *names.flat_map { |name| ['-v', name] }, chdir: "#{tree}/#{pkgpath}")
  abort "#{pkgpath}: bmake failed: #{err}" unless status.success?
  names.zip(out.lines.map(&:strip)).to_h
end

def run(*cmd, **opts)
  out, status = Open3.capture2e(*cmd, **opts)
  abort "#{cmd.join(' ')} failed:\n#{out}" unless status.success?
end

# Zeitwerk from its distfile, as Rails uses it.
zw = vars(tree, makeconf, 'devel/ruby-zeitwerk', 'DISTNAME')['DISTNAME']
Gem::Package.new("#{distdir}/#{zw}.gem").extract_files("#{work}/#{zw}")
$LOAD_PATH.unshift("#{work}/#{zw}/lib")
require 'zeitwerk'

# Constant paths that a file defines, with their lexical nesting.
def defined_cpaths(node, nesting = [], found = [])
  case node
  when Prism::ClassNode, Prism::ModuleNode
    name = nesting + [node.constant_path.full_name]
    found << name.join('::')
    node.body && defined_cpaths(node.body, name, found)
    return found
  when Prism::ConstantWriteNode
    found << (nesting + [node.name.to_s]).join('::')
  when Prism::ConstantPathWriteNode
    found << (nesting + [node.target.full_name]).join('::')
  end
  node.compact_child_nodes.each { |child| defined_cpaths(child, nesting, found) }
  found
end

def unloadable_calls(node, found = [])
  found << node.location.start_line if node.is_a?(Prism::CallNode) && node.name == :unloadable && node.receiver.nil?
  node.compact_child_nodes.each { |child| unloadable_calls(child, found) }
  found
end

meta = vars(tree, makeconf, 'meta-pkgs/ruby-redmine-plugins', 'DEPENDS', 'PKG_FAIL_REASON')
abort "meta-pkgs/ruby-redmine-plugins: #{meta['PKG_FAIL_REASON']}" unless meta['PKG_FAIL_REASON'].empty?
plugins = meta['DEPENDS'].split.map { |dep| dep[%r{:\.\./\.\./(devel/ruby-redmine_[^/\s]+)\z}, 1] }.compact.sort
abort 'meta-pkgs/ruby-redmine-plugins lists no plugins' if plugins.empty?

failures = []
plugins.each do |pkgpath|
  v = vars(tree, makeconf, pkgpath, 'PKG_FAIL_REASON', 'DISTFILES', 'DIST_SUBDIR', 'WRKDIR', 'WRKSRC',
           'PATCHDIR', 'PLIST_SRC', 'PLUGIN_NAME')
  abort "#{pkgpath}: #{v['PKG_FAIL_REASON']}" unless v['PKG_FAIL_REASON'].empty?
  base = "#{work}/#{File.basename(pkgpath)}"
  wrkdir = "#{base}/work"
  FileUtils.mkdir_p(wrkdir)
  v['DISTFILES'].split.each do |file|
    path = File.join(distdir, v['DIST_SUBDIR'], file)
    abort "#{pkgpath}: missing distfile #{path}; run bmake fetch" unless File.file?(path)
    run('tar', 'xzf', path, chdir: wrkdir)
  end
  rel = v['WRKSRC'].delete_prefix(v['WRKDIR'])
  abort "#{pkgpath}: WRKSRC #{v['WRKSRC']} is outside WRKDIR" if rel == v['WRKSRC']
  wrksrc = "#{wrkdir}#{rel}"
  Dir.glob("#{v['PATCHDIR']}/patch-*").sort.each do |patch|
    run('patch', '-p0', '-s', '-N', '-E', '-i', patch, chdir: wrksrc)
  end
  # The installed tree, as listed in the PLIST.
  inst = "#{base}/plugins/#{v['PLUGIN_NAME']}"
  prefix = "${RM_PLUGINDIR}/#{v['PLUGIN_NAME']}/"
  v['PLIST_SRC'].split.flat_map { |plist| File.readlines(plist, chomp: true) }.each do |line|
    next if line.start_with?('@')
    abort "#{pkgpath}: unexpected PLIST entry #{line}" unless line.start_with?(prefix)
    file = line.delete_prefix(prefix)
    abort "#{pkgpath}: #{file} is in the PLIST but not in the source" unless File.file?("#{wrksrc}/#{file}")
    FileUtils.mkdir_p(File.dirname("#{inst}/#{file}"))
    FileUtils.cp("#{wrksrc}/#{file}", "#{inst}/#{file}")
  end
  # Redmine::PluginLoader pushes the engine eager load paths and lib.
  roots = Dir.glob(["#{inst}/app/*", "#{inst}/app/*/concerns"]).select { |dir| File.directory?(dir) }
  roots.reject! { |dir| %w[assets javascript].include?(File.basename(dir)) }
  roots << "#{inst}/lib" if File.directory?("#{inst}/lib")
  loader = Zeitwerk::Loader.new
  loader.tag = v['PLUGIN_NAME']
  roots.each { |dir| loader.push_dir(dir) }
  expected = loader.all_expected_cpaths
  checked = 0
  roots.flat_map { |dir| Dir.glob("#{dir}/**/*.rb") }.uniq.sort.each do |file|
    shown = file.delete_prefix("#{inst}/")
    result = Prism.parse_file(file)
    unless result.success?
      failures << "#{pkgpath}: #{shown} does not parse"
      next
    end
    unloadable_calls(result.value).each do |line|
      failures << "#{pkgpath}: #{shown}:#{line} calls unloadable, which Rails 7 removed"
    end
    cpath = expected[file]
    next unless cpath
    checked += 1
    found = defined_cpaths(result.value)
    unless found.include?(cpath)
      failures << "#{pkgpath}: #{shown} must define #{cpath} for Zeitwerk, defines #{found.empty? ? 'nothing' : found.join(', ')}"
    end
  end
  puts "#{pkgpath}: #{checked} autoloaded files checked"
end
abort "FAIL:\n#{failures.join("\n")}" unless failures.empty?
puts "PASS: #{plugins.size} Redmine plugins define the constants that Zeitwerk expects and do not call unloadable"
