#!/usr/bin/env python

#copyright michael vandenberghe 2005
#gnu gpl 2.0


import dialog
import time
import sys
import glob
import commands
import os.path
import os
import re
import getopt

######################################################################################################
# variables used for the installation

h3kver="2.2"
iversion="2.2-1.3"

install_type=""

custom_ver="2.6.11.10"

# kernel types format = 'kerneltype':[ "fb kernel options", "no fb kernel options" ]
initrd="/initrd.splash"
kernel_types = {
				'hwd':[ "vga=0x317 splash=verbose hwd","splash=none hwd"],
				'generic':[ "vga=0x317",""],
				'custom':[ "vga=0x317",""]
				}
kernelfb_args=""
kernenlnofb_args=""
kernel_type=""

root_part=""
boot_part=""
swap_part=""

#################################################
# mount location for h3knix root and cdrom

mount_point="/mnt/h3knix"
cdrom_point="/mnt/cdrom"

#################################################
# package list locations

# pkg sizes have to be doubles so they calculate right when
# the progress is calculated

listloc=cdrom_point+"/lists/"
pkg_core=listloc+"core.list"
pkg_core_size=79.00
pkg_base=listloc+"base.list"
pkg_base_size=39.00
pkg_ext=listloc+"ext.list"
pkg_ext_size=15.00
pkg_media=listloc+"media.list"
pkg_media_size=7.00
pkg_dialup=listloc+"dialup.list"
pkg_dialup_size=3.00

#################################################
# check if we can find the core, otherwise abort

if os.path.exists(pkg_core) == False:
	print "\n h3knix core not found, cannot continue"
	print pkg_core+" not found!\n"
	sys.exit(1)

#################################################
# logfile

log_file="/tmp/h3knix_install.log"
commands.getoutput("echo \"Started install.py\" > "+log_file)

#################################################
# supported file systems

filesystems = ["ext2","ext3","reiserfs","xfs","swap"]
filesystems_list = []
for i in filesystems:
	filesystems_list.append((i,i))

#################################################
# fstab
fstab_file=mount_point+"/etc/fstab"
fstab_head = """
#file system   mount-point     fs-type    options      dump  fsck-order
"""

fstab_tail = """
#system
sysfs             /sys          sysfs   defaults         0    0
proc              /proc         proc    defaults         0    0
devpts            /dev/pts      devpts  gid=4,mode=620   0    0
shm               /dev/shm      tmpfs   defaults         0    0
"""
#################################################
# grub
grub_vars={'root':"",'setup':""}

#################################################
# rc.conf configuration defaults
rc_clock="localtime"
rc_timezone="America/Denver"
rc_consolefont=""
rc_keymap = "us"
rc_hostname="h3knix"
rc_body="""
MODULES=()

SCRIPTS=()
"""

rc_numlock_header="""
# numlock setting at boot for console
#  leave it set to "on" to have numlock turned on at boot
# otherwise set it to "off"
"""
rc_numlock = "on"
rc_network_header="""
# change net to "static" if you want to use ip settings below
# "dhcp", to get the address automatically at boot
# "none" or "", if you don't want the network initialized at boot
"""
rc_network_type_abstract="dynamic"
rc_network_type = "dhcp"
# network information for static network, order: ip, gateway, broadcast, netmask
rc_ip_header="""
# ip address settings for eth0 with "static" network"""
rc_network_info = ["192.168.0.101","192.168.0.1","192.168.0.255","255.255.255.0"]

######################################################################################################
# the dialog window

d = dialog.Dialog(dialog="./dialog")
d.add_persistent_args(["--backtitle", "h3knix "+h3kver+" installation"])


######################################################################################################
# partition and drive detection class




class detect: # build a list of detected partitions and drives
	partitions = []
	drives = []
	swaps = []

	def __init__(self): # initialize all values for partitions and drives
		for i in glob.glob('/dev/hd?[0-9]*'):
			self.partitions.append((i,i))
		for i in glob.glob('/dev/sd?[0-9]*'):
			self.partitions.append((i,i))
		self.partitions.reverse()
			
		for i in glob.glob('/dev/hd?'):
				self.drives.append((i,i))
		for i in glob.glob('/dev/sd?'):
			self.drives.append((i,i))
		self.drives.reverse()
		
		tmp = commands.getoutput("/sbin/fdisk -l | grep swap | cut -d \" \" -f 1").split("\n")
		for i in tmp:
			self.swaps.append((i,i))
		self.swaps.append(("custom","manually select a partition"))
		self.swaps.reverse()
		
		
	def getParts(self): # return the list of detected partitions
		return self.partitions
		
	def getDrives(self): # return the list of detected drives
		return self.drives
		
	def getSwaps(self): # return the list of detected drives
		return self.swaps

	def refresh(self):
		self.partitions = []
		self.drives = []
		self.swaps = []
		self.__init__()


