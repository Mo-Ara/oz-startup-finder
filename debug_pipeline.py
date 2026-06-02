from __future__ import annotations

import sqlite3
from pathlib import Path
from agents.orchestrator import OzStartupFinderPipeline, _json_from_event_text
import asyncio

async def main():
    pipeline = OzStartupFinderPipeline()
    state = await pipeline.run('melbourne fintech')
    print('retrieved:', len(state.retrieved_candidates))
    print('enriched:', len(state.enriched_leads))
    print('scored:', len(state.scored_leads))
    print('synthesis:', state.synthesis)
    print('router_output:', state.router_output)

if __name__ == '__main__':
    asyncio.run(main())
