import fitz  # pymupdf
import concurrent.futures
import os
from agents.boardroom_agents import (
    run_analyst,
    run_skeptic,
    run_strategist,
    run_skeptic_rebuttal,
    run_strategist_counter,
    run_auditor,
)


def extract_text(file_path: str) -> str:
    """Extract text from PDF or txt file."""
    if file_path.endswith(".pdf"):
        doc = fitz.open(file_path)
        text = ""
        for i, page in enumerate(doc):
            text += f"\n[Page {i+1}]\n"
            text += page.get_text()
        return text
    else:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()


def clean_text(text: str) -> str:
    """Normalize extracted text and remove repeated boilerplate lines."""
    import re

    # Preserve line structure first, then normalize per-line.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[^\x00-\x7F\n]+", " ", text)  # remove non-ASCII, keep newlines
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.split("\n")]
    lines = [line for line in lines if line]

    # PDF headers/footers are often repeated many times; keep only first instance.
    counts = {}
    for line in lines:
        counts[line] = counts.get(line, 0) + 1

    deduped_lines = []
    kept_repeated = set()
    for line in lines:
        if counts[line] >= 4:
            if line in kept_repeated:
                continue
            kept_repeated.add(line)
        deduped_lines.append(line)

    text = "\n".join(deduped_lines)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def truncate(text: str, max_chars: int | None = None) -> str:
    """Truncate document to fit context window safely."""
    if max_chars is None:
        max_chars = int(os.getenv("BOARDROOM_MAX_CHARS", "28000"))
    if len(text) > max_chars:
        return text[:max_chars] + "\n\n[Document truncated for context window]"
    return text


def run_boardroom(file_path: str) -> dict:
    """Run specialist agents, then Auditor."""
    print(f"[Boardroom] Reading document: {file_path}")
    raw_text = extract_text(file_path)
    raw_text = clean_text(raw_text)
    document = truncate(raw_text)
    print(f"[Boardroom] Document length: {len(document)} chars")

    use_parallel = os.getenv("BOARDROOM_PARALLEL", "false").lower() == "true"
    if use_parallel:
        print("[Boardroom] Running Analyst, Skeptic, Strategist in parallel...")
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)
        futures = {
            "analyst": executor.submit(run_analyst, document),
            "skeptic": executor.submit(run_skeptic, document),
            "strategist": executor.submit(run_strategist, document),
        }
        try:
            analyst = futures["analyst"].result(timeout=180)
            skeptic = futures["skeptic"].result(timeout=180)
            strategist = futures["strategist"].result(timeout=180)
            executor.shutdown(wait=False, cancel_futures=True)
        except concurrent.futures.TimeoutError:
            print("[Boardroom] Parallel run timed out, falling back to sequential mode...")
            for future in futures.values():
                future.cancel()
            executor.shutdown(wait=False, cancel_futures=True)
            analyst = run_analyst(document)
            skeptic = run_skeptic(document)
            strategist = run_strategist(document)
    else:
        print("[Boardroom] Running Analyst, Skeptic, Strategist sequentially for stability...")
        analyst = run_analyst(document)
        skeptic = run_skeptic(document)
        strategist = run_strategist(document)

    print("[Boardroom] Running Rebuttal Round...")
    skeptic_rebuttal = run_skeptic_rebuttal(document, analyst, strategist)
    strategist_counter = run_strategist_counter(document, analyst, skeptic, skeptic_rebuttal)

    print("[Boardroom] Running Auditor...")
    auditor = run_auditor(document, analyst, skeptic, strategist, skeptic_rebuttal, strategist_counter)

    return {
        "analyst": analyst,
        "skeptic": skeptic,
        "strategist": strategist,
        "skeptic_rebuttal": skeptic_rebuttal,
        "strategist_counter": strategist_counter,
        "auditor": auditor,
    }