######################################################################################################
# handles exit requests
def handle_exit():
	response = d.yesno("Are you sure you want to exit?\n  All progress will be lost",width=60)
	if response == 0 or response == 2:
		print "Cleaning dirs..."
		if os.path.isdir(mount_point+"/caps"):
			commands.getoutput("rm -rf "+mount_point+"/caps")
		print "Cleaning mount points..."
		os.system("umount "+mount_point)
		if boot_part != "":
			os.system("umount "+mount_point+"/boot")
		print "Exiting..."
		sys.exit(0)

	
######################################################################################################
# supporting functions

def mount_parts():
	if commands.getoutput("df | grep "+mount_point) == "":
		d.infobox("Mounting root partition...",width=60)
		os.system("mount "+root_part+" "+mount_point)
	else:
		if commands.getoutput("df | grep "+mount_point).split()[0] != root_part:
			os.system("umount "+mount_point)
			d.infobox("Mounting root partition...",width=60)
			os.system("mount "+root_part+" "+mount_point)
	if boot_part != "":
		if os.path.isdir(mount_point+"/boot") == False:
			os.system("mkdir "+mount_point+"/boot")
		if commands.getoutput("df | grep "+mount_point+"/boot") == "":
			d.infobox("Mounting boot partition...",width=60)
			os.system("mount "+boot_part+" "+mount_point+"/boot")
		else:
			if commands.getoutput("df | grep "+mount_point+"/boot").split()[0] != boot_part:
				os.system("umount "+mount_point+"/boot")
				d.infobox("Mounting boot partition...",width=60)
				os.system("mount "+boot_part+" "+mount_point+"/boot")


def mountbind():
	os.system("mount --bind /dev "+mount_point+"/dev")
	os.system("mount --bind /sys "+mount_point+"/sys")
	os.system("mount --bind /proc "+mount_point+"/proc")

def umountbind():
	os.system("umount "+mount_point+"/dev")
	os.system("umount "+mount_point+"/sys")
	os.system("umount "+mount_point+"/proc")



def simple_menu(message,list):
	while 1:
		(code, tag) = d.menu(
	            message,
	            width=60,
	            choices=list)
		return tag

def select_root():
	global root_part
	root_part = simple_menu("Choose a root partition:",detected.getParts())
	
def select_boot():
	global boot_part
	boot_part = simple_menu("Choose a boot partition:",detected.getParts())
	
def select_swap():
	global swap_part
	swap_part = simple_menu("Choose a swap partition ( detected ):",detected.getSwaps())
	if swap_part == "custom":
			swap_part = simple_menu("Choose a swap partition ( manual ):",detected.getParts())

######################################################################################################
# pre installation

def do_format(format_part,format_type):
	if os.path.exists(format_part):
		if format_type == "ext2":
			os.system("mkfs -t ext2 "+format_part)
		elif format_type == "ext3":
			os.system("mkfs -t ext3 "+format_part)
		elif format_type == "reiserfs":
			os.system("mkfs -t reiserfs "+format_part)
		elif format_type == "xfs":
			os.system("mkfs -t xfs -f "+format_part)
		elif format_type == "swap":
			os.system("mkswap "+format_part)
			r = re.compile('\d')
			drive = r.sub("",format_part)
			r = re.compile('[a-z]|[A-Z]|/')
			part = r.sub("",format_part)
			os.system("sfdisk -c "+drive+" "+part+" 82")
		else:
			d.msgbox("Error: "+format_type+" is not supported",width=60)
		detected.refresh()
	else:
		d.msgbox("Error: "+format_part+" doesn't exist",width=60)

def pre():
	while 1:
		(code, tag) = d.menu(
	            "Pre-Installation tasks",
	            width=60,
	            choices=[("partition", "(c) Partition the hard disk"),
 	                     ("format",    "(c) Format a partition"),
 	                     ("continue",  "Continue to next stage ->")])
		if tag == "continue":
			break
		elif tag == "format":
			format_part = simple_menu("Choose a partition to format:",detected.getParts())
			if format_part != "":
					format_type = simple_menu("Choose a file system format to use:",filesystems_list)
					if format_type != "":
							response = d.yesno("Are you sure you want format "+format_part+" with "+format_type+"?\n  Data on "+format_part+" will be lost!",width=60)
							if response == 0 or response == 2:
								do_format(format_part,format_type)
								commands.getoutput("echo \"Formatted "+format_part+" with "+format_type+"\" >> "+log_file)
		elif tag == "partition":
			format_drive = simple_menu("Choose a drive to partition:",detected.getDrives())
			if format_drive != "":
					os.system("/sbin/cfdisk "+format_drive)
					commands.getoutput("echo \"partitioned "+format_drive+"\" >> "+log_file)
					detected.refresh()
					response = d.yesno("A reboot is suggested after modifying the partition table.\n  Reboot now?",width=60)
					if response == 0 or response == 2:
						os.execl("/sbin/reboot","reboot")
						return 1
		else:
			handle_exit();

