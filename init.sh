#!/bin/sh

case $1 in
	stop)
		rm /bin/manual
		rm /bin/menu
		rm /bin/h3kchroot
		rm /bin/setup
	;;
	*)
		ln -sf /mnt/cdrom/manual /bin/manual
		ln -sf /mnt/cdrom/menu /bin/menu
		ln -sf /mnt/cdrom/h3kchroot /bin/h3kchroot
		cp /mnt/cdrom/setup /bin/setup
	;;
esac
