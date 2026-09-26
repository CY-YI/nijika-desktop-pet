"""Briefly run a real layered window and report timer/display frame pacing."""

import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pet import PetWindow  # noqa: E402


class ProbedPet(PetWindow):
    def __init__(self, width):
        super().__init__(width=width, demo_seconds=5)
        self.starts = []
        self.durations = []

    def tick(self):
        start = time.perf_counter()
        super().tick()
        if self.hwnd:
            self.starts.append(start)
            self.durations.append((time.perf_counter() - start) * 1000)


def summary(samples):
    ordered = sorted(samples)
    return f"median={statistics.median(samples):.1f}ms p95={ordered[int(len(samples) * .95)]:.1f}ms"


pet = ProbedPet(int(sys.argv[1]) if len(sys.argv) > 1 else 320)
pet.run()
intervals = [(b - a) * 1000 for a, b in zip(pet.starts, pet.starts[1:])]
print(f"frames={len(pet.starts)} over={pet.starts[-1] - pet.starts[0]:.2f}s")
print(f"frame interval: {summary(intervals)}")
print(f"tick duration: {summary(pet.durations)}")
