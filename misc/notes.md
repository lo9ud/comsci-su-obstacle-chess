# Notes

---------------------
Things to check:

- Check that a piece exists at origin
- Check that the piece is of the correct color
- Check that the piece can move to destination
- Check that the destination is not occupied by a piece of the same color
- Check that the path to the destination is clear
- Check that the king is not in check after the move
- Pawns:
  - Check that the pawn is not moving diagonally if there is no piece to capture
  - Check that the pawn is not moving forward if there is a piece in front of it
  - Check that the pawn is not moving two squares forward if there is a piece in front of it
  - check for en passant
- Kings:
  - Check that the king is not moving into check
  - Check for castling
- Mines/Traps:
  - Check for initial move > 0
  - Null moves only if move > 0
- Fix castling being weird as hell
- Initial move checks
  - incr/decr
  - null
  - standard state y/n
- Check
  - can place wall to block check
  