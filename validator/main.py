from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import jsonschema
import json
from fastapi.responses import JSONResponse, RedirectResponse

app = FastAPI(title="Onboard Validator (local)")

class ValidateRequest(BaseModel):
    payload: Dict[str, Any]
    expected_schema: Optional[Dict[str,Any]] = None
    test_endpoint: Optional[str] = None
    auth: Optional[Dict[str,Any]] = None

@app.get('/', include_in_schema = False)
async def docs():
    return RedirectResponse('/docs')

@app.post("/validate")
async def validate(req: ValidateRequest):
    payload = req.payload
    schema = req.expected_schema
    schema_errors: List[Dict[str,Any]] = []
    schema_ok = True

    # JSON Schema validation (if provided)
    if schema:
        try:
            jsonschema.validate(instance=payload, schema=schema)
        except jsonschema.ValidationError as e:
            schema_ok = False
            schema_errors.append({
                "message": str(e.message),
                "path": list(e.path),
                "validator": e.validator,
                "validator_value": e.validator_value
            })

    # Simple connection test stub (no external requests by default)
    connection_test = {"tested": False, "ok": None, "details": "No endpoint provided."}
    if req.test_endpoint:
        # Basic HEAD request (no external libs other than requests)
        try:
            import requests
            headers = {}
            if req.auth:
                # support basic token auth
                if req.auth.get("type") == "bearer" and req.auth.get("token"):
                    headers["Authorization"] = f"Bearer {req.auth.get('token')}"
            r = requests.head(req.test_endpoint, headers=headers, timeout=5)
            connection_test = {"tested": True, "ok": r.status_code < 400, "status_code": r.status_code}
        except Exception as e:
            connection_test = {"tested": True, "ok": False, "details": str(e)}

    # Generate small suggestions (very basic)
    suggestions = []
    if not schema_ok:
        suggestions.append("Revisa los campos indicados en schema_errors; añade los campos faltantes o corrige tipos.")
    else:
        suggestions.append("El payload cumple con el schema (si se proporcionó).")

    # Very small "fix" suggestion example (patch)
    patches = []
    if schema_errors:
        patches.append({"op":"add","path":"/missing_example","value":"example_value"})

    result = {
        "ok": schema_ok and (connection_test.get("ok") in (True, None)),
        "schema_errors": schema_errors,
        "connection_test": connection_test,
        "suggestions": suggestions,
        "patches": patches,
        "summary": "Validation completed locally."
    }
    return result
