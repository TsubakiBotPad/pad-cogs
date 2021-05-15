class MenuPanes:
    INITIAL_EMOJI = None,
    DATA = {
    }
    HIDDEN_EMOJIS = [
    ]

    @classmethod
    def emoji_names(cls):
        return [k for k, v in cls.DATA.items() if k not in cls.HIDDEN_EMOJIS]

    @classmethod
    def transitions(cls):
        return {k: v[0] for k, v in cls.DATA.items() if v[0] is not None}

    @classmethod
    def pane_types(cls):
        return {v[1]: v[0] for k, v in cls.DATA.items() if v[1] and v[1] not in cls.HIDDEN_EMOJIS}
