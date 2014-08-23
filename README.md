netcam_fix
==========

Reads a (M)JPEG stream from a buggy network camera, fixes it, and streams it itself

How to use this script
----------------------

1. Download this script
2. Make the file exacutable (chmod a+x netcam_fix.py)
3. Run the script with ./netcam_fix.py --help to see the argument list

Example
-------

* sudo ./netcam_fix.py --nodaemon http://192.168.1.1/cgi/mjpg/mjpeg.cgi

netcam_fix connects to the webcam at 192.168.1.1 and listens for incoming
connections at localhost on port 8000. Will write log in /var/log/netcam_fix
and drop root privileges 
You can connect to it with motion using the following configuration directive

* netcam_url http://localhost:8000/

When you have tested that the script is working, you can then start it without
the --nodaemon option to have it daemonize and run in background
