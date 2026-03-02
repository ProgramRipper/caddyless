#!/usr/bin/env python3

import json
import os
import sys
from argparse import REMAINDER, ArgumentParser
from contextlib import suppress
from random import randint
from typing import Any, Literal, NoReturn
from urllib.request import Request, urlopen
from urllib.response import addinfourl

parser = ArgumentParser()
parser.add_argument("name")
parser.add_argument("cmd", nargs=REMAINDER)


class CaddyException(Exception):
    code: int
    error: str

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.error = message
        super().__init__(f"Caddy API error: {message} (code: {code})")


def config(
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"],
    path: str,
    data: Any = None,
) -> Any:
    resp: addinfourl = urlopen(
        Request(
            "http://localhost:2019" + path,
            json.dumps(data).encode() if data else None,
            {"Content-Type": "application/json"} if data else {},
            method=method,
        )
    )

    if resp.status is None:
        raise Exception("Unexpected response from Caddy API: no status code")
    if resp.status != 200:
        message = resp.read().decode()
        if resp.headers.get_content_type() == "application/json":
            message = json.loads(message)["error"]
        raise CaddyException(resp.status, message)

    return (
        json.load(resp) if resp.headers.get_content_type() == "application/json" else None
    )


def route(data: Any, host: str, port: int) -> Any:
    routes = data["apps"]["http"]["servers"]["portless"]["routes"]

    for route in routes:
        if route["match"][0]["host"][0] == host:
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
                "match": [{"host": [host]}],
                "terminal": True,
            },
        )

    return data


def main(name: str, cmd: list[str]) -> NoReturn:
    host = name if name == "localhost" or "." in name else f"{name}.localhost"
    port = int(os.environ.setdefault("PORT", str(randint(1024, 49152))))

    data = config("GET", "/config/")
    try:
        data = route(data, host, port)
    except (KeyError, TypeError):
        data = route(
            {
                "apps": {
                    "http": {
                        "servers": {
                            "portless": {
                                "listen": [":443"],
                                "routes": [],
                            }
                        }
                    },
                    "tls": {
                        "automation": {
                            "policies": [
                                {
                                    "issuers": [{"module": "internal"}],
                                    "on_demand": True,
                                }
                            ]
                        }
                    },
                },
            },
            host,
            port,
        )
    config("POST", "/load", data)

    with suppress(ValueError):
        cmd[cmd.index("$PORT")] = str(port)

    sys.stderr.write(
        f"\x1b[90mReverse proxy from \x1b[1;4;34mhttps://{host}\x1b[0m\x1b[90m to http://localhost:{port}\n"
        f"Running command: PORT={port} {' '.join(cmd)}\x1b[0m\n"
        "\n"
    )

    os.execlp(cmd[0], *cmd)


def __main__():
    main(**vars(parser.parse_args()))


if __name__ == "__main__":
    __main__()
