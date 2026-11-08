import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Set up figure with high DPI
fig, ax = plt.subplots(figsize=(16, 11), dpi=300)
ax.set_xlim(0, 16)
ax.set_ylim(0, 11)
ax.axis('off')
fig.patch.set_facecolor('#ffffff')

def draw_card(ax, x, y, w, h, title, subtitle="", items=None, bg='#ffffff', border='#cbd5e1', title_color='#0f172a', title_size=10.5, corner_radius=0.12):
    box = patches.FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad={corner_radius},rounding_size=0.12",
        facecolor=bg, edgecolor=border, linewidth=1.4, zorder=2
    )
    ax.add_patch(box)
    
    # Header background band for key nodes
    ax.text(x + w/2, y + h - 0.28, title, ha='center', va='center', fontsize=title_size, fontweight='bold', color=title_color, zorder=3)
    
    curr_y = y + h - 0.58
    if subtitle:
        ax.text(x + w/2, curr_y, subtitle, ha='center', va='center', fontsize=8, color='#64748b', style='italic', zorder=3)
        curr_y -= 0.32
        
    if items:
        for item in items:
            ax.text(x + 0.25, curr_y, item, ha='left', va='center', fontsize=7.8, color='#334155', zorder=3)
            curr_y -= 0.24

def draw_arrow(ax, x1, y1, x2, y2, label="", color='#475569', lw=1.8, label_pos=0.5, curved=False, rad=0.2):
    connectionstyle = f"arc3,rad={rad}" if curved else "arc3,rad=0"
    arrow = patches.FancyArrowPatch(
        (x1, y1), (x2, y2),
        connectionstyle=connectionstyle,
        arrowstyle='-|>', mutation_scale=14,
        linewidth=lw, color=color, zorder=4
    )
    ax.add_patch(arrow)
    if label:
        lx = x1 + (x2 - x1) * label_pos
        ly = y1 + (y2 - y1) * label_pos
        ax.text(lx, ly, label, fontsize=7.5, fontweight='bold', color=color,
                bbox=dict(boxstyle="round,pad=0.25", facecolor="#ffffff", edgecolor=color, alpha=0.95, linewidth=0.8),
                ha='center', va='center', zorder=5)

# 1. Top Header Banner
banner = patches.FancyBboxPatch(
    (3.5, 9.9), 9.0, 0.8,
    boxstyle="round,pad=0.1,rounding_size=0.12",
    facecolor='#0f172a', edgecolor='#0f172a', linewidth=1, zorder=2
)
ax.add_patch(banner)
ax.text(8.0, 10.42, "SELF-EVALUATING LESSON GENERATOR", ha='center', va='center', fontsize=13, fontweight='bold', color='#ffffff', zorder=3)
ax.text(8.0, 10.12, "System Architecture: Autonomous Pedagogical Content Generation with Deterministic Rubric QA", ha='center', va='center', fontsize=8.5, color='#94a3b8', zorder=3)

# 2. Row 1: Inputs & Entrypoints (y=8.3, h=1.2)
draw_card(ax, 0.8, 8.3, 3.2, 1.2, "User Interfaces (Ingress)", items=[
    "• Web Dashboard (ui.py on port 8000)",
    "• Command Line CLI (main.py)",
    "• Live Server-Sent Events (SSE) Stream"
], bg='#f8fafc', border='#94a3b8')

draw_card(ax, 4.5, 8.3, 3.2, 1.2, "Topic Ingress", items=[
    "• Submission Topic: Introduction to RAG",
    "• Arbitrary Technical Subject Support",
    "• Deliberate Error Demo Toggle"
], bg='#eff6ff', border='#3b82f6', title_color='#1d4ed8')

draw_card(ax, 8.2, 8.3, 3.2, 1.2, "Cross-Run Memory", items=[
    "• Source: data/memory.json",
    "• Historical Failure Trend Analysis",
    "• Injects Standing Quality Rules"
], bg='#fefce8', border='#eab308', title_color='#a16207')

