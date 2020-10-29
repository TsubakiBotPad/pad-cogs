import json


class BaseModel(object):

    def to_dict(self):
        raise NotImplementedError

    def to_string(self):
        return json.dumps(self.to_dict())

    def __repr__(self):
        try:
            print(self.to_string())
        except NotImplementedError:
            super()
