import logging

class Group(object):

    def __init__(self, **g):
        self.type = g['type']

        # These may exist
        self.skills = g['skills']
        self.condition = g['condition']