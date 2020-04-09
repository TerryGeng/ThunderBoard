import io
import threading
import socket
import struct
import logging
import time

from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room, leave_room

import objects

class DashboardServer:
    def __init__(self, recv_server_host = "0.0.0.0", recv_server_port = 2333, web_server_host = "0.0.0.0", web_server_port = 2334):
        self.recv_server_host = recv_server_host
        self.recv_server_port = recv_server_port
        self.web_server_host = web_server_host
        self.web_server_port = web_server_port
        self.object_create_handlers = {}
        self.objects = {}
        self.clients = []
        self.object_subscriptions = {}

    def serve(self):
        logging.info(f"Initializing data-receiving server at {self.recv_server_host}:{self.recv_server_port} "
                     f"in separated thread....")
        self.recv_socket = socket.socket()
        self.recv_socket.bind((self.recv_server_host, self.recv_server_port))

        recv_thread = threading.Thread(target=self.recv_loop, name="RecvThread")
        recv_thread.daemon = True
        recv_thread.start()


        logging.info(f"Initializing web server at {self.web_server_host}:{self.web_server_port} ....")
        self.run_web_server()

    # This function need to run in main thread. This required by Flask.
    def run_web_server(self):
        self.flask_app = Flask(__name__)
        #self.flask_app.config['DEBUG'] = True
        self.flask_app.config['TEMPLATES_AUTO_RELOAD'] = True
        self.socketio = SocketIO(self.flask_app)
        self.register_web_server_methods(self.flask_app, self.socketio)
        self.socketio.run(self.flask_app, host=self.web_server_host, port=self.web_server_port)

    def recv_chunk(self, _socket, length):
        received = 0
        chunks = io.BytesIO()
        while received < length:
            chunk = _socket.recv(length)
            if chunk == b'':
                raise ConnectionError("Socket connection broken")
            chunks.write(chunk)
            received += len(chunk)

        return chunks.getbuffer()

    def maintain_connection(self, conn, addr):
        while True:
            try:
                # get metadata length
                metadata_length, = struct.unpack("h", self.recv_chunk(conn, 2))

                # get metadata
                metadata = self.recv_chunk(conn, metadata_length).tobytes().decode('utf-8')

                type = ""
                id = ""
                name = ""
                length = 0
                for line in metadata.split("\n"):
                    if line:
                        key, value = line.split("=", 1)
                        if key == "Type":
                            type = value
                        elif key == "Id":
                            id = value
                        elif key == "Name":
                            name = value
                        elif key == "Length":
                            length = int(value)

                data = self.recv_chunk(conn, length)

                if not id in self.objects:
                    self.objects[id] = self.object_create_handlers[type](name)
                    self.object_subscriptions[id] = []
                    self.send_new_object_notification(id)

                self.objects[id].update(data.tobytes())
                self.send_update(id)
            except ConnectionError:
                logging.debug(f"Lost connection with {addr[0]}:{addr[1]}")
                return

    def recv_loop(self):
        self.recv_socket.listen()
        while True:
            try:
                conn, addr = self.recv_socket.accept()
                logging.debug(f"Connection established with {addr[0]}:{addr[1]}")
                th = threading.Thread(target=self.maintain_connection, args=(conn, addr), name=f"Recv-{addr[0]}:{addr[1]}")
                th.start()
            except KeyboardInterrupt:
                break

        self.recv_socket.close()

    def send_update(self, object_id):
        if object_id in self.object_subscriptions and self.object_subscriptions[object_id]:
            object = self.objects[object_id]
            logging.debug(f"Send updated data ver {object.version} of {object.name}")
            self.socketio.emit('update', {
                'id': object_id,
                'type': object.type,
                'version': object.version,
                'name': object.name,
                'data': object.dump(),
            }, room=object_id)

    def send_new_object_notification(self, obj_id):
        self.socketio.emit('new object available', obj_id)

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
                id = max(self.clients) + 1

            logging.debug(f"Client {id} joined.")
            self.clients.append(id)
            for obj_id, object in self.objects.items():
                join_room(obj_id)
                self.object_subscriptions[obj_id].append(id)

            emit("id assigned", id)

        @socketio.on('subscribe')
        def subscribe(obj_id):
            if obj_id in self.objects:
                self.object_subscriptions[obj_id].append(id)
                join_room(obj_id)

        @socketio.on('leave')
        def leave(id):
            del self.clients[id]



if __name__ == '__main__':
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(asctime)s %(levelname)s %(threadName)s] %(message)s', "%b %d %H:%M:%S")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    server = DashboardServer()
    objects.register_object_types(server)
    server.serve()

