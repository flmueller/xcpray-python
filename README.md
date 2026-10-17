# xcpray – Python scripts for XCP-Ray

Python client of the script interface of **XCP-Ray**, a measurement and calibration tool for
ECUs with XCP (CAN, CAN FD, UDP/IP, serial). With it a script reads and writes ECU values
while XCP-Ray is connected, starts and stops measurements and puts markers into the
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

## API

| Call | |
| --- | --- |
| `connect(host="127.0.0.1", port=None, token=None, token_file=None)` | port: `XCPRAY_PORT` or 5591; token: `XCPRAY_TOKEN`, the file `XCPRAY_TOKEN_FILE` or the default file |
| `info()` | version, project, measuring, ECUs with their state |
| `list_signals(ecu=None)` | name (`ECU:NAME`), kind, unit, min, max, writable, texts |
| `read(*signals)` | current values from the ECU, physical; one signal: the value, several: a dict |
| `read_texts(*signals)` | the values as shown in XCP-Ray (texts of enumerations) |
| `write(signal, value)` | writes a parameter, returns the value read back |
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
