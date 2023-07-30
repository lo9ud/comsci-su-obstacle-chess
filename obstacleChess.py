import sys
from src import board, logger, piece


def main():
    if "--debug" in sys.argv:
        DEBUG = True
    else:
        DEBUG = False

    sys.argv.remove("--debug")

    outstream = logger.Logger(logger.StdOut, debug=DEBUG)
    board.Board.setlogger(outstream)

    input_file, output_file, *game_file = sys.argv[1:]
    start_board = board.Board.from_file(open(input_file))

    if game_file:
        game_file = game_file[0]
        start_board.apply_file(open(game_file))

    raise NotImplementedError


if __name__ == '__main__':
    main()
