# ai-generated: 100% - Codex made the measured Toxiproxy experiment reproducible and idempotent.
"""Run after docker compose --profile gap up -d; only updates this lab's named proxy/toxic."""
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def call(method, path, body=None, ignore=()):
    request = Request("http://localhost:8474" + path, method=method,
                      data=None if body is None else json.dumps(body).encode(),
                      headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=5) as response:
            return json.load(response) if response.status != 204 else None
    except HTTPError as error:
        if error.code not in ignore:
            raise


def main():
    toxic = json.loads(Path(__file__).parents[1].joinpath("gap.json").read_text())["toxic"]
    proxy = {"name": "svcdesk", "listen": "0.0.0.0:8666", "upstream": "svcdesk:8080", "enabled": True}
    call("POST", "/proxies", proxy, ignore=(409,))
    call("POST", "/proxies/svcdesk", proxy)
    call("DELETE", "/proxies/svcdesk/toxics/lab3-latency", ignore=(404,))
    call("POST", "/proxies/svcdesk/toxics", {
        "name": "lab3-latency", "type": "latency", "stream": "downstream", "toxicity": 1.0,
        "attributes": {"latency": toxic["latency"], "jitter": toxic["jitter"]},
    })
    print("Configured svcdesk proxy at localhost:8666 with", toxic)


if __name__ == "__main__":
    main()
