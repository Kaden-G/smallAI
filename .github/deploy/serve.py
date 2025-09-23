#!/usr/bin/env python3
force: bool = False


# Attempt to import the hybrid parser module (preferred)
hp_module = None
models = None
try:
hp_module = importlib.import_module('hybrid_parser')
# optional API: load_models / predict_query / to_spl
if hasattr(hp_module, 'load_models'):
models = hp_module.load_models()
except Exception:
hp_module = None
models = None




@app.get('/health')
def health():
return {
'status': 'ok',
'hp_loaded': hp_module is not None and models is not None
}




@app.post('/rewrite-query')
def rewrite(req: QueryRequest):
"""Return parsed slots and generated SPL for a given NL query.


If the in-process module is importable and exposes a `predict_query` API,
use it. Otherwise fallback to running the CLI script.
"""
# If we have an inproc module and models, use it (unless force requests CLI fallback)
if hp_module and models and not req.force:
try:
parsed = hp_module.predict_query(req.query, models)
spl = None
if hasattr(hp_module, 'to_spl'):
spl = hp_module.to_spl(parsed)
return { 'parsed': parsed, 'spl': spl, 'source': 'inproc' }
except Exception as e:
raise HTTPException(status_code=500, detail=f'inproc error: {e}')


# Otherwise fallback to CLI execution
# Use -f flag if force requested, which makes CLI skip interactive prompts
cmd = ['python', str(ROOT / 'src' / 'hybrid_parser.py')]
if req.force:
cmd.insert(2, '-f') # python -m -f ... (ensure correct placement)
cmd.append(req.query)


try:
proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
except Exception as e:
raise HTTPException(status_code=500, detail=str(e))


if proc.returncode != 0:
raise HTTPException(status_code=500, detail=f'CLI error: {proc.stderr or proc.stdout}')


# Parse CLI stdout for the two expected lines
parsed = None
spl = None
for line in proc.stdout.splitlines():
line = line.strip()
if line.startswith('Hybrid Parsed:'):
try:
parsed = ast.literal_eval(line.split('Hybrid Parsed:')[1].strip())
except Exception:
parsed = line.split('Hybrid Parsed:')[1].strip()
if line.startswith('Generated SPL:'):
spl = line.split('Generated SPL:')[1].strip()


return { 'parsed': parsed, 'spl': spl, 'stdout': proc.stdout, 'source': 'cli' }