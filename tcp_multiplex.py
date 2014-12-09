import socket
import threading

class TcpMultiplex(object):

	def __init__(self):
		self.want_stop = False

	def run(self):
		port = 2101

		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		s.bind(("", port))
		s.listen(1)
		conn, addr = s.accept()
		print 'Connected by', addr
		conn.settimeout(1.)
		self.reader(conn)
		conn.close()

	def reader(self, conn):
		buff = ""
		while not self.want_stop:
			try:
				buff += conn.recv(1024)
			except socket.timeout:
				continue

			if '\n' in buff:
				cmds = buff.split('\n')

				for cmd in cmds[:-1]:
					cmd = cmd.strip()
					if cmd == '?ping':
						conn.send('ok\n')

				buff = cmds[-1]

	def stop(self):
		self.want_stop = True
