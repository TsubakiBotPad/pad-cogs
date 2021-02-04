class EnemySkill(object):
    def __init__(self, raw: "List[str]"):
        self.enemy_skill_id = int(raw[0])
        self.name = raw[1].replace('\n', ' ')
        self.type = int(raw[2])
        self.flags = int(raw[3], 16)  # 16bitmap for params
        self.params = [None] * 16
        offset = 0
        p_idx = 4
        while offset < self.flags.bit_length():
            if (self.flags >> offset) & 1 != 0:
                p_value = raw[p_idx]
                self.params[offset] = int(p_value) if p_value.lstrip('-').isdigit() else p_value
                p_idx += 1
            offset += 1

    def process(self):
        return "Unknown: [{},{},{},{}]".format(self.id, self.name, self.type, self.params)

class ESNone(EnemySkill):
    def __init__(self, id = None):
        self.enemy_skill_id = id
        self.name = None
        self.type = None
        self.flags = None
        self.params = None