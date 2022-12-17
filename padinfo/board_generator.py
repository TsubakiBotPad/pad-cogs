class BoardGenerator(object):
    """Generate a Dawnglare link with optional inversion."""

    allowed_letters = "RGBLDHXJMPZ"
    inversion = "-1"
    dawnglare_link = "https://pad.dawnglare.com/?patt={}&showfill=1"
    board_sizes = {
        20: {"height": 4, "width": 5},
        30: {"height": 5, "width": 6},
        42: {"height": 6, "width": 7}
    }

    def __init__(self, board):
        self.board = board.replace(" ", "")
        self.invert = self.inversion in self.board
        self.board = self.board.replace(self.inversion, "")
        self.board_length = len(self.board)
        self.invalid_size = self.board_length not in self.board_sizes
        self.invalid_orbs = not all(letter in self.allowed_letters for letter in self.board)

        if self.invalid_size or self.invalid_orbs:
            return

        self.board_height = self.board_sizes[self.board_length].get('height')
        self.board_width = self.board_sizes[self.board_length].get('width')

        if self.invert:
            self.board = self.invert_fill(self.board)
        self.link = self.get_link()

    def invert_fill(self, board):
        inverted_board = ""
        k = 0

        for i in range(self.board_height):
            k = i
            build_string = ""
            for j in range(self.board_width):
                build_string += board[k]
                k += self.board_height
            inverted_board += build_string

        return inverted_board

    def get_link(self):
        link = self.dawnglare_link.format(self.board)

        if self.board_length == 20 or self.board_length == 42:
            link = f"{link}&height={self.board_height}&width={self.board_width}"

        return link
