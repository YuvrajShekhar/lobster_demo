# flatfile2json

One endpoint: turn a fixed-width or delimited flat file into JSON, against a
declared schema. Built as a small, single-feature proof-of-concept for
Lobster's [Full Stack Software Engineer
(Angular/Python)](https://lobster-data-gmbh.jobs.personio.com/job/2782611)
role — the everyday first step of onboarding a trading partner onto an
integration platform, without the rest of a platform around it.

## Why this shape

- **One feature, end-to-end.** No database, no worker, no queue — just a
  schema, a parser, and an endpoint. Easy to explain in five minutes and
  easy to extend.
- **Partial success, not all-or-nothing.** A real partner feed usually has a
  handful of malformed rows in an otherwise clean batch. `/convert` returns
  every row it could parse plus a list of `{line_number, message}` for the
  ones it couldn't, rather than failing the whole file on one bad line
  (`app/parser.py::convert`).
- **The schema is data, not code.** Field name, type, and position are
  declared as JSON (`app/schema_models.py`) — the same field spec you'd hand
  a partner as "here's how to format your file," and validated up front with
  Pydantic before any row is touched.

## Try it

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://localhost:8000 for a minimal in-browser demo, or call it directly:

```bash
curl -X POST http://localhost:8000/convert \
  -F 'schema={"format":"delimited","fields":[{"name":"sku","type":"string","column":0},{"name":"quantity","type":"integer","column":1}]}' \
  -F 'file=@orders.csv'
```

```json
{
  "records": [{"sku": "ABC-123", "quantity": 4}],
  "errors": []
}
```

Fixed-width works the same way, with `start`/`length` instead of `column` —
see the demo page for a worked example.

## Tests & type checking

```bash
python -m pytest -q     # 11 tests
python -m mypy app      # strict, zero errors
```

## Docker

```bash
docker build -t flatfile2json .
docker run -p 8000:8000 flatfile2json
```

Stateless single container — no Postgres, no other services, so it's a
one-service Railway deploy.

## Deliberately out of scope

No auth, no persistence of past conversions, no streaming for very large
files (loads the whole file into memory) — all reasonable for a real product,
all unnecessary for demonstrating the parsing logic itself.
