import io
import socket
import struct
import time
import threading


class BaseSender:
    def __init__(self, name, board="", id="", server_host="localhost", server_port=2333):
        self.type = 'base'
        self.name = name
        self.board = board if board else "Default"
        self.id =  "%s%f" % (name, time.time()) if not id else id
        self.recv_server_host = server_host
        self.recv_server_port = server_port
        self.recv_socket = None
        self.socket_lock = threading.Lock()
        self.metadata = {}

        threading.Thread(target=self._ping, daemon=True).start()

    def send(self, data):
        raise NotImplementedError

    def _establish(self):
        self.recv_socket = socket.socket()
        self.recv_socket.connect((self.recv_server_host, self.recv_server_port))

    def _send(self, data):
        sent_len = 0
        with self.socket_lock:
            while sent_len < len(data):
                if not self.recv_socket:
                    self._establish()

                chunk_len = self.recv_socket.send(memoryview(data)[sent_len:])
                if chunk_len == 0:
                    self._establish()
                    sent_len = 0 # resend
                else:
                    sent_len += chunk_len

    def _send_with_metadata(self, metadata, data: bytes):
        metadata['Type'] = self.type
        metadata['Id'] = self.id
        metadata['Name'] = self.name
        metadata['Board'] = self.board
        metadata['Length'] = len(data)

        metadata_str = ""
        for key, value in metadata.items():
            metadata_str += f"{key}={value}\n"

        metadata = bytes(metadata_str, 'utf-8')
        metadata_len = struct.pack("h", len(metadata))

        to_be_sent = metadata_len + metadata + data

        self._send(to_be_sent)

    def _ping(self):
        while True:
            if self.recv_socket:
                time.sleep(3)
                self._send_with_metadata({'PING': 1, 'Id': self.id}, b"")

    def close(self):
        self._send_with_metadata({"Inactive": 1, 'Id': self.id}, b"")
        self.recv_socket.close()
        self.recv_socket = None

    def close_and_discard(self):
        self._send_with_metadata({"Inactive": 1, 'Discard': 1, 'Id': self.id}, b"")
        self.recv_socket.close()
        self.recv_socket = None

    def __del__(self):
        self.close()


class TextSender(BaseSender):
    def __init__(self, name, board="", rotate=True, id="", server_host="localhost", server_port=2333):
        super().__init__(name, board, id, server_host, server_port)
        self.type = "text"
        if rotate:
            self.metadata['rotate'] = True
        else:
            self.metadata['rotate'] = False

    def send(self, text):
        self._send_with_metadata(self.metadata, bytes(text, 'utf-8'))


class ImageSender(BaseSender):
    def __init__(self, name, board="", id="", server_host="localhost", server_port=2333):
        super().__init__(name, board, id, server_host, server_port)
        self.type = "image"

    def send(self, image):
        self._send_with_metadata(self.metadata, image.getvalue())


class PlotSender(ImageSender):
    def __init__(self, name, board="", id="", server_host="localhost", server_port=2333):
        super().__init__(name, board, id, server_host, server_port)

    def send(self, fig): # fig: 'matplotlib.figure.Figure'
        image_buffer = io.BytesIO()
        fig.savefig(image_buffer, dpi=120, format="jpg")
        self._send_with_metadata(self.metadata, image_buffer.getvalue())
