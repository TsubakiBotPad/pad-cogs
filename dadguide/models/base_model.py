import json


class BaseModel(object):

    def to_dict(self):
        raise NotImplementedError

    def to_string(self):
        return self.__class__.__name__ + "<" + json.dumps(self.to_dict())[1:-1] + ">"

    def __repr__(self):
        try:
            return self.to_string()
        except NotImplementedError:
            return super().__repr__()
