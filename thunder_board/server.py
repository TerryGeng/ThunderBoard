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

    def send_chunk(self, _socket, data):
        sent_len = 0
        while sent_len < len(data):
            chunk_len = _socket.send(memoryview(data)[sent_len:])
            if chunk_len == 0:
                raise ConnectionError("Socket connection broken")
            else:
                sent_len += chunk_len

    def maintain_connection(self, conn, addr):
        id = None
        while True:
            try:
                # get metadata length
                metadata_length, = struct.unpack("h", self.recv_chunk(conn, 2))

                if not metadata_length: # PING message has length 0
                    if id in self.objects:
                        self.objects[id].last_active = time.time()
                        self.objects[id].active = True
                        logging.debug(f"PING packet received for {id}")
                    continue

                # get metadata
                metadata_str = self.recv_chunk(conn, metadata_length).tobytes().decode('utf-8')
                metadata = {}

                for line in metadata_str.split("\n"):
                    if line:
                        key, value = line.split("=", 1)
                        metadata[key] = value


                logging.debug(f"Packet received, metadata {metadata}")

                id = metadata['Id']
                length = int(metadata['Length']) if 'Length' in metadata else 0
                control_msg = metadata['CTL']

                data = self.recv_chunk(conn, length)

                if id in self.objects:
                    self.objects[id].last_active = time.time()
                    self.objects[id].active = True
                    self.objects[id].socket = conn

                    if control_msg == "PING":
                        logging.debug(f"PING packet received for {id}")
                        continue
                    elif control_msg == "INACTIVE" or control_msg == "DISCARD":
                        self.objects[id].active = False
                        self.objects[id].socket = None
                        logging.info(f"Set Inactive flag to object {self.objects[id].name} ({id})")
                        if control_msg == "DISCARD":
                            del self.object_subscriptions[id]
                            del self.objects[id]
                            self.socketio.emit("close", id, room=id)
                            self.socketio.close_room(id)
                            return
                    elif control_msg == "DATA":
                        self.objects[id].update(metadata, data.tobytes())
                else:
                    if control_msg == "DATA":
                        logging.info("Create object %s" % id)
                        type = metadata['Type']
                        name = metadata['Name']
                        board = metadata['Board']
                        self.objects[id] = self.object_create_handlers[type](name, board)
                        self.objects[id].socket = conn
                        self.object_subscriptions[id] = []
                        self.send_new_object_notification(id)
                        self.objects[id].update(metadata, data.tobytes())
                    else:
                        continue

                self.send_update(id)

            except ConnectionError:
                logging.debug(f"Lost connection with {addr[0]}:{addr[1]}")
                if id:
                    self.wait_check_alive(id)
                return
            except KeyError:
                logging.error(f"Ill-formatted packet from {addr[0]}:{addr[1]}.")
                return


    def wait_check_alive(self, id):
        time.sleep(5)
        if time.time() - self.objects[id].last_active > 4:
            self.objects[id].active = False
            logging.info(f"PING not received. Set Inactive flag to object {self.objects[id].name} ({id})")
            self.send_update(id)

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
                'name': object.name,
                'active': object.active
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

        @socketio.on('send')
        def send(json):
            logging.info(f"Receive message from browser client, refer to {json['obj_id']}")
            if json['obj_id'] in self.objects and self.objects[json['obj_id']].send_enable:
                dict_str = ""
                for key, value in json.items():
                    if key != 'obj_id':
                        dict_str += f"{key}={value}\n"

                data = bytes(dict_str, 'utf-8')
                data_len = struct.pack("h", len(data))

                to_be_sent = data_len + data

                logging.debug(f"Send message to {json['obj_id']}: {dict_str}")
                self.send_chunk(self.objects[json['obj_id']].socket, to_be_sent)

        @socketio.on('clean inactive')
        def clean_inactive():
            item_to_clean = []
            for id, obj in self.objects.items():
                if not obj.active:
                    item_to_clean.append(id)

            for id in item_to_clean:
                del self.object_subscriptions[id]
                del self.objects[id]

        @socketio.on('unsubscribe')
        def unsubscribe(json):
            if json['obj_id'] in self.objects:
                self.object_subscriptions[json['obj_id']].remove(json['client_id'])
                leave_room(json['obj_id'])

        @socketio.on('leave')
        def leave(id):
            del self.clients[id]


