"""Lightweight deterministic response-quality checks."""
class ResponseEvaluator:
    """Reject clearly malformed responses before persistence/stream completion."""

    @staticmethod
    def validate(response: str) -> str:
        clean = response.strip()
        if not clean:
            raise ValueError("Model returned an empty response.")
        if len(clean) < 8:
            raise ValueError("Model response is implausibly short.")
        return clean