draw_card(ax, 11.9, 8.3, 3.3, 1.2, "LLM Engine & Resilience", items=[
    "• Primary: gemini-3.5-flash-lite",
    "• Fallbacks: 3.5-flash, 3.8-flash, 3.7-flash",
    "• Exponential Backoff on 503 / 429"
], bg='#faf5ff', border='#a855f7', title_color='#7e22ce')

# 3. Row 2: Draft Generator (y=6.3, h=1.5, w=8.0, x=4.0)
draw_card(ax, 4.0, 6.3, 8.0, 1.5, "Draft Generator (generator.py)", "Constructs beginner-friendly draft using pedagogical rules & memory context", items=[
    "1. Pedagogy Constraints: Zero technical background assumed; short sentences; everyday vocabulary",
    "2. Mandatory Triad: Explicitly covers What it is, Why it matters, and How it operates",
    "3. Relatable Analogy: Requires a concrete everyday analogy (e.g., open-book library exam)",
    "4. Feedback Injection: Prepends critical corrections when triggered by prior attempt failure"
], bg='#f0fdf4', border='#22c55e', title_color='#15803d', title_size=11)

# 4. Row 3: Rubric Evaluator (y=3.8, h=2.0, w=8.0, x=4.0)
draw_card(ax, 4.0, 3.8, 8.0, 2.0, "Rubric Evaluator (evaluator.py)", "Independent quality assurance pass with structured JSON schema", items=[
    "[✓/✗] accurate_and_grounded       - Technically factual, no model hallucinations",
    "[✓/✗] beginner_friendly_language   - Plain English, no assumed prerequisites",
    "[✓/✗] teaches_by_example          - Concrete real-world worked example/analogy",
    "[✓/✗] no_unexplained_jargon        - Every term defined before or at first use",
    "[✓/✗] covers_key_points            - What, Why, and How explicitly addressed",
    "[✓/✗] coherent_teaching_flow       - Clear Intro -> Body Explanation -> Takeaways",
    "Deterministic Quality Gate: overall_pass = all(checkpoints == True) verified in Python code"
], bg='#fef2f2', border='#ef4444', title_color='#b91c1c', title_size=11)

# 5. Decision Nodes (Pass & Fail)
# Fail / Self-Correction (Left)
draw_card(ax, 0.8, 4.5, 2.8, 1.9, "Self-Correction Loop", "Triggered if any check fails", items=[
    "• Evaluator generates critique",
    "• Structured diff captured",
    "• Rejection logged to disk",
    "• Formats corrective feedback",
    "• Retries up to MAX_RETRIES (2)"
], bg='#fff7ed', border='#f97316', title_color='#c2410c')

# Pass Node (Right)
draw_card(ax, 12.4, 4.2, 2.8, 1.6, "Decision: PASS", "All 6 checks evaluated True", items=[
    "• Quality contract satisfied",
    "• Ship-ready lesson verified",
    "• Invokes Orchestrator export",
    "• Updates memory standing rules"
], bg='#f0fdf4', border='#16a34a', title_color='#15803d')

# 6. Row 4: Persistence & Outputs (y=0.7, h=1.8)
draw_card(ax, 0.8, 0.7, 3.3, 1.8, "Audit & Persistence", items=[
    "• logs/rejection_log.json",
    "  Records every rejected draft,",
    "  failing checkpoints, and critiques",
    "• data/runs/<timestamp>.json",
    "  Full execution history & attempt diffs"
], bg='#f8fafc', border='#64748b', title_color='#334155')

draw_card(ax, 4.5, 0.7, 3.3, 1.8, "Cross-Run Memory", items=[
    "• data/memory.json",
    "• Scans historical runs in data/runs/",
    "• Checkpoint failure count > 1 creates",
    "  standing pedagogical rules"
], bg='#fefce8', border='#ca8a04', title_color='#854d0e')

