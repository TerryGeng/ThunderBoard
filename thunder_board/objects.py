import io
import base64
import logging
import time
import json
import threading

from PIL import Image

class BaseObject:
    type = "base"

    def __init__(self, name, board, send_enable=False):
        self.name = name
        self.board = board
        self.version = 0
        self.last_active = time.time()
        self.active = True
        self.send_enable = send_enable
        self.socket = None

    @staticmethod
    def init(name, board):
        return BaseObject(name, board)

    def update(self, metadata, data):
        self.version += 1
        pass

    def dump_to(self, to_send):
        return to_send


class TextObject(BaseObject):
    type = "text"

    def __init__(self, name, board):
        super().__init__(name, board)
        self.text = ""
        self.version = 0
        self.rotate = True

    @staticmethod
    def init(name, board):
        return TextObject(name, board)

    def update(self, metadata, text_data):
        self.version += 1
        if metadata['rotate'] == 'True':
            self.rotate = True
        else:
            self.rotate = False

        self.text = text_data.decode('utf-8')
        logging.debug(f"ver {self.version}: {self.text}")

    def dump_to(self, dump_to):
        dump_to['data'] = self.text
        if self.rotate:
            dump_to['rotate'] = 'True'
        else:
            dump_to['rotate'] = 'False'

        return dump_to


class ImageObject(BaseObject):
    type = "image"

    IMAGE_MAX_SIZE = (650, 650)

    def __init__(self, name, board):
        super().__init__(name, board)
        self.image = None

    @staticmethod
    def init(name, board):
        return ImageObject(name, board)

    def update(self, metadata, image):
        self.version += 1
        if 'compress' not in metadata or metadata['compress'] == 'False':
            im = Image.open(io.BytesIO(image))
            im.thumbnail(self.IMAGE_MAX_SIZE, Image.ANTIALIAS)
            buffer = io.BytesIO()
            im = im.convert("RGB")
            im.save(buffer, format="JPEG", dpi=[100, 100], quality=90)
            self.image = base64.b64encode(buffer.getvalue()).decode('utf-8')
        else:
            self.image = base64.b64encode(image).decode('utf-8')

    def dump_to(self, dump_to):
        dump_to['data'] = self.image
        return dump_to


class DialogObject(BaseObject):
    type = 'dialog'

    def __init__(self, name, board):
        super().__init__(name, board, send_enable=True)
        self.fields = []

    @staticmethod
    def init(name, board):
        return DialogObject(name, board)

    def update(self, metadata, data):
        self.version += 1
        self.fields = json.loads(data)

    def dump_to(self, dump_to):
        dump_to['fields'] = self.fields
        return dump_to




def register_object_types(server):
    server.object_create_handlers['text'] = TextObject.init
    server.object_create_handlers['image'] = ImageObject.init
    server.object_create_handlers['dialog'] = DialogObject.init