######################################################################################################
# setup the partitions used for h3nix

def part(can_goback):
	global root_part, swap_part, boot_part
	while 1:
		(code, tag) = d.menu(
	            "Installation partition locations",
	            width=70,
	            choices=[("root", "(r) Where h3knix will be installed : "+root_part),
 	                     ("boot", "(o)  Storage for kernels/bootloader: "+boot_part),
			     		 ("swap", "(s) Swap partition                 : "+swap_part),
			     		 ("back", "<- Go back to previous stage"),
 	                     ("continue", "Continue to next stage ->")])
		if tag == "continue":
			if root_part == "":
				d.msgbox("Cannot continue, root partition required!",width=60)
			else:
				break
		elif tag == "back":
			if can_goback != "no":
				pre()
			else:
				d.msgbox("Cannot go back!",width=60)
		elif tag == "root":
			select_root()
		elif tag == "boot":
			select_boot()
		elif tag == "swap":
			select_swap()
		else:
			handle_exit();

######################################################################################################
# install the distro

def installpkg(pkg):
	pkg = pkg.strip()
	estat = commands.getstatusoutput("tar xjf "+cdrom_point+"/"+pkg+".cap -C "+mount_point+"/caps/")[0]
	if estat == 0:
		istat = commands.getstatusoutput("cd "+mount_point+"/caps/"+os.path.basename(pkg)+" && inpath="+mount_point+" sh main.sh")[0]
		if istat == 0:
			commands.getstatusoutput("rm -rf "+mount_point+"/caps/"+os.path.basename(pkg))
			commands.getoutput("echo \"Installed "+pkg+"\" >> "+log_file)
			return 0
		else:
			d.msgbox("Error:\nInstall "+pkg+" failed\nExit_Status=%i" % istat,width=60)
			return 1
	else:
		d.msgbox("Error:\nExtract "+pkg+" failed\nExit_Status=%i" % estat,width=60)
		return 1
	return 1

def do_custom(): # finish custom installer
	commands.getoutput("echo \"Started custom installer\" >> "+log_file)
	d.msgbox("Custom install type not supported yet",width=60)
	return 1

def do_dialup():
	total=pkg_dialup_size
	cur=0.00
	try:
		dialup_file=open(pkg_dialup,'r').readlines()
	except:
		return 1
	
	files=[dialup_file]
	commands.getoutput("echo \"Started dialup install\" >> "+log_file)
	d.gauge_start("Progress: 0% # dialup Install #", title="Installing h3knix")
	if os.path.isdir(mount_point+"/caps") == False:
		os.mkdir(mount_point+"/caps")
	for file in files:
		for pkg in file:
			d.gauge_update(round((cur/total)*100), ("Progress: %i%% # dialup Install #\n"+pkg) % round((cur/total)*100), update_text=1)
			if installpkg(pkg) != 0:
				d.gauge_stop()
				return 1
			cur+=1
	d.gauge_stop()
	if os.path.isdir(mount_point+"/caps"):
		commands.getoutput("rm -rf "+mount_point+"/caps")
	return 0
	
	
def do_minimal():
	total=pkg_core_size+pkg_base_size
	cur=0.00
	try:
		core_file=open(pkg_core,'r').readlines()
		base_file=open(pkg_base,'r').readlines()
	except:
		return 1
	
	files=[core_file,base_file]
	commands.getoutput("echo \"Started minimal install\" >> "+log_file)
	d.gauge_start("Progress: 0% # Minimal Install #", title="Installing h3knix")
	if os.path.isdir(mount_point+"/caps") == False:
		os.mkdir(mount_point+"/caps")
	for file in files:
		for pkg in file:
			d.gauge_update(round((cur/total)*100), ("Progress: %i%% # Minimal Install #\n"+pkg) % round((cur/total)*100), update_text=1)
			if installpkg(pkg) != 0:
				d.gauge_stop()
				return 1
			cur+=1
	d.gauge_stop()
	if os.path.isdir(mount_point+"/caps"):
		commands.getoutput("rm -rf "+mount_point+"/caps")
	return 0

