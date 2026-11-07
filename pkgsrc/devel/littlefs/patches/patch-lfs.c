$NetBSD$

--- lfs.c.orig
+++ lfs.c
@@ -4779,7 +4779,8 @@ int lfs_fs_traverse_(lfs_t *lfs,
             continue;
         }
 
-        if (((f->flags & LFS_F_DIRTY) || (f->flags & LFS_F_DUSTY))
+        if (((f->flags & LFS_F_DIRTY) || (f->flags & LFS_F_DUSTY)
+                || lfs_pair_isnull(f->m.pair))
                 && !(f->flags & LFS_F_INLINE)) {
             int err = lfs_ctz_traverse(lfs, &f->cache, &lfs->rcache,
                     f->ctz.head, f->ctz.size, cb, data);
