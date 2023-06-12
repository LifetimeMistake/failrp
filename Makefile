INPUT_FS=base.squashfs
FS_ROOT=unpacked_squashfs
OUTPUT_FS=build.squashfs

all: clean unpack setup build clean
unpack:
	# Unpack base image
	echo "Unpacking base image"
	unsquashfs -d "$(FS_ROOT)" "$(INPUT_FS)"

setup:
	apt update && apt install -y wine wine64
	# Copy files
	mkdir "$(FS_ROOT)/app"
	cp -r libs "$(FS_ROOT)/app/libs"
	cp requirements.txt "$(FS_ROOT)/app"
	cp bootstrap-requirements.txt "$(FS_ROOT)/app"
	cp install.sh "$(FS_ROOT)/app"
	cp init.sh "$(FS_ROOT)/app"
	cp app.py "$(FS_ROOT)/app"
	cp banner.py "$(FS_ROOT)/app"
	cp bootstrap.py "$(FS_ROOT)/app"
	cp start-failrp.service "$(FS_ROOT)/etc/systemd/system/"

	# Install service
	chroot "$(FS_ROOT)" /bin/bash /app/install.sh

	# Clean installation files
	rm "$(FS_ROOT)/app/requirements.txt"
	rm "$(FS_ROOT)/app/bootstrap-requirements.txt"
	rm "$(FS_ROOT)/app/install.sh"

build:
	echo "Building squashfs..."
	mksquashfs "$(FS_ROOT)" "$(OUTPUT_FS)" -noappend -always-use-fragments -comp xz -Xbcj x86
	rm -r "$(FS_ROOT)"
	echo "OK - All done!"

clean:
	$(RM) -r "$(FS_ROOT)"