def do_standard():
	total=pkg_core_size+pkg_base_size+pkg_ext_size+pkg_media_size
	cur=0.00
	try:
		core_file=open(pkg_core,'r').readlines()
		base_file=open(pkg_base,'r').readlines()
		ext_file=open(pkg_ext,'r').readlines()
		media_file=open(pkg_media,'r').readlines()
	except:
		d.msgbox("Error:\nCould not open list files",width=60)
		return 1
	
	files=[core_file,base_file,ext_file,media_file]
	
	commands.getoutput("echo \"Started standard install\" >> "+log_file)
	d.gauge_start("Progress: 0% # Standard Install #", title="Installing h3knix")
	if os.path.isdir(mount_point+"/caps") == False:
		os.mkdir(mount_point+"/caps")
	for file in files:
		for pkg in file:
			d.gauge_update(round((cur/total)*100), ("Progress: %i%% # Standard Install #\n"+pkg) % round((cur/total)*100), update_text=1)
			if installpkg(pkg) != 0:
				d.gauge_stop()
				return 1
			cur+=1
	d.gauge_stop()
	if os.path.isdir(mount_point+"/caps"):
		commands.getoutput("rm -rf "+mount_point+"/caps")
	return 0
	
def distro(can_goback):
	global install_type
	while 1:
		mount_parts()
		(code, tag) = d.menu(
	            "Installation type",
	            width=65,
	            choices=[("standard", "(s) Suggested packages for installation"),
 	                    ("minimal", "(o) Only the packages that are vital"),
			   		   #("custom", "(o) Choose every package for installation"),
			    	    ("back", "<- Go back to previous stage")])
		if tag == "minimal":
			install_type="minimal"
			if do_minimal() != 1:
				break
			else:
				d.msgbox("Error:\nMinimal Install failed",width=60)
		elif tag == "standard":
			install_type="standard"
			if do_standard() != 1:
				break
			else:
				d.msgbox("Error:\nStandard Install failed",width=60)
		elif tag == "custom":
			install_type="custom"
			if do_custom() != 1:
				break
			else:
				d.msgbox("Error:\nCustom Install failed",width=60)
		elif tag == "back":
			if can_goback != "no":
				part("yes")
			else:
				d.msgbox("Cannot go back!",width=60)
		else:
			handle_exit();

######################################################################################################
# kernel
def kernel():
	global kernel_type
	mount_parts()
	if os.path.isdir(mount_point+"/boot"):
		while 1:
			(code, tag) = d.menu(
		            "Pick a kernel",
		            width=65,
		            choices=[("hwd",     "(s) Use the hardware detection kernel ( 2.6.11.10-hwd )"),
		            	     ("generic", "(o) Use a generic kernel  ( 2.6.11.7 )"),
	 	                     ("custom",  "(o) Build a custom kernel ( 2.6.11.10 )")])
			if tag == "hwd":
				kernel_type="hwd"
				d.infobox("Installing hwd kernel ...",width=60)
				outstat=commands.getstatusoutput("cp "+cdrom_point+"/system/kernels/hwd "+mount_point+"/boot/h3knix-hwd")[0]
				if outstat == 0:
					commands.getoutput("mkdir -p "+mount_point+"/lib/modules/2.6.11.10-hwd")
					if os.path.isdir(mount_point+"/lib/modules/2.6.11.10-hwd"):
						if os.path.isdir("/lib/modules/2.6.11.10-hwd") == False:
							commands.getoutput("mount -o loop "+cdrom_point+"/system/modules.squashfs /lib/modules")
						outstat=commands.getstatusoutput("cp -Rd /lib/modules/2.6.11.10-hwd/* "+mount_point+"/lib/modules/2.6.11.10-hwd/")[0]
						commands.getoutput("/sbin/splash -s -f /etc/bootsplash/themes/h3knix/config/bootsplash-1024x768.cfg >> "+mount_point+"/boot/initrd.splash")
					else:
						outstat=1
			elif tag == "generic":
				kernel_type="generic"
				d.infobox("Installing generic kernel ...",width=60)
				outstat=commands.getstatusoutput("cp "+cdrom_point+"/system/kernels/generic "+mount_point+"/boot/h3knix-generic")[0]
				commands.getoutput("mkdir -p "+mount_point+"/lib/modules/2.6.11.7 && touch "+mount_point+"/lib/modules/2.6.11.7/modules.dep")
			elif tag == "custom":
				kernel_type="custom"
				outstat=1
				if os.path.exists(mount_point+"/usr/src/linux-"+custom_ver+".tar.bz2") and os.path.isdir(mount_point+"/usr/src/linux-"+custom_ver) == False:
					d.infobox("Extracting kernel source...",width=60)
					commands.getstatusoutput("tar xjf "+mount_point+"/usr/src/linux-"+custom_ver+".tar.bz2 -C "+mount_point+"/usr/src/")
				if os.path.isdir(mount_point+"/usr/src/linux-"+custom_ver):
					d.infobox("Starting configuration for custom kernel...",width=60)
					commands.getoutput("mkdir -p "+mount_point+"/lib/modules/"+custom_ver+" && touch "+mount_point+"/lib/modules/"+custom_ver+"/modules.dep")
					configstat = os.system("chroot "+mount_point+" /bin/bash -c \"cd /usr/src/linux-"+custom_ver+" && make menuconfig\"")
					if configstat == 0:
						buildstat = os.system("chroot "+mount_point+" /bin/bash -c \"cd /usr/src/linux-"+custom_ver+" && make && make modules_install\"")
						os.system("cp "+mount_point+"/usr/src/linux-"+custom_ver+"/arch/i386/boot/bzImage "+mount_point+"/boot/h3knix-custom")
						outstat=0
					else:
						d.msgbox("Error:\nmake menuconfig failed\nCannot build kernel!",width=70)
				else:
					d.msgbox("Error:\nCannot find folder "+mount_point+"/usr/src/linux-"+custom_ver+"\nCannot build kernel!",width=70)
			else:
				handle_exit()

			if outstat != 0:
				d.msgbox("Error:\nKernel install failed!",width=70)
			else:
				break
	else:
		d.msgbox("Error:\nCannot find folder "+mount_point+"/boot\nCannot install kernel!",width=70)
		
