#This is meant to replace the 's with "" to denote strings
def itsRawMate(raw_skill: str):
    raw_skill = list(raw_skill)
    found_apostrophe = -1
    index = 0
    while index < len(raw_skill):
        sus_char = raw_skill[index]
        if sus_char == '\'':
            if found_apostrophe == -1:
                found_apostrophe = index
            else:
                # this might be the second apostrophe check if the next character is a comma
                if raw_skill[index + 1] == ',':
                    # While this doesn't exist in the data you never know. Check for a space after the comma as data
                    # seperated by a comma does NOT have a space after the comma
                    if raw_skill[index + 2] != ' ':
                        raw_skill[found_apostrophe] = '"'
                        raw_skill[index] = '"'
                        found_apostrophe = -1
                elif raw_skill[index + 1] == '\n':
                    # I mean...It might be a new line
                    raw_skill[found_apostrophe] = '"'
                    raw_skill[index] = '"'
                    found_apostrophe = -1
        elif sus_char == '"':
            # fix Gungho's awful escaping by replacing \" with "" as per most CSV standards
            raw_skill.insert(index, '"')
            index += 1
        index += 1
    return "".join(raw_skill)