import io
import socket
import struct
import time
import threading
import json
import logging


class BaseClient:
    def __init__(self, name, board="", id="", server_host="localhost", server_port=2333):
        self.type = 'base'
        self.name = name
        self.board = board if board else "Default"
        self.id =  "%s%f" % (name, time.time()) if not id else id
        self.recv_server_host = server_host
        self.recv_server_port = server_port
        self.socket = None
        self.socket_send_lock = threading.Lock()
        self.metadata = {}

        threading.Thread(target=self._ping, daemon=True).start()

    def send(self, data):
        raise NotImplementedError

    def _establish(self):
        self.socket = socket.socket()
        self.socket.connect((self.recv_server_host, self.recv_server_port))

    def _send(self, data):
        sent_len = 0
        with self.socket_send_lock:
            while sent_len < len(data):
                if not self.socket:
                    self._establish()

                chunk_len = self.socket.send(memoryview(data)[sent_len:])
                if chunk_len == 0:
                    self._establish()
                    sent_len = 0 # resend
                else:
                    sent_len += chunk_len

    def _send_control_msg(self, control_msg):
        metadata = {
            "Id": self.id,
            "CTL": control_msg
        }

        metadata_str = ""
        for key, value in metadata.items():
            metadata_str += f"{key}={value}\n"

        metadata = bytes(metadata_str, 'utf-8')
        metadata_len = struct.pack("h", len(metadata))

        to_be_sent = metadata_len + metadata

        self._send(to_be_sent)

    def _send_with_metadata(self, metadata, data):
        metadata['Type'] = self.type
        metadata['Id'] = self.id
        metadata['Name'] = self.name
        metadata['Board'] = self.board
        metadata['Length'] = len(data)
        metadata['CTL'] = "DATA"

        metadata_str = ""
        for key, value in metadata.items():
            metadata_str += f"{key}={value}\n"

        metadata = bytes(metadata_str, 'utf-8')
        metadata_len = struct.pack("h", len(metadata))

        to_be_sent = metadata_len + metadata + data

        self._send(to_be_sent)

    def _ping(self):
        while True:
            if self.socket:
                time.sleep(3)
                self._send(struct.pack("h", 0))
            else:
                self._send_control_msg("PING")

    def _recv_chunk(self, _socket, length):
        received = 0
        chunks = io.BytesIO()
        while received < length:
            chunk = _socket.recv(length)
            if chunk == b'':
                raise ConnectionError("Socket connection broken")
            chunks.write(chunk)
            received += len(chunk)

        return chunks.getbuffer()

    def recv_loop(self):
        time.sleep(1)
        while True:
            if not self.socket:
                self._establish()

            data_length, = struct.unpack("h", self._recv_chunk(self.socket, 2))
            data_str = self._recv_chunk(self.socket, data_length).tobytes().decode('utf-8')

            logging.debug(f"Received message {data_str}")

            data = {}
            for line in data_str.split("\n"):
                if line:
                    key, value = line.split("=", 1)
                    data[key] = value

            self.message_handler(data)

    def start_recv_thread(self):
        threading.Thread(name="Loop", target=self.recv_loop, daemon=True).start()

    def message_handler(self, data_dict):
        raise NotImplementedError

    def close(self):
        self._send_control_msg("INACTIVE")
        self.socket.close()
        self.socket = None

    def close_and_discard(self):
        self._send_control_msg("DISCARD")
        self.socket.close()
        self.socket = None

    def __del__(self):
        self.close()


class TextClient(BaseClient):
    def __init__(self, name, board="", rotate=True, id="", server_host="localhost", server_port=2333):
        super().__init__(name, board, id, server_host, server_port)
        self.type = "text"
        if rotate:
            self.metadata['rotate'] = True
        else:
            self.metadata['rotate'] = False

    def send(self, text):
        self._send_with_metadata(self.metadata, bytes(text, 'utf-8'))


class ImageClient(BaseClient):
    def __init__(self, name, board="", id="", server_host="localhost", server_port=2333, format="jpeg"):
        super().__init__(name, board, id, server_host, server_port)
        self.type = "image"
        self.format = format
        self.metadata['format'] = format

    def send(self, image):
        self._send_with_metadata(self.metadata, image.getbuffer())


class PlotClient(ImageClient):
    def __init__(self, name, board="", id="", server_host="localhost", server_port=2333, format="png"):
        super().__init__(name, board, id, server_host, server_port, format)

    def send(self, fig): # fig: 'matplotlib.figure.Figure'
        image_buffer = io.BytesIO()
        fig.savefig(image_buffer, format=self.format)
        img_data = image_buffer.getbuffer()

        if self.format == "svg":
            img_data = self.sanitize_mpl_svg(img_data)

        self._send_with_metadata(self.metadata, img_data)

    def sanitize_mpl_svg(self, buf: memoryview):
        line_to_remove = [0, 1, 2, 3, 5, 6, 7, 8, 9]
        current_line = 0
        for i in range(len(buf)):
            if buf[i] == b"\n"[0]:
                current_line += 1
                if current_line > max(line_to_remove):
                    break
            if current_line in line_to_remove:
                buf[i] = b" "[0]

        return buf


class DialogClient(BaseClient):
    def __init__(self, name, board="", id="", server_host="localhost", server_port=2333):
        super().__init__(name, board, id, server_host, server_port)
        self.type = "dialog"
        self.groups = {}
        self.groups['Default'] = []
        self.groups_order = [ 'Default' ]
        self.fields = {}
        self.handlers = {}

    def add_group(self, name=""):
        if name not in self.groups:
            self.groups[name] = []
            self.groups_order.append(name)

    def add_button(self, name="", text="", handler=None, group="Default", enabled=True):
        if not name:
            raise ValueError("Name can not be empty.")

        if not name in self.fields:
            self.groups[group].append(name)

        self.fields[name] = { 'type': 'button',
                              'text': text,
                              'enabled': enabled }
        if handler:
            self.fields[name]['handle'] = 'on_click'
            self.handlers[name + '@on_click'] = handler

    def add_input_box(self, name="", label_text="", handler=None, default_value="", group="Default", enabled=True):
        if not name:
            raise ValueError("Name can not be empty.")

        if not name in self.fields:
            self.groups[group].append(name)

        self.fields[name] = { 'type': 'input',
                              'text': label_text,
                              'value': default_value,
                              'enabled': enabled }
        if handler:
            self.fields[name]['handle'] = 'on_change'
            self.handlers[name + '@on_change'] = handler

    def add_text_label(self, name="", text="", group="Default"):
        if not name:
            raise ValueError("Name can not be empty.")

        if not name in self.fields:
            self.groups[group].append(name)

        self.fields[name] = { 'type': 'label',
                              'text': text }

    def add_slider(self, name="", label_text="", value_range=None, default_value="", group="Default", enabled=True):
        pass

    def display(self):
        fields_to_send = []
        for group in self.groups_order:
            fields = self.groups[group]
            for field in fields:
                fields_to_send.append(
                    {
                        'group': group,
                        'name': field,
                        **self.fields[field]
                    }
                )

        self._send_with_metadata(self.metadata, bytes(json.dumps(fields_to_send), 'utf-8'))

    def message_handler(self, data_dict):
        event = data_dict['event']
        args = data_dict['args']
        logging.info(f"Event {event} emitted with args {args}")
        if event in self.handlers:
            self.handlers[event](args)
