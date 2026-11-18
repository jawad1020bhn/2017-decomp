/* incoming.c -- which club makes an offer for one of the user's players (MLTransfers.lua,
 * INCOMING). This file is what the module's routine means; the module ships the assembly
 * gcc makes of it, kept in money_cave.py as INCOMING_SOURCE (keystone assembles that, so the
 * build needs no compiler). offer_source.py regenerates the assembly from here.
 *
 * Entered at fcn_0381e2eb in the place of its prologue: the routine of fcn_03652df0 that
 * creates an offer asks it for the buying club. Only the key 0x02100a66 (the slot the offer
 * creator asks for) is touched; every other call runs the game's own code.
 *
 * pick() answers 0 when the game's own answer should stand (nothing passes, or the game's
 * club itself passes), else the club to answer with. The rules, in the order of
 * money_cave.accepts (the routine MLTransfers.lua puts in ai_candidates), narrowed to what
 * a club that is not choosing a player for its own plan can be asked:
 *
 *   * the club is not the club whose player it is, and the game does not skip it (+0x31e);
 *   * it is not a rival of that club (RIVALS);
 *   * PERSONA: the player is in the age band of its archetype (with `strict` weighing the
 *     draw), the rating it makes of him (with `fog` on it) is not below its eleven by more
 *     than `ambition`, and he is not above its eleven by more than `prestige`;
 *   * SCOUTING: it knows him (`knows`); a listed player, one rated KNOWN_FROM or more and a
 *     famous one (KNOWN_FAME) are known to every club;
 *   * the place it buys from: for this position, this time, it looks among the players
 *     without a contract, the listed players or the players of other clubs (`free`, `listed`,
 *     `clubs`); unless the position need marked his position, it takes him only when it
 *     looks where he is;
 *   * NEED: its plan record (mode data + 0xccb80c) has a free slot that asks for his
 *     position, or the position need of MLTransfers.lua marked that position (the byte at
 *     +0x109, with the rating its search starts above next to it). Without one of the two it
 *     does not buy for that position at all; a marked position is a club in want of him: it
 *     stretches its ceiling (`panic`) and it does not mind his age or his rating;
 *   * AFFORDABILITY: his value (the value routine of MLMoney.lua) after the discount for a
 *     player without a contract or one listed by his club does not exceed the ceiling of its
 *     level raised by its persona (wealth, and the panic of a club in want of him) and by the
 *     premium draw. The fee is not touched: MLMoney.lua works it out later.
 *
 * Every draw of these rules takes the day of the career into it (the day number at mode data
 * + 0xc2cbb0, the year after it), so that the club that bids for a player is not the same
 * club every day of the window. The day is the one the game itself puts into the offer.
 *
 * The club answered is the one whose slot ([club + 0x314] >> 7) is nearest to the game's
 * own among those that pass. The game's own room test (fcn_03652df0: more than 16 players)
 * is not made here: the game makes it.
 */
#define u32 unsigned int
#define u8 unsigned char

#define U(x) (*(volatile u32 *)(x))               /* a dword */
#define W_(x) (*(volatile unsigned short *)(x))   /* a word */
#define B(x) (*(volatile u8 *)(x))                /* a byte */

