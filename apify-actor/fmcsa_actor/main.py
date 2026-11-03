"""Apify Actor entrypoint.

The run reads the caller's FMCSA WebKey from the secret input and writes
carrier records from the official QCMobile API to the default dataset.
"""

from __future__ import annotations

import asyncio

from apify import Actor

from .client import FmcsaClient
from .input_parser import parse_input


async def main() -> None:
    async with Actor:
        raw = await Actor.get_input() or {}
        request = parse_input(raw)
        Actor.log.info(
            "Querying the official FMCSA QCMobile API (dot=%s, docket=%s, name=%s).",
            request.dot_number,
            request.docket_query,
            request.carrier_name,
        )
        client = FmcsaClient(request.web_key)
        rows = await asyncio.to_thread(client.lookup, request)
        Actor.log.info("Saving %s record(s) from the official FMCSA API to the dataset.", len(rows))
        if rows:
            await Actor.push_data(rows)
