import json

import anthropic
import httpx

from app.core.config import settings

CANONICAL_INVOICE_FIELDS = [
    "vendor_name",
    "invoice_number",
    "invoice_date",
    "due_date",
    "total_amount",
    "currency",
    "payment_terms_days",
]

_EXTRACT_TOOL = {
    "name": "record_extraction",
    "description": "Record the structured data extracted from a document.",
    "input_schema": {
        "type": "object",
        "properties": {
            "document_type": {
                "type": "string",
                "enum": ["invoice", "contract", "unknown"],
                "description": "Best guess at what kind of document this is.",
            },
            "invoice": {
                "type": "object",
                "description": "Populate when document_type is 'invoice'. Leave fields null if not present in the text.",
                "properties": {
                    "vendor_name": {"type": ["string", "null"]},
                    "invoice_number": {"type": ["string", "null"]},
                    "invoice_date": {"type": ["string", "null"], "description": "ISO 8601 date, YYYY-MM-DD"},
                    "due_date": {"type": ["string", "null"], "description": "ISO 8601 date, YYYY-MM-DD"},
                    "total_amount": {"type": ["number", "null"]},
                    "currency": {"type": ["string", "null"], "description": "ISO 4217 code, e.g. USD, EUR, GBP"},
                    "payment_terms_days": {"type": ["integer", "null"], "description": "e.g. 30 for 'Net 30'"},
                    "line_items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "description": {"type": "string"},
                                "quantity": {"type": ["number", "null"]},
                                "unit_price": {"type": ["number", "null"]},
                                "amount": {"type": ["number", "null"]},
                            },
                            "required": ["description"],
                        },
                    },
                },
            },
            "contract": {
                "type": "object",
                "description": "Populate when document_type is 'contract'.",
                "properties": {
                    "parties": {"type": "array", "items": {"type": "string"}},
                    "effective_date": {"type": ["string", "null"], "description": "ISO 8601 date, YYYY-MM-DD"},
                    "termination_date": {"type": ["string", "null"], "description": "ISO 8601 date, YYYY-MM-DD"},
                    "governing_law": {"type": ["string", "null"]},
                    "key_terms": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "required": ["document_type"],
    },
}

_MAP_COLUMNS_TOOL = {
    "name": "record_column_mapping",
    "description": "Map this table's column headers onto the canonical field names, using the sample rows to judge meaning.",
    "input_schema": {
        "type": "object",
        "properties": {
            "mapping": {
                "type": "object",
                "description": "Canonical field name -> source column name. Omit a field if no column matches it.",
                "properties": {field: {"type": "string"} for field in CANONICAL_INVOICE_FIELDS},
            }
        },
        "required": ["mapping"],
    },
}

# Ollama's structured-output `format` uses plain JSON Schema (no tool-call
# envelope), and its constrained decoding doesn't need the ["string", "null"]
# unions above - optional fields simply aren't in "required" and can be
# omitted, so these are separate, simpler schemas rather than a translation
# of the Anthropic tool schemas.
_OLLAMA_EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "document_type": {"type": "string", "enum": ["invoice", "contract", "unknown"]},
        "invoice": {
            "type": "object",
            "properties": {
                "vendor_name": {"type": "string"},
                "invoice_number": {"type": "string"},
                "invoice_date": {"type": "string", "description": "ISO 8601 date, YYYY-MM-DD"},
                "due_date": {"type": "string", "description": "ISO 8601 date, YYYY-MM-DD"},
                "total_amount": {"type": "number"},
                "currency": {"type": "string", "description": "ISO 4217 code, e.g. USD, EUR, GBP"},
                "payment_terms_days": {"type": "integer", "description": "e.g. 30 for 'Net 30'"},
                "line_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string"},
                            "quantity": {"type": "number"},
                            "unit_price": {"type": "number"},
                            "amount": {"type": "number"},
                        },
                        "required": ["description"],
                    },
                },
            },
        },
        "contract": {
            "type": "object",
            "properties": {
                "parties": {"type": "array", "items": {"type": "string"}},
                "effective_date": {"type": "string", "description": "ISO 8601 date, YYYY-MM-DD"},
                "termination_date": {"type": "string", "description": "ISO 8601 date, YYYY-MM-DD"},
                "governing_law": {"type": "string"},
                "key_terms": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
    "required": ["document_type"],
}

_OLLAMA_MAP_COLUMNS_SCHEMA = {
    "type": "object",
    "properties": {
        "mapping": {
            "type": "object",
            "properties": {field: {"type": "string"} for field in CANONICAL_INVOICE_FIELDS},
        }
    },
    "required": ["mapping"],
}


class LLMTransientError(Exception):
    """Retryable failure talking to the LLM backend (network, rate limit, 5xx)."""


_GENERATE_SQL_TOOL = {
    "name": "record_sql",
    "description": "Record the read-only SQL SELECT statement that answers the question.",
    "input_schema": {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "A single PostgreSQL SELECT statement. No trailing semicolon, no other statement types.",
            },
        },
        "required": ["sql"],
    },
}

