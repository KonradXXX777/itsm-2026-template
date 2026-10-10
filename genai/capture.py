# ai-generated: 100% - Codex instrumented one genuine local Ollama completion with the course-pinned library.
"""Run from the repository root; exports real SDK spans, never handcrafted attributes."""
import os
from pathlib import Path

from openai import OpenAI
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.exporter.otlp.json.file.trace_exporter import FileSpanExporter
from opentelemetry.instrumentation.genai.openai import OpenAIInstrumentor


def main():
    provider = TracerProvider(resource=Resource.create({"service.name": "svcdesk-genai-evidence"}))
    provider.add_span_processor(SimpleSpanProcessor(FileSpanExporter(path=Path(__file__).with_name("spans.json"))))
    trace.set_tracer_provider(provider)
    OpenAIInstrumentor().instrument(tracer_provider=provider)
    # Content capture is not enabled: prompt/completion text can contain personal information.
    client = OpenAI(base_url=os.getenv("GENAI_BASE_URL", "http://localhost:11434/v1"),
                    api_key="ollama-local", max_retries=0, timeout=120)
    try:
        result = client.chat.completions.create(
            model=os.getenv("GENAI_MODEL", "qwen2.5:0.5b"),
            messages=[{"role": "user", "content": "In one sentence, explain what an error budget means for a service."}],
            temperature=0, max_tokens=64,
        )
        print(result.choices[0].message.content)
        print("Model:", result.model, "usage:", result.usage)
    finally:
        client.close()
        provider.force_flush()
        provider.shutdown()


if __name__ == "__main__":
    main()
