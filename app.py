import os
import socket
import html
from pathlib import Path

import gradio as gr

from orchestrator import run_boardroom

CUSTOM_CSS = """
.gradio-container {
    background: #ececec;
    font-family: Inter, "Segoe UI", Arial, sans-serif;
}

.gradio-container .prose,
.gradio-container .prose p,
.gradio-container .prose li,
.gradio-container .prose strong,
.gradio-container .prose em,
.gradio-container .prose h1,
.gradio-container .prose h2,
.gradio-container .prose h3,
.gradio-container .prose h4 {
    color: #0f172a !important;
}

.dashboard-wrap {
    max-width: 1200px;
    margin: 28px auto;
    padding: 28px;
    border-radius: 28px;
    background: #f7f7f7;
    box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
}

.topbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 24px;
}

.brand {
    display: flex;
    align-items: center;
    gap: 12px;
}

.brand-badge {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    background: #111827;
    color: #f9fafb;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
}

.brand-title {
    margin: 0;
    font-size: 24px;
    line-height: 1.15;
    color: #0f172a;
}

.brand-subtitle {
    margin: 2px 0 0 0;
    color: #64748b;
    font-size: 14px;
}

.topbar-search {
    display: flex;
    align-items: center;
    min-width: 260px;
    gap: 10px;
    border: 1px solid #e5e7eb;
    border-radius: 999px;
    background: #ffffff;
    color: #94a3b8;
    padding: 10px 16px;
}

.hero-panel, .upload-panel, .status-panel, .result-panel {
    border: 1px solid #eceff3;
    border-radius: 22px;
    background: #ffffff;
}

.hero-panel {
    padding: 24px 28px;
}

.hero-title {
    margin: 0;
    color: #111827;
    font-size: 34px;
    line-height: 1.15;
}

.hero-subtitle {
    margin: 10px 0 0;
    color: #94a3b8;
    font-size: 30px;
    line-height: 1.2;
}

.kpi-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
    margin-top: 18px;
}

.kpi-card {
    background: #f8fafc;
    border-radius: 14px;
    padding: 14px;
}

.kpi-label {
    color: #64748b;
    font-size: 13px;
}

.kpi-value {
    color: #0f172a;
    font-size: 19px;
    font-weight: 600;
    margin-top: 4px;
}

.upload-panel {
    padding: 20px;
}

.upload-title {
    margin: 0;
    color: #111827;
    font-size: 20px;
}

.upload-copy {
    margin: 8px 0 18px;
    color: #64748b;
    font-size: 14px;
}

.status-panel {
    margin-top: 16px;
    padding: 14px 16px;
    background: #f8fafc;
    border-color: #dbe5f0;
    color: #0f172a !important;
}

.status-panel p {
    margin: 0;
    color: #0f172a !important;
}

.result-panel {
    padding: 10px 16px 16px;
    min-height: 430px;
    background: #f8fafc;
    border-color: #dbe5f0;
    color: #0f172a !important;
}

.result-panel h3 {
    margin: 10px 0 4px;
}

.result-panel .prose,
.result-panel .prose p,
.result-panel .prose li,
.result-panel .prose strong,
.result-panel .prose em,
.result-panel .prose code {
    color: #0f172a !important;
}

.gradio-container [role="tablist"] {
    background: #243247 !important;
    border-radius: 14px 14px 0 0;
    padding-left: 8px;
}

.gradio-container button[role="tab"] {
    color: #dbe5f0 !important;
}

.gradio-container button[role="tab"][aria-selected="true"] {
    color: #ffffff !important;
    border-bottom: 2px solid #f97316 !important;
}

.gradio-container [role="tabpanel"] {
    background: #ffffff;
    border: 1px solid #dbe5f0;
    border-top: none;
    border-radius: 0 0 16px 16px;
}

.debate-panel {
    min-height: 520px;
    background: #f8fafc;
    border: 1px solid #dbe5f0;
    border-radius: 16px;
    padding: 14px;
}

.debate-chat {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.debate-msg {
    border: 1px solid #dbe5f0;
    border-radius: 12px;
    background: #ffffff;
    padding: 10px 12px;
}

.debate-role {
    font-weight: 700;
    color: #1e293b;
    margin-bottom: 6px;
}

.debate-text {
    color: #0f172a;
    line-height: 1.45;
    font-size: 14px;
}

.primary-btn {
    background: linear-gradient(135deg, #f97316, #ea580c) !important;
    border: none !important;
    color: #fff !important;
}

.secondary-btn {
    background: #e2e8f0 !important;
    border: none !important;
    color: #0f172a !important;
}

@media (max-width: 900px) {
    .dashboard-wrap {
        margin: 16px;
        padding: 18px;
    }

    .hero-title {
        font-size: 28px;
    }

    .hero-subtitle {
        font-size: 23px;
    }

    .kpi-grid {
        grid-template-columns: 1fr;
    }
}
"""

TOPBAR_HTML = """
<div class="dashboard-wrap">
    <div class="topbar">
        <div class="brand">
            <span class="brand-badge">B</span>
            <div>
                <h1 class="brand-title">Boardroom Dashboard</h1>
                <p class="brand-subtitle">4-agent document intelligence workspace</p>
            </div>
        </div>
        <div class="topbar-search">🔎 Start searching here ...</div>
    </div>
</div>
"""