/* the free memory MLTransfers.lua writes (money_cave.py: CAVE_2) */
#define CEILING_TAB 0x047d4200u          /* 10 dwords by club level: the value it takes for sure */
#define STRETCH_AT 0x047d4234u           /* percent above the ceiling at which the chance ends */
#define NEED_AT 0x047d4238u              /* percent by which need raises the ceiling */
#define FREE_AT 0x047d423cu              /* percent of his value for a player without a contract */
#define LISTED_AT 0x047d4240u            /* the same for a player listed by his club */
#define PERSONA_LOW_AT 0x047d4244u
#define PERSONA_RANGE_AT 0x047d4248u
#define STRENGTH_A_AT 0x047d424cu        /* rating points per ranking point, times 65536 */
#define STRENGTH_B_AT 0x047d4250u
#define HAND_COUNT_AT 0x047d4260u
#define RANGE_LOW_TAB 0x047d4264u        /* 10 bytes by club level */
#define RANGE_TOP_TAB 0x047d426eu
#define BY_LEVEL_TAB 0x047d4278u         /* 10 rows of 8 bytes: the personas of a level */
#define GENES_TAB 0x047d42c8u            /* 16 personas of 20 bytes */
#define HAND_TYPES 0x047d4408u           /* 192 bytes: the persona of a named club */
#define HAND_IDS 0x047d44c8u             /* 192 dwords: the ids of the named clubs */
#define RIVAL_COUNT_AT 0x047d47c8u
#define RIVAL_PAIRS 0x047d47ccu          /* 64 pairs of dwords */
#define STRICT_FREE_AT 0x047d4fe8u
#define AGE_SHIFT_AT 0x047d4ffcu
#define FAME_KNOWN_AT 0x047d4fe4u        /* a player of this popularity or more is known to every club, times 1 << 20 */
#define KNOWN_AT 0x047d4ff8u             /* a player of this rating or more is known to every club */
/* the free memory MLMoney.lua writes (money_cave.py: CAVE) */
#define FEE_CODE 0x047b0c90u             /* eax = rating, ebx = player record -> value in edi */
/* the game */
#define MODE_OBJECT_AT 0x026503e0u       /* dword: the mode object; its +0x30 is the mode data */
#define MODE_DAY 0xc2cbb0u               /* word: the day of the year, 0 = 1 January; the year after it */
#define CURRENT_CLUB_AT 0x0251f85cu      /* dword: the club of the player being handled */
#define FIND_PLAYER 0x03822835u          /* (id low, id high), ecx = mode data -> the player record */
#define RATING 0x03853b42u               /* (player record, -> position, kind) -> rating in al */
#define CLUB_TABLE 0x481be0u             /* mode data: the clubs, records of 0x520 */
#define CLUB_TABLE_COUNT 0x5fece0u
#define CLUB_STRIDE 0x520u
#define CLUB_FLAGS 0x31eu
#define CLUB_SLOT 0x314u
#define RANK_TABLE 0xcc84ccu             /* mode data: the club ranking, 16-byte records */
#define RANK_COUNT 0x28a0u
#define RANK_MOST 650
#define PLAN_RECORDS 0xccb80cu           /* mode data: one plan record per club, 0x118 bytes */
#define PLAN_SIZE 0x118u
#define PLAN_MOST 851
#define PLAN_COUNT 0xd06434u
#define PLAN_SLOTS 16
#define PLAN_NEED_AT 0x109u              /* two bytes: position + 1, and the rating the search starts above */
#define NO_POSITION 13

#define LEVELS 10
#define HAND 192
#define RIVALS 64
#define PERSONA_BYTES 20
#define NO_CEILING 0xffffffffu
#define NO_CLUB 0xffffffffu
#define MOST_CLUBS 0x400

/* the entries of a persona (money_cave.py: GENE_NAMES) */
#define FREE 0
#define LISTED 1
#define CLUBS 2
#define WINTER 3
#define KNOWS 4
#define FOG 5
#define WEALTH 6
#define PREMIUM 7
#define PANIC 8
#define FAME 9
#define AMBITION 10
#define PRESTIGE 11
#define STRICT 13
#define AGE_FROM 14
#define AGE_TO 15
/* the two bytes after them: where the second search looks (money_cave.py: THEN_1, THEN_2) */
#define THEN_1 16
#define NO_CHANNELS 0xff

#define HASH_A 0x01000193u
#define HASH_B 0x9e3779b1u
#define HASH_C 0x85ebca6bu
#define HASH_AGE 0x1b873593u
#define HASH_FOG 0xe6546b65u
#define HASH_SHIFT 0x2545f491u
#define HASH_KNOWS 0x165667b1u
#define HASH_POSITION 0xc2b2ae35u

/* ---- the game's own routines, entered as its code enters them ------------- */

extern u32 value_oracle(u32 rec, u32 rating);
extern u32 rating_oracle(u32 rec, u32 scratch);
extern u32 player_oracle(u32 idl, u32 idh, u32 mode);

