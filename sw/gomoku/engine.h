#ifndef GOMOKU_ENGINE_H
#define GOMOKU_ENGINE_H
#include <stdint.h>
#define G_SIZE 15
#define G_STRIDE 17
#define G_CELLS 289
#define G_MAX_PLY 20
#define G_CANDIDATES 24
typedef struct {
 uint8_t board[G_CELLS],nearby[G_CELLS];
 uint16_t pattern[2][G_CELLS][4],history[225],count;
 uint8_t side,winner;
 int32_t total[2];
 uint64_t hash;
} Gomoku;
typedef struct {uint16_t pos;int32_t rank;} GMove;
typedef struct {
 uint32_t nodes,tt_hits,cutoffs;
 int32_t score;
 int16_t x,y;
 uint8_t depth,stopped;
} GResult;
typedef int (*GStop)(void *context);
void g_new(Gomoku *g);
int g_play(Gomoku *g,int x,int y);
int g_undo(Gomoku *g);
int g_at(const Gomoku *g,int x,int y);
void g_clear_table(void);
GResult g_search(Gomoku *g,unsigned depth,uint32_t node_limit,GStop stop,void *context);
int g_consistent(const Gomoku *g);
#endif
