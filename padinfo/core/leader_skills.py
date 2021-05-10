import re


def humanize_number(number, sigfigs=2):
    n = float("{0:.{1}g}".format(number, sigfigs))
    if n >= 1e9:
        return str(int(n // 1e9)) + "B"
    elif n >= 1e6:
        return str(int(n // 1e6)) + "M"
    elif n >= 1e3:
        return str(int(n // 1e3)) + "k"
    else:
        return str(int(n))


def createMultiplierText(ls1, ls2=False):
    if ls2 and not ls1:
        ls1, ls2 = ls2, ls1

    if ls1.__class__.__name__ == "LeaderSkillModel":
        hp1, atk1, rcv1, resist1, combo1, fua1, mfua1, te1 = ls1.data
    else:
        hp1, atk1, rcv1, resist1, combo1, fua1, mfua1, te1 = 1, 1, 1, 0, 0, 0, 0, 0

    if ls2.__class__.__name__ == "LeaderSkillModel":
        hp2, atk2, rcv2, resist2, combo2, fua2, mfua2, te2 = ls2.data
    elif ls2 is False:
        hp2, atk2, rcv2, resist2, combo2, fua2, mfua2, te2 = hp1, atk1, rcv1, resist1, combo1, fua1, mfua1, te1
    elif ls2 is None:
        hp2, atk2, rcv2, resist2, combo2, fua2, mfua2, te2 = 1, 1, 1, 0, 0, 0, 0, 0
    else:
        raise ValueError(f"ls2 must be LeaderSkillModel or None, not {type(ls2)}")

    return format_ls_text(
        hp1 * hp2,
        atk1 * atk2,
        rcv1 * rcv2,
        1 - (1 - resist1) * (1 - resist2),
        combo1 + combo2,
        fua1 + fua2,
        mfua1 + mfua2,
        te1 + te2
    )


def createSingleMultiplierText(ls=None):
    if ls:
        hp, atk, rcv, resist, combo, fua, mfua, te = ls.data
    else:
        hp, atk, rcv, resist, combo, fua, mfua, te = 1, 1, 1, 0, 0, 0, 0, 0

    return format_ls_text(hp, atk, rcv, resist, combo, fua, mfua, te)


def format_number(val):
    return '{:.2f}'.format(val).strip('0').rstrip('.')


def format_ls_text(hp, atk, rcv, resist=0, combo=0, fua=0, mfua=0, te=0):
    resist = ' Resist {}%'.format(format_number(100 * resist)) if resist else ''

    combos = '+{}c'.format(combo) if combo else ''
    true_damage = '{}'.format(humanize_number(fua, 2)) if fua else ''
    any_fua = 'fua' if fua or mfua else ''

    joined = ' '.join((a for a in [combos, true_damage, any_fua] if a))
    extras = f"[{joined}]" if joined else ''

    return f"[{format_number(hp)}/{format_number(atk)}/{format_number(rcv)}{resist}] {extras}"


async def perform_leaderskill_query(dgcog, raw_query, author_id):
    # Remove unicode quotation marks
    query = re.sub("[\u201c\u201d]", '"', raw_query)

    # deliberate order in case of multiple different separators.
    for sep in ('"', '/', ',', ' '):
        if sep in query:

            left_query, *right_query = [x.strip() for x in query.split(sep) if x.strip()] or (
                '', '')  # or in case of ^ls [sep] which is empty list
            # split on first separator, with if x.strip() block to prevent null values from showing up, mainly for quotes support
            # right query is the rest of query but in list form because of how .strip() works. bring it back to string form with ' '.join
            right_query = ' '.join(q for q in right_query)
            if sep == ' ':
                # Handle a very specific failure case, user typing something like "uuvo ragdra"
                m = await dgcog.find_monster(query, author_id)
                if m and left_query in dgcog.index.modifiers[m]:
                    left_query = query
                    right_query = None

            break

    else:  # no separators
        left_query, right_query = query, None
    left_m = await dgcog.find_monster(left_query, author_id)
    if right_query:
        right_m = await dgcog.find_monster(right_query, author_id)
    else:
        right_m = left_m
    return left_m, left_query, right_m, right_query
