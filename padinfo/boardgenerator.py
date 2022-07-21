class BoardGenerator(object):
    """Generate a Dawnglare link with optional inversion."""

    allowed_letters = "RGBLDHXJMPZ "
    inversion = "-1"
    dawnglare_link = "https://pad.dawnglare.com/?patt={}&showfill=1"

    def __init__(self, board):
        self.board = board.split()
        self.invalid_board = False
        self.invert = self.inversion_check()
        self.generate_clean_board()
        self.validate_orbs()
        self.board_length = len(self.clean_board)
        self.eval_board_size()
        self.generate_link()

    def inversion_check(self):
        if BoardGenerator.inversion in self.board:
            invert = True
        else:
            invert = False

        return invert

    def generate_clean_board(self):
        board = self.board

        if self.invert:
            board.remove(BoardGenerator.inversion)
            clean = ''.join(self.invert_board(board))
        else:
            clean = ''.join(board)

        self.clean_board = clean

    def invert_board(self, board):
        build_string = []
        inverted_board = []

        try:
            for i in range(len(board[0])):
                for j in range(len(board)):
                    build_string.append(board[j][i])
                clean_string = ''.join(build_string)
                inverted_board.append(clean_string)
                build_string = []
        except:
            self.invalid_board = True

        return inverted_board

    def validate_orbs(self):
        if not all(letter in BoardGenerator.allowed_letters for letter in self.clean_board):
            invalid_orbs = True
        else:
            invalid_orbs = False

        self.invalid_orbs = invalid_orbs

    def eval_board_size(self):
        length = self.board_length

        if length == 20:
            height = 4
            width = 5
        elif length == 42:
            height = 6
            width = 7
        elif length == 30:
            height = 5
            width = 6
        else:
            height = 0
            width = 0
            self.invalid_board = True

        self.board_height = height
        self.board_width = width

    def generate_link(self):
        length = self.board_length
        link = BoardGenerator.dawnglare_link.format(self.clean_board)

        if length == 20 or length == 42:
            link = f"{link}&height={self.board_height}&width={self.board_width}"

        self.link = link
