---
lab3_genai_diff:
  instrumentation: "opentelemetry-instrumentation-genai-openai 1.2b0; opentelemetry-sdk 1.45.0; openai 3.19.2; opentelemetry-exporter-otlp-json-file 0.66b0"
  spec_ref: semantic-conventions@v1.41.1
  attributes:
    - {name: gen_ai.operation.name, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.provider.name, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.request.model, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.request.temperature, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.request.max_tokens, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.response.finish_reasons, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.response.model, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.response.id, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.usage.input_tokens, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.usage.output_tokens, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.request.top_p, emitted: false, in_spec: true, stability: development}
    - {name: gen_ai.response.time_to_first_chunk, emitted: false, in_spec: true, stability: development}
    - {name: gen_ai.input.messages, emitted: false, in_spec: true, stability: development}
    - {name: gen_ai.output.messages, emitted: false, in_spec: true, stability: development}
---
<!-- ai-generated: 100% - Codex executed a genuine local completion and compared its raw exported keys with the pinned registry. -->

# Actual emitted telemetry, not a fabricated trace

On 2026-10-10, `capture.py` called Ollama's OpenAI-compatible
`http://localhost:11434/v1` endpoint, model `qwen2.5:0.5b`, with a short
error-budget question, temperature 0 and max_tokens 64. The response completed
with finish reason `stop`, 43 input and 26 output tokens. `spans.json` is the
unmodified OTLP JSON produced by `FileSpanExporter`; trace
`ff507e5dd6ab670c7681b95bd95f923e` identifies this one actual invocation.
No API key for a paid provider was used. The local placeholder key is not a secret.

All ten emitted `gen_ai.*` keys occur in the pinned
[v1.41.1 registry](https://github.com/open-telemetry/semantic-conventions/blob/v1.41.1/model/gen-ai/registry.yaml)
and have `development` stability. This is agreement of names and stability,
not a claim that every convention is stable or every optional field is required.
The span advertises schema URL 1.37.0; the comparison deliberately uses the
course-supported 1.41.1 snapshot, not a moving `main` branch.

`gen_ai.provider.name=openai` describes the instrumentation's API/provider
flavour, not proof that OpenAI hosted this request. `server.address=localhost`,
port 11434 and both model names identify the local execution. The registry
allows the client-observed provider to differ from the actual model supplier.
This distinction matters for routing and cost attribution dashboards.

There is a type nuance beyond the checker's name/stability comparison:
temperature 0 was exported as OTLP `intValue`, while the registry describes
temperature as a double. A downstream typed pipeline should normalize numeric
values rather than infer a schema from this one integer-valued request.
Token counts and max_tokens are correctly integer-valued; finish reasons form
an array, not a single string.

The four `emitted: false` examples are genuinely absent. top_p was not set;
time-to-first-chunk does not apply to this non-streaming call. Content capture
was not enabled, so input/output messages are intentionally absent to limit
privacy exposure. `openai.response.system_fingerprint`, `server.*` and SDK
resource attributes exist too, but are outside the requested `gen_ai.*` diff.
Response IDs belong in traces, never as Prometheus labels.

The small model's answer confused an SRE error budget with financial costs.
A successful trace proves that a call occurred and records operational cost;
it does not prove answer quality. This evidence is independent of `/kb/search`
and introduces no model dependency into the service's runtime or Docker build.

## Reproduce

Start local Ollama, pull `qwen2.5:0.5b`, then from the repository root:

```sh
uv venv .venv-genai --python 3.13
uv pip install --python .venv-genai/bin/python -r genai/requirements.txt
.venv-genai/bin/python genai/capture.py
```

The exporter appends batches; preserve the submitted evidence, or move the old
file aside before making another capture. Review the new keys before changing
the diff. Custom endpoints/models can be selected with `GENAI_BASE_URL` and
`GENAI_MODEL`; they still must make a real model call.
