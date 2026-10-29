"""Python client of the script interface of XCP-Ray, a measurement and calibration tool for XCP.

XCP-Ray (File > Settings > Script interface) listens on 127.0.0.1 and accepts JSON-RPC 2.0, one
JSON message per line. This module connects, authenticates with the token that XCP-Ray writes
into the file ``api-token`` next to its settings, and offers the methods as Python calls::

    import xcpray

    with xcpray.connect() as ray:
        ray.write("ENGINE:sim_amplitude", 20)
        print(ray.read("ENGINE:sim_sine", "ENGINE:sim_amplitude"))

Signals of a bus with a DBC (CAN) or LDF (LIN) are named "BUS:Message.Signal": read() decodes
the last frame received, write() sets the value of the restbus simulation.

No dependencies besides the Python standard library (3.8 or newer).
"""

import json
import os
import socket
import sys
import time

__version__ = "0.2.0"
__all__ = ["connect", "Client", "XcpRayError", "default_token_file", "DEFAULT_PORT"]

DEFAULT_PORT = 5591


class XcpRayError(Exception):
    """An error answered by XCP-Ray (e.g. a value outside the limits), or a lost connection."""

    def __init__(self, message, code=None):
        super().__init__(message)
        self.code = code


def default_token_file():
    """The token file of XCP-Ray with its default settings: Linux ~/.config/xcpray/api-token
    ($XDG_CONFIG_HOME), Windows %APPDATA%\\xcpray\\api-token."""
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "xcpray", "api-token")


class Client:
    """A connection to XCP-Ray. Use connect() to make one."""

    def __init__(self, host="127.0.0.1", port=None, token=None, token_file=None, timeout=30.0):
        port = int(port or os.environ.get("XCPRAY_PORT", DEFAULT_PORT))
        if token is None:
            token = os.environ.get("XCPRAY_TOKEN")
        if token is None:
            path = token_file or os.environ.get("XCPRAY_TOKEN_FILE") or default_token_file()
            try:
                with open(path, encoding="utf-8") as f:
                    token = f.read().strip()
            except OSError as e:
                raise XcpRayError(f"no token: {path} cannot be read ({e}); is the script interface of XCP-Ray on?") from e
        try:
            self._socket = socket.create_connection((host, port), timeout=timeout)
        except OSError as e:
            raise XcpRayError(f"XCP-Ray does not answer on {host}:{port} ({e}); is the script interface on?") from e
        self._file = self._socket.makefile("r", encoding="utf-8", newline="\n")
        self._next_id = 1
        self.call("auth", token=token)

    # --- the methods of XCP-Ray ---------------------------------------------------------------

    def info(self):
        """Version, project, whether it measures, the ECUs with their state."""
        return self.call("info")

    def describe(self):
        """The methods of the interface with their parameters (JSON schema)."""
        return self.call("describe")

    def list_signals(self, ecu=None):
        """Measurements and parameters ("ECU:NAME") and bus signals ("BUS:Message.Signal", kind
        "bus_signal", with frame and cycle_ms): dicts with name, kind, unit, min, max, writable, texts."""
        return self.call("list_signals", **({"ecu": ecu} if ecu else {}))

    def read(self, *signals):
        """Current values: {name: value}; a single name gives the value itself. ECU signals are
        read from the ECU, bus signals decoded from the last frame on the bus (read_full() gives
        its age in s). Enumerations give their raw value; read_texts() gives the texts."""
        result = self.read_full(*signals)
        values = {}
        for r in result:
            if "error" in r:
                raise XcpRayError(f"{r['signal']}: {r['error']}")
            values[r["signal"]] = r["value"]
        return values[signals[0]] if len(signals) == 1 else values

    def read_texts(self, *signals):
        """Like read(), but the values as shown in XCP-Ray (texts of enumerations, formatted numbers)."""
        result = self.read_full(*signals)
        texts = {r["signal"]: r.get("text", r.get("error")) for r in result}
        return texts[signals[0]] if len(signals) == 1 else texts

    def read_full(self, *signals):
        """The complete answer of XCP-Ray: one dict per signal with value, text, unit or error;
        bus signals also with age (s since the frame) and tx (sent by XCP-Ray)."""
        return self.call("read", signals=list(signals))

    def write(self, signal, value):
        """Writes a parameter (a number in physical units, or a text of an enumeration) and returns
        the value read back. The limits of the A2L apply: outside them it raises XcpRayError.
        A bus signal sets the value of the restbus simulation (limited to what the signal can
        hold) and returns it; it is sent while its frame is active and the simulation runs."""
        return self.call("write", signal=signal, value=value).get("value")

    def restbus_start(self, bus):
        """Starts the restbus simulation of a bus (connects it if needed); True if it runs."""
        return self.call("restbus_start", bus=bus)["running"]

    def restbus_stop(self, bus):
        """Stops the restbus simulation of a bus; False once it has stopped."""
        return self.call("restbus_stop", bus=bus)["running"]

    def start_measurement(self):
        """Starts the measurement and the recording; True if it measures."""
        return self.call("start_measurement")["measuring"]

    def stop_measurement(self):
        """Stops the measurement; False once it has stopped."""
        return self.call("stop_measurement")["measuring"]

    def marker(self, text):
        """An event with this text in the running recording (marked in the scopes)."""
        return self.call("marker", text=text)["recorded"]

    # --- helpers ------------------------------------------------------------------------------

    @staticmethod
    def wait(seconds):
        """Waits (a plain time.sleep, for scripts that read like a test plan)."""
        time.sleep(seconds)

    def call(self, method, **params):
        """Calls any method of the interface; returns its result or raises XcpRayError."""
        request = {"jsonrpc": "2.0", "id": self._next_id, "method": method, "params": params}
        self._next_id += 1
        try:
            self._socket.sendall((json.dumps(request) + "\n").encode("utf-8"))
            while True:
                line = self._file.readline()
                if not line:
                    raise XcpRayError("XCP-Ray closed the connection")
                answer = json.loads(line)
                if answer.get("id") == request["id"] or answer.get("id") is None:
                    break
        except OSError as e:
            raise XcpRayError(f"connection to XCP-Ray lost ({e})") from e
        if "error" in answer:
            raise XcpRayError(answer["error"].get("message", "error"), answer["error"].get("code"))
        return answer.get("result")

    def close(self):
        try:
            self._file.close()
        finally:
            self._socket.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def connect(host="127.0.0.1", port=None, token=None, token_file=None, timeout=30.0):
    """Connects to XCP-Ray on this computer. Port: argument, $XCPRAY_PORT or 5591. Token:
    argument, $XCPRAY_TOKEN, the file token_file / $XCPRAY_TOKEN_FILE, or default_token_file()."""
    return Client(host, port, token, token_file, timeout)