_OLLAMA_SQL_SCHEMA = {
    "type": "object",
    "properties": {"sql": {"type": "string"}},
    "required": ["sql"],
}


def _rag_prompt(question: str, context: str) -> str:
    return (
        "Answer the question using only the context below. If the context doesn't "
        "contain the answer, say you don't know - don't make anything up.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}"
    )


def _sql_prompt(question: str, schema_description: str) -> str:
    return (
        "Write a single read-only PostgreSQL SELECT statement that answers the "
        "question, using only the tables and columns described below. Never use "
        "INSERT, UPDATE, DELETE, or any statement other than SELECT. No trailing "
        "semicolon, no commentary - just the query.\n\n"
        f"{schema_description}\n\nQuestion: {question}"
    )


def _explain_prompt(question: str, sql: str, rows: list[dict]) -> str:
    return (
        "A user asked a question about their data, and this SQL query was run "
        "against the database to answer it. Explain the result in plain language, "
        "directly answering the question. Don't mention SQL or the query itself.\n\n"
        f"Question: {question}\n\nQuery: {sql}\n\nResult rows (JSON): {json.dumps(rows, default=str)}"
    )


_ROUTE_VALUES = ["rag", "sql", "both"]

_ROUTE_TOOL = {
    "name": "record_route",
    "description": "Record which system(s) should answer the question.",
    "input_schema": {
        "type": "object",
        "properties": {
            "route": {
                "type": "string",
                "enum": _ROUTE_VALUES,
                "description": (
                    "'rag' for questions about the content/meaning of specific documents "
                    "(what does the contract say, who is the vendor). 'sql' for questions "
                    "needing aggregation/counting/math over many records (total, average, "
                    "how many, by month/vendor/currency). 'both' only when the question "
                    "genuinely needs a number AND an explanation grounded in document text "
                    "(why did X happen, what's driving Y)."
                ),
            },
        },
        "required": ["route"],
    },
}

_OLLAMA_ROUTE_SCHEMA = {
    "type": "object",
    "properties": {"route": {"type": "string", "enum": _ROUTE_VALUES}},
    "required": ["route"],
}


def _route_prompt(question: str) -> str:
    return f"Decide how to answer this question: {question}"


def _explain_anomalies_prompt(currency: str, anomalies: list[dict]) -> str:
    lines = "\n".join(
        f'{i}. vendor "{row["vendor_name"]}", ratio {round(row["ratio"], 1)}' for i, row in enumerate(anomalies, start=1)
    )
    return (
        "These invoices were flagged as statistical outliers against their own "
        f"vendor's historical average, in {currency}. Below is the exact "
        f"vendor name and ratio (invoice amount / vendor's own average) for "
        f"each of the {len(anomalies)} anomaly/anomalies found. Write exactly "
        f"{len(anomalies)} line(s), one per numbered item below, each stating "
        "the vendor name and its ratio as '<ratio>x' - use the ratio given, do "
        "not compute or guess a different number. Output only those lines, "
        "nothing else (no preamble, no notes).\n\n"
        f"{lines}"
    )


def _synthesize_prompt(question: str, rag_answer: str, sql_explanation: str) -> str:
    return (
        "Answer the question by combining two findings below into one coherent "
        "answer - a semantic-search result over document text, and a SQL query "
        "result over structured records. Don't mention 'semantic search' or 'SQL' "
        "or refer to them as separate sources; just answer naturally, using "
        "whichever parts of each are relevant.\n\n"
        f"Question: {question}\n\n"
        f"Document search finding: {rag_answer}\n\n"
        f"Data query finding: {sql_explanation}"
    )


