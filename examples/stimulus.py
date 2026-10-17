"""A simple stimulus: parameters set at fixed times while XCP-Ray measures and records.

Start XCP-Ray with the project, switch on File > Settings > Script interface, connect the ECU,
then run:  python stimulus.py
The names below belong to the simulator of XCP-Ray (xcp-sim, examples/udp_demo.x1p); use your own.
"""

import time

import xcpray

# time after the start [s], signal, value
STEPS = [
    (0.0, "ENGINE:sim_amplitude", 10),
    (2.0, "ENGINE:sim_frequency", 2),
    (4.0, "ENGINE:sim_amplitude", 20),
    (6.0, "ENGINE:sim_enable", "OFF"),
    (8.0, "ENGINE:sim_enable", "ON"),
]
DURATION = 10.0  # then the measurement stops
WATCH = ["ENGINE:sim_sine", "ENGINE:sim_amplitude"]  # printed every second

with xcpray.connect() as ray:
    print("XCP-Ray", ray.info()["version"])
    ray.start_measurement()
    ray.marker("stimulus started")
    start = time.monotonic()
    pending = sorted(STEPS, key=lambda s: s[0])
    next_print = 0.0
    while True:
        t = time.monotonic() - start
        while pending and pending[0][0] <= t:
            _, signal, value = pending.pop(0)
            print(f"{t:6.2f} s  {signal} = {value} -> {ray.write(signal, value)}")
        if t >= next_print:
            print(f"{t:6.2f} s  {ray.read(*WATCH)}")
            next_print += 1.0
        if t >= DURATION:
            break
        time.sleep(0.01)
    ray.marker("stimulus done")
    ray.stop_measurement()
