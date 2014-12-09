import argparse
import logging
import signal
import socket
import SocketServer
import threading

log = logging.getLogger(__name__)

# defaults
EAST_PORT=2102
EAST_HOST=""

WEST_PORT=2101
WEST_HOST="localhost"

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
		log.info("[out] connect %s:%d" % self.client_address)

		in_sockets = self.server.m.in_sockets
		out_sockets = self.server.m.out_sockets

		out_sockets.add(conn)

		for cmd in iterlines(conn):
			log.debug("[out] cmd=%r" % (cmd,))

			cmd = cmd.strip()
			if cmd == '?ping':
				self.server.m.out_sockets.sendall_one(conn, 'ok\n')
			elif cmd == '?nin':
				self.server.m.out_sockets.sendall_one(conn, '%d\n' % (in_sockets.num(),))
			elif cmd == '?nout':
				self.server.m.out_sockets.sendall_one(conn, '%d\n' % (out_sockets.num(),))
			else:
				self.server.m.in_sockets.sendall(cmd+'\n')

		log.info("[out] disconnect %s:%d" % self.client_address)

		out_sockets.remove(conn)

class TCPInHandler(SocketServer.BaseRequestHandler):
	def handle(self):
		self.reader(self.request)

	def reader(self, conn):
		log.info("[inp] connect %s:%d" % self.client_address)

		self.server.m.in_sockets.add(conn)

		while True:
			resp = conn.recv(1024)
			if not resp:
				break

			log.debug("[inp] recv=%r" % (resp,))

			self.server.m.out_sockets.sendall(resp)

		log.info("[inp] disconnect %s:%d" % self.client_address)

		self.server.m.in_sockets.remove(conn)

class TcpMultiplex(object):

	def __init__(self, in_port=2102, out_port=2101, in_host='', out_host='localhost'):
		self.in_port = in_port
		self.out_port = out_port

		self.in_host = in_host
		self.out_host = out_host

		self.out_sockets = MultiSocket()
		self.in_sockets = MultiSocket()

		self.is_running = threading.Lock()
		self.is_running.acquire()

	def run(self, poll_interval=.5):
		log.info("Listening on: inp=%s:%d out=%s:%d" % (self.in_host, self.in_port, self.out_host, self.out_port))
		self.in_server = ThreadingTCPServer((self.in_host, self.in_port), TCPInHandler)
		self.in_server.m = self
		self.out_server = ThreadingTCPServer((self.out_host, self.out_port), TCPOutHandler)
		self.out_server.m = self

		self.in_thread = threading.Thread(target=self.in_server.serve_forever, args=(poll_interval,))
		self.out_thread = threading.Thread(target=self.out_server.serve_forever, args=(poll_interval,))

		self.in_thread.start()
		self.out_thread.start()

		self.is_running.release()

		# allow for signal processing
		while True:
			self.in_thread.join(.2)
			if not self.in_thread.isAlive():
				break

		self.out_thread.join()

		log.info("Stopping")

		self.in_server.server_close()
		self.out_server.server_close()

	def stop(self):
		self.in_server.shutdown()
		self.out_server.shutdown()

def main():
	parser = argparse.ArgumentParser(description="multiplex a TCP connection to multiple clients.")

	parser.add_argument('--east-port', metavar='PORT', type=int, default=EAST_PORT, dest='east_port',
			help="port to listen on for connection from a device")
	parser.add_argument('--east-if', metavar='ADDR', default=EAST_HOST, dest='east_host',
			help="interface to listen on for connection from a device")

	parser.add_argument('--west-port', metavar='PORT', type=int, default=WEST_PORT, dest='west_port',
			help="port to listen on for connection from clients")
	parser.add_argument('--west-if', metavar='ADDR', default=WEST_HOST, dest='west_host',
			help="interface to listen on for connection from clients")

	args = parser.parse_args()

	logging.basicConfig(level=logging.INFO)

	m = TcpMultiplex(in_port=args.east_port, in_host=args.east_host,
			out_port=args.west_port, out_host=args.west_host)

	def handler(signum, frame):
		log.warning("Signal %d caught! Stopping scan..." % (signum,))
		m.stop()

	signal.signal(signal.SIGTERM, handler)
	signal.signal(signal.SIGINT, handler)

	m.run()

if __name__ == "__main__":
	main()
