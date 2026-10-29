# xcpray – Python scripts for XCP-Ray

Python client of the script interface of **XCP-Ray**, a measurement and calibration tool for
ECUs with XCP (CAN, CAN FD, UDP/IP, serial). With it a script reads and writes ECU values
while XCP-Ray is connected, reads and sets signals of CAN and LIN buses (DBC, LDF, restbus simulation), starts and stops measurements and puts markers into the
recording, for example to play a stimulus during a test.

The library is MIT licensed and needs nothing but Python 3.8 or newer. XCP-Ray itself is free
to use, but not open source.

## Installation

```sh
pip install git+https://github.com/flmueller/xcpray-python
```

or copy `src/xcpray/` next to your script.

## In XCP-Ray

File > Settings > Script interface (Python): switch it on (port 5591 by default). XCP-Ray then
listens on 127.0.0.1 only and writes a new token into the file `api-token` next to its
settings (Linux `~/.config/xcpray/`, Windows `%APPDATA%\xcpray\`); a script authenticates with
it. Writes of a script go the same way as typed values: the limits of the A2L apply, and they
appear in the log and in the recording, marked "(script)".

### From another computer

File > Settings > Script interface > "Allow access from other computers" makes XCP-Ray listen on
all interfaces. Copy the token shown there and connect with it:

```python
ray = xcpray.connect(host="192.168.1.20", token="…")    # or XCPRAY_TOKEN
```

The connection is not encrypted (token and values in plain text): use it only in trusted
networks.

## Example

```python
import xcpray

with xcpray.connect() as ray:
    print(ray.info())                                   # version, project, ECUs
    ray.start_measurement()
    ray.write("ENGINE:sim_amplitude", 20)              # physical value, read back
    ray.write("ENGINE:sim_enable", "OFF")              # a text of an enumeration
    ray.wait(2)
    print(ray.read("ENGINE:sim_sine", "ENGINE:sim_amplitude"))
    ray.marker("step done")                            # an event in the recording
    ray.stop_measurement()
```

`examples/stimulus.py` plays a list of (time, signal, value) during a measurement. Checks are
plain Python, e.g. with `assert` or pytest.

### Buses (DBC, LDF) and the restbus simulation

Signals of a CAN bus with a DBC or a LIN bus with an LDF are named `BUS:Message.Signal`.
`read()` decodes the last frame received on the bus (also without a measurement, while the bus
is connected); `read_full()` adds its age in seconds. `write()` sets the value of the restbus
simulation: it is sent while its frame is active (checked in the restbus display) and the
simulation runs. Needs XCP-Ray 0.36 or newer.

```python
with xcpray.connect() as ray:
    ray.restbus_start("BODY")
    ray.write("BODY:BCM_Wiper.WiperMode", "fast")       # a text of the value table, or a number
    ray.wait(0.5)
    print(ray.read("BODY:Wiper_Status.WiperPosition"))  # decoded from the last frame
    ray.restbus_stop("BODY")
```

## API

| Call | |
| --- | --- |
| `connect(host="127.0.0.1", port=None, token=None, token_file=None)` | port: `XCPRAY_PORT` or 5591; token: `XCPRAY_TOKEN`, the file `XCPRAY_TOKEN_FILE` or the default file |
| `info()` | version, project, measuring, ECUs with their state |
| `list_signals(ecu=None)` | name (`ECU:NAME`, `BUS:Message.Signal`), kind, unit, min, max, writable, texts |
| `read(*signals)` | current values, physical (ECU: read from it; bus: the last frame); one signal: the value, several: a dict |
| `read_texts(*signals)` | the values as shown in XCP-Ray (texts of enumerations) |
| `write(signal, value)` | writes a parameter, returns the value read back; a bus signal: the value of the restbus simulation |
| `restbus_start(bus)`, `restbus_stop(bus)` | starts / stops the restbus simulation of a bus |
| `start_measurement()`, `stop_measurement()` | as F5 / F6 in XCP-Ray |
| `marker(text)` | an event in the running recording |
| `describe()` | the methods of the interface with their parameters (JSON schema) |
| `call(method, **params)` | any method by name |

Errors (a value outside the limits, an unknown signal, no connection) raise `xcpray.XcpRayError`.

## Protocol

JSON-RPC 2.0 over TCP on 127.0.0.1, one JSON message per line; the first call is
`{"method": "auth", "params": {"token": "..."}}`. `describe` lists the methods with JSON schemas
of their parameters, so other languages (or an MCP adapter) can use the interface as well.

## License

MIT, see [LICENSE](LICENSE).
