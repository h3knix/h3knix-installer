#!/bin/bash


echo "Starting makecd.sh"
echo ""

if [ -e block ] ; then
	echo "Blocker found, cannot continue"
	echo ""
	echo ""
	cat block
	echo ""
	exit 1
fi

h3kver="2.2"

echo "Generating iso -> h3knix-$h3kver.iso"
mkisofs -o h3knix-$h3kver.iso -R -V "h3knix $h3kver" -T -b \
isolinux/isolinux.bin -c isolinux/boot.cat -no-emul-boot -boot-load-size \
4 -boot-info-table -A "h3knix $h3kver" .

echo "Generating md5sum -> h3knix-$h3kver.md5"
md5sum h3knix-$h3kver.iso > h3knix-$h3kver.md5

echo ""
echo "Completed"
