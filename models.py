import os
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

AMD_API_BASE = os.getenv("AMD_API_BASE", "http://134.199.199.49:8000/v1")
AMD_API_KEY = os.getenv("AMD_API_KEY", "EMPTY")
DEFAULT_MODEL = "amd/Llama-3.1-70B-Instruct-FP8-KV"
MODEL = os.getenv("BOARDROOM_MODEL", os.getenv("AMD_MODEL", DEFAULT_MODEL))
DEFAULT_CONTINUATION_ROUNDS = int(os.getenv("BOARDROOM_CONTINUE_ROUNDS", "1"))

client = OpenAI(
    base_url=AMD_API_BASE,
    api_key=AMD_API_KEY,
    timeout=120.0,
)


def _is_punctuation_loop(text: str) -> bool:
    compact = re.sub(r"\s+", "", text or "")
    if not compact:
        return True
    return text.count("!") / len(compact) >= 0.8

def chat(
    system: str,
    user: str,
    max_tokens: int = 1024,
    temperature: float = 0.3,
    model: str | None = None,
    continuation_rounds: int | None = None,
) -> str:
    selected_model = model or MODEL
    rounds = DEFAULT_CONTINUATION_ROUNDS if continuation_rounds is None else max(0, continuation_rounds)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    parts = []

    for _ in range(rounds + 1):
        resp = client.chat.completions.create(
            model=selected_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = resp.choices[0].message.content or ""
        finish_reason = resp.choices[0].finish_reason
        if _is_punctuation_loop(content):
            if not parts:
                parts.append(content)
            break
        parts.append(content)
        if finish_reason != "length":
            break
        messages.append({"role": "assistant", "content": content})
        messages.append(
            {
                "role": "user",
                "content": "Continue from where you stopped. Do not repeat earlier points.",
            }
        )

    return "\n".join(part.strip() for part in parts if part.strip()).strip()
