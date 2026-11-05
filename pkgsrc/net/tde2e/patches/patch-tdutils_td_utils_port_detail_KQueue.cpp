# $NetBSD$

Use the actual kevent udata type for pointer and integer BSD ABIs.
Origin: EmberBSD portability fix.

--- tdutils/td/utils/port/detail/KQueue.cpp.orig
+++ tdutils/td/utils/port/detail/KQueue.cpp
@@ -84,11 +84,7 @@
   if (changes_n_ == static_cast<int>(events_.size())) {
     flush_changes();
   }
-#if TD_NETBSD
-  auto set_udata = reinterpret_cast<std::intptr_t>(udata);
-#else
-  auto set_udata = udata;
-#endif
+  auto set_udata = reinterpret_cast<decltype(events_[0].udata)>(udata);
   EV_SET(&events_[changes_n_], ident, filter, flags, fflags, data, set_udata);
   VLOG(fd) << "Subscribe [fd:" << ident << "] [filter:" << filter << "] [udata: " << udata << "]";
   changes_n_++;
@@ -165,11 +161,7 @@
     if (event->fflags & EV_ERROR) {
       LOG(FATAL) << "EV_ERROR in kqueue is not supported";
     }
-#if TD_NETBSD
     auto udata = reinterpret_cast<void *>(event->udata);
-#else
-    auto udata = event->udata;
-#endif
     VLOG(fd) << "Event [fd:" << event->ident << "] [filter:" << event->filter << "] [udata: " << udata << "]";
     // LOG(WARNING) << "Have event->ident = " << event->ident << "event->filter = " << event->filter;
     auto pollable_fd = PollableFd::from_list_node(static_cast<ListNode *>(udata));
