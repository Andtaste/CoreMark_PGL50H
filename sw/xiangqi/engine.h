#ifndef XIANGQI_ENGINE_H
#define XIANGQI_ENGINE_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef int (*XQStop)(void *context);
typedef struct {
 uint32_t nodes,qnodes,tt_probes,tt_hits,cutoffs;
 int32_t move,score,depth,stopped;
} XQResult;
void xq_init(void);
void xq_new(void);
void xq_clear_tt(void);
int xq_get(int square);
int xq_side(void);
int xq_ply(void);
int xq_checked(void);
int xq_outcome(void); /* 0 playing, 1 red wins, 2 black wins, 3 draw */
int xq_play(int from,int to);
int xq_undo(void);
int xq_fen(const char *fen);
int xq_legal(int from,int to);
uint64_t xq_perft(unsigned depth);
XQResult xq_search(unsigned depth,uint32_t node_limit,XQStop stop,void *context);
int xq_move_from(int move);
int xq_move_to(int move);
uint32_t xq_history_bytes(void);
uint32_t xq_tt_bytes(void);
#ifdef __cplusplus
}
#endif
#endif
