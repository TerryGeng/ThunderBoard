import io
import threading
import socket
import struct
import logging
import time

from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room, leave_room

from thunder_board import objects


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
        id = None
        while True:
            try:
                # get metadata length
                metadata_length, = struct.unpack("h", self.recv_chunk(conn, 2))

                # get metadata
                metadata_str = self.recv_chunk(conn, metadata_length).tobytes().decode('utf-8')
                metadata = {}

                for line in metadata_str.split("\n"):
                    if line:
                        key, value = line.split("=", 1)
                        metadata[key] = value


                logging.debug(f"Packet received, metadata {metadata}")

                id = metadata['Id']
                if id in self.objects:
                    self.objects[id].last_active = time.time()

                if 'PING' in metadata:
                    continue

                type = metadata['Type']
                name = metadata['Name']
                board = metadata['Board']
                length = int(metadata['Length'])

                data = self.recv_chunk(conn, length)

                if 'Discard' in metadata:
                    if id in self.objects:
                        logging.info(f"Discard object {name} ({id})")
                        del self.object_subscriptions[id]
                        del self.objects[id]
                        if 'Close' in metadata:
                            self.socketio.emit("discard and close", id, room=id)
                        else:
                            self.socketio.emit("discard", id, room=id)
                        self.socketio.close_room(id)
                    return

                if not id in self.objects:
                    logging.info("Create object %s" % id)
                    self.objects[id] = self.object_create_handlers[type](name, board)
                    self.object_subscriptions[id] = []
                    self.send_new_object_notification(id)

                self.objects[id].update(metadata, data.tobytes())
                self.send_update(id)
            except ConnectionError:
                logging.debug(f"Lost connection with {addr[0]}:{addr[1]}")
                if id:
                    self.wait_check_alive(id)
                return

    def wait_check_alive(self, id):
        time.sleep(5)
        if time.time() - self.objects[id].last_active > 4:
            logging.info(f"Discard object {self.objects[id].name} ({id})")
            del self.object_subscriptions[id]
            del self.objects[id]
            self.socketio.emit("discard", id, room=id)

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
            to_send = {
                'id': object_id,
                'type': object.type,
                'board': object.board,
                'version': object.version,
                'name': object.name
            }
            object.dump_to(to_send)
            self.socketio.emit('update', to_send, room=object_id)

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
        def subscribe(json):
            if json['obj_id'] in self.objects:
                self.object_subscriptions[json['obj_id']].append(json['client_id'])
                join_room(json['obj_id'])
                self.send_update(json['obj_id'])

        @socketio.on('list')
        def list(json):
            obj_list = []
            for id, obj in self.objects.items():
                subscribed = True if json['client_id'] in self.object_subscriptions[id] else False
                obj_list.append({'id': id, 'name': obj.name, 'board': obj.board, 'subscribed': subscribed})
            emit("list", obj_list)

        @socketio.on('unsubscribe')
        def unsubscribe(json):
            if json['obj_id'] in self.objects:
                self.object_subscriptions[json['obj_id']].remove(json['client_id'])
                leave_room(json['obj_id'])

        @socketio.on('leave')
        def leave(id):
            del self.clients[id]