__asm__(
        ".globl value_oracle\n"
        "value_oracle:\n"                 /* (rec, rating) */
        "    push ebp\n"
        "    push ebx\n"
        "    push edi\n"
        "    sub esp, 0x20\n"
        "    mov ebp, esp\n"
        "    mov ebx, [ebp + 0x30]\n"     /* rec: the first argument */
        "    mov eax, [ebp + 0x34]\n"     /* rating */
        "    call 0x047b0c90\n"           /* the value routine of MLMoney.lua -> edi */
        "    mov eax, edi\n"
        "    add esp, 0x20\n"
        "    pop edi\n"
        "    pop ebx\n"
        "    pop ebp\n"
        "    ret\n"
        ".globl rating_oracle\n"
        "rating_oracle:\n"                /* (rec, -> scratch) -> rating in al */
        "    push esi\n"
        "    push edi\n"
        "    mov eax, [esp + 0xc]\n"      /* rec */
        "    mov ecx, [esp + 0x10]\n"     /* the scratch dword, as the position */
        "    mov dword ptr [ecx], 13\n"
        "    push 2\n"
        "    push ecx\n"
        "    push eax\n"
        "    call 0x03853b42\n"
        "    add esp, 12\n"
        "    movzx eax, al\n"
        "    pop edi\n"
        "    pop esi\n"
        "    ret\n"
        ".globl player_oracle\n"
        "player_oracle:\n"                /* (id low, id high, mode data) */
        "    mov eax, [esp + 4]\n"
        "    mov edx, [esp + 8]\n"
        "    mov ecx, [esp + 0xc]\n"
        "    push edx\n"
        "    push eax\n"
        "    call 0x03822835\n"           /* ret 8 */
        "    ret\n"
        );

/* the player being offered (what every rule needs of him) */
struct player {
    u32 rec;                             /* his record */
    u32 key;                             /* the key of his id (player_key) */
    u32 rating;                          /* as the game rates him */
    u32 pos;                             /* the position of his record: the value routine's own */
    u32 scratch;                         /* the dword the rating routine writes the position into */
    u32 age;
    u32 pop;                             /* popularity, 0 to 4095 */
    u32 where_;                          /* 0 no contract, 1 listed by his club, 2 any other */
};

static u32 club_key(u32 club) { return club * HASH_B; }

static u32 high_byte(u32 x, u32 factor) { return (x * factor) >> 24; }

/* a x b / c as the routines of the modules work it out: the largest number if it does not
   fit 32 bits */
static u32 muldiv(u32 a, u32 b, u32 c)
{
    u32 r;
    __asm__("mov eax, %1\n\t"
            "mul %2\n\t"
            "cmp edx, %3\n\t"
            "jae muldiv_over%= \n\t"
            "div %3\n\t"
            "jmp muldiv_done%= \n"
            "muldiv_over%= :\n\tmov eax, -1\n"
            "muldiv_done%= :\n\tmov %0, eax"
            : "=m"(r) : "m"(a), "m"(b), "m"(c) : "eax", "edx", "cc");
    return r;
}

/* ---- the tables --------------------------------------------------------- */

static u32 gene(u32 persona, int i, u32 club)
{
    u32 h = high_byte(((u32)i * HASH_A) ^ club_key(club), HASH_C);
    u32 f = U(PERSONA_LOW_AT) + ((h * U(PERSONA_RANGE_AT)) >> 8);
    return muldiv(B(persona + i), f, 1000);
}

static u32 persona_of(u32 club, u32 level)
{
    u32 n = U(HAND_COUNT_AT);
    if (n > HAND) n = HAND;
    while (n--) {                                    /* the last entry counts, as the routine of ai_candidates */
        if (U(HAND_IDS + 4 * n) == club) return GENES_TAB + PERSONA_BYTES * B(HAND_TYPES + n);
    }
    if (level > LEVELS - 1) level = LEVELS - 1;
    return GENES_TAB + PERSONA_BYTES * B(BY_LEVEL_TAB + 8 * level + (club_key(club) >> 29));
}

static u32 eleven_of(u32 points, u32 level)
{
    u32 v;
    if (level > LEVELS - 1) level = LEVELS - 1;
    v = (points * U(STRENGTH_A_AT) + U(STRENGTH_B_AT)) >> 16;
    if (v < B(RANGE_LOW_TAB + level)) v = B(RANGE_LOW_TAB + level);
    if (v > B(RANGE_TOP_TAB + level)) v = B(RANGE_TOP_TAB + level);
    return v;
}

/* its ranking record: the first, as the game's own search answers for a club it lacks */
static void rank_of(u32 mode, u32 club, u32 *points, u32 *level)
{
    u32 base = mode + RANK_TABLE, n = U(mode + RANK_COUNT), i, rec = base;
    if (n > RANK_MOST) n = RANK_MOST;
    for (i = 0; i < n; i++) {
        if (U(base + 16 * i) == club) { rec = base + 16 * i; break; }
    }
    *points = W_(rec + 8);
    *level = B(rec + 0xe);
}

