$NetBSD$

Identify NetBSD-family account tools for the useradd and groupadd providers.

--- lib/puppet/provider/nameservice/objectadd.rb.orig
+++ lib/puppet/provider/nameservice/objectadd.rb
@@ -4,6 +4,10 @@
 
 class Puppet::Provider::NameService
   class ObjectAdd < Puppet::Provider::NameService
+    def self.netbsd_account_tools?
+      Puppet.runtime[:facter].value('os.family') == 'NetBSD' || Puppet.runtime[:facter].value('os.name') == 'NetBSD'
+    end
+
     def deletecmd
       [command(:delete), @resource[:name]]
     end
