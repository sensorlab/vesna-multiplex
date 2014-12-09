import socket
import SocketServer
import threading

class ThreadingTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
	#allow_reuse_address = True
	pass

class TCPOutHandler(SocketServer.BaseRequestHandler):
	def handle(self):
		self.reader(self.request)

	def reader(self, conn):
		print "reader"
		conn.settimeout(1.)
		buff = ""
		while True:
			try:
				resp = conn.recv(1024)
			except socket.timeout:
				continue

			if not resp:
				break

			buff += resp

			print repr(buff)

			if '\n' in buff:
				cmds = buff.split('\n')

				for cmd in cmds[:-1]:
					cmd = cmd.strip()
					if cmd == '?ping':
						conn.send('ok\n')

				buff = cmds[-1]

class TCPInHandler(SocketServer.BaseRequestHandler):
	def handle(self):
		pass

class TcpMultiplex(object):

	def __init__(self):
		pass

	def run(self):
		print "start"
		port = 2101
		#ThreadingTCPServer.allow_reuse_address = True
		self.in_server = ThreadingTCPServer(("", 2102), TCPInHandler)
		self.out_server = ThreadingTCPServer(("", port), TCPOutHandler)

		self.in_thread = threading.Thread(target=self.in_server.serve_forever)
		self.out_thread = threading.Thread(target=self.out_server.serve_forever)

		self.in_thread.start()
		self.out_thread.start()

		self.in_thread.join()
		self.out_thread.join()

		self.in_server.server_close()
		self.out_server.server_close()
		print "exit"

	def stop(self):
		self.in_server.shutdown()
		self.out_server.shutdown()