######################################################################################################
# rc configuration


def writerc():
	global rc_clock,rc_timezone,rc_timezone,rc_consolefont,rc_keymap,rc_hostname,rc_body,rc_numlock_header,rc_numlock,rc_network_header,rc_network_type,rc_network_type_abstract,rc_ip_header,rc_network_info
	mount_parts()
	try:
		rcfile=open(mount_point+"/etc/rc.conf",'w')
		hosts=open(mount_point+"/etc/hosts",'w')
	except:
		d.msgbox("Error:\nCannot open "+mount_point+"/etc/rc.conf\nCannot configure rc!",width=70)
		return 1
	
	d.infobox("Writing rc.conf..",width=60)
	rcfile.write("HARDWARECLOCK="+rc_clock+"\n")
	rcfile.write("TIMEZONE="+rc_timezone+"\n")
	rcfile.write("KEYMAP="+rc_keymap+"\n")
	rcfile.write("CONSOLEFONT="+"\n")
	rcfile.write("USECOLOR=\"yes\""+"\n")
	rcfile.write("\nHOSTNAME="+rc_hostname+"\n")
	rcfile.write(rc_body+"\n")
	rcfile.write(rc_numlock_header+"\n")
	rcfile.write("NUM="+rc_numlock+"\n")
	rcfile.write(rc_network_header+"\n")
	rcfile.write("NET=\""+rc_network_type+"\"\n"+"\n")
	rcfile.write(rc_ip_header+"\n")
	rcfile.write("ipaddress="+rc_network_info[0]+"\n")
	rcfile.write("gateway="+rc_network_info[1]+"\n")
	rcfile.write("broadcast="+rc_network_info[2]+"\n")
	rcfile.write("netmask="+rc_network_info[3]+"\n")
	hosts.write("127.0.0.1 localhost "+rc_hostname+"\n")
	hosts.close()
	rcfile.close()
	d.msgbox("rc.conf generation complete",width=70)

def network():
	global rc_network_header,rc_network_type,rc_network_type_abstract,rc_ip_header,rc_network_info
	while 1:
		(code, tag) = d.menu(
			"Configure Network | current="+rc_network_type_abstract,
			width=65,
			choices=[("dynamic",  "Setup network with dhcp"),
		    		 ("static",   "Setup network address and information manually"),
	 	    		 ("dialup",   "Install dialup packages"),
	 	    		 ("finished", "Done with networking")])
		if tag == "dynamic":
			rc_network_type="dhcp"
			rc_network_type_abstract="dynamic"
		elif tag == "static":
			rc_network_type="static"
			rc_network_type_abstract="static"
			(code, ipanswer) = d.inputbox("Specify ip address", init=rc_network_info[0])
			if ipanswer != "":
				rc_network_info[0] = ipanswer
			(code, ganswer) = d.inputbox("Specify gateway", init=rc_network_info[1])
			if ganswer != "":
				rc_network_info[1] = ganswer
			(code, banswer) = d.inputbox("Specify broadcast", init=rc_network_info[2])
			if banswer != "":
				rc_network_info[2] = banswer
			(code, nanswer) = d.inputbox("Specify netmask", init=rc_network_info[3])
			if nanswer != "":
				rc_network_info[3] = nanswer
		elif tag == "dialup":
			response = d.yesno("Dialup packages will now be installed, continue?",width=60)
			if response == 0 or response == 2:
				do_dialup()
				rc_network_type="none"
				rc_network_type_abstract="dialup"
		elif tag == "finished":
			break
		else:
			handle_exit()
		
