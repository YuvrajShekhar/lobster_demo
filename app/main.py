import json

from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import ValidationError

from app.parser import ConversionResult, convert
from app.schema_models import ConversionSchema

app = FastAPI(
    title="flatfile2json",
    description="Converts fixed-width or delimited flat files into JSON, against a declared field schema.",
    version="0.1.0",
)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/convert", response_model=ConversionResult)
async def convert_file(file: UploadFile, schema_json: str = Form(..., alias="schema")) -> ConversionResult:
    try:
        parsed_schema = ConversionSchema.model_validate(json.loads(schema_json))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"schema is not valid JSON: {exc}") from None
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=json.loads(exc.json())) from None

    raw_bytes = await file.read()
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"file is not valid UTF-8: {exc}") from None

    return convert(text, parsed_schema)


@app.get("/", response_class=HTMLResponse)
async def demo_page() -> str:
    return DEMO_HTML


DEMO_HTML = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>flatfile2json</title>
<style>
  :root { color-scheme: dark; }
  body { font-family: ui-monospace, monospace; background: #0e1620; color: #e7edf3;
         max-width: 900px; margin: 40px auto; padding: 0 20px; }
  h1 { font-size: 18px; font-weight: 600; }
  p.sub { color: #8ea0b3; font-size: 13px; margin-top: -8px; }
  textarea { width: 100%; background: #16212c; color: #e7edf3; border: 1px solid #263444;
             border-radius: 6px; padding: 10px; font-family: inherit; font-size: 13px; }
  label { display: block; margin: 18px 0 6px; font-size: 13px; color: #8ea0b3; }
  button { margin-top: 16px; background: #4fa8e8; color: #0e1620; border: none;
           padding: 9px 16px; border-radius: 6px; font-weight: 600; cursor: pointer; font-family: inherit; }
  pre { background: #16212c; border: 1px solid #263444; border-radius: 6px; padding: 14px;
        white-space: pre-wrap; font-size: 12.5px; margin-top: 20px; }
</style>
</head>
<body>
  <h1>flatfile2json</h1>
  <p class="sub">Paste a flat file and a schema, convert to JSON. POST /convert for the API.</p>

  <label>Flat file contents (fixed-width example below)</label>
  <textarea id="file" rows="6">JOHN DOE  0420250115
JANE SMITH1520250116</textarea>

  <label>Schema (JSON)</label>
  <textarea id="schema" rows="10">{
  "format": "fixed_width",
  "fields": [
    {"name": "name", "type": "string", "start": 0, "length": 10},
    {"name": "quantity", "type": "integer", "start": 10, "length": 2},
    {"name": "order_date", "type": "date", "start": 12, "length": 8, "date_format": "%Y%m%d"}
  ]
}</textarea>

  <button onclick="run()">Convert</button>
  <pre id="output">Result will appear here.</pre>

<script>
async function run() {
  const fileText = document.getElementById('file').value;
  const schemaText = document.getElementById('schema').value;
  const output = document.getElementById('output');

  const form = new FormData();
  form.append('file', new Blob([fileText], { type: 'text/plain' }), 'input.txt');
  form.append('schema', schemaText);

  output.textContent = 'Converting...';
  try {
    const res = await fetch('/convert', { method: 'POST', body: form });
    const body = await res.json();
    output.textContent = JSON.stringify(body, null, 2);
  } catch (err) {
    output.textContent = 'Request failed: ' + err;
  }
}
</script>
</body>
</html>
"""
