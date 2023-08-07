import sys
import game, board, output
from common import *


def main():
    if len(sys.argv) <= 2:  # too few arguments
        return  # TODO: What do i do if there are no arguments/incorrect arguments?

    # Unpack input_, output_ and game_ file paths
    # using the list unpacking operator ensures this will succeed regardless of game_ path existing
    input_file_path, output_file_path, *opt = sys.argv[1:]

    # If the game_ path exists (i.e. the opt list has any elements), extract it from the list
    game_file_path = opt[0] if len(opt) > 0 else ""

    # Read the file in
    with open(input_file_path, "r") as input_file:
        raw_file_contents = input_file.readlines()
    # Strip out comments and empty lines
    comments_stripped = [line for line in raw_file_contents if not line.startswith("%")]
    file_contents = [
        line.replace("\n", "") for line in comments_stripped
    ]

    # check for empty file:
    if not file_contents:
        # If empty, error on first tile and return
        err_print(output.Error.ILLEGAL_BOARD % algebraic(0, 0))
        return
    # Attempt to create a boardstate
    start_state = board.BoardState.from_str(file_contents[-1])
    if isinstance(start_state, Failure):
        # If the state creation failed, notify and early return
        err_print(f"ERROR: {output.Error.ILLEGAL_STATUSLINE}")
        return
    # State creation passed, unwrap result
    start_state = start_state.unwrap()

    # Attempt to create a board
    start_board = board.Board.from_strs(file_contents[:-1], start_state)
    if isinstance(start_board, Failure):
        # If the board creation failed, notify and early return
        err_print(f"ERROR: {start_board.unwrap()}")
        return
    # Board creation passed, unwrap result
    start_board = start_board.unwrap()

    # instantiate the game
    current_game = game.Game(start_board)

    # validate the board
    validation_result = current_game.validate()
    if isinstance(validation_result, Failure):
        # Validation failed, print error to screen and early return
        err_print(f"ERROR: {validation_result.unwrap()}")
        return

    # create the output file
    with open(output_file_path, "w") as output_file:
        # write the game state to the output file
        output_file.write(current_game.canonical())


if __name__ == "__main__":
    main()
