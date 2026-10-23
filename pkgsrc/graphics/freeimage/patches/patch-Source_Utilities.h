$NetBSD$

Use byte copies for pixel storage with no word or floating-point alignment.
Origin: EmberBSD (AI-assisted); actual GCC16 alignment sanitizer regression.

--- Source/Utilities.h.orig
+++ Source/Utilities.h
@@ -312,48 +312,11 @@
 inline void 
 AssignPixel(BYTE* dst, const BYTE* src, unsigned bytesperpixel) {
 	switch (bytesperpixel) {
-		case 1:	// FIT_BITMAP (8-bit)
-			*dst = *src;
+		case 1: case 2: case 3: case 4:
+		case 6: case 8: case 12: case 16:
+			// Pixel storage can be unaligned, including successive 24-bit pixels.
+			memcpy(dst, src, bytesperpixel);
 			break;
-
-		case 2: // FIT_UINT16 / FIT_INT16 / 16-bit
-			*(reinterpret_cast<WORD*>(dst)) = *(reinterpret_cast<const WORD*> (src));
-			break;
-
-		case 3: // FIT_BITMAP (24-bit)
-			*(reinterpret_cast<WORD*>(dst)) = *(reinterpret_cast<const WORD*> (src));
-			dst[2] = src[2];
-			break;
-
-		case 4: // FIT_BITMAP (32-bit) / FIT_UINT32 / FIT_INT32 / FIT_FLOAT
-			*(reinterpret_cast<DWORD*>(dst)) = *(reinterpret_cast<const DWORD*> (src));
-			break;
-
-		case 6: // FIT_RGB16 (3 x 16-bit)
-			*(reinterpret_cast<DWORD*>(dst)) = *(reinterpret_cast<const DWORD*> (src));
-			*(reinterpret_cast<WORD*>(dst + 4)) = *(reinterpret_cast<const WORD*> (src + 4));	
-			break;
-
-		// the rest can be speeded up with int64
-			
-		case 8: // FIT_RGBA16 (4 x 16-bit)
-			*(reinterpret_cast<DWORD*>(dst)) = *(reinterpret_cast<const DWORD*> (src));
-			*(reinterpret_cast<DWORD*>(dst + 4)) = *(reinterpret_cast<const DWORD*> (src + 4));	
-			break;
-		
-		case 12: // FIT_RGBF (3 x 32-bit IEEE floating point)
-			*(reinterpret_cast<float*>(dst)) = *(reinterpret_cast<const float*> (src));
-			*(reinterpret_cast<float*>(dst + 4)) = *(reinterpret_cast<const float*> (src + 4));
-			*(reinterpret_cast<float*>(dst + 8)) = *(reinterpret_cast<const float*> (src + 8));
-			break;
-		
-		case 16: // FIT_RGBAF (4 x 32-bit IEEE floating point)
-			*(reinterpret_cast<float*>(dst)) = *(reinterpret_cast<const float*> (src));
-			*(reinterpret_cast<float*>(dst + 4)) = *(reinterpret_cast<const float*> (src + 4));
-			*(reinterpret_cast<float*>(dst + 8)) = *(reinterpret_cast<const float*> (src + 8));
-			*(reinterpret_cast<float*>(dst + 12)) = *(reinterpret_cast<const float*> (src + 12));
-			break;
-			
 		default:
 			assert(FALSE);
 	}
