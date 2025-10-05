#!/usr/bin/env python3
"""
SmallAI API Server
FastAPI service for natural language to Splunk SPL query conversion
"""

import sys
import os
from pathlib import Path
import importlib
import subprocess
import ast
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Add src to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

app = FastAPI(
    title="SmallAI Parser",
    description="Natural Language to Splunk SPL Query Parser",
    version="2.0"
)

# Request model
class QueryRequest(BaseModel):
    query: str
    force: bool = False


# Attempt to import the hybrid parser module
hp_module = None
try:
    hp_module = importlib.import_module('hybrid_parser')
except Exception as e:
    print(f"Warning: Could not import hybrid_parser: {e}")


@app.get('/health')
def health():
    """Health check endpoint"""
    return {
        'status': 'ok',
        'hp_loaded': hp_module is not None,
        'version': '2.0'
    }


@app.post('/parse')
def parse_query(req: QueryRequest):
    """
    Parse natural language query and generate Splunk SPL.

    Returns:
        - parsed: Extracted slots (action, time, user, source, etc.)
        - spl: Generated Splunk SPL query
        - source: 'inproc' (Python) or 'cli' (subprocess)
    """
    # Use hybrid_parser's parse_natural_language if available
    if hp_module and not req.force:
        try:
            from hybrid_parser import parse_natural_language, generate_spl_query

            slots = parse_natural_language(req.query)
            spl = generate_spl_query(slots, req.query)

            return {
                'query': req.query,
                'slots': slots,
                'spl': spl,
                'source': 'inproc'
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f'Parser error: {str(e)}')

    # Fallback to CLI execution
    cmd = ['python3', str(ROOT / 'hybrid_parser.py'), req.query]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=str(ROOT))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'CLI execution error: {str(e)}')

    if proc.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f'CLI error: {proc.stderr or proc.stdout}'
        )

    # Parse CLI stdout
    parsed_slots = None
    spl = None

    for line in proc.stdout.splitlines():
        line = line.strip()
        if line.startswith('Parsed Slots:'):
            try:
                parsed_slots = ast.literal_eval(line.split('Parsed Slots:')[1].strip())
            except Exception:
                parsed_slots = line.split('Parsed Slots:')[1].strip()
        if line.startswith('SPL:'):
            spl = line.split('SPL:')[1].strip()

    return {
        'query': req.query,
        'slots': parsed_slots,
        'spl': spl,
        'stdout': proc.stdout,
        'source': 'cli'
    }


@app.get('/')
def root():
    """Root endpoint with API information"""
    return {
        'name': 'SmallAI Parser API',
        'version': '2.0',
        'endpoints': {
            '/health': 'Health check',
            '/parse': 'POST - Parse natural language query to SPL',
            '/docs': 'API documentation (Swagger UI)',
            '/redoc': 'API documentation (ReDoc)'
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
