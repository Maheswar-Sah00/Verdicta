import os
import re
from models import chat

DOCUMENT_PROMPT = """Here is the document you must analyse:

{document}

---
{instruction}

Always cite specific parts of the document using [§p.X] notation where X is the approximate page or section number.
"""

ANALYST = """You are the Analyst. Extract and summarize the key facts, figures, dates,
named parties, assumptions, and critical claims from the document.
Be neutral and precise. Structure your answer with clear numbered sections."""

SKEPTIC = """You are the Skeptic. Challenge the document rigorously.
Find contradictions, weak assumptions, missing evidence, implementation risks,
and model/market realism gaps. Provide a deep critique with concrete evidence.
Use numbered points and cite document sections."""

STRATEGIST = """You are the Strategist. Produce practical recommendations that respond
to both opportunities and risks in the document. Each recommendation must include:
1) action, 2) rationale from the document, and 3) implementation caution."""

AUDITOR = """You are the Auditor. You will receive the outputs of the Analyst, Skeptic,
and Strategist (including rebuttals). Your job is to:
1. Identify claims not supported by the document
2. Resolve the most important disagreements with evidence
3. Produce a final verdict with:
   - Consensus findings
   - Open risks and uncertainties
   - Recommended decision
Mark any unverified claims with [UNVERIFIED]."""


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    parsed = int(value)
    return max(minimum, min(parsed, maximum))


SPECIALIST_MAX_TOKENS = _env_int("BOARDROOM_SPECIALIST_MAX_TOKENS", 900, 256, 2400)
SPECIALIST_RETRY_MAX_TOKENS = _env_int("BOARDROOM_SPECIALIST_RETRY_MAX_TOKENS", 700, 192, 1800)
DEBATE_MAX_TOKENS = _env_int("BOARDROOM_DEBATE_MAX_TOKENS", 700, 192, 1800)
AUDITOR_MAX_TOKENS = _env_int("BOARDROOM_AUDITOR_MAX_TOKENS", 1200, 320, 2600)
AUDITOR_RETRY_MAX_TOKENS = _env_int("BOARDROOM_AUDITOR_RETRY_MAX_TOKENS", 900, 256, 2000)


def _is_punctuation_loop(text: str) -> bool:
    compact = re.sub(r"\s+", "", text or "")
    if not compact:
        return True
    exclamation_ratio = text.count("!") / len(compact)
    if re.search(r"!{30,}", text):
        return True
    return exclamation_ratio >= 0.3 and text.count("!") >= 80


def _sanitize_output(text: str) -> str:
    text = re.sub(r"!{30,}\s*$", "", text or "").rstrip()
    return text