static u32 plan_of(u32 mode, u32 club)
{
    u32 base = mode + PLAN_RECORDS, n = U(mode + PLAN_COUNT), i;
    if (n > PLAN_MOST) n = PLAN_MOST;
    for (i = 0; i < n; i++) {
        if (U(base + PLAN_SIZE * i) == club) return base + PLAN_SIZE * i;
    }
    return 0;
}

/* a free slot of its plan looks for his position (1), or the position need marked it (2) */
static int in_need(u32 plan, u32 pos, u32 rating)
{
    int i;
    if (!plan) return 0;
    for (i = 0; i < PLAN_SLOTS; i++) {
        u32 w = U(plan + 8 + 16 * i + 8);
        u32 state = (w >> 22) & 0x1f;
        u32 kind = (w >> 14) & 0xff;                 /* 0: nothing; 1 buy, 2 loan */
        if (kind && ((w >> 7) & 0x7f) == pos && (state == 0 || state == 7)) return 1;
    }
    return (B(plan + PLAN_NEED_AT) == pos + 1 && rating > B(plan + PLAN_NEED_AT + 1)) ? 2 : 0;
}

/* ---- the rules ---------------------------------------------------------- */

static int rival(u32 a, u32 b)
{
    u32 n = U(RIVAL_COUNT_AT), i;
    if (n > RIVALS) n = RIVALS;
    for (i = 0; i < n; i++) {
        u32 x = U(RIVAL_PAIRS + 8 * i), y = U(RIVAL_PAIRS + 8 * i + 4);
        if ((x == a && y == b) || (x == b && y == a)) return 1;
    }
    return 0;
}

/* would this club take him? (money_cave.offer_wants) rec: its record in the club table */
static int wants(u32 mode, u32 rec, const struct player *p)
{
    u32 club = U(rec), persona, g[PERSONA_BYTES], points, level, own, both, turn, date;
    u32 seen, price, limit, stretch, add, age_shift, need;

    if (rival(club, U(CURRENT_CLUB_AT))) return 0;
    rank_of(mode, club, &points, &level);
    persona = persona_of(club, level);
    {
        int i;
        for (i = 0; i < PERSONA_BYTES; i++) g[i] = gene(persona, i, club);
    }
    own = eleven_of(points, level);
    /* the day of the career: every draw of the rules takes it, so that the club that bids
       is not the same club on every day of the window */
    date = (W_(mode + MODE_DAY + 2) | (W_(mode + MODE_DAY) << 16)) * HASH_A;
    both = p->key ^ club_key(club) ^ date;
    turn = (p->pos * HASH_POSITION) ^ club_key(club) ^ date;
    /* need: it buys for that position at all; 2 when the position need marked it, that is,
       when this club is in want of him: it stretches its ceiling and does not mind his age
       or his rating, as a club with too small a squad does in the transfers of the computer
       clubs (money_cave.accepts) */
    need = in_need(plan_of(mode, club), p->pos, p->rating);
    if (!need && p->rating + g[AMBITION] >= own) need = 1;
    /* prestige: he does not join a club far below him */
    if (p->rating > own + g[PRESTIGE]) return 0;
    /* scouting: a club knows a part of the players; a listed player, a good one and a
       famous one are known to all */
    if (p->where_ != 1 && p->rating < U(KNOWN_AT) && p->pop < (U(FAME_KNOWN_AT) >> 20)
        && (high_byte(both, HASH_KNOWS) * 100) >> 8 >= g[KNOWS]) {
        return 0;
    }
    /* where it looks for a player of that position this time */
    if (B(persona + THEN_1) != NO_CHANNELS) {
        u32 draw = (high_byte(turn, HASH_C) * 100) >> 8;
        if (draw < g[FREE]) { if (p->where_ != 0) return 0; }
        else if (draw < g[FREE] + g[LISTED]) { if (p->where_ != 1) return 0; }
        else if (draw < g[FREE] + g[LISTED] + g[CLUBS]) { if (p->where_ != 2) return 0; }
        else if (need != 2 || B(persona + THEN_1) != p->where_) return 0;
    }
    if (!need) return 0;
    /* the ages of its archetype, with `strict` weighing the draw */
    if (need != 2) {
        age_shift = ((high_byte(club_key(club), HASH_SHIFT) * (2 * U(AGE_SHIFT_AT) + 1)) >> 8) - U(AGE_SHIFT_AT);
        if (!(p->age - age_shift >= B(persona + AGE_FROM) && p->age - age_shift <= B(persona + AGE_TO))) {
            u32 strict = g[STRICT] * (p->where_ == 0 ? U(STRICT_FREE_AT) : 100);
            u32 draw = (high_byte(both, HASH_AGE) * 100) >> 8;
            if (draw * 100 < strict) return 0;
        }
    }
    /* ambition: as this club sees him */
    seen = p->rating + ((high_byte(both, HASH_FOG) * (2 * g[FOG] + 1)) >> 8) - g[FOG];
    if (need != 2 && seen + g[AMBITION] < own) return 0;
    /* what it can afford */
    if (U(CEILING_TAB + 4 * level) == NO_CEILING) return 1;
    price = value_oracle(p->rec, seen);
    if (p->where_ != 2) price = muldiv(price, p->where_ == 0 ? U(FREE_AT) : U(LISTED_AT), 100);
    limit = muldiv(U(CEILING_TAB + 4 * level), g[WEALTH], 100);
    if (need == 2) limit = muldiv(limit, muldiv(U(NEED_AT), g[PANIC], 100) + 100, 100);
    stretch = muldiv(U(STRETCH_AT), g[PREMIUM], 100);
    add = muldiv(limit, high_byte(both, HASH_C) * stretch, 25600);
    limit = limit + add < limit ? NO_CLUB : limit + add;
    add = muldiv(limit, p->pop * g[FAME], 100000);
    limit = limit + add < limit ? NO_CLUB : limit + add;
    return price <= limit;
}

