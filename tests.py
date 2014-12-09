import serial
import socket
import tcp_multiplex
import threading
import unittest

class TestTcpMultiplexConnection(unittest.TestCase):

	def setUp(self):
		self.m = tcp_multiplex.TcpMultiplex()
		self.t = threading.Thread(target=self.m.run)
		self.t.start()

	def tearDown(self):
		self.m.stop()
		self.t.join()

	def test_ping(self):
		comm = serial.serial_for_url("socket://localhost:2101", timeout=60)
		comm.write("?ping\n")

		resp = comm.readline()
		self.assertEqual("ok\n", resp)

	def xest_ping_many(self):
		N = 5

		comm = [ serial.serial_for_url("socket://localhost:2101", timeout=60) for n in xrange(N) ]

		for c in comm:
			c.write("?ping\n")

		for c in comm:
			resp = c.readline()
			self.assertEqual("ok\n", resp)

class TestTcpMultiplexStatic(unittest.TestCase):

	def test_reader_ping(self):
		m = tcp_multiplex.TcpMultiplex()

		class MockConn:
			def __init__(self):
				self.cnt = -1
				self.b = ""

			def recv(self, n):
				self.cnt += 1
				if self.cnt == 0:
					return "?ping\n"
				else:
					m.stop()
					raise socket.timeout

			def send(self, b):
				self.b += b

		c = MockConn()
		m.reader(c)

		self.assertEqual("ok\n", c.b)

if __name__ == '__main__':
	unittest.main()
