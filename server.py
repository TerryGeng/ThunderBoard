import threading
import struct
import logging
import zmq
from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room, leave_room

import objects

class ClientSubscription:
    def __init__(self, client_id):
        self.client_id = client_id
        self.subscription = {}

class DashboardServer:
    def __init__(self, recv_server_host = "*", recv_server_port = 2333, web_server_host = "0.0.0.0", web_server_port = 2334):
        self.recv_server_host = recv_server_host
        self.recv_server_port = recv_server_port
        self.web_server_host = web_server_host
        self.web_server_port = web_server_port
        self.object_create_handlers = {}
        self.objects = {}
        self.clients = {}

    def serve(self):
        logging.info(f"Initializing data-receiving server at {self.recv_server_host}:{self.recv_server_port} ....")
        self.init_recv_server(self.recv_server_host, self.recv_server_port)
        recv_thread = threading.Thread(target=self.recv_loop, name="RecvThread")
        recv_thread.daemon = True
        recv_thread.start()

        logging.info(f"Initializing web server at {self.web_server_host}:{self.web_server_port} ....")
        self.run_web_server(self.web_server_host, self.web_server_port)

    def init_recv_server(self, recv_server_host = "*", recv_server_port = 2333):
        self.recv_context = zmq.Context()
        self.recv_socket = self.recv_context.socket(zmq.PULL)
        self.recv_socket.bind(f"tcp://{recv_server_host}:{recv_server_port}")
        self.recv_poller = zmq.Poller()
        self.recv_poller.register(self.recv_socket, zmq.POLLIN)

    def run_web_server(self, web_server_host = "0.0.0.0", web_server_port = 2334):
        self.flask_app = Flask(__name__)
        self.socketio = SocketIO(self.flask_app)
        self.register_web_server_methods(self.flask_app, self.socketio)
        self.socketio.run(self.flask_app, host=web_server_host, port=web_server_port)

    def _unpack_msg(self, msg):
        # Unpack metadata
        metadata_len, = struct.unpack('h', msg[0:2])
        metadata = msg[2: metadata_len+2].decode('utf-8')
        lines = metadata.split()

        type = ""
        id = ""
        name = ""
        for line in lines:
            if line:
                key, value = line.split("=", 1)
                if key == "Type":
                    type = value
                elif key == "Id":
                    id = value
                elif key == "Name":
                    name = value

        data = msg[metadata_len + 2:]

        return type, id, name, data

    def update_object(self, type, id, name, data):
        if not id in self.objects:
            self.objects[id] = self.object_create_handlers[type](name)

        self.objects[id].update(data)

    def recv_loop(self):
        while True:
            try:
                socks = dict(self.recv_poller.poll())
                if self.recv_socket in socks:
                    print("incoming message!")
                    msg = self.recv_socket.recv()
                    type, id, name, data = self._unpack_msg(msg)
                    self.update_object(type, id, name, data)
            except KeyboardInterrupt:
                break

    def register_web_server_methods(self, app, socketio):
        # I don't know if there's any other elegant way of doing this.
        # Flask suggests I create apps at module level but this certainly doesn't fit our use case.

        @app.route("/", methods=['GET'])
        def index():
            return render_template('index.html')

        @socketio.on('join')
        def join():
            id = 0
            if self.clients:
                id = max(self.clients.keys()) + 1
            join_room(id)
            emit("id assigned", id)


if __name__ == '__main__':
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('[%(asctime)s %(levelname)s %(threadName)s] %(message)s', "%b %d %H:%M:%S")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    server = DashboardServer()
    objects.register_object_types(server)
    server.serve()