class _AnthropicBackend:
    def __init__(self):
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def extract_document_fields(self, text: str) -> dict:
        message = self._create(
            tools=[_EXTRACT_TOOL],
            tool_choice={"type": "tool", "name": "record_extraction"},
            content=(
                "Classify the following document and extract its structured fields "
                "using the record_extraction tool. Only use information present in "
                "the text; use null for anything you can't find.\n\n---\n\n" + text
            ),
        )
        return self._tool_input(message, "record_extraction")

    def map_csv_columns(self, columns: list[str], sample_rows: list[dict]) -> dict:
        message = self._create(
            tools=[_MAP_COLUMNS_TOOL],
            tool_choice={"type": "tool", "name": "record_column_mapping"},
            content=(
                "Map these table columns to the canonical field names using the "
                "record_column_mapping tool.\n\n"
                f"Columns: {json.dumps(columns)}\n\n"
                f"Sample rows: {json.dumps(sample_rows, default=str)}"
            ),
        )
        result = self._tool_input(message, "record_column_mapping")
        return result.get("mapping", {})

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError(
            "Anthropic has no embeddings API. Leave EMBEDDING_PROVIDER=ollama (the default), "
            "or point it at a provider that offers one."
        )

    def answer_question(self, question: str, context: str) -> str:
        return self._generate_text(_rag_prompt(question, context))

    def generate_sql(self, question: str, schema_description: str) -> str:
        message = self._create(
            tools=[_GENERATE_SQL_TOOL],
            tool_choice={"type": "tool", "name": "record_sql"},
            content=_sql_prompt(question, schema_description),
        )
        return self._tool_input(message, "record_sql")["sql"]

    def explain_query_results(self, question: str, sql: str, rows: list[dict]) -> str:
        return self._generate_text(_explain_prompt(question, sql, rows))

    def classify_route(self, question: str) -> str:
        message = self._create(
            tools=[_ROUTE_TOOL],
            tool_choice={"type": "tool", "name": "record_route"},
            content=_route_prompt(question),
        )
        return self._tool_input(message, "record_route")["route"]

    def synthesize_answer(self, question: str, rag_answer: str, sql_explanation: str) -> str:
        return self._generate_text(_synthesize_prompt(question, rag_answer, sql_explanation))

    def explain_anomalies(self, currency: str, anomalies: list[dict]) -> str:
        return self._generate_text(_explain_anomalies_prompt(currency, anomalies))

    def _generate_text(self, prompt: str) -> str:
        try:
            message = self._client.messages.create(
                model=settings.llm_model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
        except (anthropic.APIConnectionError, anthropic.RateLimitError, anthropic.InternalServerError) as exc:
            raise LLMTransientError(str(exc)) from exc
        return "".join(block.text for block in message.content if block.type == "text").strip()

    def _create(self, *, tools, tool_choice, content):
        try:
            return self._client.messages.create(
                model=settings.llm_model,
                max_tokens=4096,
                tools=tools,
                tool_choice=tool_choice,
                messages=[{"role": "user", "content": content}],
            )
        except (anthropic.APIConnectionError, anthropic.RateLimitError, anthropic.InternalServerError) as exc:
            raise LLMTransientError(str(exc)) from exc

    @staticmethod
    def _tool_input(message: anthropic.types.Message, tool_name: str) -> dict:
        for block in message.content:
            if block.type == "tool_use" and block.name == tool_name:
                return block.input
        raise ValueError(f"LLM response did not include the expected '{tool_name}' tool call")


class _OllamaBackend:
    def __init__(self):
        self._client = httpx.Client(base_url=settings.ollama_base_url, timeout=120.0)

    def extract_document_fields(self, text: str) -> dict:
        return self._chat_json(
            "Classify the following document and extract its structured fields as JSON "
            "matching the schema. Only use information present in the text; omit fields "
            "you can't find.\n\n---\n\n" + text,
            _OLLAMA_EXTRACT_SCHEMA,
        )

    def map_csv_columns(self, columns: list[str], sample_rows: list[dict]) -> dict:
        result = self._chat_json(
            "Map these table columns to the canonical field names as JSON matching the schema.\n\n"
            f"Columns: {json.dumps(columns)}\n\n"
            f"Sample rows: {json.dumps(sample_rows, default=str)}",
            _OLLAMA_MAP_COLUMNS_SCHEMA,
        )
        return result.get("mapping", {})

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self._post("/api/embed", {"model": settings.ollama_embed_model, "input": texts})
        return response["embeddings"]

    def answer_question(self, question: str, context: str) -> str:
        return self._chat_text(_rag_prompt(question, context))

    def generate_sql(self, question: str, schema_description: str) -> str:
        result = self._chat_json(_sql_prompt(question, schema_description), _OLLAMA_SQL_SCHEMA)
        return result["sql"]

    def explain_query_results(self, question: str, sql: str, rows: list[dict]) -> str:
        return self._chat_text(_explain_prompt(question, sql, rows))

    def classify_route(self, question: str) -> str:
        result = self._chat_json(_route_prompt(question), _OLLAMA_ROUTE_SCHEMA)
        return result["route"]

    def synthesize_answer(self, question: str, rag_answer: str, sql_explanation: str) -> str:
        return self._chat_text(_synthesize_prompt(question, rag_answer, sql_explanation))

    def explain_anomalies(self, currency: str, anomalies: list[dict]) -> str:
        return self._chat_text(_explain_anomalies_prompt(currency, anomalies))

    def _chat_text(self, prompt: str) -> str:
        response = self._post(
            "/api/chat",
            {
                "model": settings.ollama_chat_model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
        )
        return response["message"]["content"].strip()

    def _chat_json(self, prompt: str, schema: dict) -> dict:
        response = self._post(
            "/api/chat",
            {
                "model": settings.ollama_chat_model,
                "messages": [{"role": "user", "content": prompt}],
                "format": schema,
                "stream": False,
            },
        )
        content = response["message"]["content"].strip()
        if content.startswith("```"):
            # Some models (esp. cloud-hosted ones) wrap output in a markdown
            # fence even when a JSON `format` schema was requested.
            content = content.strip("`").removeprefix("json").strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Ollama returned non-JSON content: {content[:200]!r}") from exc

    def _post(self, path: str, body: dict) -> dict:
        try:
            response = self._client.post(path, json=body)
            response.raise_for_status()
        except httpx.ConnectError as exc:
            raise LLMTransientError(f"Could not reach Ollama at {settings.ollama_base_url}") from exc
        except httpx.TimeoutException as exc:
            raise LLMTransientError("Ollama request timed out") from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code >= 500:
                raise LLMTransientError(f"Ollama server error: {exc.response.status_code}") from exc
            raise ValueError(f"Ollama request failed: {exc.response.status_code} {exc.response.text}") from exc
        return response.json()


def _make_backend(provider: str):
    if provider == "ollama":
        return _OllamaBackend()
    if provider == "anthropic":
        return _AnthropicBackend()
    raise ValueError(f"Unknown LLM provider: {provider!r}")


class LLMService:
    """Wraps extraction/embedding calls behind a provider backend (anthropic or ollama).

    Chat (extraction, column mapping) and embeddings are configured separately
    via llm_provider / embedding_provider, since Anthropic has no embeddings API.
    """

    def __init__(self):
        self._chat_backend = _make_backend(settings.llm_provider)
        self._embed_backend = (
            self._chat_backend if settings.embedding_provider == settings.llm_provider else _make_backend(settings.embedding_provider)
        )

    def extract_document_fields(self, text: str) -> dict:
        """Classify a PDF's text and extract type-specific structured fields."""
        return self._chat_backend.extract_document_fields(text)

    def map_csv_columns(self, columns: list[str], sample_rows: list[dict]) -> dict:
        """Semantically map a table's columns to the canonical invoice/transaction schema."""
        return self._chat_backend.map_csv_columns(columns, sample_rows)

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of text chunks for pgvector storage/search."""
        return self._embed_backend.embed(texts)

    def answer_question(self, question: str, context: str) -> str:
        """Answer a question grounded in pre-retrieved context chunks (RAG)."""
        return self._chat_backend.answer_question(question, context)

    def generate_sql(self, question: str, schema_description: str) -> str:
        """Generate a single read-only SELECT statement answering the question."""
        return self._chat_backend.generate_sql(question, schema_description)

    def explain_query_results(self, question: str, sql: str, rows: list[dict]) -> str:
        """Turn SQL query results into a plain-language answer."""
        return self._chat_backend.explain_query_results(question, sql, rows)

    def classify_route(self, question: str) -> str:
        """Decide whether a question needs RAG, SQL, or both. Always one of
        _ROUTE_VALUES - falls back to the safest ('both') if the model
        returns something outside the enum despite the schema constraint.
        """
        route = self._chat_backend.classify_route(question)
        return route if route in _ROUTE_VALUES else "both"

    def synthesize_answer(self, question: str, rag_answer: str, sql_explanation: str) -> str:
        """Combine a RAG answer and a SQL explanation into one coherent answer."""
        return self._chat_backend.synthesize_answer(question, rag_answer, sql_explanation)

    def explain_anomalies(self, currency: str, anomalies: list[dict]) -> str:
        """Phrase a batch of already-computed vendor-baseline anomalies in plain language."""
        return self._chat_backend.explain_anomalies(currency, anomalies)
