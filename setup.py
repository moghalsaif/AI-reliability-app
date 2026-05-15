from setuptools import setup, find_packages

setup(
    name="ai-reliability-lab",
    version="0.1.0",
    description="AI Reliability Lab - Infrastructure for agent reliability engineering",
    python_requires=">=3.10",
    packages=find_packages(where="packages/shared/src") + 
             find_packages(where="packages/sdk/src") +
             find_packages(where="packages/evals/src") +
             find_packages(where="packages/reliability/src") +
             find_packages(where="packages/tracing/src") +
             find_packages(where="packages/prompts/src") +
             find_packages(where="apps/api/src") +
             find_packages(where="apps/worker/src") +
             find_packages(where="apps/evaluator/src"),
    package_dir={
        "": "packages/shared/src",
        "reliability_sdk": "packages/sdk/src/reliability_sdk",
        "reliability_evals": "packages/evals/src/reliability_evals",
        "reliability_engine": "packages/reliability/src/reliability_engine",
        "reliability_tracing": "packages/tracing/src/reliability_tracing",
        "reliability_prompts": "packages/prompts/src/reliability_prompts",
        "reliability_api": "apps/api/src/reliability_api",
        "reliability_worker": "apps/worker/src/reliability_worker",
        "reliability_evaluator": "apps/evaluator/src/reliability_evaluator",
    },
    install_requires=[
        "requests>=2.31.0",
        "numpy>=1.24.0",
    ],
    extras_require={
        "api": [
            "fastapi>=0.104.0",
            "uvicorn[standard]>=0.24.0",
            "pydantic>=2.0.0",
            "redis>=5.0.0",
            "clickhouse-connect>=0.7.0",
            "celery>=5.3.0",
        ],
        "evals": [
            "sentence-transformers>=2.2.0",
        ],
        "otel": [
            "opentelemetry-api>=1.20.0",
            "opentelemetry-sdk>=1.20.0",
            "opentelemetry-exporter-otlp>=1.20.0",
        ],
        "dev": [
            "pytest>=7.0",
            "pytest-asyncio>=0.21",
            "httpx>=0.25.0",
            "black>=23.0",
            "mypy>=1.0",
        ],
    },
)
