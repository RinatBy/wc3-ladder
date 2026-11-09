import socket
import socketserver
import threading
import unittest
from uploads import Server


class DeadlineTests(unittest.TestCase):
    def test_slow_client_connection_is_closed_within_total_deadline(self):
        ended=threading.Event();entered=threading.Event()
        class Waiting(socketserver.BaseRequestHandler):
            def handle(self):
                entered.set()
                try: self.request.recv(1)
                except OSError: pass
                finally: ended.set()
        server=Server(('127.0.0.1',0),Waiting)
        server.max_connection_seconds=0.1
        worker=threading.Thread(target=lambda:server.serve_forever(poll_interval=0.01),daemon=True)
        worker.start()
        try:
            with socket.create_connection(server.server_address,timeout=1):
                self.assertTrue(entered.wait(1),'Receiver did not accept the test connection')
                self.assertTrue(ended.wait(1),'Slow request occupied the receiver beyond its deadline')
        finally:
            server.shutdown();server.server_close();worker.join(1)


if __name__=='__main__': unittest.main()