draw_card(ax, 8.2, 0.7, 3.3, 1.8, "Markdown Lesson Export", items=[
    "• data/runs/final_lesson.md",
    "• Clean GitHub-flavored Markdown",
    "• Ready for direct copy-paste into",
    "  submission document"
], bg='#f0fdfa', border='#0d9488', title_color='#0f766e')

draw_card(ax, 11.9, 0.7, 3.3, 1.8, "Publication PDF", items=[
    "• data/runs/final_lesson.pdf",
    "• Built via ReportLab engine",
    "• Clean white background, callout",
    "  boxes, book typography & page numbers"
], bg='#eff6ff', border='#2563eb', title_color='#1d4ed8')

# --- ARROWS ---
# Ingress to Topic
draw_arrow(ax, 4.0, 8.9, 4.5, 8.9, lw=1.6, color='#64748b')

# Topic to Generator
draw_arrow(ax, 6.1, 8.3, 6.1, 7.8, label="Topic String", color='#2563eb', label_pos=0.5)

# Memory to Generator
draw_arrow(ax, 9.5, 8.3, 8.5, 7.8, label="Standing Rules", color='#ca8a04', label_pos=0.45)

# LLM to Generator
draw_arrow(ax, 13.0, 8.3, 11.2, 7.8, label="Gemini API Call", color='#7e22ce', label_pos=0.45)

# Generator to Evaluator
draw_arrow(ax, 8.0, 6.3, 8.0, 5.8, label="Draft Content", color='#16a34a', lw=2.2, label_pos=0.5)

# Evaluator to Decision Nodes
draw_arrow(ax, 12.0, 4.9, 12.4, 4.9, label="all(checks == True)", color='#16a34a', lw=2.2, label_pos=0.45)
draw_arrow(ax, 4.0, 4.9, 3.6, 5.2, label="any(checks == False)", color='#ef4444', lw=2.2, label_pos=0.45)

# Retry Loop: Fail Card back to Generator
draw_arrow(ax, 2.2, 6.4, 4.0, 6.9, label="Prepend Corrective Feedback", color='#ea580c', lw=2.0, curved=True, rad=-0.25, label_pos=0.5)

# Fail Card records to Audit Log
draw_arrow(ax, 1.2, 4.5, 1.2, 2.5, label="Log Rejection", color='#ef4444', lw=1.5, curved=True, rad=-0.2, label_pos=0.5)

# Pass Node to Orchestrator Distribution
draw_arrow(ax, 13.55, 4.2, 13.55, 3.0, lw=2.0, color='#16a34a')

# Horizontal Orchestrator Distribution Bus
ax.plot([2.45, 13.55], [3.0, 3.0], color='#16a34a', linewidth=2.0, zorder=4)
ax.text(8.0, 3.2, "Orchestrator Finalization Bus (orchestrator.py)", ha='center', va='center', fontsize=8, fontweight='bold', color='#15803d',
        bbox=dict(boxstyle="round,pad=0.2", facecolor="#f0fdf4", edgecolor="#16a34a", linewidth=0.8), zorder=5)

# Drops to the 4 output cards
draw_arrow(ax, 2.45, 3.0, 2.45, 2.5, color='#16a34a', lw=1.8)
draw_arrow(ax, 6.15, 3.0, 6.15, 2.5, color='#16a34a', lw=1.8)
draw_arrow(ax, 9.85, 3.0, 9.85, 2.5, color='#16a34a', lw=1.8)
draw_arrow(ax, 13.55, 3.0, 13.55, 2.5, color='#16a34a', lw=1.8)

# Output generation
plt.tight_layout()
plt.savefig("architecture_diagram.png", dpi=300, bbox_inches='tight')
plt.savefig("architecture_diagram.svg", format='svg', bbox_inches='tight')
print("Complete: architecture_diagram.png and architecture_diagram.svg generated.")
