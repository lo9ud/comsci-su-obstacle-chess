import sys
from src import game, board, output

DEBUG = True

def get_input_or_fail(prompt:str) -> str:
    if DEBUG:
        return input(prompt)
    else:
        raise ValueError("No input file path provided")

def main():
    # Get the input and output file paths from the command line arguments
    if len(sys.argv) > 1:
        input_file_path, output_file_path, *game_file_path = sys.argv[1:]
        if game_file_path:
            game_file_path = game_file_path[0] # extracts the game file path from the list
    else:
        input_file_path = get_input_or_fail("Enter the input file path: ")
        output_file_path = get_input_or_fail("Enter the output file path: ")
    
    # create a board from the input file
    with open(input_file_path, 'r') as input_file:
        file_contents = input_file.readlines()
        # Strip out comments and empty lines
        file_contents = [line.replace("\n", "").replace(" ","") for line in file_contents if not (line.startswith("%") and line not in {"\n", "\r", "\r\n",""})]
        start_board = board.Board.from_str(file_contents[:-1])
        start_state = board.BoardState.from_str(start_board, file_contents[-1])
        
    
    # instantiate the game
    try:
        current_game = game.Game(start_board, start_state)
    except output.BoardError as e:
        output.print_error(e.error, e.param)
    

if __name__ == '__main__': main()