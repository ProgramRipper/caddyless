#!/usr/bin/env python3

import importlib.resources
import json
import os
import re
import string
import sys
from argparse import REMAINDER, ArgumentParser
from collections import defaultdict
from contextlib import suppress
from random import randint
from typing import Any, NoReturn
from urllib.request import Request, urlopen


class JSON(defaultdict):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(JSON, *args, **kwargs)

    def __repr__(self) -> str:
        return dict.__repr__(self)


def serialize(obj: Any) -> bytes:
    def _serialize(obj: Any) -> Any:
        if isinstance(obj, list):
            return [_serialize(item) for item in obj]

        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                value = _serialize(value)
                if not isinstance(value, dict) or value:
                    result[key] = value
            return result

        return obj

    return json.dumps(_serialize(obj)).encode()


def deserialize(obj: str | bytes | bytearray) -> Any:
    def _deserialize(obj: Any) -> Any:
        if isinstance(obj, list):
            return [_deserialize(item) for item in obj]

        if isinstance(obj, dict):
            return JSON({key: _deserialize(value) for key, value in obj.items()})

        return obj

    return _deserialize(json.loads(obj))


def sanitize_host(host: str) -> str:
    labels = []
    for label in host.split("."):
        label = label.lower()
        label = re.sub(r"[^a-z0-9-]", "-", label)
        if label.startswith("xn--"):
            label = "xn--" + re.sub(r"-{2,}", "-", label[4:])
        else:
            label = re.sub(r"-{2,}", "-", label)
        label = label.strip("-")
        if label:
            labels.append(label)
    return ".".join(labels)


def check_host(host: str) -> None:
    if not 0 < len(host) <= 253:
        raise ValueError

    for label in host.split("."):
        if not 0 < len(label) <= 63:
            raise ValueError
        if label.startswith("-") or label.endswith("-"):
            raise ValueError
        if set(label) > set(string.ascii_lowercase + string.digits + "-"):
            raise ValueError


def check_tld(host: str) -> bool:
    labels = host.rsplit(".", 1)
    if len(labels) == 1:
        return host == "localhost"

    tld = labels[-1]

    if tld in {"alt", "example", "local", "localhost", "onion", "test"}:
        return True

    if __package__:
        file = importlib.resources.open_binary(__package__, "tlds-alpha-by-domain.txt")
    else:
        file = urlopen("https://data.iana.org/TLD/tlds-alpha-by-domain.txt")

    with file:
        return tld.upper().encode() in (
            line.strip() for line in file if not line.startswith(b"#")
        )


def init_config(config: Any) -> None:
    config["apps"]["http"]["servers"]["portless"] = {"listen": [":443"], "routes": []}
    policy = {"issuers": [{"module": "internal"}], "on_demand": True}
    policies = config["apps"]["tls"]["automation"].setdefault("policies", [])
    if policy not in policies:
        policies.insert(0, policy)


def main(name: str, cmd: list[str]) -> NoReturn:
    if name == "run":
        raise  # TODO
    else:
        host = name
        check_host(host)

    if not check_tld(host):
        host += ".localhost"

    port = int(os.environ.setdefault("PORT", str(randint(1024, 49152))))
    with suppress(ValueError):
        cmd[cmd.index("$PORT")] = str(port)

    config = deserialize(urlopen("http://localhost:2019/config/").read()) or JSON()
    if not config["apps"]["http"]["servers"]["portless"]:
        init_config(config)

    routes = config["apps"]["http"]["servers"]["portless"]["routes"]
    for route in routes:
        if route["match"][0]["host"] == [host, f"*.{host}"]:
            route["handle"][0]["upstreams"][0]["dial"] = f"localhost:{port}"
            break
    else:
        routes.insert(
            0,
            {
                "handle": [
                    {
                        "handler": "reverse_proxy",
                        "upstreams": [{"dial": f"localhost:{port}"}],
                    }
                ],
                "match": [{"host": [host, f"*.{host}"]}],
                "terminal": True,
            },
        )

    urlopen(
        Request(
            "http://localhost:2019/config/",
            serialize(config),
            {"Content-Type": "application/json"},
            method="POST",
        )
    )

    sys.stderr.write(
        f"\x1b[90mReverse proxy from \x1b[1;4;34mhttps://{host}\x1b[0m\x1b[90m to http://localhost:{port}\n"
        f"Running command: PORT={port} {' '.join(cmd)}\x1b[0m\n"
        "\n"
    )
    os.execlp(cmd[0], *cmd)


def __main__() -> NoReturn:
    parser = ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("cmd", nargs=REMAINDER)

    main(**vars(parser.parse_args()))


if __name__ == "__main__":
    __main__()