/* ---- the chooser -------------------------------------------------------- */

u32 pick(u32 mode, u32 frame, u32 key)
{
    struct player p;
    u32 deal, idl, idh, seller, base, count, i, c, slot, game_club = 0, best = 0, best_slot = 0x100;

    if (!mode) return 0;
    seller = U(CURRENT_CLUB_AT);
    if (!seller || seller == NO_CLUB) return 0;
    deal = U(frame + 8);
    if (!deal) return 0;
    idl = U(deal);
    idh = U(deal + 4);
    p.rec = player_oracle(idl, idh, mode);
    if (!p.rec || p.rec == NO_CLUB) return 0;
    if ((idl & 0xffff) != W_(p.rec + 0x2c)) return 0;   /* not the record the deal names */
    p.key = (idl & 0xffff) ^ (idh * HASH_A);
    p.pos = (U(p.rec + 4) >> 28) & 0xf;
    p.rating = rating_oracle(p.rec, (u32)&p.scratch);
    p.age = (U(p.rec + 0x1c) >> 7) & 0x3f;
    p.pop = (U(p.rec + 0xb4) >> 11) & 0xfff;
    p.where_ = (U(p.rec + 0xb4) & 0xf) - 1 <= 1 ? 0 : (U(p.rec + 0xb8) & 0x60000000) ? 1 : 2;

    base = mode + CLUB_TABLE;
    count = U(mode + CLUB_TABLE_COUNT);
    if (!count || count > MOST_CLUBS) return 0;
    for (i = 0; i < count; i++) {                 /* the club the game would answer */
        c = U(base + CLUB_STRIDE * i);
        if (!c || c == seller) continue;
        if ((U(base + CLUB_STRIDE * i + CLUB_FLAGS) & 7) == 1) continue;
        if (((U(base + CLUB_STRIDE * i + CLUB_SLOT) >> 7) & 0xff) == key) { game_club = c; break; }
    }
    if (game_club && wants(mode, base + CLUB_STRIDE * i, &p)) return 0;
    for (i = 0; i < count; i++) {
        c = U(base + CLUB_STRIDE * i);
        if (!c || c == seller) continue;
        if ((U(base + CLUB_STRIDE * i + CLUB_FLAGS) & 7) == 1) continue;
        if (!wants(mode, base + CLUB_STRIDE * i, &p)) continue;
        slot = (U(base + CLUB_STRIDE * i + CLUB_SLOT) >> 7) & 0xff;
        if ((slot >= key ? slot - key : key - slot) < best_slot) {
            best_slot = slot >= key ? slot - key : key - slot;
            best = c;
        }
    }
    return best;
}
