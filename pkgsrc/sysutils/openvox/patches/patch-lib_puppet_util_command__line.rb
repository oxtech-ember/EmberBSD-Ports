$NetBSD$

Fix subcommand handling for our suffixed bins.

--- lib/puppet/util/command_line.rb.orig
+++ lib/puppet/util/command_line.rb
@@ -39,7 +39,7 @@
       # @return [String] name of the subcommand is being executed
       # @api public
       def subcommand_name
-        return @command if @command != 'puppet'
+        return @command if (@command != 'puppet' && @command != 'puppet@RUBY_SUFFIX@')
 
         if @argv.first =~ OPTION_OR_MANIFEST_FILE
           nil
@@ -51,7 +51,7 @@
       # @return [Array<String>] the command line arguments being passed to the subcommand
       # @api public
       def args
-        return @argv if @command != 'puppet'
+        return @argv if (@command != 'puppet' && @command != 'puppet@RUBY_SUFFIX@')
 
         if subcommand_name.nil?
           @argv
