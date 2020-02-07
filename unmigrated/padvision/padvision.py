import PIL.Image
import io
import traceback

ORB_IMG_SIZE = 40

class PadVision:
    def __init__(self, bot):
        self.bot = bot

def setup(bot):
    n = PadVision(bot)
    bot.add_cog(n)


###############################################################################
# Library code
###############################################################################

EXTRACTABLE = 'rbgldhjpmo'

# returns y, x
def board_iterator():
    for y in range(5):
        for x in range(6):
            yield y, x


class OrbExtractor(object):
    def __init__(self, img):
        self.img = img
        self.find_start_end()
        self.compute_sizes()

    def find_start_end(self):
        img = self.img
        height, width, _ = img.shape

        # Detect left/right border size
        xstart = 0
        while True:
            low = int(height * 2 / 3)
            # board starts in the lower half, and has slightly deeper indentation
            # than the monster display
            if max(img[low, xstart]) > 0:
                break
            xstart += 1

        # compute true baseline from the bottom (removes android buttons)
        yend = height - 1
        while True:
            if max(img[yend, xstart + 10]) > 0:
                break
            yend -= 1

        self.xstart = xstart
        self.yend = yend

        self.x_adj = 0
        self.y_adj = 2
        self.orb_adj = 1

    def compute_sizes(self):
        img = self.img
        height, width, _ = img.shape

        # compute true board size
        board_width = width - (self.xstart * 2) - self.x_adj
        orb_size = board_width / 6 - self.orb_adj

        ystart = self.yend - orb_size * 5 + self.y_adj

        self.ystart = ystart
        self.orb_size = orb_size

    def get_orb_vertices(self, x, y):
        # Consider adding an offset here to get rid of padding?
        offset = 0
        box_ystart = y * self.orb_size + self.ystart
        box_yend = box_ystart + self.orb_size
        box_xstart = x * self.orb_size + self.xstart
        box_xend = box_xstart + self.orb_size
        return int(box_xstart + offset), int(box_ystart + offset), int(box_xend - offset), int(box_yend - offset)

    def get_orb_coords(self, x, y):
        box_xstart, box_ystart, box_xend, box_yend = self.get_orb_vertices(x, y)
        coords = (slice(box_ystart, box_yend),
                slice(box_xstart, box_xend),
                slice(None))
        return coords

    def get_orb_img(self, x, y):
        return self.img[self.get_orb_coords(x, y)]



nn_orb_types = [
    'b',
    'd',
    'g',
    'h',
    'j',
    'l',
    'm',
    'o',
    'p',
    'r',
]

class NeuralClassifierBoardExtractor(object):
    def __init__(self, model_path, np_img, img_bytes):
        self.model_path = model_path
        self.np_img = np_img
        self.img = PIL.Image.open(io.BytesIO(img_bytes))
        self.processed = False
        self.results = [['u' for x in range(6)] for y in range(5)]

    def process(self):
        try:
            self._process()
        except Exception as ex:
            print("orb extractor failed " + str(ex))
            traceback.print_exc()

    def _process(self):
        import numpy as np
        import tensorflow as tf

        oe = OrbExtractor(self.np_img)

        # Load TFLite model and allocate tensors.
        interpreter = tf.contrib.lite.Interpreter(model_path=self.model_path)
        interpreter.allocate_tensors()

        # Get input and output tensors.
        input_details = interpreter.get_input_details()[0]
        output_details = interpreter.get_output_details()[0]

        input_orb_size = input_details['shape'][1]
        input_tensor_idx = input_details['index']
        output_tensor_idx = output_details['index']

        input_data = np.zeros((1, input_orb_size, input_orb_size, 3), dtype='uint8')

        for y, x in board_iterator():
            box_coords = oe.get_orb_vertices(x, y)
            orb_img = self.img.crop(box_coords)
            orb_img = orb_img.resize((input_orb_size, input_orb_size), PIL.Image.ANTIALIAS)
            input_data[0] = np.array(orb_img)

            interpreter.set_tensor(input_tensor_idx, input_data)
            interpreter.invoke()
            output_data = interpreter.get_tensor(output_tensor_idx)
            max_idx = np.argmax(output_data)
            self.results[y][x] = nn_orb_types[max_idx]

    def get_board(self):
        if not self.processed:
            self.process()
            self.processed = True
        return self.results

