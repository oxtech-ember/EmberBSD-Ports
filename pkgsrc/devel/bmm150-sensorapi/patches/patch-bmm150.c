--- bmm150.c.orig
+++ bmm150.c
@@ -620,6 +620,10 @@
          * but in default the MSB is always 0
          */
         dev->intf_rslt = dev->write(reg_addr, reg_data, len, dev->intf_ptr);
+        if (dev->intf_rslt != BMM150_INTF_RET_SUCCESS)
+        {
+            rslt = BMM150_E_COM_FAIL;
+        }
     }
     else
     {
@@ -650,6 +654,10 @@
 
         /* Read the data from the reg_addr */
         dev->intf_rslt = dev->read(reg_addr, reg_data, len, dev->intf_ptr);
+        if (dev->intf_rslt != BMM150_INTF_RET_SUCCESS)
+        {
+            rslt = BMM150_E_COM_FAIL;
+        }
     }
     else
     {