HERO_HTML = """
<div class="hero-panel">
    <h2 class="hero-title">Hey, Need help? 👋</h2>
    <p class="hero-subtitle">Just ask me anything about your document.</p>
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-label">Specialist Agents</div>
            <div class="kpi-value">4 Working Together</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Workflow</div>
            <div class="kpi-value">Parallel + Verified Verdict</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Supported Inputs</div>
            <div class="kpi-value">PDF and TXT</div>
        </div>
    </div>
</div>
"""


def analyse(file):
    if file is None:
        return "⚠️ Please upload a PDF or TXT file to start.", "", "", "", "", ""

    try:
        results = run_boardroom(file.name)
        name = Path(file.name).name
        status = f"✅ Deliberation complete for **{name}**."
        debate_html = build_debate_transcript(results)
        return (
            status,
            results["analyst"],
            results["skeptic"],
            results["strategist"],
            results["auditor"],
            debate_html,
        )
    except Exception as exc:
        return f"❌ Error: {exc}", "", "", "", "", ""


def reset_ui():
    return None, "Upload a document and click **Start Deliberation**.", "", "", "", "", ""


def build_debate_transcript(results: dict) -> str:
    ordered_messages = [
        ("Analyst", results.get("analyst", "")),
        ("Skeptic", results.get("skeptic", "")),
        ("Strategist", results.get("strategist", "")),
        ("Skeptic Rebuttal", results.get("skeptic_rebuttal", "")),
        ("Strategist Counter", results.get("strategist_counter", "")),
        ("Auditor Verdict", results.get("auditor", "")),
    ]

    chunks = ['<div class="debate-chat">']
    for role, message in ordered_messages:
        safe_message = html.escape(message or "(No output)")
        safe_message = safe_message.replace("\n", "<br>")
        chunks.append(
            f'<div class="debate-msg"><div class="debate-role">{role}</div>'
            f'<div class="debate-text">{safe_message}</div></div>'
        )
    chunks.append("</div>")
    return "".join(chunks)


def resolve_server_port(host: str, start_port: int = 7860, attempts: int = 25):
    env_port = os.getenv("GRADIO_SERVER_PORT")
    if env_port:
        return int(env_port)

    for port in range(start_port, start_port + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((host, port))
                return port
            except OSError:
                continue
    return None


with gr.Blocks(
    title="Boardroom",
) as demo:
    gr.HTML(TOPBAR_HTML)

    with gr.Group(elem_classes=["dashboard-wrap"]):
        with gr.Row(equal_height=True):
            with gr.Column(scale=5):
                gr.HTML(HERO_HTML)
            with gr.Column(scale=4, elem_classes=["upload-panel"]):
                gr.HTML(
                    """
                    <h3 class="upload-title">Upload a Document</h3>
                    <p class="upload-copy">
                        Drop a PDF or TXT file, then launch the Boardroom to get
                        Analyst, Skeptic, Strategist, and Auditor outputs.
                    </p>
                    """
                )
                file_input = gr.File(
                    label="Document",
                    file_types=[".pdf", ".txt"],
                )
                with gr.Row():
                    run_btn = gr.Button(
                        "Start Deliberation",
                        variant="primary",
                        elem_classes=["primary-btn"],
                    )
                    reset_btn = gr.Button("Reset", elem_classes=["secondary-btn"])

        status_out = gr.Markdown(
            "Upload a document and click **Start Deliberation**.",
            elem_classes=["status-panel"],
        )

        with gr.Tabs():
            with gr.Tab("Debate Messages"):
                debate_out = gr.HTML(elem_classes=["debate-panel"])
            with gr.Tab("Analyst"):
                analyst_out = gr.Markdown(elem_classes=["result-panel"])
            with gr.Tab("Skeptic"):
                skeptic_out = gr.Markdown(elem_classes=["result-panel"])
            with gr.Tab("Strategist"):
                strategist_out = gr.Markdown(elem_classes=["result-panel"])
            with gr.Tab("Auditor Verdict"):
                auditor_out = gr.Markdown(elem_classes=["result-panel"])

    run_btn.click(
        fn=analyse,
        inputs=[file_input],
        outputs=[status_out, analyst_out, skeptic_out, strategist_out, auditor_out, debate_out],
    )

    reset_btn.click(
        fn=reset_ui,
        inputs=None,
        outputs=[file_input, status_out, analyst_out, skeptic_out, strategist_out, auditor_out, debate_out],
    )

if __name__ == "__main__":
    server_name = os.getenv("GRADIO_SERVER_NAME", "127.0.0.1")
    share = os.getenv("GRADIO_SHARE", "false").strip().lower() == "true"
    launch_kwargs = {
        "server_name": server_name,
        "share": share,
        "theme": gr.themes.Soft(primary_hue="orange", neutral_hue="slate"),
        "css": CUSTOM_CSS,
    }
    server_port = resolve_server_port(host=server_name)
    if server_port is not None:
        launch_kwargs["server_port"] = server_port
    demo.launch(**launch_kwargs)