def _trim(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...[trimmed]..."


def _compact_document_for_retry(document: str, max_chars: int = 2000) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", document)
    compact = []
    seen = set()
    total = 0
    for sentence in sentences:
        clean = sentence.strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        if total + len(clean) + 1 > max_chars:
            break
        compact.append(clean)
        total += len(clean) + 1
    result = " ".join(compact).strip()
    if result:
        return result
    return _trim(document, max_chars)


def _run_specialist_with_retry(system_prompt: str, instruction: str, document: str) -> str:
    primary_prompt = DOCUMENT_PROMPT.format(document=document, instruction=instruction)
    response = _sanitize_output(chat(system_prompt, primary_prompt, max_tokens=SPECIALIST_MAX_TOKENS))
    if not _is_punctuation_loop(response):
        return response

    for max_chars in (1000, 700, 500):
        compact_doc = _compact_document_for_retry(document, max_chars=max_chars)
        retry_prompt = (
            "Document excerpt:\n\n"
            f"{compact_doc}\n\n"
            "Task:\n"
            f"{instruction}\n\n"
            "Use concise plain text, no repeated punctuation."
        )
        response = _sanitize_output(chat(
            system_prompt,
            retry_prompt,
            max_tokens=SPECIALIST_RETRY_MAX_TOKENS,
            temperature=0.0,
            continuation_rounds=0,
        ))
        if not _is_punctuation_loop(response):
            return response
    return _sanitize_output(response)


def run_analyst(document: str) -> str:
    return _run_specialist_with_retry(
        ANALYST,
        "Analyse this document and extract all key facts, assumptions, and evidence.",
        document,
    )


def run_skeptic(document: str) -> str:
    return _run_specialist_with_retry(
        SKEPTIC,
        "Challenge this document deeply. Provide at least 8 weaknesses/risks with evidence citations.",
        document,
    )


def run_strategist(document: str) -> str:
    return _run_specialist_with_retry(
        STRATEGIST,
        "Based on this document, provide 5 strategic recommendations with rationale and implementation cautions.",
        document,
    )


def run_skeptic_rebuttal(document: str, analyst: str, strategist: str) -> str:
    rebuttal_prompt = f"""Document:
{_trim(document, 5000)}

Analyst output:
{_trim(analyst, 1400)}

Strategist output:
{_trim(strategist, 1400)}

Challenge the analyst and strategist reasoning:
1. Which claims are weakly supported?
2. Which recommendations ignore major risks?
3. What evidence gaps must be resolved before action?
Use a numbered list with citations."""
    rebuttal = _sanitize_output(chat(SKEPTIC, rebuttal_prompt, max_tokens=DEBATE_MAX_TOKENS, temperature=0.1))
    if not _is_punctuation_loop(rebuttal):
        return rebuttal

    retry_prompt = f"""Document excerpt:
{_compact_document_for_retry(document, max_chars=900)}

Analyst summary:
{_trim(analyst, 700)}

Strategist summary:
{_trim(strategist, 700)}

List the top 5 unresolved risks and evidence gaps. Keep it concise."""
    return _sanitize_output(chat(
        SKEPTIC,
        retry_prompt,
        max_tokens=500,
        temperature=0.0,
        continuation_rounds=0,
    ))


def run_strategist_counter(document: str, analyst: str, skeptic: str, skeptic_rebuttal: str) -> str:
    counter_prompt = f"""Document:
{_trim(document, 5000)}

Analyst output:
{_trim(analyst, 1400)}

Skeptic output:
{_trim(skeptic, 1400)}

Skeptic rebuttal:
{_trim(skeptic_rebuttal, 1400)}

Respond as the strategist:
1. Accept valid criticisms explicitly
2. Revise strategy to address those criticisms
3. Prioritize actions by impact and feasibility
Cite document evidence."""
    counter = _sanitize_output(chat(STRATEGIST, counter_prompt, max_tokens=DEBATE_MAX_TOKENS, temperature=0.1))
    if not _is_punctuation_loop(counter):
        return counter

    retry_prompt = f"""Document excerpt:
{_compact_document_for_retry(document, max_chars=900)}

Skeptic concerns:
{_trim(skeptic, 700)}
{_trim(skeptic_rebuttal, 700)}

Provide 5 revised actions with risk controls and sequencing."""
    return _sanitize_output(chat(
        STRATEGIST,
        retry_prompt,
        max_tokens=500,
        temperature=0.0,
        continuation_rounds=0,
    ))


def run_auditor(
    document: str,
    analyst: str,
    skeptic: str,
    strategist: str,
    skeptic_rebuttal: str = "",
    strategist_counter: str = "",
) -> str:
    combined = f"""ANALYST OUTPUT:
{analyst}

SKEPTIC OUTPUT:
{skeptic}

STRATEGIST OUTPUT:
{strategist}

SKEPTIC REBUTTAL:
{skeptic_rebuttal}

STRATEGIST COUNTER:
{strategist_counter}

ORIGINAL DOCUMENT:
{document}"""
    verdict = _sanitize_output(chat(AUDITOR, combined, max_tokens=AUDITOR_MAX_TOKENS))
    if not _is_punctuation_loop(verdict):
        return verdict

    for specialist_limit, doc_limit in ((900, 1200), (700, 900), (500, 700)):
        compact_retry_prompt = f"""ANALYST OUTPUT (trimmed):
{_trim(analyst, specialist_limit)}

SKEPTIC OUTPUT (trimmed):
{_trim(skeptic, specialist_limit)}

STRATEGIST OUTPUT (trimmed):
{_trim(strategist, specialist_limit)}

ORIGINAL DOCUMENT (trimmed):
{_compact_document_for_retry(document, max_chars=doc_limit)}

Produce a detailed final verdict with explicit [UNVERIFIED] tags when needed.
Use plain text and avoid repeated punctuation."""
        verdict = _sanitize_output(chat(
            AUDITOR,
            compact_retry_prompt,
            max_tokens=AUDITOR_RETRY_MAX_TOKENS,
            temperature=0.0,
            continuation_rounds=0,
        ))
        if not _is_punctuation_loop(verdict):
            return verdict

    emergency_prompt = f"""Document summary:
{_compact_document_for_retry(document, max_chars=800)}

Analyst:
{_trim(analyst, 500)}

Skeptic:
{_trim(skeptic, 500)}

Strategist:
{_trim(strategist, 500)}

Give a short final verdict with:
1) consensus findings
2) unresolved risks [UNVERIFIED]
3) recommendation.
No repeated punctuation."""
    return _sanitize_output(
        chat(
            AUDITOR,
            emergency_prompt,
            max_tokens=450,
            temperature=0.0,
            continuation_rounds=0,
        )
    )
