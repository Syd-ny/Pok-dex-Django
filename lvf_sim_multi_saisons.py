# LVF_sim_multi_saisons.py
# ============================================
# Ligue Virtuelle des Fléchettes – Multi-saisons
# ============================================
from __future__ import annotations

from itertools import combinations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Set
import math
import random
import json
import csv
from pathlib import Path
import argparse

# ==========================
# CONFIGURATION GLOBALE LVF
# ==========================

class CONFIG:
    RNG_SEED: Optional[int] = 47   # None pour hasard non déterministe

    NATIONALITY_WEIGHTS = {
        "GBR": 14, "NLD": 14, "IRL": 8, "BEL": 7, "FRA": 7,
        "DEU": 6, "ESP": 5, "ITA": 5, "SWE": 4, "DNK": 3, "NOR": 3,
        "PRT": 3, "CHE": 2, "AUT": 2, "CZE": 2, "POL": 2, "SCO": 4,
        "WAL": 2, "ISL": 1, "ROU": 2, "SRB": 1, "UKR": 1, "MAR": 1,
        "JPN": 2, "CAN": 1, "USA": 1,
    }

    # Ages
    AGE_MIN = 16
    AGE_MAX = 65

    # Distribution des niveaux (points / volée de 3) ~ loi normale tronquée
    SKILL_MIN = 5.0
    SKILL_MAX = 90.0
    SKILL_MEAN = 40.0
    SKILL_SD = 15.0

    # Variance par visite
    VISIT_SD_FACTOR = 0.18
    VISIT_MIN_SD = 6.0

    # Talents (base 10)
    TALENT_BASE_P_SIMPLE = 0.075
    TALENT_BASE_P_DOUBLE = 0.013
    TALENT_BASE_P_TRIPLE = 0.0015
    TRIPLE_STACK_MALUS = 0.55

    # Modèle de checkout
    FINISH_A = -6.0
    FINISH_B = 0.09
    FINISH_C = 0.9

    # Relations
    REL_BASE = {"tight": 0.35, "mid": 0.20, "sweep": 0.05}
    REL_CULTURE = {"SAME": 1.15, "CLOSE": 1.10, "FAR": 0.90}
    REL_AGE_DIFF_MALUS_PER_YEAR = 0.005

    # Romance
    ROMANCE_MIN_AGE = 18
    ROMANCE_MAX_AGE_DIFF = 5
    ROMANCE_BASE = 0.05
    COUPLE_THRESHOLD = 45.0
    NPC_COUPLE_CHANCE = 0.02
    BIRTH_CHANCE_ANNUAL = 0.18

    # Divisions & formats
    D1_PLAYERS = 36
    D1_MATCHES = 20
    D2_GROUPS = 2; D2_PLAYERS_PER_GROUP = 58
    D3_GROUPS = 3; D3_PLAYERS_PER_GROUP = 84
    D4_GROUPS = 4; D4_PLAYERS_PER_GROUP = 120

    # Barèmes (corrigés)
    BO3_POINTS = {
        "intra": {(2,1): 2, (2,0): 4},
        "inter": {(2,1): 1, (2,0): 3},
    }
    BO5_POINTS = {
        "intra": {(3,2): 2, (3,1): 4, (3,0): 7},
        "inter": {(3,2): 1, (3,1): 3, (3,0): 5},
    }

    # Déclin & progression inter-saisons
    AGE_DECLINE_START = 33
    AGE_DECLINE_PER_YEAR = 0.25
    AGE_DECLINE_44 = 0.45
    AGE_DECLINE_60 = 0.9
    OFFSEASON_PROGRESS_SCALE = 2.8

    # Retraite
    RETIRE_SOFT_START = 35
    RETIRE_HARD = 66
    RETIRE_EXP_BASE = 0.015
    PERFORMANCE_DELTA_FACTOR = 0.02

# =============
# OUTILS RNG
# =============

class RNG:
    _rng: random.Random = random.Random()

    @classmethod
    def seed(cls, s: Optional[int]):
        if s is None:
            cls._rng = random.Random()
        else:
            cls._rng = random.Random(s)

    @classmethod
    def rand(cls) -> float:
        return cls._rng.random()

    @classmethod
    def choice(cls, seq):
        return cls._rng.choice(seq)

    @classmethod
    def randint(cls, a, b):
        return cls._rng.randint(a, b)

    @classmethod
    def gauss(cls, mu, sd):
        return cls._rng.gauss(mu, sd)

# =============
# UTILITAIRES
# =============

def truncated_normal(mu: float, sd: float, lo: float, hi: float) -> float:
    x = mu
    for _ in range(16):
        x = RNG.gauss(mu, sd)
        if lo <= x <= hi:
            break
    return max(lo, min(hi, x))

# =====================
# MODÈLES DE DONNÉES
# =====================

@dataclass
class Relationship:
    target_id: int
    kind: str  # "affinite" | "rivalite" | "romance"
    strength: float = 10.0  # 0..100

@dataclass
class Player:
    pid: int
    name: str
    nickname: str
    age: int
    nation: str
    sex: str = "M"
    orientation: str = "hetero"

    # Niveau général (moyenne / volée)
    skill: float = 40.0
    skill_sd: float = 8.0
    potential: float = 40.0
    morale: float = 0.7

    # Talents (base 10, typiquement 6–18)
    talent_simple: float = 10.0
    talent_double: float = 10.0
    talent_triple: float = 10.0

    # Compétences fines par type (facteurs multiplicatifs)
    aim_simple: float = 1.0
    aim_double: float = 1.0
    aim_triple: float = 1.0

    # Potentiels par type (0..100)
    pot_simple: float = 50.0
    pot_double: float = 50.0
    pot_triple: float = 50.0

    # Caractéristiques additionnelles
    target_pref: str = "T20"
    tempo: float = 1.0
    clutch: float = 1.0
    streak: float = 0.0

    # Vie sociale / perso
    relations: Dict[int, Relationship] = field(default_factory=dict)
    partner_id: Optional[int] = None
    npc_partner: bool = False
    children: int = 0

    # Compétition
    division: str = "D4"
    group: Optional[str] = None
    points: int = 0
    legs_for: int = 0
    legs_against: int = 0

    # Suivi de performance saisonnière (pour retraite)
    season_points: int = 0
    best_season_points: int = 0

    def reset_competition(self):
        self.points = 0
        self.legs_for = 0
        self.legs_against = 0

    @property
    def legs_diff(self) -> int:
        return self.legs_for - self.legs_against

    def expected_visit_sd(self) -> float:
        base = max(CONFIG.VISIT_MIN_SD, self.skill * CONFIG.VISIT_SD_FACTOR)
        base *= (0.9 + 0.2 * self.tempo)
        base *= (0.95 + 0.1 * (0.5 + self.streak))
        return base

    def _age_decline_step(self) -> float:
        if self.age < 44:
            return CONFIG.AGE_DECLINE_PER_YEAR
        if self.age < 60:
            return CONFIG.AGE_DECLINE_44
        return CONFIG.AGE_DECLINE_60

    def aging_and_progress(self):
        # Déclin lié à l'âge
        if self.age >= CONFIG.AGE_DECLINE_START:
            self.skill -= self._age_decline_step() * (0.5 + RNG.rand())
        # Progression hors-saison (globale)
        youth_factor = max(0.0, (30 - self.age) / 16.0)
        gain = (self.potential / 100.0) * CONFIG.OFFSEASON_PROGRESS_SCALE * youth_factor * RNG.rand()
        self.skill += gain
        # Clamp
        self.skill = max(CONFIG.SKILL_MIN, min(CONFIG.SKILL_MAX, self.skill))
        # Progression fine par type
        for kind in ("simple", "double", "triple"):
            potk = getattr(self, f"pot_{kind}")
            fine_gain = (potk / 100.0) * CONFIG.OFFSEASON_PROGRESS_SCALE * youth_factor * RNG.rand() * 0.6
            cur = getattr(self, f"aim_{kind}")
            cur += fine_gain * 0.02
            setattr(self, f"aim_{kind}", max(0.7, min(1.3, cur)))
        self.age += 1

    def should_retire(self) -> bool:
        if self.age >= CONFIG.RETIRE_HARD:
            return True
        if self.age < CONFIG.RETIRE_SOFT_START:
            return False
        age_term = math.exp(CONFIG.RETIRE_EXP_BASE * (self.age - CONFIG.RETIRE_SOFT_START)) - 1.0
        delta = max(0, self.best_season_points - self.season_points)
        perf_term = 1.0 + CONFIG.PERFORMANCE_DELTA_FACTOR * delta
        p = min(0.85, 0.02 * age_term * perf_term)
        return RNG.rand() < p

# ========================
# GÉNÉRATION DES JOUEURS
# ========================