def rc():
	global rc_clock,rc_timezone,rc_timezone,rc_consolefont,rc_keymap,rc_hostname,rc_body,rc_numlock_header,rc_numlock,rc_network_header,rc_network_type,rc_network_type_abstract,rc_ip_header,rc_network_info
	while 1:
		(code, tag) = d.menu(
			"Configure init scripts",
			width=65,
			choices=[#("time",     "Configure time zone and hardware clock"),
		    		 ("hostname", "Setup hostname                 : "+rc_hostname),
	 	    		 ("numlock",  "Configure numlock state on boot: "+rc_numlock),
	 	    		 ("network",  "Configure network              : "+rc_network_type_abstract),
	 	    		 ("finished", "Done with rc.conf ( writes rc.conf )")])
		#if tag == "time":
		#	d.msgbox("Error:\nnot supported yet!",width=70)
		if tag == "hostname":
			(code, answer) = d.inputbox("Specify new hostname", init=rc_hostname)
			if answer != "":
				rc_hostname = answer
		elif tag == "numlock":
			response = d.yesno("Do you want numlock to be turned on during bootup?",width=60)
			if response == 0 or response == 2:
				rc_numlock="on"
			else:
				rc_numlock="off"
		elif tag == "network":
			network()
		elif tag == "finished":
			writerc()
			break
		else:
			handle_exit()
				
######################################################################################################
# grub functions


# returns an entry for menu.lst, 
# requires the title, a kernel and kernel arguments, and if needed an extra path for grub
def build_entry(title,ktype,kargs,extra): 
	global grub_vars
	return """
title="""+title+"""
"""+grub_vars['root']+"""
kernel /"""+extra+"""h3knix-"""+ktype+""" ro root="""+root_part+""" """+kargs+"""
"""

# if the menu.lst file exists
# this funciton will ask the user what he wants to do with it
def backup_menu():
	menuname=mount_point+"/boot/grub/menu.lst"
	if os.path.exists(menuname):
		while 1:
			(code, tag) = d.menu(
				"Old grub config file found, what do you want to do with it?",
				width=65,
				choices=[("backup", "Backup the old config"),
		 	    		 ("append", "Add to the old config"),
		 	    		 ("overwrite",  "Overwrite the old config")])
			if tag == "backup":
				counter=0
				while os.path.exists(menuname+str(counter)):
					counter+=1
				if os.path.exists(menuname+str(counter)) == False:
					outstat=commands.getstatusoutput("mv "+menuname+" "+menuname+str(counter))[0]
					if outstat != 0:
						d.msgbox("Error, cannot create backup file for "+menuname,width=60)
						return "none","none"
					d.msgbox("Backed up "+menuname+" to "+menuname+str(counter),width=60)
					return menuname,"write"
				else:
					d.msgbox("Error, cannot create backup file for "+menuname,width=60)
					return "none","none"
			elif tag == "append":
				return menuname,"append"
			elif tag == "overwrite":
				return menuname,"write"
			else:
				handle_exit()		
	else:
		return menuname,"write"

# configure grub
# if ktype is specified as all, all the kernel_types found in boot folder
# will be added to the grub config file		
def grubconfig(ktype):
	if grub_vars['root'] == "":
		if initgrub() == 1:
			return 1
	if boot_part != "":
		part=boot_part
		extra=""
	else:
		part = root_part
		extra="boot/"
		
	menuheader = """
default 0
timeout 5
"""
	d.infobox("Generating menu.lst",width=70)
	menuname,menumode = backup_menu()
	if menuname != "none":
		if menumode == "write":
			menulst=open(menuname,'w')
			menulst.write(menuheader)
		else:
			menulst=open(menuname,'a')
		if ktype != "all":
			menulst.write(build_entry("h3knix",ktype,kernel_types[ktype][0],extra))
			menulst.write(build_entry("h3knix-nofb",ktype,kernel_types[ktype][1],extra))
		else:
			for ktype in kernel_types:
				if os.path.exists(mount_point+"/boot/h3knix-"+ktype):
					menulst.write(build_entry("h3knix_"+ktype,ktype,kernel_types[ktype][0],extra))
					menulst.write(build_entry("h3knix_"+ktype+"-nofb",ktype,kernel_types[ktype][1],extra))
		menulst.close()
		d.msgbox("grub configured, menu.lst was generated.",width=70)
	
