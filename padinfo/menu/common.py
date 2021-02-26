emoji_buttons = {
    'home': '\N{HOUSE BUILDING}',
    'reset': '\N{WHITE MEDIUM STAR}',
}


class MenuPanes:
    INITIAL_EMOJI = emoji_buttons['home'],
    DATA = {
    }
    HIDDEN_EMOJIS = [
    ]

    @classmethod
    def emoji_names(cls):
        return [k for k, v in cls.DATA.items() if v[1] not in cls.HIDDEN_EMOJIS]

    @classmethod
    def transitions(cls):
        return {k: v[0] for k, v in cls.DATA.items() if v[0] is not None}

    @classmethod
    def pane_types(cls):
        return {v[1]: v[0] for k, v in cls.DATA.items() if v[1] and v[1] not in cls.HIDDEN_EMOJIS}

    @classmethod
    def emoji_name_to_emoji(cls, name: str):
        for n, data_pair in cls.DATA.items():
            if data_pair[1] == name:
                return n
        return None

    @classmethod
    def respond_to_emoji_with_parent(cls, emoji: str):
        """Only defined for menus that support having children"""
        if cls.DATA.get(emoji) is None:
            return None
        return cls.DATA[emoji][0] is not None

    @classmethod
    def respond_to_emoji_with_child(cls, emoji: str):
        """Only defined for menus that support having children"""
        if cls.DATA.get(emoji) is None:
            return None
        return cls.DATA[emoji][2]
