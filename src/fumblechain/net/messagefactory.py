"""
author: ADG

Message factory
"""

import json

from utils.serde import Encoder
from .messages import SerializationError, DeserializationError, MESSAGE_TYPES


class MessageFactory:
    KEY_HEAD = "head"
    KEY_BODY = "body"
    KEY_MAGIC = "magic"
    KEY_ID = "id"
    KEY_CMD = "command"
    KEY_SIZE = "size"
    MESSAGES = MESSAGE_TYPES

    def __init__(self, magic):
        """
        Init the message factory
        @magic: this blockchain magic int
        """
        self.magic = magic

    def serialize(self, msg, id, *args, **kwargs):
        """
        serialize a message packet
        @msg: the message to serialize
        @id: this node id
        @kwargs: message arguments
        """
        body = msg.serialize(*args, **kwargs)
        if not body:
            raise SerializationError("no data")
        jbody = json.dumps(body, cls=Encoder)
        size = len(jbody)
        head = {self.KEY_MAGIC: self.magic,
                self.KEY_CMD: msg.COMMAND,
                self.KEY_SIZE: size,
                self.KEY_ID: id}
        payload = {self.KEY_HEAD: head, self.KEY_BODY: body}
        return json.dumps(payload, cls=Encoder)

    def deserialize(self, data):
        """
        deserialize a message from data
        @data: the received data
        """
        pld = json.loads(data)
        head = pld[self.KEY_HEAD]
        magic = head[self.KEY_MAGIC]
        if magic != self.magic:
            raise DeserializationError("bad magic")
        body = pld[self.KEY_BODY]
        jbody = json.dumps(body)
        lenbody = len(jbody)
        if lenbody != head[self.KEY_SIZE]:
            raise DeserializationError("bad message size")
        return self._des_msg(head[self.KEY_CMD], body), head[self.KEY_ID]

    def _des_msg(self, cmd, body):
        """
        deserialize the message body
        @cmd: the message command
        @body: the message body
        """
        msg = None
        for m in self.MESSAGES:
            if cmd == m.COMMAND:
                msg = m()
                msg.deserialize(body)
        if not msg:
            err = 'unknown message \"{}\": {}'.format(cmd, body)
            raise DeserializationError(err)
        return msg
