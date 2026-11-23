$NetBSD$

NetBSD groupadd takes an explicit GID range after -r.

--- lib/puppet/provider/group/groupadd.rb.orig
+++ lib/puppet/provider/group/groupadd.rb
@@ -11,7 +11,7 @@
 
   commands :add => "groupadd", :delete => "groupdel", :modify => "groupmod"
 
-  has_feature :system_groups unless %w[HP-UX Solaris].include? Puppet.runtime[:facter].value('os.name')
+  has_feature :system_groups unless netbsd_account_tools? || %w[HP-UX Solaris].include?(Puppet.runtime[:facter].value('os.name'))
 
   verify :gid, _("GID must be an integer") do |value|
     value.is_a? Integer