# initialize grub install values
def initgrub():
	global grub_vars,kernel_types,initrd
	if os.path.isdir(mount_point+"/boot") == False:
		d.msgbox("Error:\nCannot find "+mount_point+"/boot!\nCannot install grub",width=70)
		return 1
	if os.path.exists(mount_point+"/usr/sbin/grub") == False:
		d.msgbox("Error:\nCannot find "+mount_point+"/sbin/grub!\nCannot install grub",width=70)
		return 1
	if os.path.isdir("/usr/lib/grub/i386-pc"):
		if boot_part != "":
			part=boot_part
			extra=""
			kernel_types['hwd'][0] = kernel_types['hwd'][0]+"\ninitrd="+initrd
		else:
			part = root_part
			extra="/boot"
			initrd="initrd=/boot"+initrd
			kernel_types['hwd'][0] = kernel_types['hwd'][0]+"\n"+initrd
		p = re.compile('\d|/dev/hd|/dev/sd')
		bootletter=p.sub("",part)
		bdic={'a':'hd0','b':'hd1','c':'hd2','d':'hd3','e':'hd4','f':'hd5','g':'hd6','h':'hd7','i':'hd8','j':'hd9','k':'hd10'}
		p = re.compile('[a-z]|[A-Z]|/dev/')
		partnum = "%i" % (int(p.sub("",part)) -1)
		grub_vars['root']="root ("+bdic[bootletter]+","+partnum+")"
		grub_vars['setup']="setup ("+bdic[bootletter]+")"
		if os.path.isdir(mount_point+"/boot/grub") == False:
			os.mkdir(mount_point+"/boot/grub")
		cpstat=commands.getstatusoutput("cp /usr/lib/grub/i386-pc/* "+mount_point+"/boot/grub/")[0]
		if cpstat != 0:
			d.msgbox("Error:\nCopying grub stage files failed!\nCannot install grub",width=70)
			return 1
		return 0
	else:
		d.msgbox("Error:\nCannot find /usr/lib/grub/i386-pc!\nCannot install grub",width=70)
		return 1

# menu for installing grub	
def grub():
	mount_parts()
	global grub_vars
	if grub_vars['root'] == "":
		if initgrub() == 1:
			return 1
	while 1:
		(code, tag) = d.menu(
			 "Grub paramaters ( *may require adjustment )",
		     width=70,
		     choices=[("grub_root",  "Partition containing grub files: "+grub_vars['root']),
	 	              ("grub_mbr",   "MBR grub should be installed on: "+grub_vars['setup']),
	 	              ("install",   " > Install grub now <"),
	 	              ("back",      "<- back")])
		if tag == "grub_root":
			(code, answer) = d.inputbox("Specify new grub root command", init=grub_vars['root'])
			if answer != "":
				grub_vars['root'] = answer
		elif tag == "grub_mbr":	
			(code, answer) = d.inputbox("Specify new grub setup command", init=grub_vars['setup'])
			if answer != "":
				grub_vars['setup'] = answer
		elif tag == "install":
			os.system("echo \""+grub_vars['root']+"\n"+grub_vars['setup']+"\nquit\" | /usr/sbin/grub --batch; read -p \"Press enter to continue...\" one")
		else:
			break

def bootloader(ktype):
	while 1:
		(code, tag) = d.menu(
			 "Choose an operation",
		     width=70,
		     choices=[("grub",  "(c) Install grub ( overwites existing bootloader )"),
		       	      ("grubconfig", "(c) Configure grub"),
	 	              ("continue",  "-> Continue")])
		if tag == "grub":
			grub()
		elif tag == "grubconfig":	
			grubconfig(ktype)
		elif tag == "continue":
			break
		else:
			handle_exit()

######################################################################################################
# post configuration

