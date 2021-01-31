from abc import abstractmethod


class ViewState:
    @abstractmethod
    def serialize(self):
        pass
