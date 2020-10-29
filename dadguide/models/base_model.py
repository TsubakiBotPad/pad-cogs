import json


class BaseModel(object):

    def generate_log(self):
        raise NotImplementedError

    def to_json(self):
        return json.dumps(self.generate_log())

    def __repr__(self):
        try:
            print(self.to_json())
        except NotImplementedError:
            super()
