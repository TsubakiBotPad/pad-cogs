class BoardGenerator(object):
    """Generate a Dawnglare link with optional inversion."""

    allowed_letters = "RGBLDHXJMPZ "
    inversion = "-1"
    dawnglare_link = "https://pad.dawnglare.com/?patt={}&showfill=1"

    def __init__(self, board):
        self.board = board.split()
        self.board_height = None
        self.board_width = None
        self.invalid_board = False
        self.invert = BoardGenerator.inversion in self.board
        self.clean_board = self.get_clean_board()
        self.invalid_orbs = not all(letter in BoardGenerator.allowed_letters for letter in self.clean_board)
        self.board_length = len(self.clean_board)
        self.eval_board_size()
        self.link = self.get_link()

    def get_clean_board(self):
        board = self.board

        if self.invert:
            board.remove(BoardGenerator.inversion)
            clean = ''.join(self.invert_fill(board))
        else:
            clean = ''.join(board)

        return clean

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

    def eval_board_size(self):
        length = self.board_length

        if length == 20:
            height, width = 4, 5
        elif length == 42:
            height, width = 6, 7
        elif length == 30:
            height, width = 5, 6
        else:
            height = 0
            width = 0
            self.invalid_board = True

        self.board_height = height
        self.board_width = width

    def get_link(self):
        length = self.board_length
        link = BoardGenerator.dawnglare_link.format(self.clean_board)

        if length == 20 or length == 42:
            link = f"{link}&height={self.board_height}&width={self.board_width}"

        return link