def genfstab():
	mount_parts()
	try:
		d.infobox("Generating fstab...",width=60)
		fstab = open(fstab_file,'w')
		fstab.write(fstab_head)
		fstab.write("\n#rootfs\n")
		fstab.write(root_part+"\t/\t"+commands.getoutput("df -T | grep "+mount_point+"$").split()[1].strip()+"\tdefaults\t0    0\n")
		if swap_part == "":
			swapchar="#"
		else:
			swapchar=""
		fstab.write("\n#swap partition\n")
		fstab.write(swapchar+swap_part+"\tswap\tswap\tpri=1\t0    0\n")
		fstab.write(fstab_tail)
		commands.getoutput("echo \"Generated fstab\" >> "+log_file)
	except:
		d.msgbox("Error:\nCannot open fstab for writing!\n"+mount_point+"/etc/fstab",width=70)

	
def post():
	genfstab()
	response = d.yesno("Do you want to configure a bootloader?\n Only grub bootloader supported... for now",width=60)
	if response == 0 or response == 2:
		bootloader(kernel_type)
		commands.getoutput("echo \"Configured bootloader\" >> "+log_file)
	rc()

######################################################################################################
# debuggin functions
def printout():
	print ""
	print "## Summary ##"
	print "InstallationType: "+install_type
	print "      KernelType: "+kernel_type
	print "   rootPartition: "+root_part
	print "   bootPartition: "+boot_part
	print "   swapPartition: "+swap_part
	if log_file != "/dev/null":
		print "log file generated at "+log_file
	print ""
	commands.getoutput("echo \"\" >> "+log_file)
	commands.getoutput("echo \"## Summary ##\" >> "+log_file)
	commands.getoutput("echo \"InstallationType: "+install_type+"\" >> "+log_file)
	commands.getoutput("echo \"      KernelType: "+kernel_type+"\" >> "+log_file)
	commands.getoutput("echo \"   rootPartition: "+root_part+"\" >> "+log_file)
	commands.getoutput("echo \"   bootPartition: "+boot_part+"\" >> "+log_file)
	commands.getoutput("echo \"   swapPartition: "+swap_part+"\" >> "+log_file)
	
	
######################################################################################################
# help	
	
def help(arg):
	print """
 h3knix installer """+iversion+""" help:

 > Pre installation Tasks:
	 
  --partition
 	Setup partitions

 > Installation Tasks:
  
  --distro
  	Install packages
  		Note: this will not run the full installer
  		        only the package installation!
  		 	  To run the full installer, 
  		        execute setup without any arguments.
 
 > Post installation Tasks:
 
  --kernel
 	Setup a kernel for h3knix
 	
  --bootloader
 	Setup a bootloader for h3knix
 	
  --fstab
 	Setup fstab for h3knix
 	
  --rc
  	Setup rc.conf for h3knix
"""

######################################################################################################
# functions for command line arguments

def cmd_partition(arg):
	pre()

def cmd_distro(arg):
	if root_part == "":
		part("no")
	mount_parts()
	distro("no")
	
def cmd_kernel(arg):
	if root_part == "":
		part("no")
	mount_parts()
	kernel()
	
def cmd_fstab(arg):
	if root_part == "":
		part("no")
	mount_parts()
	genfstab()
	
def cmd_bootloader(arg):
	if root_part == "":
		part("no")
	mount_parts()
	bootloader("all")
	
def cmd_rc(arg):
	if root_part == "":
		part("no")
	mount_parts()
	rc()
		
######################################################################################################
# run the installation, in the correct order

def cmd_version(arg):
	print "\nh3knix installer "+iversion+"\n"

detected = detect()

try:
	
	options= { '-h':help, '-v':cmd_version , '--kernel':cmd_kernel, "--bootloader":cmd_bootloader , "--fstab":cmd_fstab , "--partition":cmd_partition , "--distro":cmd_distro , "--rc":cmd_rc }
	try:
		# try to parse command line arguments
		opts, args = getopt.getopt(sys.argv[1:], "vh",[ "bootloader","kernel","fstab", "partition", "distro", "rc" ])
	except getopt.GetoptError:
		print "\n\tInvalid argument -- see help \"-h\"\n"
		sys.exit(1)
		
	if len(opts) == 0:
		pre()
		part("yes")
		distro("yes")
		kernel()
		post()
		d.msgbox("h3knix installation complete!",width=70)
		print "Cleaning dirs..."
		if os.path.isdir(mount_point+"/caps"):
			commands.getoutput("rm -rf "+mount_point+"/caps")
	
	for opt, arg in opts:
		if options.has_key (opt):
			options [opt](arg)
		else:
			print "\nInvalid option: " + opt
			print "see help \"-h\"\n"
			sys.exit (1)
	
	if len(opts) > 0:
		sys.exit(0)	
	
except KeyboardInterrupt:
	print ""
	print "Keyboard interrupt caught, exiting"
	print ""
	sys.exit(1)

######################################################################################################
# debugging
printout()

