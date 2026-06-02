from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path('.').resolve()))

from agents.orchestrator import OzStartupFinderPipeline


async def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s | %(message)s',
        stream=sys.stdout,
    )
    query = 'Melbourne Fintech'
    pipeline = OzStartupFinderPipeline(session_id='system-debug-orch')
    state = await pipeline.run(query)
    payload = {
        'query': query,
        'retrieved_count': len(state.retrieved_candidates),
        'retrieved_sample': state.retrieved_candidates[:5],
        'enriched_count': len(state.enriched_leads),
        'scored_count': len(state.scored_leads),
        'synthesis_summary': (state.synthesis or {}).get('summary'),
    }
    sys.stdout.write('ORCH_DEBUG=' + json.dumps(payload, indent=2, ensure_ascii=False) + '\n')
    return 0 if state.retrieved_candidates else 2


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
