"""Compare steady-state inventory CPU without launching Steam or the game."""

import argparse
from contextlib import nullcontext
from pathlib import Path
import platform
import resource
from statistics import median
import tempfile
import time
from unittest.mock import patch

from harness import live_inventory, main_launcher, reward_probe


def cpu_time():
    return sum(usage.ru_utime + usage.ru_stime for usage in (
        resource.getrusage(resource.RUSAGE_SELF), resource.getrusage(resource.RUSAGE_CHILDREN)))


def measure(name, root, scans, interval):
    session = (live_inventory.prepare(root) if name == "native"
               else nullcontext(main_launcher._inventory))
    observe_fallback = (patch.object(reward_probe, "_process_inventory",
                                     wraps=reward_probe._process_inventory)
                        if name == "native" else nullcontext())
    latencies = []
    with observe_fallback as fallback:
        with session as lookup:
            cpu_start = cpu_time()
            wall_start = time.perf_counter()
            for _ in range(scans):
                started = time.perf_counter()
                lookup()
                latencies.append(time.perf_counter() - started)
                time.sleep(interval)
        # The session reaps its worker before RUSAGE_CHILDREN is read.
        return cpu_time() - cpu_start, time.perf_counter() - wall_start, latencies, (
            fallback.call_count if fallback is not None else 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scans", type=int, default=20, help="Scans per block")
    parser.add_argument("--interval", type=float, default=0.5, help="Seconds between scans")
    options = parser.parse_args()
    if platform.system() != "Darwin" or options.scans < 1 or options.interval < 0:
        parser.error("Requires macOS, a positive scan count and a nonnegative interval")

    samples = {"legacy": [], "native": []}
    with tempfile.TemporaryDirectory(prefix="inventory-benchmark-", dir="/private/tmp") as directory:
        for order in (("legacy", "native"), ("native", "legacy")):
            for name in order:
                samples[name].append(measure(name, Path(directory), options.scans, options.interval))

    print(f"macOS {platform.mac_ver()[0]} ({platform.machine()}), "
          f"{options.scans * 2} scans per implementation, {options.interval:g}s between scans")
    cpu_per_scan = {}
    for name, blocks in samples.items():
        cpu = sum(block[0] for block in blocks)
        elapsed = sum(block[1] for block in blocks)
        latencies = [latency for block in blocks for latency in block[2]]
        cpu_per_scan[name] = cpu * 1000 / len(latencies)
        print(f"{name}: {cpu_per_scan[name]:.2f} ms CPU/scan, "
              f"{median(latencies) * 1000:.2f} ms median wall/scan, "
              f"{100 * cpu / elapsed:.2f}% of one core at measured cadence")
    print(f"Native legacy fallbacks: {sum(block[3] for block in samples['native'])}")
    print(f"CPU reduction: {100 * (1 - cpu_per_scan['native'] / cpu_per_scan['legacy']):.1f}%")


if __name__ == "__main__":
    main()
