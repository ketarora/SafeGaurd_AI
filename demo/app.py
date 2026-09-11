from flask import Flask, request, render_template_string
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.pipeline import SupportAgentPipeline

app = Flask(__name__, static_folder='static')
pipeline = None

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SafeGuard AI — Pipeline Inspector</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        /* ── Tokens ─────────────────────────────────────────── */
        :root {
            --bg:           #ffffff;
            --surface:      #fafafa;
            --surface-2:    #f4f4f5;
            --border:       #e4e4e7;
            --border-strong: #d4d4d8;
            --text-1:       #09090b;
            --text-2:       #3f3f46;
            --text-3:       #71717a;
            --text-muted:   #a1a1aa;
            --black:        #09090b;
            --white:        #ffffff;
            --green:        #16a34a;
            --green-bg:     #f0fdf4;
            --green-border: #bbf7d0;
            --red:          #dc2626;
            --red-bg:       #fef2f2;
            --red-border:   #fecaca;
            --amber:        #d97706;
            --amber-bg:     #fffbeb;
            --blue:         #2563eb;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: 'Inter', -apple-system, system-ui, sans-serif;
            background: var(--bg);
            color: var(--text-1);
            min-height: 100vh;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }

        /* ── Shell ──────────────────────────────────────────── */
        .shell {
            max-width: 720px;
            margin: 0 auto;
            padding: 60px 24px 100px;
        }

        /* ── Header ─────────────────────────────────────────── */
        .header {
            margin-bottom: 48px;
            text-align: center;
        }

        .brand-mark {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 12px;
        }

        .brand-icon {
            width: 32px; height: 32px;
            background: var(--black);
            border-radius: 8px;
            display: flex; align-items: center; justify-content: center;
        }

        .brand-mark h1 {
            font-size: 20px;
            font-weight: 800;
            letter-spacing: -0.5px;
            color: var(--black);
        }

        .header .subtitle {
            font-size: 14px;
            color: var(--text-3);
            line-height: 1.5;
            max-width: 480px;
            margin: 0 auto;
        }

        /* ── Input Section ──────────────────────────────────── */
        .input-section {
            margin-bottom: 40px;
        }

        .input-box {
            border: 1.5px solid var(--border);
            border-radius: 14px;
            overflow: hidden;
            transition: border-color 0.2s;
        }

        .input-box:focus-within {
            border-color: var(--black);
        }

        textarea {
            width: 100%;
            min-height: 100px;
            border: none;
            padding: 18px 20px 12px;
            font-family: 'Inter', sans-serif;
            font-size: 15px;
            color: var(--text-1);
            resize: none;
            background: transparent;
            line-height: 1.6;
        }

        textarea::placeholder { color: var(--text-muted); }
        textarea:focus { outline: none; }

        .input-bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 12px 12px 16px;
            gap: 10px;
        }

        .chips {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
            flex: 1;
        }

        .chip {
            font-size: 12px;
            font-weight: 500;
            color: var(--text-3);
            background: var(--surface-2);
            border: 1px solid transparent;
            border-radius: 100px;
            padding: 5px 12px;
            cursor: pointer;
            transition: all 0.15s;
            user-select: none;
        }

        .chip:hover {
            color: var(--text-1);
            border-color: var(--border);
            background: var(--surface);
        }

        .btn-run {
            background: var(--black);
            color: var(--white);
            border: none;
            height: 36px;
            padding: 0 20px;
            border-radius: 100px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s;
            white-space: nowrap;
            flex-shrink: 0;
        }

        .btn-run:hover { opacity: 0.8; }
        .btn-run:disabled { opacity: 0.35; cursor: default; }

        /* ── Loader ─────────────────────────────────────────── */
        .loader {
            display: none;
            text-align: center;
            padding: 48px 0;
        }

        .loader.active { display: block; }

        @keyframes bounce {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }

        .bounce-dots {
            display: inline-flex;
            gap: 5px;
            margin-bottom: 12px;
        }

        .bounce-dots span {
            width: 8px; height: 8px;
            background: var(--black);
            border-radius: 50%;
            animation: bounce 1.4s ease-in-out infinite;
        }

        .bounce-dots span:nth-child(1) { animation-delay: -0.32s; }
        .bounce-dots span:nth-child(2) { animation-delay: -0.16s; }

        .loader p {
            font-size: 13px;
            color: var(--text-muted);
        }

        /* ── Divider ────────────────────────────────────────── */
        .divider {
            height: 1px;
            background: var(--border);
            margin: 8px 0 32px;
        }

        .section-title {
            font-size: 11px;
            font-weight: 600;
            color: var(--text-muted);
            letter-spacing: 0.8px;
            text-transform: uppercase;
            margin-bottom: 20px;
        }

        /* ── Step Cards ─────────────────────────────────────── */
        .step {
            border: 1px solid var(--border);
            border-radius: 12px;
            margin-bottom: 12px;
            overflow: hidden;
            opacity: 0;
            transform: translateY(12px);
            transition: opacity 0.45s ease, transform 0.45s ease;
        }

        .step.visible {
            opacity: 1;
            transform: translateY(0);
        }

        .step-top {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 16px 20px;
            background: var(--surface);
            border-bottom: 1px solid var(--border);
        }

        .step-badge {
            width: 24px; height: 24px;
            border-radius: 6px;
            background: var(--black);
            color: var(--white);
            font-size: 12px;
            font-weight: 700;
            display: flex; align-items: center; justify-content: center;
            font-family: 'JetBrains Mono', monospace;
            flex-shrink: 0;
        }

        .step-top h3 {
            font-size: 14px;
            font-weight: 600;
            color: var(--text-1);
            flex: 1;
        }

        .step-body {
            padding: 16px 20px;
        }

        /* ── Rows ───────────────────────────────────────────── */
        .row {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            padding: 11px 0;
        }

        .row + .row {
            border-top: 1px solid var(--surface-2);
        }

        .row-key {
            font-size: 13px;
            color: var(--text-3);
        }

        .row-val {
            font-size: 14px;
            font-weight: 600;
            color: var(--text-1);
            font-family: 'JetBrains Mono', monospace;
            text-align: right;
            max-width: 55%;
        }

        .row-val.prose {
            font-family: 'Inter', sans-serif;
            font-weight: 400;
            color: var(--text-2);
            font-size: 13px;
            line-height: 1.55;
        }

        /* ── Confidence ─────────────────────────────────────── */
        .conf-wrap {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .conf-track {
            width: 80px; height: 5px;
            background: var(--surface-2);
            border-radius: 10px;
            overflow: hidden;
        }

        .conf-bar {
            height: 100%;
            border-radius: 10px;
            transition: width 0.7s cubic-bezier(0.16, 1, 0.3, 1);
        }

        /* ── Precedents ─────────────────────────────────────── */
        .prec {
            display: flex;
            gap: 14px;
            padding: 14px 16px;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 10px;
            margin-bottom: 8px;
            transition: border-color 0.15s;
        }

        .prec:hover { border-color: var(--border-strong); }

        .prec-score {
            font-family: 'JetBrains Mono', monospace;
            font-weight: 600;
            font-size: 13px;
            color: var(--green);
            padding-top: 1px;
            flex-shrink: 0;
        }

        .prec-id {
            font-size: 11px;
            color: var(--text-muted);
            font-family: 'JetBrains Mono', monospace;
            margin-bottom: 3px;
        }

        .prec-text {
            font-size: 13px;
            color: var(--text-2);
            line-height: 1.5;
        }

        .prec-empty {
            text-align: center;
            padding: 24px 16px;
            color: var(--text-muted);
            font-size: 13px;
            border: 1px dashed var(--border);
            border-radius: 10px;
        }

        /* ── Draft ──────────────────────────────────────────── */
        .draft-wrap {
            margin-top: 16px;
        }

        .draft-label {
            font-size: 11px;
            font-weight: 600;
            color: var(--text-muted);
            letter-spacing: 0.3px;
            margin-bottom: 8px;
        }

        .draft-box {
            background: var(--surface);
            border: 1px solid var(--border);
            border-left: 3px solid var(--black);
            border-radius: 8px;
            padding: 16px 18px;
            font-size: 14px;
            color: var(--text-2);
            line-height: 1.7;
        }

        /* ── Pills ──────────────────────────────────────────── */
        .pill {
            font-size: 11px;
            font-weight: 600;
            padding: 3px 10px;
            border-radius: 6px;
        }

        .pill-escalate {
            background: var(--red-bg);
            color: var(--red);
            border: 1px solid var(--red-border);
        }

        .pill-auto {
            background: var(--green-bg);
            color: var(--green);
            border: 1px solid var(--green-border);
        }

        /* ── Safety alert ───────────────────────────────────── */
        .safety-banner {
            display: flex;
            gap: 10px;
            align-items: flex-start;
            padding: 14px 16px;
            background: var(--red-bg);
            border: 1px solid var(--red-border);
            border-radius: 8px;
            margin-bottom: 12px;
        }

        .safety-banner svg { flex-shrink: 0; color: var(--red); margin-top: 1px; }

        .safety-banner p {
            font-size: 13px;
            font-weight: 500;
            color: var(--red);
            line-height: 1.4;
        }

        /* ── Grounding tag ──────────────────────────────────── */
        .ground-tag {
            font-size: 12px;
            font-weight: 600;
            font-family: 'JetBrains Mono', monospace;
        }

        .ground-strong { color: var(--green); }
        .ground-moderate { color: var(--amber); }
        .ground-weak, .ground-none { color: var(--red); }

        /* ── Architecture footer ────────────────────────────── */
        .arch {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0;
            margin-top: 48px;
            padding: 18px 20px;
            border-top: 1px solid var(--border);
        }

        .arch-node {
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .arch-dot {
            width: 7px; height: 7px;
            border-radius: 50%;
        }

        .arch-node span {
            font-size: 12px;
            font-weight: 500;
            color: var(--text-3);
        }

        .arch-arrow {
            margin: 0 14px;
            color: var(--text-muted);
            font-size: 12px;
        }

        /* ── Responsive ─────────────────────────────────────── */
        @media (max-width: 600px) {
            .shell { padding: 32px 16px 60px; }
            .input-bar { flex-direction: column; align-items: stretch; }
            .btn-run { width: 100%; text-align: center; }
            .arch { flex-wrap: wrap; gap: 8px; justify-content: center; }
            .arch-arrow { margin: 0 6px; }
        }
    </style>
</head>
<body>
    <div class="shell">
        <!-- Header -->
        <header class="header">
            <div class="brand-mark">
                <div class="brand-icon">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                </div>
                <h1>SafeGuard AI</h1>
            </div>
            <p class="subtitle">Classify intent · retrieve precedents · draft reply · decide escalation</p>
        </header>

        <!-- Input -->
        <form method="POST" id="main-form" class="input-section">
            <div class="input-box">
                <textarea name="message" id="input-msg" placeholder="Paste a customer support tweet — e.g. &quot;Charged $34 for a trip that said $18 upfront @Uber_Support&quot;" required>{{ message }}</textarea>
                <div class="input-bar">
                    <div class="chips">
                        <span class="chip" data-tweet="My driver ran a red light and I genuinely felt unsafe the entire ride @Uber_Support">🚨 Safety</span>
                        <span class="chip" data-tweet="Applied SAVE20 promo code but still charged full price on my last trip @Uber_Support">🎟️ Promo</span>
                        <span class="chip" data-tweet="Trip was $34 but upfront price said $18. How do you explain this @Uber_Support">💸 Fare</span>
                        <span class="chip" data-tweet="I left my laptop in the back seat of my Uber. Please help me get it back @Uber_Support">📦 Lost item</span>
                    </div>
                    <button type="submit" class="btn-run" id="submit-btn">Analyze →</button>
                </div>
            </div>
        </form>

        <!-- Loader -->
        <div class="loader" id="loader">
            <div class="bounce-dots"><span></span><span></span><span></span></div>
            <p>Running pipeline...</p>
        </div>

        {% if result %}
        <div class="divider"></div>
        <div class="section-title">Pipeline output</div>

        <!-- Step 1 -->
        <div class="step" id="step-1">
            <div class="step-top">
                <div class="step-badge">1</div>
                <h3>Classification</h3>
            </div>
            <div class="step-body">
                <div class="row">
                    <span class="row-key">Intent</span>
                    <span class="row-val">{{ result.classification.intent }}</span>
                </div>
                <div class="row">
                    <span class="row-key">Confidence</span>
                    <span class="row-val">
                        {% set pct = (result.classification.confidence * 100)|round(1) %}
                        <div class="conf-wrap">
                            <div class="conf-track">
                                <div class="conf-bar" style="width:{{ pct }}%; background:{% if pct >= 70 %}var(--green){% elif pct >= 40 %}var(--amber){% else %}var(--red){% endif %};"></div>
                            </div>
                            {{ pct }}%
                        </div>
                    </span>
                </div>
                <div class="row">
                    <span class="row-key">Reasoning</span>
                    <span class="row-val prose">{{ result.classification.reasoning }}</span>
                </div>
            </div>
        </div>

        <!-- Step 2 -->
        <div class="step" id="step-2">
            <div class="step-top">
                <div class="step-badge">2</div>
                <h3>Retrieval + Draft</h3>
                <span class="ground-tag ground-{{ result.draft.grounding_quality }}" style="margin-left:auto;">{{ result.draft.grounding_quality }}</span>
            </div>
            <div class="step-body">
                {% for p in result.draft.precedents %}
                <div class="prec">
                    <span class="prec-score">{{ (p.similarity * 100)|round(0)|int }}%</span>
                    <div>
                        <div class="prec-id">{{ p.id }}</div>
                        <div class="prec-text">{{ p.brand_reply }}</div>
                    </div>
                </div>
                {% else %}
                <div class="prec-empty">No precedents exceeded the similarity threshold</div>
                {% endfor %}

                <div class="draft-wrap">
                    <div class="draft-label">Drafted reply</div>
                    <div class="draft-box">{{ result.draft.draft_reply }}</div>
                </div>
            </div>
        </div>

        <!-- Step 3 -->
        <div class="step" id="step-3">
            <div class="step-top">
                <div class="step-badge">3</div>
                <h3>Escalation</h3>
                <span class="pill {% if result.escalation.decision == 'escalate' %}pill-escalate{% else %}pill-auto{% endif %}" style="margin-left:auto;">
                    {{ result.escalation.decision }}
                </span>
            </div>
            <div class="step-body">
                {% if result.escalation.hard_rule_triggered %}
                <div class="safety-banner">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                    <p>Safety guardrail triggered — deterministic escalation enforced in code, not by LLM</p>
                </div>
                {% endif %}
                <div class="row">
                    <span class="row-key">Reason</span>
                    <span class="row-val prose">{{ result.escalation.reason }}</span>
                </div>
            </div>
        </div>
        {% endif %}

        <!-- Architecture -->
        <div class="arch">
            <div class="arch-node"><div class="arch-dot" style="background:var(--blue);"></div><span>Tweet</span></div>
            <div class="arch-arrow">→</div>
            <div class="arch-node"><div class="arch-dot" style="background:var(--amber);"></div><span>Classify</span></div>
            <div class="arch-arrow">→</div>
            <div class="arch-node"><div class="arch-dot" style="background:var(--green);"></div><span>Retrieve + Draft</span></div>
            <div class="arch-arrow">→</div>
            <div class="arch-node"><div class="arch-dot" style="background:var(--red);"></div><span>Escalate</span></div>
        </div>
    </div>

    <script>
        // Chip click → fill textarea
        document.querySelectorAll('.chip').forEach(c => {
            c.addEventListener('click', () => {
                document.getElementById('input-msg').value = c.dataset.tweet;
                document.getElementById('input-msg').focus();
            });
        });

        // Submit state
        document.getElementById('main-form').addEventListener('submit', () => {
            document.getElementById('submit-btn').disabled = true;
            document.getElementById('submit-btn').textContent = 'Analyzing...';
            document.getElementById('loader').classList.add('active');
        });

        // Staggered reveal
        window.addEventListener('load', () => {
            ['step-1', 'step-2', 'step-3'].forEach((id, i) => {
                const el = document.getElementById(id);
                if (el) setTimeout(() => el.classList.add('visible'), 200 + i * 500);
            });
        });
    </script>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    global pipeline
    if request.method == "POST":
        message = request.form.get("message", "")
        if not pipeline:
            pipeline = SupportAgentPipeline(classifier_name="llm")
        result = pipeline.process(message).to_dict()
        return render_template_string(HTML, message=message, result=result)
    return render_template_string(HTML, message="", result=None)

if __name__ == "__main__":
    app.run(port=5000, debug=False)
