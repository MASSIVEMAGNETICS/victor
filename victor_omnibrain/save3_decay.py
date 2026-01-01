import math
import time

class SAVE3Decay:
    def __init__(self, half_life: float = 100.0):
        self.half_life = half_life
        self.decay_rate = math.log(2) / half_life
        self.score = 1.0
        self.last_access = time.time()

    def decay(self, current_tick: float):
        """Apply decay to current score"""
        time_diff = current_tick - self.last_access
        self.score *= math.exp(-self.decay_rate * time_diff)
        self.last_access = current_tick
