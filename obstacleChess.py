import sys
import game, board, output
from common import *
import instream, outstream


def main():  # sourcery skip: extract-method
    if len(sys.argv) <= 2:  # too few arguments
        return  # TODO: What do i do if there are no arguments/incorrect arguments?

    # Unpack input_, output_ and game_ file paths
    # using the list unpacking operator ensures this will succeed regardless of game_ path existing
    input_file_path, output_file_path, *opt = sys.argv[1:]

    # If the game_ path exists (i.e. the opt list has any elements), extract it from the list
    game_file_path = opt[0] if len(opt) > 0 else ""

    # Create a stream for the input
    input_file = instream.InStream(input_file_path)
    raw_file_contents = input_file.readAllLines()
    # Strip out comments and empty lines
    comments_stripped = [line for line in raw_file_contents if not line.startswith("%")]
    file_contents = [
        line.replace("\n", "").replace(" ", "") for line in comments_stripped
    ]

    # Attempt to create a boardstate
    start_state = board.BoardState.from_str(file_contents[-1])
    if isinstance(start_state, Failure):
        # If the state creation failed, notify and early return
        stdio.writeln(f"ERROR: {output.Error.ILLEGAL_STATUSLINE}")
        return
    # State creation passed, unwrap result
    start_state = start_state.unwrap()

    # Attempt to create a board
    start_board = board.Board.from_str(file_contents[:-1], start_state)
    if isinstance(start_board, Failure):
        # If the board creation failed, notify and early return
        stdio.writeln(f"ERROR: {start_board.unwrap()}")
        return
    # Board creation passed, unwrap result
    start_board = start_board.unwrap()

    # instantiate the game
    current_game = game.Game(start_board)

    # validate the board
    validation_result = current_game.validate()
    if isinstance(validation_result, Failure):
        # Validation failed, print error to screen and early return
        stdio.writeln(f"ERROR: {validation_result.unwrap()}")
        return

    # create the output file
    output_file = outstream.OutStream(output_file_path)

    # write the game state to the output file
    output_file.write(current_game.canonical())


if __name__ == "__main__":
    main()
