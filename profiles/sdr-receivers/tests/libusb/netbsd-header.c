/* SPDX-License-Identifier: BSD-2-Clause */
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <sys/types.h>
#define USB_MAX_ENDPOINTS 16
#define UE_GET_ADDR(x) ((x) & 15)
#define LIBUSB_TRANSFER_TYPE_CONTROL 0
#define LIBUSB_TRANSFER_TYPE_ISOCHRONOUS 1
#define LIBUSB_TRANSFER_TYPE_BULK 2
#define LIBUSB_TRANSFER_TYPE_INTERRUPT 3
#define LIBUSB_TRANSFER_SHORT_NOT_OK 1
#define LIBUSB_ERROR_IO -1
#define LIBUSB_ERROR_INVALID_PARAM -2
#define LIBUSB_ERROR_ACCESS -3
#define LIBUSB_ERROR_NO_DEVICE -4
#define LIBUSB_ERROR_NOT_FOUND -5
#define LIBUSB_ERROR_BUSY -6
#define LIBUSB_ERROR_TIMEOUT -7
#define LIBUSB_ERROR_OVERFLOW -8
#define LIBUSB_ERROR_PIPE -9
#define LIBUSB_ERROR_INTERRUPTED -10
#define LIBUSB_ERROR_NO_MEM -11
#define LIBUSB_ERROR_NOT_SUPPORTED -12
#define LIBUSB_ERROR_OTHER -99
#define LIBUSB_SUCCESS 0
#define USB_SET_TIMEOUT 100
#define USB_SET_SHORT_XFER 101
#define USB_SET_BULK_RA_OPT 102
#define USB_SET_BULK_RA 103
#define UNUSED(x) (void)(x)
#define usbi_dbg(...) ((void)0)
#define HANDLE_CTX(x) NULL
#define TRANSFER_CTX(x) NULL
#define ITRANSFER_CTX(x) NULL
#define IS_XFERIN(t) (((t)->endpoint & 0x80) != 0)
#define USBI_TRANSFER_TO_LIBUSB_TRANSFER(x) (&(x)->transfer)
typedef void usb_config_descriptor_t;
struct usb_bulk_ra_wb_opt { unsigned ra_wb_buffer_size; unsigned ra_wb_request_size; };
struct libusb_device { void *priv; };
struct libusb_device_handle { struct libusb_device *dev; void *priv; };
struct libusb_transfer { struct libusb_device_handle *dev_handle; unsigned char endpoint, type; unsigned timeout, flags; unsigned char *buffer; int length; };
struct usbi_transfer { struct libusb_transfer transfer; int transferred; };
#define usbi_get_device_priv(d) ((d)->priv)
#define usbi_get_device_handle_priv(h) ((h)->priv)
static int opens, closes, reads, writes, options, enables, nextfd=10;
static int fail_open, fail_opt, fail_enable, wrong_option;
static unsigned char closed_fds[256];
static int test_open(const char *p,int flags,...) { (void)flags; if (fail_open && strstr(p,".02")) { errno=EACCES; return -1; } opens++; return nextfd++; }
static int test_close(int fd) { if(fd<0 || fd>=256 || closed_fds[fd]) abort(); closed_fds[fd]=1; closes++; errno=EINTR; return 0; }
static ssize_t test_read(int fd,void *b,size_t n) { (void)fd; memset(b,0x5a,n); reads++; return n; }
static ssize_t test_write(int fd,const void *b,size_t n) { (void)fd;(void)b;writes++;return n; }
static int test_ioctl(int fd,unsigned long cmd,...) {
 (void)fd; va_list ap;va_start(ap,cmd);void *arg=va_arg(ap,void*);va_end(ap);
 if(cmd==USB_SET_BULK_RA_OPT) { struct usb_bulk_ra_wb_opt *o=arg;options++;if(o->ra_wb_buffer_size!=1048576 || o->ra_wb_request_size!=65536)wrong_option=1;if(fail_opt){errno=EIO;return -1;} }
 if(cmd==USB_SET_BULK_RA) { enables++;if(*(int*)arg!=1)wrong_option=1;if(fail_enable){errno=ENOMEM;return -1;} }
 return 0;
}
#define open test_open
#define close test_close
#define read test_read
#define write test_write
#define ioctl test_ioctl
