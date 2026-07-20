#!/usr/bin/env python3
# -*- tab-width: 4; indent-tabs-mode: nil; py-indent-offset: 4 -*-
#
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Call one tool on the local low-level computer-use HTTP MCP server.

This intentionally small bridge lets PowerShell verification harnesses use the
real long-lived MCP server rather than importing its Win32 implementation or
falling back to a series of short-lived CLI processes.  The server owns the
off-screen desktop handle for the full run.
"""

import argparse
import asyncio
import base64
import datetime
import json
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8765/mcp")
    parser.add_argument("--tool", required=True)
    parser.add_argument("--arguments-json", default="{}")
    parser.add_argument("--arguments-base64")
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")
    arguments_text = args.arguments_json
    if args.arguments_base64 is not None:
        try:
            arguments_text = base64.b64decode(
                args.arguments_base64, validate=True
            ).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as error:
            parser.error("--arguments-base64 is not valid UTF-8 JSON: {}".format(error))
    try:
        args.arguments = json.loads(arguments_text)
    except json.JSONDecodeError as error:
        parser.error("tool arguments are not valid JSON: {}".format(error))
    if not isinstance(args.arguments, dict):
        parser.error("--arguments-json must decode to an object")
    return args


async def call_tool(args):
    timeout = datetime.timedelta(seconds=args.timeout)
    async with streamable_http_client(args.url) as (read, write, _session_id):
        async with ClientSession(read, write, read_timeout_seconds=timeout) as session:
            await session.initialize()
            # This server exposes each Pydantic input model as the function's
            # named ``params`` argument.  Parameterless tools use an empty
            # object; every other call must preserve that wrapper.
            tool_arguments = (
                {"params": args.arguments} if args.arguments else {}
            )
            result = await session.call_tool(
                args.tool, tool_arguments, read_timeout_seconds=timeout
            )

    texts = [block.text for block in result.content if block.type == "text"]
    if not texts:
        raise RuntimeError("MCP tool returned no text result")
    payload_text = "\n".join(texts)
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as error:
        raise RuntimeError("MCP tool returned invalid JSON: {}".format(error)) from error
    if result.isError or not isinstance(payload, dict) or payload.get("ok") is not True:
        raise RuntimeError("MCP tool failed: {}".format(payload_text))
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def main():
    args = parse_arguments()
    try:
        asyncio.run(call_tool(args))
    except Exception as error:
        print("{}: {}".format(type(error).__name__, error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
