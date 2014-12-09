import socket
import SocketServer
import threading

class ThreadingTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
	allow_reuse_address = True

class MultiSocket(object):
	def __init__(self):
		self.sockets = {}
		self.lock = threading.Lock()

	def num(self):
		return len(self.sockets)

	def add(self, socket):
		fd = socket.fileno()
		assert fd not in self.sockets
		self.sockets[fd] = socket

	def remove(self, socket):
		fd = socket.fileno()
		del self.sockets[fd]

	def sendall_one(self, s, string):
		self.lock.acquire()
		s.sendall(string)
		self.lock.release()

	def sendall(self, string):
		self.lock.acquire()
		for s in self.sockets.itervalues():
			try:
				s.sendall(string)
			except socket.error:
				pass
		self.lock.release()

def iterlines(s):
	rest = ""
	while True:
		resp = s.recv(1024)
		if not resp:
			return

		lines = (rest+resp).split('\n')
		for line in lines[:-1]:
			yield line

		rest = lines[-1]

class TCPOutHandler(SocketServer.BaseRequestHandler):
	def handle(self):
		self.reader(self.request)

	def reader(self, conn):
		print "reader"

		in_sockets = self.server.m.in_sockets
		out_sockets = self.server.m.out_sockets

		out_sockets.add(conn)

		for cmd in iterlines(conn):
			cmd = cmd.strip()
			if cmd == '?ping':
				self.server.m.out_sockets.sendall_one(conn, 'ok\n')
			elif cmd == '?nin':
				self.server.m.out_sockets.sendall_one(conn, '%d\n' % (in_sockets.num(),))
			elif cmd == '?nout':
				self.server.m.out_sockets.sendall_one(conn, '%d\n' % (out_sockets.num(),))
			else:
				self.server.m.in_sockets.sendall(cmd+'\n')

		out_sockets.remove(conn)

class TCPInHandler(SocketServer.BaseRequestHandler):
	def handle(self):
		self.reader(self.request)

	def reader(self, conn):
		self.server.m.in_sockets.add(conn)

		while True:
			resp = conn.recv(1024)
			if not resp:
				break

			print resp

			self.server.m.out_sockets.sendall(resp)

		self.server.m.in_sockets.remove(conn)

class TcpMultiplex(object):

	def __init__(self):
		self.out_sockets = MultiSocket()
		self.in_sockets = MultiSocket()

		self.is_running = threading.Lock()
		self.is_running.acquire()

	def run(self, poll_interval=.5):
		print "start"
		port = 2101
		#ThreadingTCPServer.allow_reuse_address = True
		self.in_server = ThreadingTCPServer(("", 2102), TCPInHandler)
		self.in_server.m = self
		self.out_server = ThreadingTCPServer(("", port), TCPOutHandler)
		self.out_server.m = self

		self.in_thread = threading.Thread(target=self.in_server.serve_forever, args=(poll_interval,))
		self.out_thread = threading.Thread(target=self.out_server.serve_forever, args=(poll_interval,))

		self.in_thread.start()
		self.out_thread.start()

		self.is_running.release()

		self.in_thread.join()
		self.out_thread.join()

		self.in_server.server_close()
		self.out_server.server_close()
		print "exit"

	def stop(self):
		self.in_server.shutdown()
		self.out_server.shutdown()
