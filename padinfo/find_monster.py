import re

COLOR_MAP = {}

for r in ('r','red','fire'): COLOR_MAP[r] = 'r'
for b in ('b','blue','water'): COLOR_MAP[b] = 'b'
for g in ('g','green','wood'): COLOR_MAP[g] = 'g'
for l in ('l','light','yellow','white'): COLOR_MAP[l] = 'l'
for d in ('d','dark','purple','black'): COLOR_MAP[d] = 'd'
for x in ('x','none','null','nil'): COLOR_MAP[x] = 'x'

COLORS = 'rbgld?x'

def prefix_to_filter(prefix):
    prefix = prefix.lower()

    # light, nil, wood
    if prefix in COLOR_MAP:
        m = COLORS.index(COLOR_MAP[prefix])
        def filter_via_attribute(monster):
            return monster.attr1.value == m

    # light/red, l/r, yellow/fire
    match = re.match(r'^({0})/?({0})$'.format('|'.join(COLOR_MAP)), prefix)
    if match:
        m, s = [COLORS.index(COLOR_MAP[a]) for a in match.groups()]
        def filter_via_attributes(monster):
            return monster.attr1.value == m and monster.attr2.value == s
        return filter_via_attributes
