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
		log.info("[west] connect %s:%d" % self.client_address)

		east_sockets = self.server.m.east_sockets
		west_sockets = self.server.m.west_sockets

		west_sockets.add(conn)

		for cmd in iterlines(conn):
			log.debug("[west] cmd=%r" % (cmd,))

			if cmd.startswith('?'):
				resp = self.command(cmd.strip())
				log.debug("[west] resp=%r" % (resp,))
				west_sockets.sendall_one(conn, resp)
			else:
				east_sockets.sendall(cmd+'\n')

		log.info("[out] disconnect %s:%d" % self.client_address)

		west_sockets.remove(conn)

	def command(self, cmd):
		east_sockets = self.server.m.east_sockets
		west_sockets = self.server.m.west_sockets

		if cmd == '?ping':
			return 'ok\n'
		elif cmd == '?count east':
			return '%d\nok\n' % (east_sockets.num(),)
		elif cmd == '?count west':
			return '%d\nok\n' % (west_sockets.num(),)
		else:
			return 'error: unknown multiplexer command %r' % (cmd,)

class TCPInHandler(SocketServer.BaseRequestHandler):
	def handle(self):
		self.reader(self.request)

	def reader(self, conn):
		log.info("[east] connect %s:%d" % self.client_address)

		self.server.m.east_sockets.add(conn)

		while True:
			resp = conn.recv(1024)
			if not resp:
				break

			log.debug("[east] recv=%r" % (resp,))

			self.server.m.west_sockets.sendall(resp)

		log.info("[east] disconnect %s:%d" % self.client_address)

		self.server.m.east_sockets.remove(conn)

class VESNAMultiplex(object):

	def __init__(self, east_port=2102, west_port=2101, east_host='', west_host='localhost'):
		self.east_port = east_port
		self.west_port = west_port

		self.east_host = east_host
		self.west_host = west_host

		self.west_sockets = MultiSocket()
		self.east_sockets = MultiSocket()

		self.is_running = threading.Lock()
		self.is_running.acquire()

	def run(self, poll_interval=.5):
		log.info("Listening on: east=%s:%d west=%s:%d" % (self.east_host, self.east_port, self.west_host, self.west_port))
		self.east_server = ThreadingTCPServer((self.east_host, self.east_port), TCPInHandler)
		self.east_server.m = self
		self.west_server = ThreadingTCPServer((self.west_host, self.west_port), TCPOutHandler)
		self.west_server.m = self

		self.east_thread = threading.Thread(target=self.east_server.serve_forever, args=(poll_interval,))
		self.west_thread = threading.Thread(target=self.west_server.serve_forever, args=(poll_interval,))

		self.east_thread.start()
		self.west_thread.start()

		self.is_running.release()

		# allow for signal processing
		while True:
			self.east_thread.join(.2)
			if not self.east_thread.isAlive():
				break

		self.west_thread.join()

		log.info("Stopping")

		self.east_server.server_close()
		self.west_server.server_close()

	def stop(self):
		self.east_server.shutdown()
		self.west_server.shutdown()

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

	m = VESNAMultiplex(east_port=args.east_port, east_host=args.east_host,
			west_port=args.west_port, west_host=args.west_host)

	def handler(signum, frame):
		log.warning("Signal %d caught! Stopping scan..." % (signum,))
		m.stop()

	signal.signal(signal.SIGTERM, handler)
	signal.signal(signal.SIGINT, handler)

	m.run()

if __name__ == "__main__":
	main()