FIRST_NAMES_M = ["Liam","Noah","Ethan","Lucas","Oscar","Yann","Ivan","Markus","Carlos","Akira","Niko","Andrei","Tom","Kai"]
FIRST_NAMES_F = ["Amandine","Hanna","Sofia","Lucia","Marie","Fiona","Petra","Olga","Anna","Mika","Yuki","Chloe","Laura","Ines"]
SURNAMES = ["Smith","Brown","Taylor","Walker","Miller","Cooper","Clark","Baker","Foster","Carter","Parker","Turner","Marshall","Schmidt","Müller","Wagner","Fischer","Weber","Becker","Keller","Brandt","Kraus"]
NICK_FRAGMENTS = [
    ("The", ["Calm","Fox","Owl","Moose","Blade","Shadow","Mechanic","Bull","Ice","Storm","Omen","Comet","Spark","Mirage","Voltage","Vortex","Beacon","Anchor","Cipher","Quartz","Aegis"]),
    ("", ["Golden Arm","High Voltage","Dragon Fury","Steel Rain","Lucky Dart","Silver Fang","Green Fire","Red Comet","Neon Pulse","Night Shift","Cold Ember"])
]

def weighted_choice(weights: Dict[str, int]) -> str:
    total = sum(weights.values())
    r = RNG.rand() * total
    acc = 0
    for k, w in weights.items():
        acc += w
        if r <= acc:
            return k
    return list(weights.keys())[-1]

def synth_name() -> Tuple[str,str]:
    first = RNG.choice(FIRST_NAMES_F if RNG.rand()<0.18 else FIRST_NAMES_M)
    last = RNG.choice(SURNAMES)
    return first, last

class PlayerFactory:
    _next_id = 1

    @classmethod
    def make_player(cls) -> Player:
        nation = weighted_choice(CONFIG.NATIONALITY_WEIGHTS)
        sex = "F" if RNG.rand() < 0.18 else "M"
        first, last = synth_name()
        full_name = f"{first} {last}"
        prefix, words = RNG.choice(NICK_FRAGMENTS)
        exotic = ""
        if RNG.rand() < 0.15:
            exotic = RNG.choice(["El ","La ","Il ","Le ","Der ","The ","O'","Van ","Van der ","Al-"])
        nick = (prefix + (" " if prefix else "") + exotic + RNG.choice(words)).strip()
        age = RNG.randint(CONFIG.AGE_MIN, CONFIG.AGE_MAX)
        skill = truncated_normal(CONFIG.SKILL_MEAN, CONFIG.SKILL_SD, CONFIG.SKILL_MIN, CONFIG.SKILL_MAX)
        potential = max(10.0, min(95.0, truncated_normal(50, 20, 5, 98)))
        aim_simple = max(0.7, min(1.3, RNG.gauss(1.0, 0.08)))
        aim_double = max(0.7, min(1.3, RNG.gauss(1.0, 0.08)))
        aim_triple = max(0.7, min(1.3, RNG.gauss(1.0, 0.08)))
        pot_simple = max(5.0, min(98.0, truncated_normal(50, 18, 5, 98)))
        pot_double = max(5.0, min(98.0, truncated_normal(50, 18, 5, 98)))
        pot_triple = max(5.0, min(98.0, truncated_normal(50, 18, 5, 98)))
        p = Player(
            pid=cls._next_id,
            name=full_name,
            nickname=nick,
            age=age,
            nation=nation,
            sex=sex,
            skill=skill,
            skill_sd=max(6.0, skill * CONFIG.VISIT_SD_FACTOR),
            potential=potential,
            target_pref=RNG.choice(["T20","T20","T20","T19","T18"]),
            tempo=max(0.8, min(1.3, truncated_normal(1.0, 0.12, 0.75, 1.35))),
            clutch=max(0.9, min(1.2, truncated_normal(1.0, 0.08, 0.85, 1.25))),
            streak=(RNG.rand()-0.5)*0.2,
            talent_simple=max(4.0, truncated_normal(10, 3, 2, 20)),
            talent_double=max(3.0, truncated_normal(10, 3, 2, 20)),
            talent_triple=max(2.0, truncated_normal(10, 3, 2, 22)),
            aim_simple=aim_simple, aim_double=aim_double, aim_triple=aim_triple,
            pot_simple=pot_simple, pot_double=pot_double, pot_triple=pot_triple
        )
        cls._next_id += 1
        return p

# =====================
# SIMULATEUR DE MATCH
# =====================

def finish_probability(skill: float, remaining: int) -> float:
    x = CONFIG.FINISH_A + CONFIG.FINISH_B*skill - CONFIG.FINISH_C*math.log(max(2, remaining))
    return 1.0 / (1.0 + math.exp(-x))

def _talent_logistic(base_p_at10: float, talent: float) -> float:
    if talent <= 0:
        return 0.0
    k = -math.log(1 - base_p_at10) / 10.0
    return 1.0 - math.exp(-k * talent)

def per_dart_hit_probs(p: Player) -> Tuple[float,float,float]:
    """
    1) Talents → probas brutes
    2) Modulation par compétences fines (aim_*)
    3) Ajustement (bisection) pour coller l'espérance à p.skill/3 (calibration scoring)
    """
    ps0 = _talent_logistic(CONFIG.TALENT_BASE_P_SIMPLE, p.talent_simple) * p.aim_simple
    pd0 = _talent_logistic(CONFIG.TALENT_BASE_P_DOUBLE, p.talent_double) * p.aim_double
    pt0 = _talent_logistic(CONFIG.TALENT_BASE_P_TRIPLE, p.talent_triple) * p.aim_triple

    if p.target_pref == "T19":
        pt0 *= 1.03
    elif p.target_pref == "T18":
        pt0 *= 1.02
    else:
        pt0 *= 1.03

    # Miss ~ augmente doucement avec skill
    miss_mu = max(6.0, min(22.0, 10.0 + 0.10 * p.skill))
    E_miss = miss_mu
    target_per_dart = max(5.0, min(30.0, p.skill / 3.0))

    def expected_per_dart(alpha: float):
        pt = alpha * pt0
        pd = alpha * pd0
        ps = alpha * ps0
        s = pt + pd + ps
        if s > 0.98:
            pt *= 0.98 / s
            pd *= 0.98 / s
            ps *= 0.98 / s
            s = 0.98
        return pt*60.0 + pd*40.0 + ps*20.0 + (1.0 - s) * E_miss, (ps, pd, pt)

    lo, hi = 0.25, 3.0
    best_ps, best_pd, best_pt = ps0, pd0, pt0
    for _ in range(28):
        mid = 0.5 * (lo + hi)
        E, (ps_mid, pd_mid, pt_mid) = expected_per_dart(mid)
        if E < target_per_dart:
            lo = mid
        else:
            hi = mid
            best_ps, best_pd, best_pt = ps_mid, pd_mid, pt_mid

    return best_ps, best_pd, best_pt

def simulate_leg(pA: Player, pB: Player, starter: str, leg_target: int = 501) -> str:
    scoreA = leg_target
    scoreB = leg_target
    turn = starter
    psA, pdA, ptA = per_dart_hit_probs(pA)
    psB, pdB, ptB = per_dart_hit_probs(pB)
    while True:
        if turn == 'A':
            triples = 0
            visit = 0
            for _ in range(3):
                adj_pt = ptA * (CONFIG.TRIPLE_STACK_MALUS ** triples)
                r = RNG.rand()
                if r < adj_pt:
                    triples += 1; visit += 60
                elif r < adj_pt + pdA:
                    visit += 40
                elif r < adj_pt + pdA + psA:
                    visit += 20
                else:
                    visit += max(0, int(truncated_normal(10.0 + 0.10 * pA.skill, 5.0 * pA.tempo, 0, 26)))
            scoreA = max(0, scoreA - visit)
            clutch_mult = 1.0 + min(0.2, (pA.clutch - 1.0) * 0.2)
            if 2 <= scoreA <= 170:
                if RNG.rand() < min(0.98, finish_probability(pA.skill, scoreA) * (clutch_mult if scoreA <= 100 else 1.0)):
                    return 'A'
            elif scoreA == 1:
                scoreA += 1
            elif scoreA == 0:
                return 'A'
            turn = 'B'
        else:
            triples = 0
            visit = 0
            for _ in range(3):
                adj_pt = ptB * (CONFIG.TRIPLE_STACK_MALUS ** triples)
                r = RNG.rand()
                if r < adj_pt:
                    triples += 1; visit += 60
                elif r < adj_pt + pdB:
                    visit += 40
                elif r < adj_pt + pdB + psB:
                    visit += 20
                else:
                    visit += max(0, int(truncated_normal(10.0 + 0.10 * pB.skill, 5.0 * pB.tempo, 0, 26)))
            scoreB = max(0, scoreB - visit)
            clutch_mult = 1.0 + min(0.2, (pB.clutch - 1.0) * 0.2)
            if 2 <= scoreB <= 170:
                if RNG.rand() < min(0.98, finish_probability(pB.skill, scoreB) * (clutch_mult if scoreB <= 100 else 1.0)):
                    return 'B'
            elif scoreB == 1:
                scoreB += 1
            elif scoreB == 0:
                return 'B'
            turn = 'A'

