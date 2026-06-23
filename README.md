# Boardroom

**Boardroom** is a multi-agent document intelligence workspace. It simulates a corporate boardroom where four distinct AI personas collaboratively analyze, debate, and verify the contents of uploaded documents (PDF or TXT). 

Instead of relying on a single LLM response, Boardroom runs a highly structured **Debate and Verification Workflow**. This prevents hallucinations, uncovers hidden risks, and provides a deeply vetted final verdict.

---

## 🧠 The Agents

The system uses four specialized agents, each with a distinct system prompt and mandate:

1. **The Analyst**
   - **Role**: The neutral fact-finder.
   - **Mandate**: Extracts key facts, figures, dates, assumptions, and critical claims. Structures the baseline reality of the document without bias or strategic input.
2. **The Skeptic**
   - **Role**: The challenger.
   - **Mandate**: Aggressively challenges the document and the other agents. Finds contradictions, weak assumptions, missing evidence, implementation risks, and gaps in realism.
3. **The Strategist**
   - **Role**: The pragmatist.
   - **Mandate**: Produces practical recommendations. Responds to both the opportunities in the document and the risks highlighted by the Skeptic. Provides actionable steps with rationales and implementation cautions.
4. **The Auditor**
   - **Role**: The final judge.
   - **Mandate**: Receives all outputs (including the debate rebuttals). Identifies unsupported claims, resolves disagreements, marks unverified statements with `[UNVERIFIED]`, and produces a final consolidated verdict (consensus, open risks, recommended decision).

---

## ⚙️ Core Workflow & Architecture

The application is built in Python and structured into three primary layers: the UI (`app.py`), the orchestration logic (`orchestrator.py`), and the agent/LLM communication layer (`boardroom_agents.py` & `models.py`).

### 1. Document Processing (`orchestrator.py`)
- **Extraction**: Reads `.pdf` (using `pymupdf`/`fitz`) or `.txt` files.
- **Cleaning & Deduplication**: Runs `clean_text()` to normalize text, strip non-ASCII characters, collapse whitespace, and automatically remove repeating PDF boilerplate (like headers/footers appearing more than 4 times).
- **Truncation**: If the document is too large for the context window, it safely truncates it using `truncate()` (default 28,000 chars, configurable via `BOARDROOM_MAX_CHARS`).

### 2. Multi-Agent Orchestration (`orchestrator.py`)
- **Phase 1 (Parallel Analysis)**: The Analyst, Skeptic, and Strategist run concurrently using a `ThreadPoolExecutor` for speed. If the parallel run times out or fails (configurable via `BOARDROOM_PARALLEL`), it safely falls back to a sequential run.
- **Phase 2 (Debate/Rebuttal)**: 
  - **Skeptic Rebuttal**: The Skeptic reviews the Analyst and Strategist outputs, pointing out weak logic or ignored risks.
  - **Strategist Counter**: The Strategist revises its plan based on the Skeptic's criticism.
- **Phase 3 (Final Audit)**: The Auditor reviews the original document, the Phase 1 outputs, and the Phase 2 debate to generate the final Verdict.

### 3. LLM Reliability Mechanisms (`boardroom_agents.py` & `models.py`)
Working with LLMs (specifically Llama-3.1 70B via a custom AMD API endpoint) requires robust error handling. We implemented several "bulletproof" mechanisms:
- **Punctuation Loop Detection**: Detects if the model gets stuck in a formatting loop (e.g., printing endless `!!!!!!!!`). If detected, the response is discarded and retried.
- **Dynamic Prompt Compression (Retries)**: If an agent fails, the system automatically retries with progressively shorter document excerpts (`_compact_document_for_retry`) and stricter temperature settings (`temperature=0.0`) to force compliance.
- **Sanitization**: Output is stripped of trailing formatting artifacts via `_sanitize_output()`.
- **Continuation Rounds**: If the model hits a max token limit before finishing, `models.py` automatically injects a "Continue from where you stopped" prompt to stitch together a complete response.

### 4. User Interface (`app.py`)
- Built with **Gradio**.
- Custom CSS for a premium, dashboard-like experience (Orange/Slate theme).
- Features a responsive KPI header, drag-and-drop file upload, and a tabbed interface separating the agents' outputs.
- Includes a dedicated **"Debate Messages"** tab that renders the entire conversation transcript (Analyst -> Skeptic -> Strategist -> Skeptic Rebuttal -> Strategist Counter -> Auditor) chronologically.

---

## 🛠️ Configuration & Environment Variables

The project uses a `.env` file to control LLM parameters and system behavior without changing code:

- `AMD_API_BASE` / `AMD_API_KEY`: API credentials for the OpenAI-compatible endpoint.
- `BOARDROOM_MODEL`: The LLM to use (defaults to `amd/Llama-3.1-70B-Instruct-FP8-KV`).
- `BOARDROOM_PARALLEL`: Set to `true` to run Phase 1 agents in parallel, `false` for sequential.
- `BOARDROOM_MAX_CHARS`: Document truncation limit.
- `BOARDROOM_*_MAX_TOKENS`: Granular token limits for the Specialist agents, Debate rounds, and the Auditor.

---

## 🚀 Getting Started

1. Ensure dependencies are installed (`pip install -r requirements.txt`).
2. Set up your `.env` file with the required API keys.
3. Run the application:
   ```bash
   python app.py
   ```
4. Open the provided local Gradio URL (e.g., `http://127.0.0.1:7860`).
5. Upload a document and click **Start Deliberation**.
