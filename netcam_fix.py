#!/usr/bin/env python3

import sys, os, pwd, grp, time, atexit, signal

import urllib.request
import base64

import http.server

import argparse

'''
Reads MJPEG steam from a buggy netcam, fixes it and streams it itself

@author Gabriele Tozzi <gabriele@tozzi.eu>
@license GPLv2
'''

# JPEG magics
MAGIC_START = b'\xff\xd8'
MAGIC_END = b'\xff\xd9'

# HTTPD Settings
DEF_PORT = 8000
BOUNDARY = '--netcam_fix_boundary'


class Daemon:
	"""A generic daemon class.
	
	Usage: subclass the daemon class and override the run() method.
	
	@autor Anonymous <http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/>
	"""

	def __init__(self, logfile=os.devnull):
		self.logfile = logfile
	
	def daemonize(self):
		"""Deamonize class. UNIX double fork mechanism."""

		try: 
			pid = os.fork()
			if pid > 0:
				# exit first parent
				sys.exit(0)
		except OSError as err:
			sys.stderr.write('fork #1 failed: {0}\n'.format(err))
			sys.exit(1)
	
		# decouple from parent environment
		os.chdir('/')
		os.setsid()
		os.umask(0)
	
		# do second fork
		try:
			pid = os.fork()
			if pid > 0:

				# exit from second parent
				sys.exit(0)
		except OSError as err:
			sys.stderr.write('fork #2 failed: {0}\n'.format(err))
			sys.exit(1)
	
		# redirect standard file descriptors
		sys.stdout.flush()
		sys.stderr.flush()
		try:
			si = open(os.devnull, 'r')
			so = open(self.logfile, 'a+')
			se = open(self.logfile, 'a+')
		except PermissionError as err:
			sys.stderr.write('Permission denied opening logfile {}\n'.format(self.logfile))
			sys.exit(1)

		os.dup2(si.fileno(), sys.stdin.fileno())
		os.dup2(so.fileno(), sys.stdout.fileno())
		os.dup2(se.fileno(), sys.stderr.fileno())
		
		# drop root privileges
		if os.getuid() == 0:
			nobody_uid = pwd.getpwnam('nobody').pw_uid
			nobody_gid = grp.getgrnam('nogroup').gr_gid
			
			# Remove group privileges
			os.setgroups([])
			
			# Try setting the new uid/gid
			os.setgid(nobody_uid)
			os.setuid(nobody_gid)

	def start(self):
		"""Start the daemon."""
		
		self.daemonize()
		self.run()

	def run(self):
		"""You should override this method when you subclass Daemon.
		
		It will be called after the process has been daemonized by
		start() or restart()."""


class mJpegHandler(http.server.BaseHTTPRequestHandler):
	''' Serves the MJPEG stream to ANY request '''
	
	# Injected at runtime
	pwdstring = None
	camera_url = None
	
	def do_GET(self):
		''' GET handler '''
		self.send_response(200)
		self.send_header('Content-type','multipart/x-mixed-replace;boundary=%s' % BOUNDARY)
		self.end_headers()
		
		# Open the parent stream
		req = urllib.request.Request(self.camera_url)
		if self.pwdstring:
			pwdstring = (self.pwdstring).encode('ascii')
			base64string = base64.encodestring(pwdstring).replace(b'\n', b'')
			req.add_header("Authorization", "Basic %s" % base64string.decode('ascii'))
		stream = urllib.request.urlopen(req, timeout=30)
		
		# Read images and stream them back
		buffer = b''
		i = 0
		lene = len(MAGIC_END)
		while True:
			buffer += stream.read(1024)
			a = buffer.find(MAGIC_START)
			b = buffer.find(MAGIC_END)
			if a != -1 and b != -1:
				# JPEG found
				i += 1
				pre = buffer[:a] # Header data, will be dropped
				jpg = buffer[a:b+lene] # JPEG data
				buffer = buffer[b+lene:]
				
				# Buggy stream fix: strip double end buffer
				if buffer.startswith(MAGIC_END):
					buffer = buffer[lene:]
				
				# DEBUG: Save data to files
				#with open('/tmp/mjpeg_%d.pre' % i, 'wb') as out:
					#out.write(pre)
				#with open('/tmp/mjpeg_%d.jpg' % i, 'wb') as out:
					#out.write(jpg)
				
				out = BOUNDARY.encode('ascii') + b"\r\n"
				out += b"Content-Length: " + str(len(jpg)).encode('ascii') + b"\r\n"
				out += b"\r\n" + jpg
		
				self.wfile.write(out)
		
		return


class Main(Daemon):
	''' Main script class '''
	
	def __init__(self, logfile, url, user=None, pwd=None, port=DEF_PORT):
		super().__init__(logfile)
		self.url = url
		if user or pwd:
			if user is None:
				user = ''
			if pwd is None:
				pwd = ''
			self.credentials = "%s:%s" % (user,pwd)
		else:
			self.credentials = None
		self.port = port
	
	def run(self):
		mJpegHandler.camera_url = self.url
		mJpegHandler.pwdstring = self.credentials
		httpd = http.server.HTTPServer(('127.0.0.1', self.port), mJpegHandler)
		print("Serving at port", self.port)
		httpd.serve_forever()


if __name__ == '__main__':
	parser = argparse.ArgumentParser(
		description = 'Reads MJPEG steam from a buggy netcam, fixes it and streams it itself',
		formatter_class = argparse.ArgumentDefaultsHelpFormatter
	)
	parser.add_argument('netcam_url', help='URL to access the network camera')
	parser.add_argument("-u", "--user", help='network camera username')
	parser.add_argument("-p", "--pass", help='network camera password', dest='pwd')
	parser.add_argument("-P", "--port", type=int, help='the port to listen to', default=DEF_PORT)
	parser.add_argument("--nodaemon", help='don\'t daemonize', action="store_true")
	parser.add_argument("--logfile", help='Log file in daemon mode', default='/var/log/netcam_fix')
	args = parser.parse_args()
	
	main = Main(args.logfile, args.netcam_url, args.user, args.pwd, args.port)
	if args.nodaemon:
		main.run()
	else:
		main.start()
