--- bmi2.c.orig
+++ bmi2.c
@@ -5696,7 +5696,7 @@
         if (rslt == BMI2_OK)
         {
             /* Burst write configuration file data corresponding to user set length */
-            rslt = bmi2_set_regs(BMI2_INIT_DATA_ADDR, (uint8_t *)config_data, write_len, dev);
+            rslt = bmi2_set_regs(BMI2_INIT_DATA_ADDR, config_data, write_len, dev);
         }
     }
     else
@@ -6029,7 +6029,7 @@
                         dev->aux_man_en = 0;
 
                         /* Set the read address of the AUX sensor */
-                        rslt = bmi2_set_regs(BMI2_AUX_RD_ADDR, (uint8_t *) &config->read_addr, 1, dev);
+                        rslt = bmi2_set_regs(BMI2_AUX_RD_ADDR, &config->read_addr, 1, dev);
                         dev->delay_us(1000, dev->intf_ptr);
                     }
                     else