def simulate_match_501(pA: Player, pB: Player, best_of_legs: int) -> Tuple[int,int]:
    need = (best_of_legs // 2) + 1
    legsA = legsB = 0
    starter = 'A' if RNG.rand() < 0.5 else 'B'
    while legsA < need and legsB < need:
        winner = simulate_leg(pA, pB, starter)
        if winner == 'A':
            legsA += 1
        else:
            legsB += 1
        starter = 'B' if starter == 'A' else 'A'
    return legsA, legsB

# ===============================
# POINTS & RELATIONS (post-match)
# ===============================

def award_points(legsA: int, legsB: int, context: str, bo: int) -> Tuple[int,int]:
    if bo == 3:
        table = CONFIG.BO3_POINTS[context]
        key = (max(legsA, legsB), min(legsA, legsB))
        if legsA > legsB:
            return table.get(key, 0), 0
        else:
            return 0, table.get(key, 0)
    else:
        table = CONFIG.BO5_POINTS[context]
        key = (max(legsA, legsB), min(legsA, legsB))
        if legsA > legsB:
            return table.get(key, 0), 0
        else:
            return 0, table.get(key, 0)

def relation_probability(legsA:int, legsB:int, nationA:str, nationB:str, ageA:int, ageB:int) -> float:
    key = None
    if (legsA, legsB) in [(3,2),(2,3)]:
        key = "tight"
    elif (legsA, legsB) in [(3,1),(1,3)]:
        key = "mid"
    elif (legsA, legsB) in [(3,0),(0,3)]:
        key = "sweep"
    else:
        if (legsA, legsB) in [(2,1),(1,2)]:
            key = "tight"
        elif (legsA, legsB) in [(2,0),(0,2)]:
            key = "sweep"
    p = CONFIG.REL_BASE.get(key, 0.20)
    if nationA == nationB:
        p *= CONFIG.REL_CULTURE["SAME"]
    else:
        close_pairs = {("FRA","BEL"), ("BEL","NLD"), ("GBR","IRL"), ("DEU","AUT"), ("SWE","DNK"), ("NOR","SWE"), ("FRA","CHE")}
        if (nationA, nationB) in close_pairs or (nationB, nationA) in close_pairs:
            p *= CONFIG.REL_CULTURE["CLOSE"]
        else:
            p *= CONFIG.REL_CULTURE["FAR"]
    d = abs(ageA - ageB) - 6
    if d > 0:
        p *= max(0.0, 1.0 - d * CONFIG.REL_AGE_DIFF_MALUS_PER_YEAR)
    return max(0.0, min(0.95, p))

def maybe_create_relation(pA: Player, pB: Player, legsA:int, legsB:int, bo:int):
    p = relation_probability(legsA, legsB, pA.nation, pB.nation, pA.age, pB.age)
    if RNG.rand() < p:
        kind = "affinite"
        if max(legsA, legsB) == (bo//2+1) and min(legsA, legsB) == 0 and RNG.rand() < 0.4:
            kind = "rivalite"
        pA.relations[pB.pid] = Relationship(pB.pid, kind, strength=10.0+RNG.rand()*15)
        pB.relations[pA.pid] = Relationship(pA.pid, kind, strength=10.0+RNG.rand()*15)

# ===========================
# PLANIFICATION DES MATCHS
# ===========================

@dataclass
class Fixture:
    a: int
    b: int
    context: str  # "intra" | "inter"
    bo: int

class Scheduler:
    @staticmethod
    def round_robin_rounds(ids: List[int]) -> List[List[Tuple[int,int]]]:
        """Retourne la liste des rondes; chaque ronde = liste de paires (a,b).
        Algorithme du 'cercle' avec bye si impair (id = -1)."""
        ids = ids[:]
        if len(ids) % 2 == 1:
            ids.append(-1)
        n = len(ids)
        half = n // 2
        rounds: List[List[Tuple[int,int]]] = []
        arr = ids[:]
        for _ in range(n - 1):
            pairs = []
            for i in range(half):
                a, b = arr[i], arr[n - 1 - i]
                if a != -1 and b != -1:
                    pairs.append((a, b))
            rounds.append(pairs)
            # rotation
            arr = [arr[0]] + [arr[-1]] + arr[1:-1]
        return rounds

    @staticmethod
    def round_robin_once(ids: List[int]) -> List[Tuple[int,int]]:
        ids = ids[:]
        if len(ids) % 2 == 1:
            ids.append(-1)
        n = len(ids)
        half = n // 2
        rounds = []
        for _ in range(n-1):
            pair = []
            for i in range(half):
                a, b = ids[i], ids[n-1-i]
                if a != -1 and b != -1:
                    pair.append((a,b))
            rounds.append(pair)
            ids = [ids[0]] + [ids[-1]] + ids[1:-1]
            rounds = Scheduler.round_robin_rounds(ids)
        return [p for rnd in Scheduler.round_robin_rounds(ids) for p in rnd]
    
    @staticmethod
    def schedule_intra_once(group_ids: List[int]) -> List[Fixture]:
        return [Fixture(a,b,"intra",bo=3) for a,b in Scheduler.round_robin_once(group_ids)]
    
    @staticmethod
    def _pick_rounds(rounds: list[list[tuple[int,int]]], k: int) -> list[tuple[int,int]]:
        """
        Mélange la liste de rondes (chaque ronde = liste de paires) et en prend exactement k,
        puis aplatit en une liste de paires (a,b).
        Garantit : chaque joueur a exactement 1 match par ronde choisie.
        """
        if k < 0 or k > len(rounds):
            raise ValueError(f"Demande {k} rondes mais il y en a {len(rounds)}.")
        rnds = rounds[:]
        RNG._rng.shuffle(rnds)
        chosen = rnds[:k]
        return [p for r in chosen for p in r]


    @staticmethod
    def _bipartite_rounds(A: list[int], B: list[int]) -> list[list[tuple[int,int]]]:
        """
        Construit des rondes 'bipartites' entre deux groupes A et B de même taille n.
        - Retourne n rondes; dans la ronde i, on joue (A[j] vs B[(j+i) % n]) pour tous j.
        - Chaque ronde = adversaires distincts, donc k rondes => k adversaires distincts
        pour chaque joueur contre le groupe opposé.
        """
        if len(A) != len(B):
            raise ValueError(f"Groupes de tailles différentes: |A|={len(A)} |B|={len(B)} "
                            f"(il faut égalité pour _bipartite_rounds).")
        n = len(A)
        rounds: list[list[tuple[int,int]]] = []
        Bperm = B[:]
        RNG._rng.shuffle(Bperm)  # petite permutation initiale pour varier
        for shift in range(n):
            pairs = []
            for j in range(n):
                pairs.append((A[j], Bperm[(j + shift) % n]))
            rounds.append(pairs)
        return rounds
    
    @staticmethod
    def _equalize_for_bipartite(A: list[int], B: list[int]) -> tuple[list[int], list[int]]:
        """
        Rend A et B de même longueur en répliquant (avec cycle) le plus petit groupe.
        On mélange l'ordre répliqué pour répartir l'effort équitablement de façon déterministe (RNG).
        """
        if len(A) == len(B):
            return A[:], B[:]
        if len(A) < len(B):
            small, big = A[:], B[:]
        else:
            small, big = B[:], A[:]

        if not small:
            raise ValueError("Groupe vide dans _equalize_for_bipartite.")

        base = small[:]
        RNG._rng.shuffle(base)
        i = 0
        while len(small) < len(big):
            small.append(base[i % len(base)])
            i += 1

        # Remettre dans l'ordre (A,B)
        if len(A) < len(B):
            return small, big
        else:
            return big, small

    def rebalance_groups(league: League, verbose: bool = True):
        """
        Rééquilibre les groupes intra-division avant la planification.
        - D2 : 2 groupes (A,B)      — cible: 58 chacun (si total == 116)
        - D3 : 3 groupes (A,B,C)    — cible: 84 chacun (si total == 252)
        - D4 : 4 groupes (A,B,C,D)  — cible: 120 chacun (si total == 480)

        Si le total courant de la division ne correspond pas au total cible (retraites, etc.),
        on répartit aussi équitablement que possible (floor/ceil) sur les groupes.
        """
        division_specs = {
            "D2": (["A", "B"], 58),
            "D3": (["A", "B", "C"], 84),
            "D4": (["A", "B", "C", "D"], 120),
        }

        for div, (groups, target_per_group) in division_specs.items():
            # Récupérer tous les joueurs de la division, classés par groupe
            by_group: dict[str, list[Player]] = {g: [] for g in groups}
            div_players = [p for p in league.players.values() if p.division == div]
            for p in div_players:
                # Si un joueur a un group code inattendu, on le "clipse" dans le premier groupe
                if p.group not in by_group:
                    p.group = groups[0]
                by_group[p.group].append(p)

            current_total = len(div_players)
            expected_total = target_per_group * len(groups)

            # Déterminer la cible par groupe
            if current_total == expected_total:
                # Cible stricte (ex : 58/84/120)
                targets = {g: target_per_group for g in groups}
            else:
                # Répartition équitable (floor/ceil) si le total ne colle pas au total nominal
                q, r = divmod(current_total, len(groups))
                targets = {}
                # Petite permutation aléatoire des groupes pour éviter toujours les mêmes qui prennent +1
                grp_order = groups[:]
                RNG._rng.shuffle(grp_order)
                for i, g in enumerate(grp_order):
                    targets[g] = q + (1 if i < r else 0)
                if verbose:
                    print(f"[rebalance_groups] {div}: total={current_total} (nominal={expected_total}). "
                        f"Répartition équilibrée={targets}.")

            # Construire listes excédentaires/déficitaires
            over: list[tuple[str, list[Player]]] = []
            under: list[tuple[str, int]] = []
            for g in groups:
                diff = len(by_group[g]) - targets[g]
                if diff > 0:
                    # Mélanger pour que les départs soient pseudo-aléatoires mais déterministes
                    RNG._rng.shuffle(by_group[g])
                    over.append((g, by_group[g][:diff]))
                elif diff < 0:
                    under.append((g, -diff))

            # Aplatir les excédents
            pool_to_move: list[Player] = []
            for g, plist in over:
                pool_to_move.extend(plist)

            # Déplacer depuis le pool vers les groupes déficitaires
            idx = 0
            for g, need in under:
                for _ in range(need):
                    if idx >= len(pool_to_move):
                        # Rien d’autre à déplacer (ça ne devrait pas arriver, mais on sécurise)
                        break
                    p = pool_to_move[idx]
                    idx += 1
                    p.group = g  # Mise à jour du groupe du joueur dans l'objet Player

            if verbose:
                after = {g: 0 for g in groups}
                for p in league.players.values():
                    if p.division == div and p.group in after:
                        after[p.group] += 1
                print(f"[rebalance_groups] {div} équilibré -> " +
                    ", ".join(f"{g}:{after[g]}/{targets[g]}" for g in groups))
                
    @staticmethod
    # (Optionnel – debug) Vérifier le nombre de matchs par joueur sur un set de paires
    def _check_degree(pairs: list[tuple[int,int]], ids: list[int], expected: int, label: str):
        deg = {pid: 0 for pid in ids}
        for a, b in pairs:
            if a in deg: deg[a] += 1
            if b in deg: deg[b] += 1
        bad = {pid: d for pid, d in deg.items() if d != expected}
        if bad:
            raise RuntimeError(f"[{label}] Degrés inattendus: {bad}")
# ==================================
# PHASE FINALE: ÉTAPES 1,2 et Super
# ==================================

@dataclass
class Group:
    name: str
    player_ids: List[int]

@dataclass
class League:
    players: Dict[int, Player]
    def get(self, pid:int) -> Player:
        return self.players[pid]

# =========================
# MOTEUR DE COMPÉTITION
# =========================

def reset_all_points(league: League):
    for p in league.players.values():
        p.reset_competition()

class Competition:
    def __init__(self, league: League):
        self.league = league
        self.fixtures: List[Fixture] = []

    def play_fixture(self, fx: Fixture):
        A = self.league.get(fx.a)
        B = self.league.get(fx.b)
        legsA, legsB = simulate_match_501(A,B,best_of_legs=fx.bo)
        A.legs_for += legsA; A.legs_against += legsB
        B.legs_for += legsB; B.legs_against += legsA
        pa, pb = award_points(legsA, legsB, fx.context, fx.bo)
        A.points += pa; B.points += pb
        maybe_create_relation(A,B,legsA,legsB,fx.bo)

    def ranking(self, pids: List[int]) -> List[Player]:
        arr = [self.league.get(pid) for pid in pids]
        return sorted(arr, key=lambda p: (p.points, p.legs_diff, p.skill), reverse=True)

# =========================
# SAISON RÉGULIÈRE D1→D4
# =========================

def schedule_fixed_degree(ids: List[int], k: int) -> List[Tuple[int,int]]:
    """
    Construit une planification simple et toujours faisable :
    - Génère le round-robin complet (n-1 rondes).
    - Mélange les rondes et en prend exactement k.
    - L’union de ces k rondes donne un graphe k-régulier parfait.
    Préconditions : 0 <= k <= len(ids)-1.
    """
    n = len(ids)
    if k < 0 or k > n - 1:
        raise ValueError(f"k={k} invalide pour n={n} (doit être dans [0, {n-1}]).")
    rounds = Scheduler.round_robin_rounds(ids)
    RNG._rng.shuffle(rounds)
    selected = rounds[:k]
    pairs = [p for rnd in selected for p in rnd]
    # sécurité : vérifier les degrés
    deg = {pid: 0 for pid in ids}
    for a,b in pairs:
        deg[a] += 1; deg[b] += 1
    missing = {pid: k - d for pid, d in deg.items() if d != k}
    if any(missing.values()):
        # Ne devrait pas arriver, mais on garde un message clair si jamais
        raise RuntimeError(f"Planification D1 inattendue : degrés non k-réguliers {missing}")
    return pairs

def schedule_bipartite_fixed_degree(left_ids: List[int], right_ids: List[int], k: int, rng: random.Random = RNG._rng) -> List[Tuple[int,int]]:
    """
    Inter-groupes : construit un graphe biparti régulier (degré k de chaque côté).
    Hypothèses ici respectées par tes tailles: len(left)==len(right) et k <= len(side).
    Construction par 'shifts' (round-robin biparti), sans doublons.
    Retour: paires (a ∈ left, b ∈ right)
    """
    m = len(left_ids); n = len(right_ids)
    assert m == n, f"Groupes de tailles différentes: {m} vs {n}"
    assert 0 <= k <= n, f"k={k} > taille groupe n={n}"
    L = left_ids[:]
    R = right_ids[:]
    rng.shuffle(L)
    rng.shuffle(R)
    pairs: List[Tuple[int,int]] = []
    # Pour chaque "shift" r, appaire L[i] avec R[(i+r) % n], ce qui garantit degré 1,
    # puis répéter k fois pour obtenir degré k (chaque r donne un perfect matching).
    used = set()
    for r in range(k):
        for i in range(n):
            a = L[i]
            b = R[(i + r) % n]
            pair = (a, b) if a < b else (b, a)
            if pair in used:
                # sécurité: si collision (très improbable), on rebrasse R et on refait ce r
                rng.shuffle(R)
                return schedule_bipartite_fixed_degree(L, R, k, rng)
            used.add(pair)
            pairs.append((a, b))
    rng.shuffle(pairs)
    return pairs

def simulate_regular_season(league: League):
    # 0) équilibrage + reset
    rebalance_groups(league, verbose=True)
    reset_all_points(league)
    comp = Competition(league)

    # ===== D1 : 36 joueurs, 20 matchs chacun, BO5, barème inter =====
    d1_ids = [p.pid for p in league.players.values() if p.division == "D1"]
    d1_pairs = schedule_fixed_degree(d1_ids, CONFIG.D1_MATCHES)  # garantit k=20 par joueur
    for a, b in d1_pairs:
        comp.play_fixture(Fixture(a, b, "inter", bo=5))

    # ===== D2 : 2 groupes x ~58 — 8 intra (BO3) + 14 inter (BO3) =====
    # -- INTRA (8 rondes round-robin par groupe) --
    for gch in ['A', 'B']:
        ids = [p.pid for p in league.players.values() if p.division == "D2" and p.group == gch]
        rr = Scheduler.round_robin_rounds(ids)     # liste de rondes (chaque ronde = n/2 paires)
        intra_pairs = Scheduler._pick_rounds(rr, 8)
        for a, b in intra_pairs:
            comp.play_fixture(Fixture(a, b, "intra", bo=3))

    # -- INTER (A vs B, 14 rondes bipartites) --
    idsA = [p.pid for p in league.players.values() if p.division == "D2" and p.group == 'A']
    idsB = [p.pid for p in league.players.values() if p.division == "D2" and p.group == 'B']
    Aeq, Beq = Scheduler._equalize_for_bipartite(idsA, idsB)
    br = Scheduler._bipartite_rounds(Aeq, Beq)    # len(br) == max(|A|,|B|)
    inter_pairs = Scheduler._pick_rounds(br, 14)
    for a, b in inter_pairs:
        comp.play_fixture(Fixture(a, b, "inter", bo=3))

    # ===== D3 : 3 groupes x ~84 — 10 intra (BO3) + 16 inter (8 vs chacun des 2 autres) =====
    d3_groups = ['A', 'B', 'C']

    # -- INTRA (10 rondes par groupe) --
    for gch in d3_groups:
        ids = [p.pid for p in league.players.values() if p.division == "D3" and p.group == gch]
        rr = Scheduler.round_robin_rounds(ids)
        intra_pairs = Scheduler._pick_rounds(rr, 10)
        for a, b in intra_pairs:
            comp.play_fixture(Fixture(a, b, "intra", bo=3))

    # -- INTER (8 rondes pour chaque paire AB, AC, BC) --
    idsA = [p.pid for p in league.players.values() if p.division == "D3" and p.group == 'A']
    idsB = [p.pid for p in league.players.values() if p.division == "D3" and p.group == 'B']
    idsC = [p.pid for p in league.players.values() if p.division == "D3" and p.group == 'C']

    for X_ids, Y_ids in [(idsA, idsB), (idsA, idsC), (idsB, idsC)]:
        Aeq, Beq = Scheduler._equalize_for_bipartite(X_ids, Y_ids)
        br = Scheduler._bipartite_rounds(Aeq, Beq)
        inter_pairs = Scheduler._pick_rounds(br, 8)
        for a, b in inter_pairs:
            comp.play_fixture(Fixture(a, b, "inter", bo=3))

    # ===== D4 : 4 groupes x ~120 — 12 intra (BO3) + 18 inter (6 vs chacun des 3 autres) =====
    d4_groups = ['A', 'B', 'C', 'D']

    # -- INTRA (12 rondes par groupe) --
    for gch in d4_groups:
        ids = [p.pid for p in league.players.values() if p.division == "D4" and p.group == gch]
        rr = Scheduler.round_robin_rounds(ids)
        intra_pairs = Scheduler._pick_rounds(rr, 12)
        for a, b in intra_pairs:
            comp.play_fixture(Fixture(a, b, "intra", bo=3))

    # -- INTER (6 rondes pour chaque paire de groupes) --
    def _ids_d4(gcode: str) -> List[int]:
        return [p.pid for p in league.players.values() if p.division == "D4" and p.group == gcode]

    for ga, gb in [('A','B'), ('A','C'), ('A','D'), ('B','C'), ('B','D'), ('C','D')]:
        Aids, Bids = _ids_d4(ga), _ids_d4(gb)
        Aeq, Beq = Scheduler._equalize_for_bipartite(Aids, Bids)
        br = Scheduler._bipartite_rounds(Aeq, Beq)
        inter_pairs = Scheduler._pick_rounds(br, 6)
        for a, b in inter_pairs:
            comp.play_fixture(Fixture(a, b, "inter", bo=3))

    return comp



# ==============================
# ORCHESTRATION POPULATION
# ==============================

def make_initial_population() -> League:
    RNG.seed(CONFIG.RNG_SEED)
    players: Dict[int, Player] = {}
    total = (CONFIG.D4_GROUPS*CONFIG.D4_PLAYERS_PER_GROUP +
             CONFIG.D3_GROUPS*CONFIG.D3_PLAYERS_PER_GROUP +
             CONFIG.D2_GROUPS*CONFIG.D2_PLAYERS_PER_GROUP +
             CONFIG.D1_PLAYERS)
    for _ in range(total):
        p = PlayerFactory.make_player()
        players[p.pid] = p
    lg = League(players)
    ordered = sorted(lg.players.values(), key=lambda p: p.skill, reverse=True)
    idx = 0
    for p in ordered[idx: idx + CONFIG.D1_PLAYERS]:
        p.division = "D1"; p.group = None
    idx += CONFIG.D1_PLAYERS
    for g in range(CONFIG.D2_GROUPS):
        block = ordered[idx: idx + CONFIG.D2_PLAYERS_PER_GROUP]
        for p in block:
            p.division = "D2"; p.group = chr(ord('A') + g)
        idx += CONFIG.D2_PLAYERS_PER_GROUP
    for g in range(CONFIG.D3_GROUPS):
        block = ordered[idx: idx + CONFIG.D3_PLAYERS_PER_GROUP]
        for p in block:
            p.division = "D3"; p.group = chr(ord('A') + g)
        idx += CONFIG.D3_PLAYERS_PER_GROUP
    for g in range(CONFIG.D4_GROUPS):
        block = ordered[idx: idx + CONFIG.D4_PLAYERS_PER_GROUP]
        for p in block:
            p.division = "D4"; p.group = chr(ord('A') + g)
        idx += CONFIG.D4_PLAYERS_PER_GROUP
    return lg

# ==============================
# CLASSEMENTS & PROMO/RELÉGATION
# ==============================

def standings_by_division(league: League) -> Dict[str, Dict[str, List[Player]]]:
    comp = Competition(league)
    out: Dict[str, Dict[str, List[Player]]] = {}
    d1 = [p.pid for p in league.players.values() if p.division=="D1"]
    out["D1"] = {"ALL": comp.ranking(d1)}
    for div, groups in [("D2", ['A','B']), ("D3", ['A','B','C']), ("D4", ['A','B','C','D'])]:
        out[div] = {}
        for g in groups:
            ids = [p.pid for p in league.players.values() if p.division==div and p.group==g]
            out[div][g] = comp.ranking(ids)
    return out

def apply_promotions_relegations(league: League):
    st = standings_by_division(league)
    # D1: bottom 6 → D2
    d1_all = st['D1']['ALL']
    for p in d1_all[-6:]:
        p.division = 'D2'; p.group = None
    # D2: top 3/group → D1 ; 73–78 overall → D3 ; last 6 → D4
    d2_all = st['D2']['A'] + st['D2']['B']
    d2_overall = sorted(d2_all, key=lambda p: (p.points, p.legs_diff, p.skill), reverse=True)
    for p in st['D2']['A'][:3] + st['D2']['B'][:3]:
        p.division = 'D1'; p.group = None
    for p in d2_overall[72:78]:
        p.division = 'D3'; p.group = None
    for p in d2_overall[-6:]:
        p.division = 'D4'; p.group = None
    # D3: top4/group → D2; bottom6/group → D4
    for g in ['A','B','C']:
        grp = st['D3'][g]
        for p in grp[:4]:
            p.division = 'D2'; p.group = None
        for p in grp[-6:]:
            p.division = 'D4'; p.group = None
    # D4: top3/group → D2; 4–9/group → D3
    for g in ['A','B','C','D']:
        grp = st['D4'][g]
        for p in grp[:3]:
            p.division = 'D2'; p.group = None
        for p in grp[3:9]:
            p.division = 'D3'; p.group = None

def rebalance_groups(league: League, verbose: bool = True):
    """
    Rééquilibre les groupes intra-division avant la planification.
    - D2 : 2 groupes (A,B)      — cible: 58 chacun (si total == 116)
    - D3 : 3 groupes (A,B,C)    — cible: 84 chacun (si total == 252)
    - D4 : 4 groupes (A,B,C,D)  — cible: 120 chacun (si total == 480)

    Si le total courant de la division ne correspond pas au total cible (retraites, etc.),
    on répartit aussi équitablement que possible (floor/ceil) sur les groupes.
    """
    division_specs = {
        "D2": (["A", "B"], 58),
        "D3": (["A", "B", "C"], 84),
        "D4": (["A", "B", "C", "D"], 120),
    }

    for div, (groups, target_per_group) in division_specs.items():
        by_group: dict[str, list[Player]] = {g: [] for g in groups}
        div_players = [p for p in league.players.values() if p.division == div]
        for p in div_players:
            if p.group not in by_group:
                p.group = groups[0]
            by_group[p.group].append(p)

        current_total = len(div_players)
        expected_total = target_per_group * len(groups)

        if current_total == expected_total:
            targets = {g: target_per_group for g in groups}
        else:
            q, r = divmod(current_total, len(groups))
            targets = {}
            grp_order = groups[:]
            RNG._rng.shuffle(grp_order)
            for i, g in enumerate(grp_order):
                targets[g] = q + (1 if i < r else 0)
            if verbose:
                print(f"[rebalance_groups] {div}: total={current_total} (nominal={expected_total}). "
                      f"Répartition équilibrée={targets}.")

        over: list[tuple[str, list[Player]]] = []
        under: list[tuple[str, int]] = []
        for g in groups:
            diff = len(by_group[g]) - targets[g]
            if diff > 0:
                RNG._rng.shuffle(by_group[g])
                over.append((g, by_group[g][:diff]))
            elif diff < 0:
                under.append((g, -diff))

        pool_to_move: list[Player] = []
        for g, plist in over:
            pool_to_move.extend(plist)

        idx = 0
        for g, need in under:
            for _ in range(need):
                if idx >= len(pool_to_move):
                    break
                p = pool_to_move[idx]
                idx += 1
                p.group = g

        if verbose:
            after = {g: 0 for g in groups}
            for p in league.players.values():
                if p.division == div and p.group in after:
                    after[p.group] += 1
            print(f"[rebalance_groups] {div} équilibré -> " +
                  ", ".join(f"{g}:{after[g]}/{targets[g]}" for g in groups))


# ==============================
# PHASE FINALE – ÉTAPES 1, 2 & SUPER TOUR
# ==============================

@dataclass
class PhaseResults:
    step1_groups: Dict[str, List[Player]]
    step1_tables: Dict[str, List[Player]]
    step2_groups: Dict[str, List[Player]]
    step2_tables: Dict[str, List[Player]]
    super_tour_order: List[Player]
    bracket_matches: List[Dict]  # chaque match avec scores et round

def _assign_groups(players: List[Player], labels: List[str], size_per_group: int) -> Dict[str, List[Player]]:
    RNG._rng.shuffle(players)
    groups: Dict[str, List[Player]] = {}
    i = 0
    for lab in labels:
        groups[lab] = players[i:i+size_per_group]
        i += size_per_group
    return groups

def _fixtures_step1(groups: Dict[str, List[Player]]) -> List[Fixture]:
    fixtures: List[Fixture] = []
    # Intra: round-robin simple (11 matchs par joueur)
    for lab, plist in groups.items():
        ids = [p.pid for p in plist]
        rr = Scheduler.round_robin_once(ids)
        fixtures += [Fixture(a,b,'intra',bo=5) for a,b in rr]
    # Inter: 16 matchs par joueur contre 4 adversaires d'autres groupes (4 fois chacun)
    all_ids = {lab: [p.pid for p in plist] for lab, plist in groups.items()}
    labs = list(groups.keys())
    used_pairs: Set[Tuple[int,int]] = set()
    for lab in labs:
        others = [pid for olab in labs if olab!=lab for pid in all_ids[olab]]
        for p in all_ids[lab]:
            RNG._rng.shuffle(others)
            chosen = []
            for q in others:
                if q in chosen or (min(p,q),max(p,q)) in used_pairs:
                    continue
                chosen.append(q)
                if len(chosen) == 4:
                    break
            for q in chosen:
                for _ in range(4):
                    used_pairs.add((min(p,q),max(p,q)))
                    fixtures.append(Fixture(p,q,'inter',bo=5))
    RNG._rng.shuffle(fixtures)
    return fixtures

def _fixtures_step2(groups: Dict[str, List[Player]]) -> List[Fixture]:
    fixtures: List[Fixture] = []
    for lab, plist in groups.items():
        ids = [p.pid for p in plist]
        rr = Scheduler.round_robin_once(ids)
        fixtures += [Fixture(a,b,'intra',bo=5) for a,b in rr]
    labs = list(groups.keys())
    all_ids = {lab: [p.pid for p in plist] for lab, plist in groups.items()}
    used_pairs: Set[Tuple[int,int]] = set()
    for lab in labs:
        others = [pid for olab in labs if olab!=lab for pid in all_ids[olab]]
        for p in all_ids[lab]:
            RNG._rng.shuffle(others)
            chosen = []
            for q in others:
                if q in chosen or (min(p,q),max(p,q)) in used_pairs:
                    continue
                chosen.append(q)
                if len(chosen) == 4:
                    break
            for q in chosen:
                for _ in range(2):
                    used_pairs.add((min(p,q),max(p,q)))
                    fixtures.append(Fixture(p,q,'inter',bo=5))
    RNG._rng.shuffle(fixtures)
    return fixtures

def select_phase1_qualifiers(standings: Dict[str, Dict[str, List[Player]]]) -> List[Player]:
    q = []
    q += standings['D1']['ALL'][:10]
    for g in ['A','B']:
        q += standings['D2'][g][:8]
    for g in ['A','B','C']:
        q += standings['D3'][g][:6]
    for g in ['A','B','C','D']:
        q += standings['D4'][g][:4]
    assert len(q) == 60, f"Qualifiers count mismatch: {len(q)}"
    return q

def _tables_for(groups: Dict[str, List[Player]], league: League) -> Dict[str, List[Player]]:
    comp = Competition(league)
    tables: Dict[str, List[Player]] = {}
    for lab, plist in groups.items():
        tables[lab] = comp.ranking([p.pid for p in plist])
    return tables

def simulate_phase1(league: League, qualifiers: List[Player]) -> Tuple[Dict[str, List[Player]], Dict[str, List[Player]]]:
    groups = _assign_groups(qualifiers, ['A','B','C','D','E'], 12)
    for p in [x for g in groups.values() for x in g]:
        p.reset_competition()
    comp = Competition(league)
    fixtures = _fixtures_step1(groups)
    for fx in fixtures:
        comp.play_fixture(fx)
    tables = _tables_for(groups, league)
    return groups, tables

def simulate_phase2(league: League, step1_tables: Dict[str, List[Player]]) -> Tuple[Dict[str, List[Player]], Dict[str, List[Player]], List[Player]]:
    direct = [step1_tables[g][0] for g in ['A','B','C','D','E']]
    pool = []
    for g in ['A','B','C','D','E']:
        pool += step1_tables[g][1:7]
    groups = _assign_groups(pool, ['F','G','H'], 10)
    for p in [x for g in groups.values() for x in g]:
        p.reset_competition()
    comp = Competition(league)
    fixtures = _fixtures_step2(groups)
    for fx in fixtures:
        comp.play_fixture(fx)
    tables = _tables_for(groups, league)
    winners = [tables[g][0] for g in ['F','G','H']]
    finalists8 = direct + winners
    return groups, tables, finalists8

# ==============================
# SUPER TOUR – DOUBLE ÉLIMINATION
# ==============================

def _play_series_with_score(pA: Player, pB: Player, bo_legs: int) -> Tuple[Player, Tuple[int,int]]:
    la, lb = simulate_match_501(pA, pB, bo_legs)
    winner = pA if la>lb else pB
    return winner, (la, lb)

def _play_series_with_score_advantage(pA: Player, pB: Player, bo_legs: int, preA: int = 0, preB: int = 0) -> Tuple[Player, Tuple[int,int]]:
    """Série avec score initial (avantage WB). Retourne (vainqueur, (legsA, legsB))."""
    need = bo_legs // 2 + 1
    legsA, legsB = preA, preB
    # premier starter aléatoire, puis alternance
    starter = 'A' if RNG.rand() < 0.5 else 'B'
    while legsA < need and legsB < need:
        w = simulate_leg(pA, pB, starter)
        if w == 'A':
            legsA += 1
        else:
            legsB += 1
        starter = 'B' if starter == 'A' else 'A'
    winner = pA if legsA > legsB else pB
    return winner, (legsA, legsB)

def simulate_double_elim(league: League, players8: List[Player]) -> Tuple[List[Player], List[Dict]]:
    # Seeding par skill (desc)
    s = sorted(players8, key=lambda p: p.skill, reverse=True)  # s[0] = seed1, s[7] = seed8
    evts: List[Dict] = []

    def play_and_log(round_name: str, A: Player, B: Player, bo: int, preA: int = 0, preB: int = 0):
        if preA or preB:
            w, score = _play_series_with_score_advantage(A, B, bo, preA, preB)
        else:
            w, score = _play_series_with_score(A, B, bo)
        evts.append({"round": round_name, "A": A.pid, "B": B.pid, "score": score, "winner": w.pid})
        loser = A if w is B else B
        return w, loser, score

    # ========= Winners Bracket =========
    # R1: (1v8), (4v5), (2v7), (3v6)
    wb1_w1, wb1_l1, _ = play_and_log("WB R1", s[0], s[7], 5)
    wb1_w2, wb1_l2, _ = play_and_log("WB R1", s[3], s[4], 5)
    wb1_w3, wb1_l3, _ = play_and_log("WB R1", s[1], s[6], 5)
    wb1_w4, wb1_l4, _ = play_and_log("WB R1", s[2], s[5], 5)

    # WB Semis
    wb2_w1, wb2_l1, _ = play_and_log("WB Semis", wb1_w1, wb1_w2, 5)
    wb2_w2, wb2_l2, _ = play_and_log("WB Semis", wb1_w3, wb1_w4, 5)

    # WB Final
    wb_final_w, wb_final_l, _ = play_and_log("WB Final", wb2_w1, wb2_w2, 5)

    # ========= Losers Bracket =========
    # LB R1 : losers des WB R1 (deux matches)
    lb_r1_w1, lb_r1_l1, _ = play_and_log("LB R1", wb1_l1, wb1_l2, 5)
    lb_r1_w2, lb_r1_l2, _ = play_and_log("LB R1", wb1_l3, wb1_l4, 5)

    # LB R2 : chaque vainqueur LB R1 affronte le loser correspondant des WB Semis
    lb_r2_w1, lb_r2_l1, _ = play_and_log("LB R2", lb_r1_w1, wb2_l1, 5)
    lb_r2_w2, lb_r2_l2, _ = play_and_log("LB R2", lb_r1_w2, wb2_l2, 5)

    # LB Finalist (demi LB)
    lb_finalist, lb_semiloser, _ = play_and_log("LB Finalist", lb_r2_w1, lb_r2_w2, 5)

    # LB Final : vainqueur vs perdant de la WB Final
    lb_challenger, lb_final_loser, _ = play_and_log("LB Final", lb_finalist, wb_final_l, 5)

    # ========= Grand Final =========
    # BO7, avec +1 leg pour le vainqueur du WB (avantage)
    # On identifie A = WB winner (avantage), B = challenger LB
    A = wb_final_w
    B = lb_challenger
    grand_w, grand_loser, _ = play_and_log("Grand Final (BO7, WB +1)", A, B, 7, preA=1, preB=0)

    # Ordre final : champion en premier, puis le reste dans un ordre approximatif (option simple)
    champion = grand_w
    final_order = [champion]
    others = [p for p in players8 if p.pid != champion.pid]
    # Tu peux raffiner ce classement avec des règles plus fines (position par round d’élimination)
    final_order += sorted(others, key=lambda p: p.skill, reverse=True)

    return final_order, evts


def simulate_phase_finale(league: League, standings: Dict[str, Dict[str, List[Player]]]) -> PhaseResults:
    qualifiers = select_phase1_qualifiers(standings)
    g1, t1 = simulate_phase1(league, qualifiers)
    g2, t2, finalists8 = simulate_phase2(league, t1)
    top8_order, bracket_matches = simulate_double_elim(league, finalists8)
    return PhaseResults(step1_groups=g1, step1_tables=t1, step2_groups=g2, step2_tables=t2,
                        super_tour_order=top8_order, bracket_matches=bracket_matches)

# ==============================
# EXPORTS
# ==============================

class DataExporter:
    @staticmethod
    def save_tables_json(path: Path, season_idx: int, groups_or_divs, tables):
        payload = {"season": season_idx, "tables": {}}
        if isinstance(tables, dict) and 'D1' in tables:
            for div, divmap in tables.items():
                payload['tables'][div] = {}
                for grp, plist in divmap.items():
                    payload['tables'][div][grp] = [
                        {"pid": p.pid, "name": p.name, "nickname": p.nickname, "nation": p.nation,
                         "points": p.points, "legs_diff": p.legs_diff, "skill": round(p.skill,1)}
                        for p in plist
                    ]
        else:
            for g in groups_or_divs:
                payload['tables'][g.name] = [
                    {"pid": p.pid, "name": p.name, "nickname": p.nickname, "nation": p.nation,
                     "points": p.points, "legs_diff": p.legs_diff, "skill": round(p.skill,1)}
                    for p in tables[g.name]
                ]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def save_phase_json(path: Path, season_idx: int, phase: PhaseResults):
        def serialize_player(p: Player):
            return {"pid": p.pid, "name": p.name, "nickname": p.nickname, "nation": p.nation,
                    "points": p.points, "legs_diff": p.legs_diff, "skill": round(p.skill,1)}
        payload = {
            "season": season_idx,
            "step1": {lab: [serialize_player(p) for p in plist] for lab, plist in phase.step1_tables.items()},
            "step2": {lab: [serialize_player(p) for p in plist] for lab, plist in phase.step2_tables.items()},
            "super_tour": [serialize_player(p) for p in phase.super_tour_order],
            "bracket": phase.bracket_matches
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def save_roster_csv(path: Path, league: League):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["pid","name","nickname","age","nation","sex","division","group","skill","potential",
                        "talent_simple","talent_double","talent_triple",
                        "aim_simple","aim_double","aim_triple",
                        "pot_simple","pot_double","pot_triple",
                        "points","legs_for","legs_against","target_pref","tempo","clutch","children"])
            for p in league.players.values():
                w.writerow([p.pid,p.name,p.nickname,p.age,p.nation,p.sex,p.division,p.group,f"{p.skill:.1f}",f"{p.potential:.1f}",
                            f"{p.talent_simple:.1f}",f"{p.talent_double:.1f}",f"{p.talent_triple:.1f}",
                            f"{p.aim_simple:.2f}",f"{p.aim_double:.2f}",f"{p.aim_triple:.2f}",
                            f"{p.pot_simple:.1f}",f"{p.pot_double:.1f}",f"{p.pot_triple:.1f}",
                            p.points,p.legs_for,p.legs_against,p.target_pref,f"{p.tempo:.2f}",f"{p.clutch:.2f}",p.children])

    @staticmethod
    def save_relations_json(path: Path, league: League):
        payload = {
            str(p.pid): [
                {"target": t, "kind": rel.kind, "strength": round(rel.strength,1)}
                for t, rel in p.relations.items()
            ] for p in league.players.values()
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def save_roster_html(path: Path, league: League):
        css = """
        <style>
            body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;background:#0b0d12;color:#e9edf1;margin:0;padding:24px}
            h1{margin:0 0 12px 0}
            .muted{color:#9aa5b1;margin:0 0 20px 0}
            table{width:100%;border-collapse:collapse;background:#121621;border:1px solid #1f2733;border-radius:8px;overflow:hidden}
            thead{background:#19202b}
            th,td{padding:8px 10px}
            tbody tr:nth-child(even){background:#0f141d}
            .right{text-align:right}
            .tag{display:inline-block;background:#1f2733;border:1px solid #303a4a;border-radius:999px;padding:2px 8px;margin-left:6px;font-size:12px}
        </style>
        """
        rows = []
        players = sorted(league.players.values(), key=lambda p: (p.division, p.group or "", -p.skill, p.pid))
        for p in players:
            rows.append(
                f"<tr>"
                f"<td>{p.pid}</td>"
                f"<td>{p.name}<span class='tag'>{p.nickname}</span></td>"
                f"<td>{p.age}</td>"
                f"<td>{p.nation}</td>"
                f"<td>{p.division}{('/'+p.group) if p.group else ''}</td>"
                f"<td class='right'>{p.skill:.1f}</td>"
                f"<td class='right'>{p.talent_simple:.1f}</td>"
                f"<td class='right'>{p.talent_double:.1f}</td>"
                f"<td class='right'>{p.talent_triple:.1f}</td>"
                f"<td class='right'>{p.aim_simple:.2f}</td>"
                f"<td class='right'>{p.aim_double:.2f}</td>"
                f"<td class='right'>{p.aim_triple:.2f}</td>"
                f"<td class='right'>{p.pot_simple:.1f}</td>"
                f"<td class='right'>{p.pot_double:.1f}</td>"
                f"<td class='right'>{p.pot_triple:.1f}</td>"
                f"<td class='right'>{p.points}</td>"
                f"<td class='right'>{p.legs_for}</td>"
                f"<td class='right'>{p.legs_against}</td>"
                f"<td>{p.target_pref}</td>"
                f"<td class='right'>{p.tempo:.2f}</td>"
                f"<td class='right'>{p.clutch:.2f}</td>"
                f"</tr>"
            )

        html = [
            "<html><head><meta charset='utf-8'><title>LVF – Roster complet</title>",
            css,
            "</head><body>",
            "<h1>LVF – Roster complet</h1>",
            "<p class='muted'>Toutes les stats par joueur. Tri : Division/Groupe puis Skill décroissant.</p>",
            "<table><thead><tr>"
            "<th>PID</th><th>Nom / Surnom</th><th>Âge</th><th>Nat</th><th>Div/Groupe</th>"
            "<th>Skill</th>"
            "<th>Tal S</th><th>Tal D</th><th>Tal T</th>"
            "<th>Aim S</th><th>Aim D</th><th>Aim T</th>"
            "<th>Pot S</th><th>Pot D</th><th>Pot T</th>"
            "<th>Pts</th><th>LF</th><th>LA</th>"
            "<th>Pref</th><th>Tempo</th><th>Clutch</th>"
            "</tr></thead><tbody>",
            *rows,
            "</tbody></table></body></html>",
        ]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(html), encoding="utf-8")

    @staticmethod
    def save_html_report(path: Path, season_idx: int, league: League, standings: Dict[str, Dict[str, List[Player]]], phase: Optional[PhaseResults] = None):
        def row(pl: Player) -> str:
            return f"<tr><td>{pl.pid}</td><td>{pl.name}</td><td>{pl.nickname}</td><td>{pl.nation}</td><td class='right'>{pl.points}</td><td class='right'>{pl.legs_diff}</td><td class='right'>{pl.skill:.1f}</td></tr>"
        def table(title: str, plist: List[Player]) -> str:
            rows = "".join(row(p) for p in plist)
            return f"""
            <section>
              <h3>{title}</h3>
              <table>
                <thead><tr><th>PID</th><th>Nom</th><th>Surnom</th><th>Nat</th><th>Pts</th><th>Diff Legs</th><th>Skill</th></tr></thead>
                <tbody>
                  {rows}
                </tbody>
              </table>
            </section>
            """
        css = """
        <style>
            body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;background:#0b0d12;color:#e9edf1;margin:0;padding:24px}
            h1{margin:0 0 8px 0}
            .muted{color:#9aa5b1;margin:0 0 24px 0}
            h2{margin-top:28px;border-left:4px solid #4f46e5;padding-left:10px}
            h3{margin:18px 0 8px 0}
            table{width:100%;border-collapse:collapse;margin-bottom:16px;background:#121621;border:1px solid #1f2733;border-radius:8px;overflow:hidden}
            thead{background:#19202b}
            th,td{padding:8px 10px}
            tbody tr:nth-child(even){background:#0f141d}
            section{margin-bottom:14px}
            .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}
        </style>
        """
        html = ["<html><head><meta charset='utf-8'><title>LVF – Rapport Saison %02d</title>%s</head><body>" % (season_idx, css)]
        html.append(f"<h1>LVF – Rapport Saison {season_idx:02d}</h1>")
        html.append("<p class='muted'>Classements triés par points → diff de legs → skill. Exports bruts disponibles en JSON/CSV dans le dossier.</p>")

        # Saison régulière – D1
        html.append("<h2>Saison régulière – D1</h2>")
        html.append(table("D1 (global)", standings['D1']['ALL']))

        # D2, D3, D4 par groupes
        for div, groups in [("D2", ['A','B']), ("D3", ['A','B','C']), ("D4", ['A','B','C','D'])]:
            html.append(f"<h2>Saison régulière – {div}</h2>")
            html.append("<div class='grid'>")
            for g in groups:
                html.append(table(f"{div} – Groupe {g}", standings[div][g]))
            html.append("</div>")

        # Phase finale
        if phase is not None:
            html.append("<h2>Phase Finale – Étape 1 (A–E)</h2>")
            html.append("<div class='grid'>")
            for lab in ['A','B','C','D','E']:
                if lab in phase.step1_tables:
                    html.append(table(f"Groupe {lab}", phase.step1_tables[lab]))
            html.append("</div>")

            html.append("<h2>Phase Finale – Étape 2 (F–H)</h2>")
            html.append("<div class='grid'>")
            for lab in ['F','G','H']:
                if lab in phase.step2_tables:
                    html.append(table(f"Groupe {lab}", phase.step2_tables[lab]))
            html.append("</div>")

            # Super Tour – classement + matches
            html.append("<h2>Super Tour LVF – Double élimination</h2>")
            if phase.super_tour_order:
                rows = "".join(
                    f"<tr><td>{i+1}</td><td>{p.pid}</td><td>{p.name}</td><td>{p.nickname}</td><td>{p.nation}</td><td class='right'>{p.skill:.1f}</td></tr>"
                    for i,p in enumerate(phase.super_tour_order)
                )
                html.append(
                    """
                    <section>
                      <table>
                        <thead><tr><th>Rang</th><th>PID</th><th>Nom</th><th>Surnom</th><th>Nat</th><th>Skill</th></tr></thead>
                        <tbody>
                    """ + rows + """
                        </tbody>
                      </table>
                    </section>
                    """
                )
            # Arbre (liste des matches avec scores)
            if phase.bracket_matches:
                rows = "".join(
                    f"<tr><td>{m['round']}</td><td>{m['A']}</td><td>{m['B']}</td><td class='right'>{m['score'][0]}–{m['score'][1]}</td><td class='right'>{m['winner']}</td></tr>"
                    for m in phase.bracket_matches
                )
                html.append("""
                <section>
                  <h3>Matches & Scores (Double élimination)</h3>
                  <table>
                    <thead><tr><th>Round</th><th>PID A</th><th>PID B</th><th>Score</th><th>Vainqueur</th></tr></thead>
                    <tbody>
                """ + rows + """
                    </tbody>
                  </table>
                </section>
                """)

        html.append("</body></html>")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(html), encoding="utf-8")

# ==============================
# WILD-CARDS / BARRAGES
# ==============================

def apply_wildcards(league: League, targets: Dict[str, int]):
    by_div: Dict[str, List[Player]] = {"D1":[],"D2":[],"D3":[],"D4":[]}
    for p in league.players.values():
        by_div.setdefault(p.division, []).append(p)

    def pick_weighted(cands: List[Player], n: int) -> List[Player]:
        sel = []
        pool = cands[:]
        while pool and len(sel) < n:
            total = sum(max(1, c.season_points) for c in pool)
            r = RNG.rand() * total
            acc = 0
            for i, c in enumerate(pool):
                acc += max(1, c.season_points)
                if r <= acc:
                    sel.append(c); pool.pop(i); break
        return sel

    need = targets.get("D1", 0) - len(by_div.get("D1", []))
    if need > 0:
        cands = [p for p in by_div.get("D2", [])]
        chosen = pick_weighted(cands, need)
        for p in chosen:
            p.division = "D1"
    need = targets.get("D2", 0) - len(by_div.get("D2", []))
    if need > 0:
        cands = [p for p in by_div.get("D3", [])]
        chosen = pick_weighted(cands, need)
        for p in chosen:
            p.division = "D2"
    need = targets.get("D3", 0) - len(by_div.get("D3", []))
    if need > 0:
        cands = [p for p in by_div.get("D4", [])]
        chosen = pick_weighted(cands, need)
        for p in chosen:
            p.division = "D3"

# ==============================
# BOUCLE MULTI-SAISONS + CLI
# ==============================

def _quota_by_division() -> dict[str, int]:
    return {
        "D1": CONFIG.D1_PLAYERS,                                  # 36
        "D2": CONFIG.D2_GROUPS * CONFIG.D2_PLAYERS_PER_GROUP,     # 2*58=116
        "D3": CONFIG.D3_GROUPS * CONFIG.D3_PLAYERS_PER_GROUP,     # 3*84=252
        "D4": CONFIG.D4_GROUPS * CONFIG.D4_PLAYERS_PER_GROUP,     # 4*120=480
    }

def _players_in_div(league: League, div: str) -> list[Player]:
    return [p for p in league.players.values() if p.division == div]

def _demote(pla: Player, to_div: str):
    pla.division = to_div
    # on laisse le group inchangé si to_div a les mêmes codes, sinon on assignera plus tard via rebalance_groups

def _promote(pla: Player, to_div: str):
    pla.division = to_div

def enforce_division_quotas(league: League):
    """
    Rétablit EXACTEMENT les quotas D1/D2/D3/D4 après les mouvements de fin de saison.
    Politique :
      - Si une division est en excès, on renvoie les 'moins méritants' vers la division du dessous
        (tri par points saison + skill en tiebreak).
      - Si une division est en déficit, on remonte les 'plus méritants' depuis la division du dessous
        (même critère).
    On itère du haut vers le bas, puis du bas vers le haut si besoin.
    """
    Q = _quota_by_division()

    # utilitaires tri "mérite"
    def merit_key(p: Player):
        # priorise la performance de la saison, puis skill en tiebreak
        return (p.season_points, p.skill)

    # Phase 1 : du haut vers le bas — on coupe les excédents
    order = ["D1", "D2", "D3", "D4"]
    for i, div in enumerate(order):
        target = Q[div]
        cur = _players_in_div(league, div)
        if len(cur) > target:
            cur.sort(key=merit_key, reverse=True)
            keep = cur[:target]
            excess = cur[target:]
            # demote l'excès vers la division inférieure (sauf D4)
            if div != "D4":
                down = order[i+1]
                for p in excess:
                    _demote(p, down)

    # Phase 2 : du bas vers le haut — on comble les déficits
    # (on part de D1 qui remonte depuis D2, puis D2 depuis D3, etc.)
    for i, div in enumerate(order):
        target = Q[div]
        cur = _players_in_div(league, div)
        if len(cur) < target and div != "D4":
            need = target - len(cur)
            down = order[i+1]
            pool = _players_in_div(league, down)
            pool.sort(key=merit_key, reverse=True)
            take = pool[:need]
            for p in take:
                _promote(p, div)

    # Re-vérif : si une division du bas est devenue excédentaire par les montées du dessus,
    # on coupe à nouveau vers le bas (cascade), ce qui doit s’annuler avec D4 (poubelle de réception).
    for i, div in enumerate(order):
        target = Q[div]
        cur = _players_in_div(league, div)
        if len(cur) > target:
            cur.sort(key=merit_key, reverse=True)
            keep = cur[:target]
            excess = cur[target:]
            if div != "D4":
                down = order[i+1]
                for p in excess:
                    _demote(p, down)

    # À ce stade, chaque division doit avoir son quota exact (somme égale au total nominal).

def run_seasons(n: int, outdir: str = "out", seed: Optional[int] = None):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)

    if seed is None:
        seed = RNG.randint(1, 10_000_000)
        (out / "seed_used.txt").write_text(str(seed), encoding="utf-8")
        print(f"→ Seed utilisé : {seed}")
    RNG.seed(seed)

    lg = make_initial_population()
    for s in range(1, n+1):
        # 1) Saison régulière
        comp = simulate_regular_season(lg)
        standings = standings_by_division(lg)

        # 2) Scores saison pour retraites
        for divmap in standings.values():
            for plist in divmap.values():
                for p in plist:
                    p.season_points = p.points
                    p.best_season_points = max(p.best_season_points, p.season_points)

        # 3) Phase Finale complète
        phase = simulate_phase_finale(lg, standings)

        # 4) Exports
        DataExporter.save_tables_json(out / f"season_{s:02d}_standings.json", s, [], standings)
        DataExporter.save_phase_json(out / f"season_{s:02d}_phase.json", s, phase)
        DataExporter.save_roster_csv(out / f"season_{s:02d}_roster.csv", lg)
        DataExporter.save_relations_json(out / f"season_{s:02d}_relations.json", lg)
        DataExporter.save_roster_html(out / f"season_{s:02d}_roster.html", lg)
        DataExporter.save_html_report(out / f"season_{s:02d}_report.html", s, lg, standings, phase)

        # 5) Fin de saison: retraites
        retiring = []
        for p in list(lg.players.values()):
            if p.should_retire():
                retiring.append(p.pid)
        for pid in retiring:
            if pid in lg.players:
                del lg.players[pid]

        # 6) Promotions / relégations (tes règles existantes)
        apply_promotions_relegations(lg)

        # 7) Wild-cards/barrages pour atteindre les cibles D1–D3 (ton code existant)
        targets = {
            "D1": CONFIG.D1_PLAYERS,
            "D2": CONFIG.D2_GROUPS*CONFIG.D2_PLAYERS_PER_GROUP,
            "D3": CONFIG.D3_GROUPS*CONFIG.D3_PLAYERS_PER_GROUP,
        }
        apply_wildcards(lg, targets)

        # 8) Régénération au total global (inchangé)
        target_total = (CONFIG.D4_GROUPS*CONFIG.D4_PLAYERS_PER_GROUP
                        + CONFIG.D3_GROUPS*CONFIG.D3_PLAYERS_PER_GROUP
                        + CONFIG.D2_GROUPS*CONFIG.D2_PLAYERS_PER_GROUP
                        + CONFIG.D1_PLAYERS)
        while len(lg.players) < target_total:
            np = PlayerFactory.make_player()
            lg.players[np.pid] = np

        # 9) Vieillissement & progression (inchangé)
        for p in lg.players.values():
            p.aging_and_progress()

        # 10) NOUVEAU : normaliser les quotas de division
        enforce_division_quotas(lg)

        # 11) Équilibrer les groupes à l’intérieur des divisions
        rebalance_groups(lg, verbose=False)

    print(f"Simulation terminée: {n} saison(s) exportée(s) dans {out.resolve()}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LVF – Simulation multi-saisons")
    parser.add_argument("--seasons", type=int, default=1, help="Nombre de saisons à simuler")
    # on prend str pour accepter "None", puis on convertit
    parser.add_argument("--seed", type=str, default=None, help="Graine RNG (int) ou 'None' pour auto")
    parser.add_argument("--out", type=str, default="out", help="Dossier d'export")
    args = parser.parse_args()
    seed_val: Optional[int]
    if args.seed is None or args.seed.lower() == "none":
        seed_val = None
    else:
        seed_val = int(args.seed)
    run_seasons(args.seasons, outdir=args.out, seed=seed_val)
