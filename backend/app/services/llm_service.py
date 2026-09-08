import json

import anthropic

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


class LLMService:
    """Wraps structured-extraction calls to the LLM behind tool-use/JSON-schema enforcement."""

    def __init__(self):
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def extract_document_fields(self, text: str) -> dict:
        """Classify a PDF's text and extract type-specific structured fields."""
        message = self._client.messages.create(
            model=settings.llm_model,
            max_tokens=4096,
            tools=[_EXTRACT_TOOL],
            tool_choice={"type": "tool", "name": "record_extraction"},
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Classify the following document and extract its structured fields "
                        "using the record_extraction tool. Only use information present in "
                        "the text; use null for anything you can't find.\n\n---\n\n" + text
                    ),
                }
            ],
        )
        return self._tool_input(message, "record_extraction")

    def map_csv_columns(self, columns: list[str], sample_rows: list[dict]) -> dict:
        """Semantically map a table's columns to the canonical invoice/transaction schema."""
        message = self._client.messages.create(
            model=settings.llm_model,
            max_tokens=1024,
            tools=[_MAP_COLUMNS_TOOL],
            tool_choice={"type": "tool", "name": "record_column_mapping"},
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Map these table columns to the canonical field names using the "
                        "record_column_mapping tool.\n\n"
                        f"Columns: {json.dumps(columns)}\n\n"
                        f"Sample rows: {json.dumps(sample_rows, default=str)}"
                    ),
                }
            ],
        )
        result = self._tool_input(message, "record_column_mapping")
        return result.get("mapping", {})

    @staticmethod
    def _tool_input(message: anthropic.types.Message, tool_name: str) -> dict:
        for block in message.content:
            if block.type == "tool_use" and block.name == tool_name:
                return block.input
        raise ValueError(f"LLM response did not include the expected '{tool_name}' tool call")
