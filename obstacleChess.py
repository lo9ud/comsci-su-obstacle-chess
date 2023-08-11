import sys
import game
import board
import output
import movehandler
from common import *


def main():
    # if len(sys.argv) <= 2:  # too few arguments
    #     return  # TODO: What do i do if there are no arguments/incorrect arguments?

    # Unpack input_, output_ and game_ file paths
    # using the list unpacking operator ensures this will succeed regardless of game_ path existing
    input_file_path, output_file_path, *opt = sys.argv[1:]

    # If the game_ path exists (i.e. the opt list has any elements), extract it from the list
    game_file_path = opt[0] if len(opt) > 0 else ""

    # Read the file in
    with open(input_file_path, "r") as input_file:
        raw_file_contents = input_file.readlines()
    # Strip out comments and empty lines
    comments_stripped = [
        line for line in raw_file_contents if not line.startswith("%")]
    file_contents = [
        line.replace("\n", "") for line in comments_stripped
    ]

    # check for empty file:
    if not file_contents:
        # If empty, error on first tile and return
        err_print(output.Error.ILLEGAL_BOARD % algebraic(0, 0))
        return

    # Attempt to create a board
    # TODO: there cannot be spaces in the board, must error on a space (i.e. is an invalid piece)
    start_board = board.Board.from_strs(file_contents)
    if isinstance(start_board, Failure):
        # If the board creation failed, notify and early return
        err_print(f"ERROR: {start_board.unwrap()}")
        return
    # Board creation passed, unwrap result
    start_board = start_board.unwrap()

    # instantiate the game
    game_result = game.Game.from_board(start_board)
    if isinstance(game_result, Failure):
        err_print(f"ERROR: {game_result.unwrap()}")
        return
    current_game = game_result.unwrap()

    # open output file
    with open(output_file_path, "w") as output_file:
        # dump the board to the output file
        current_game.dump_board(stream=output_file)


if __name__ == "__main__":
    main()
