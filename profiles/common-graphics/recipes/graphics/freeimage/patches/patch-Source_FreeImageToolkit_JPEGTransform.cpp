Origin: EmberBSD (AI-assisted), public system-JPEG lossless transforms.

--- Source/FreeImageToolkit/JPEGTransform.cpp.orig
+++ Source/FreeImageToolkit/JPEGTransform.cpp
@@ -32,6 +32,8 @@
 #include <stdio.h>
 #include <jpeglib.h>
 #include <jerror.h>
+#include <turbojpeg.h>
+#include <limits.h>
 // transupp.h isn't installed by system libjpeg/libjpeg-turbo packages; the
 // jtransform_*/jpeg_transform_info API it declares is only used in the
 // bundled-libjpeg branch below.
@@ -46,6 +48,10 @@
 #include "FreeImage.h"
 #include "Utilities.h"
 #include "FreeImageIO.h"
+
+#ifdef FREEIMAGE_SYSTEM_LIBJPEG
+#include <vector>
+#endif
 
 // ----------------------------------------------------------
 //   Source manager & Destination manager setup
@@ -160,14 +166,156 @@
 }
 
 #ifdef FREEIMAGE_SYSTEM_LIBJPEG
-// Lossless JPEG transforms need transupp.h's jtransform_* API, which isn't
-// installed by system libjpeg/libjpeg-turbo packages (it ships only as
-// jpegtran example source, not a public dev header) - report cleanly
-// unsupported rather than failing the build.
+// Use the public TurboJPEG API. The jpegtran transupp API is not installed.
+METHODDEF(void)
+system_jpeg_error_exit(j_common_ptr cinfo) {
+	(*cinfo->err->output_message)(cinfo);
+	throw FIF_JPEG;
+}
+
 static BOOL
 JPEGTransformFromHandle(FreeImageIO* src_io, fi_handle src_handle, FreeImageIO* dst_io, fi_handle dst_handle, FREE_IMAGE_JPEG_OPERATION operation, int* left, int* top, int* right, int* bottom, BOOL perfect) {
-	FreeImage_OutputMessageProc(FIF_JPEG, "Lossless JPEG transforms are unavailable in this build (built against system libjpeg)");
-	return FALSE;
+	const BOOL onlyReturnCropRect = (dst_io == NULL) || (dst_handle == NULL);
+	if(!src_io || !src_handle || !src_io->read_proc ||
+		(!onlyReturnCropRect && !dst_io->write_proc)) {
+		return FALSE;
+	}
+	if(!onlyReturnCropRect && src_handle == dst_handle) {
+		if(!dst_io->tell_proc || !dst_io->seek_proc) {
+			return FALSE;
+		}
+	}
+
+	jpeg_decompress_struct header = {};
+	jpeg_error_mgr error;
+	tjhandle transformer = NULL;
+	unsigned char* output = NULL;
+	size_t output_size = 0;
+	BOOL result = FALSE;
+	try {
+		long stream_start = 0;
+		if(!onlyReturnCropRect && src_handle == dst_handle &&
+			(stream_start = dst_io->tell_proc(dst_handle)) < 0) {
+			throw(1);
+		}
+		// Read before writing, including when both handles refer to one stream.
+		std::vector<unsigned char> input;
+		unsigned char block[4096];
+		unsigned count;
+		while((count = src_io->read_proc(block, 1, sizeof(block), src_handle)) != 0) {
+			if(count > sizeof(block)) {
+				throw(1);
+			}
+			input.insert(input.end(), block, block + count);
+		}
+		if(input.empty() || input.size() > ULONG_MAX) {
+			throw(1);
+		}
+
+		// Public libjpeg headers also describe unusual sampling factors that
+		// TurboJPEG reports as TJSAMP_UNKNOWN. Do not guess their iMCU size.
+		header.err = jpeg_std_error(&error);
+		header.err->error_exit = system_jpeg_error_exit;
+		header.err->output_message = ls_jpeg_output_message;
+		jpeg_create_decompress(&header);
+		jpeg_mem_src(&header, input.data(), (unsigned long)input.size());
+		if(jpeg_read_header(&header, TRUE) != JPEG_HEADER_OK) {
+			throw(1);
+		}
+
+		tjtransform transform = {};
+		BOOL swappedDim = FALSE, trimH = FALSE, trimV = FALSE;
+		switch(operation) {
+			case FIJPEG_OP_FLIP_H:
+				transform.op = TJXOP_HFLIP; trimH = TRUE; break;
+			case FIJPEG_OP_FLIP_V:
+				transform.op = TJXOP_VFLIP; trimV = TRUE; break;
+			case FIJPEG_OP_TRANSPOSE:
+				transform.op = TJXOP_TRANSPOSE; swappedDim = TRUE; break;
+			case FIJPEG_OP_TRANSVERSE:
+				transform.op = TJXOP_TRANSVERSE; swappedDim = trimH = trimV = TRUE; break;
+			case FIJPEG_OP_ROTATE_90:
+				transform.op = TJXOP_ROT90; swappedDim = trimH = TRUE; break;
+			case FIJPEG_OP_ROTATE_180:
+				transform.op = TJXOP_ROT180; trimH = trimV = TRUE; break;
+			case FIJPEG_OP_ROTATE_270:
+				transform.op = TJXOP_ROT270; swappedDim = trimV = TRUE; break;
+			default:
+				transform.op = TJXOP_NONE; break;
+		}
+		const int fullWidth = swappedDim ? header.image_height : header.image_width;
+		const int fullHeight = swappedDim ? header.image_width : header.image_height;
+		const int mcuWidth = DCTSIZE * (header.num_components == 1 ? 1 :
+			(swappedDim ? header.max_v_samp_factor : header.max_h_samp_factor));
+		const int mcuHeight = DCTSIZE * (header.num_components == 1 ? 1 :
+			(swappedDim ? header.max_h_samp_factor : header.max_v_samp_factor));
+		if(perfect == TRUE && ((trimH && fullWidth % mcuWidth) ||
+			(trimV && fullHeight % mcuHeight))) {
+			FreeImage_OutputMessageProc(FIF_JPEG, "Transformation is not perfect");
+			throw(1);
+		}
+		transform.options = TJXOPT_TRIM | (perfect == TRUE ? TJXOPT_PERFECT : 0);
+		char crop[64];
+		int outputWidth = fullWidth, outputHeight = fullHeight;
+		if(getCropString(crop, left, top, right, bottom, fullWidth, fullHeight)) {
+			// Expand the top/left to an iMCU boundary, as jpegtran does.
+			transform.options |= TJXOPT_CROP;
+			transform.r.x = *left / mcuWidth * mcuWidth;
+			transform.r.y = *top / mcuHeight * mcuHeight;
+			transform.r.w = outputWidth = *right - transform.r.x;
+			transform.r.h = outputHeight = *bottom - transform.r.y;
+		}
+		transformer = tj3Init(TJINIT_TRANSFORM);
+		if(!transformer || tj3DecompressHeader(transformer, input.data(), input.size()) != 0) {
+			FreeImage_OutputMessageProc(FIF_JPEG, "%s", tj3GetErrorStr(transformer));
+			throw(1);
+		}
+		if((transform.options & TJXOPT_CROP) && tj3Get(transformer, TJPARAM_SUBSAMP) == TJSAMP_UNKNOWN) {
+			FreeImage_OutputMessageProc(FIF_JPEG, "TurboJPEG cannot crop this JPEG subsampling type");
+			throw(1);
+		}
+		// Trimming applies only when the crop reaches a non-transformable edge.
+		if(trimH && outputWidth / mcuWidth > 0 &&
+			(transform.r.x + outputWidth) / mcuWidth == fullWidth / mcuWidth) {
+			outputWidth = outputWidth / mcuWidth * mcuWidth;
+		}
+		if(trimV && outputHeight / mcuHeight > 0 &&
+			(transform.r.y + outputHeight) / mcuHeight == fullHeight / mcuHeight) {
+			outputHeight = outputHeight / mcuHeight * mcuHeight;
+		}
+		const int trimmedWidth = trimH && fullWidth >= mcuWidth ? fullWidth % mcuWidth : 0;
+		const int trimmedHeight = trimV && fullHeight >= mcuHeight ? fullHeight % mcuHeight : 0;
+		if(left) *left = trimmedWidth + transform.r.x;
+		if(top) *top = trimmedHeight + transform.r.y;
+		if(right) *right = (left ? *left : 0) + outputWidth;
+		if(bottom) *bottom = (top ? *top : 0) + outputHeight;
+
+		if(!onlyReturnCropRect) {
+			if(tj3Transform(transformer, input.data(), input.size(),
+				1, &output, &output_size, &transform) != 0) {
+				FreeImage_OutputMessageProc(FIF_JPEG, "%s", tj3GetErrorStr(transformer));
+				throw(1);
+			}
+			if(src_handle == dst_handle && dst_io->seek_proc(dst_handle, stream_start, SEEK_SET) != 0) {
+				throw(1);
+			}
+			for(size_t offset = 0; offset < output_size;) {
+				const unsigned chunk = (unsigned)MIN(output_size - offset, (size_t)UINT_MAX);
+				if(dst_io->write_proc(output + offset, 1, chunk, dst_handle) != chunk) {
+					throw(1);
+				}
+				offset += chunk;
+			}
+		}
+		result = TRUE;
+	}
+	catch(...) {
+		result = FALSE;
+	}
+	tj3Free(output);
+	if(transformer) tj3Destroy(transformer);
+	jpeg_destroy_decompress(&header);
+	return result;
 }
 #else
 static BOOL
