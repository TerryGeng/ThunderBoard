import io
import base64
import logging

class BaseObject:
    type = "base"

    def __init__(self, name):
        self.name = name
        self.version = 0

    @staticmethod
    def init(name):
        return BaseObject(name)

    def update(self, data):
        self.version += 1
        pass

    def dump(self):
        return ""


class TextObject(BaseObject):
    type = "text"

    def __init__(self, name):
        super().__init__(name)
        self.text = ""

    @staticmethod
    def init(name):
        return TextObject(name)

    def update(self, text_data):
        self.version += 1
        self.text = text_data.decode('utf-8')
        logging.debug(self.text)

    def dump(self):
        return self.text


class ImageObject(BaseObject):
    type = "image"

    def __init__(self, name):
        super().__init__(name)
        self.image = None
        self.image_buffer = io.BytesIO()

    @staticmethod
    def init(name):
        return ImageObject(name)

    def update(self, image):
        self.version += 1
        self.image = base64.b64encode(image).decode('utf-8')

    def dump(self):
        return self.image

def register_object_types(server):
    server.object_create_handlers['text'] = TextObject.init
    server.object_create_handlers['image'] = ImageObject.init
