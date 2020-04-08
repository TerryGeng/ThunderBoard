import io
import socket
import struct
import time

from typing import Type, TYPE_CHECKING
if TYPE_CHECKING:
    import matplotlib.figure

class BaseSender:
    def __init__(self, name, server_host="localhost", server_port=2333):
        self.type = 'base'
        self.name = name
        self.id =  "%s%f" % (name, time.time())
        self.recv_server_host = server_host
        self.recv_server_port = server_port
        self.recv_socket = None

    def send(self, data):
        raise NotImplementedError

    def _establish(self):
        self.recv_socket = socket.socket()
        self.recv_socket.connect((self.recv_server_host, self.recv_server_port))

    def _send(self, data: bytes):
        metadata_str = f"Type={self.type}\n"
        metadata_str += f"Id={self.id}\n"
        metadata_str += f"Name={self.name}\n"
        metadata_str += f"Length={len(data)}\n"
        metadata = bytes(metadata_str, 'utf-8')
        metadata_len = struct.pack("h", len(metadata))

        to_be_sent = metadata_len + metadata + data

        sent_len = 0
        while sent_len < len(to_be_sent):
            if not self.recv_socket:
                self._establish()

            chunk_len = self.recv_socket.send(memoryview(to_be_sent)[sent_len:])
            if chunk_len == 0:
                self._establish()
                sent_len = 0 # resend
            else:
                sent_len += chunk_len



class TextSender(BaseSender):
    def __init__(self, name, server_host="localhost", server_port=2333):
        super().__init__(name, server_host, server_port)
        self.type = "text"

    def send(self, text):
        self._send(bytes(text, 'utf-8'))


class PlotSender(BaseSender):
    def __init__(self, name, server_host="localhost", server_port=2333):
        self.image_buffer = io.BytesIO()
        super().__init__(name, server_host, server_port)
        self.type = "image"

    def send(self, fig: 'matplotlib.figure.Figure'):
        fig.canvas.print_png(self.image_buffer)
        self._send(self.image_buffer.getvalue())
