"""Small sequential stdio MCP client for an isolated SolidCraft session."""

import json
import os
import queue
import shutil
import subprocess
import threading
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[3]
EXECUTABLE = os.environ.get("SOLIDCRAFT_CLI") or shutil.which("solidcraft-cli") or r"C:\Program Files\SolidCraft\solidcraft-cli.exe"


class SolidCraftMCP:
    def __init__(self, *, design=None, timeout=60):
        command = [str(EXECUTABLE), "mcp", "--headless", "--allow-path", str(WORKSPACE), "--compact"]
        if design is not None:
            command.extend(["--in", str(Path(design).resolve())])
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True, encoding="utf-8", cwd=WORKSPACE)
        self.timeout = timeout
        self.messages = queue.Queue()
        self.stderr = []
        self.request_id = 0
        threading.Thread(target=self._read_output, daemon=True).start()
        threading.Thread(target=self._read_errors, daemon=True).start()
        try:
            self.server = self._rpc("initialize", {"protocolVersion":"2024-11-05", "capabilities":{},
                                                    "clientInfo":{"name":"mac-mini-solidcraft", "version":"1.0"}})
            self._send({"jsonrpc":"2.0", "method":"notifications/initialized"})
        except Exception:
            self.close()
            raise

    def _read_output(self):
        for line in self.process.stdout:
            try:
                self.messages.put(json.loads(line))
            except json.JSONDecodeError:
                self.stderr.append(line.rstrip())
        self.messages.put(None)

    def _read_errors(self):
        for line in self.process.stderr:
            self.stderr.append(line.rstrip())

    def _send(self, request):
        self.process.stdin.write(json.dumps(request) + "\n")
        self.process.stdin.flush()

    def _rpc(self, method, params):
        self.request_id += 1
        request_id = self.request_id
        self._send({"jsonrpc":"2.0", "id":request_id, "method":method, "params":params})
        while True:
            reply = self.messages.get(timeout=self.timeout)
            if reply is None:
                raise RuntimeError("SolidCraft exited: " + "\n".join(self.stderr[-10:]))
            if reply.get("id") == request_id:
                if "error" in reply:
                    raise RuntimeError(reply["error"])
                return reply["result"]

    def call(self, tool, arguments=None):
        result = self._rpc("tools/call", {"name":tool, "arguments":arguments or {}})
        if result.get("isError"):
            raise RuntimeError(result)
        return result

    def json(self, tool, arguments=None):
        result = self.call(tool, arguments)
        text = "\n".join(block["text"] for block in result.get("content", []) if block.get("type") == "text")
        return json.loads(text)

    def close(self):
        self.process.stdin.close()
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            self.process.wait(timeout=3)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
