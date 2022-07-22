class BoardGenerator(object):
    """Generate a Dawnglare link with optional inversion."""

    allowed_letters = "RGBLDHXJMPZ "
    inversion = "-1"
    dawnglare_link = "https://pad.dawnglare.com/?patt={}&showfill=1"
    board_sizes = {
        20: {"height": 4, "width": 5},
        30: {"height": 5, "width": 6},
        42: {"height": 6, "width": 7}
    }

    def __init__(self, board):
        self.board = board.split()
        self.invert = self.inversion in self.board
        self.clean_board = self.get_clean_board()
        self.invalid_orbs = not all(letter in self.allowed_letters for letter in self.clean_board)
        self.board_length = len(self.clean_board)
        self.invalid_board = self.board_length not in self.board_sizes
        self.link = self.get_link()

    def get_clean_board(self):
        if not self.invert:
            return ''.join(self.board)

        self.board.remove(self.inversion)
        return ''.join(self.invert_fill(self.board))

    def invert_fill(self, board):
        inverted_board = []

        try:
            for i in range(len(board[0])):
                build_string = ""
                for j in range(len(board)):
                    build_string += board[j][i]
                inverted_board.append(build_string)
        except:
            self.invalid_board = True

        return inverted_board

    def get_link(self):
        link = self.dawnglare_link.format(self.clean_board)

        if self.board_length == 20 or self.board_length == 42:
            link = f"{link}&height={self.board_sizes[self.board_length]['height']}&width={self.board_sizes[self.board_length]['width']} "

        return link
