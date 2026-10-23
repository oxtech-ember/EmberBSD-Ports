/* Reset a wedged root-hub port (connected but not enabled only).
 * usage: portreset /dev/usbN PORT */
#include <sys/ioctl.h>
#include <dev/usb/usb.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>

static int
roothub(int fd, uint8_t rt, uint8_t reqno, uint16_t val, uint16_t idx,
    void *data, uint16_t len)
{
	struct usb_ctl_request req;

	memset(&req, 0, sizeof(req));
	req.ucr_addr = 0; /* root hub */
	req.ucr_request.bmRequestType = rt;
	req.ucr_request.bRequest = reqno;
	USETW(req.ucr_request.wValue, val);
	USETW(req.ucr_request.wIndex, idx);
	USETW(req.ucr_request.wLength, len);
	req.ucr_data = data;
	req.ucr_flags = USBD_SHORT_XFER_OK;
	return ioctl(fd, USB_REQUEST, &req);
}

int
main(int argc, char **argv)
{
	unsigned char buf[4];
	unsigned status;
	int fd, port;

	if (argc < 3) {
		fprintf(stderr, "usage: %s /dev/usbN PORT\n", argv[0]);
		return 2;
	}
	fd = open(argv[1], O_RDWR);
	if (fd < 0) {
		perror("open");
		return 2;
	}
	port = atoi(argv[2]);

	if (roothub(fd, 0xa3, 0, 0, port, buf, 4) < 0) {
		printf("port %u: get status failed: %s\n", port, strerror(errno));
		return 1;
	}
	status = buf[0] | (buf[1] << 8);
	printf("port %u: status=%04x%s%s\n", port, status,
	    (status & 0x0001) ? " connected" : " no-device",
	    (status & 0x0002) ? " enabled" : " disabled");

	/* Only a wedged port (connected but not enabled) needs a reset;
	 * resetting healthy ports degrades the controller. */
	if ((status & 0x0001) && !(status & 0x0002)) {
		if (roothub(fd, 0x23, 3, 0x0004, port, NULL, 0) < 0) {
			printf("reset failed: %s\n", strerror(errno));
			return 1;
		}
		printf("reset sent\n");
	} else {
		printf("no reset needed\n");
	}
	return 0;
}
