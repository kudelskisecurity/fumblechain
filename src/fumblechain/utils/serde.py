import json


class Encoder(json.JSONEncoder):
    def default(self, o):
        """Use the _serialize() method of objects that implement it.
        Otherwise use the default serializer."""
        if hasattr(o, "_serialize"):
            return o._serialize()
        else:
            return o
