from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Union
import jsonschema
from fastapi.responses import RedirectResponse
import json

app = FastAPI(title="Onboard Validator (local)")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en pruebas, luego puedes restringir
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ValidateRequest(BaseModel):
    payload: Union[Dict[str, Any], str]
    expected_schema: Optional[Union[Dict[str, Any], str]] = None
    test_endpoint: Optional[str] = None
    auth: Optional[Dict[str, Any]] = None


@app.get('/', include_in_schema=False)
async def docs():
    return RedirectResponse('/docs')


@app.post("/validate")
async def validate(req: ValidateRequest):
    # Normalizar payload y schema en caso de que lleguen como string
    payload = req.payload
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            return {"ok": False, "error": "Payload is not valid JSON", "raw": req.payload}

    schema = req.expected_schema
    if isinstance(schema, str):
        try:
            schema = json.loads(schema)
        except Exception:
            return {"ok": False, "error": "Schema is not valid JSON", "raw": req.expected_schema}

    # Logs
    print("=== Nuevo request recibido ===")
    print("Payload:")
    print(payload)
    print("Expected schema:")
    print(schema)
    print("==============================")

    schema_errors: List[Dict[str, Any]] = []
    schema_ok = True

    # Validación contra JSON Schema
    if schema:
        try:
            jsonschema.validate(instance=payload, schema=schema)
        except jsonschema.ValidationError as e:
            schema_ok = False
            # Convertimos el path (lista) a una cadena legible tipo "items[1].qty"
            field_path = ".".join(str(p) for p in e.path)
            schema_errors.append({
                "field": field_path if field_path else "(root)",
                "issue": e.message
            })
            print(f"⚠️ Schema error: {schema_errors}")

    # 🔴 Ya no se hace test de conexión
    connection_test = {"tested": False, "ok": None, "details": "Skipped"}

    # Sugerencias
    suggestions = []
    if not schema_ok:
        for err in schema_errors:
            suggestions.append(f"Corrige el campo '{err['field']}': {err['issue']}")
    else:
        suggestions.append("El payload cumple con el schema (si se proporcionó).")

    # Resumen en lenguaje natural
    summary = (
        "El payload cumple con el esquema sin errores."
        if schema_ok else
        f"El payload tiene {len(schema_errors)} error(es) en los campos: "
        + ", ".join(err["field"] for err in schema_errors)
    )

    result = {
        "ok": schema_ok,
        "schema_errors": schema_errors,  # limpio y legible
        "connection_test": connection_test,
        "suggestions": suggestions,
        "patches": [],  # opcional: podrías generar parches automáticos
        "summary": summary,
    
        # 🔑 Fix: devolver también payload y role
        "payload": payload,
        "role": payload.get("role") if isinstance(payload, dict) else None
    }
    return result
