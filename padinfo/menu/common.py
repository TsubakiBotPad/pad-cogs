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
        return [v[0] for k, v in cls.DATA.items() if v[1] not in cls.HIDDEN_EMOJIS]

    @classmethod
    def transitions(cls):
        return {v[0]: k for k, v in cls.DATA.items()}

    @classmethod
    def pane_types(cls):
        return {v[1]: k for k, v in cls.DATA.items() if v[1] and v[1] not in cls.HIDDEN_EMOJIS}

    @classmethod
    def emoji_name_to_emoji(cls, name: str):
        for _, data_pair in cls.DATA.items():
            if data_pair[1] == name:
                return data_pair[0]
        return None

    @classmethod
    def emoji_name_to_function(cls, name: str):
        for _, data_pair in cls.DATA.items():
            if data_pair[1] == name:
                return data_pair[1]
        return None

    @classmethod
    def respond_to_emoji_with_parent(cls, emoji: str):
        """Only defined for menus that support having children"""
        for _, data_pair in cls.DATA.items():
            if data_pair[0] == emoji:
                return data_pair[2]
        return None

    @classmethod
    def respond_to_emoji_with_child(cls, emoji: str):
        """Only defined for menus that support having children"""
        for _, data_pair in cls.DATA.items():
            if data_pair[0] == emoji:
                return data_pair[3]
        return None
