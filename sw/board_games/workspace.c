#include <stdint.h>
/* Exactly one owner at a time: Xiangqi history or Gomoku search/game state.
 * Mode changes occur only after the synchronous search has returned.
 * The linker retains the original fixed Xiangqi board and history positions.
 */
unsigned char board_workspace[32400] __attribute__((section(".history"),aligned(64)));
