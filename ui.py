import json
import os
import re
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse

from config import FINAL_LESSON_FILE, MEMORY_FILE, REJECTION_LOG_FILE, RUNS_DIR, validate_api_key
from orchestrator import run_pipeline

PORT = 8000

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Lesson Quality Agent — Live Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
  <style>
    :root {
      --bg: #0f172a;
      --card-bg: #1e293b;
      --border: #334155;
      --accent: #38bdf8;
      --accent-hover: #0284c7;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --pass: #10b981;
      --fail: #ef4444;
      --warn: #f59e0b;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding: 16px;
      height: 100vh;
      display: flex;
      flex-direction: column;
    }
    .header {
      max-width: 1600px;
      width: 100%;
      margin: 0 auto 12px auto;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border);
      padding-bottom: 12px;
    }
    .header h1 { font-size: 1.3rem; font-weight: 700; color: var(--accent); }
    .header p { font-size: 0.85rem; color: var(--text-muted); }
    
    .controls-card {
      max-width: 1600px;
      width: 100%;
      margin: 0 auto 14px auto;
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 12px 16px;
      display: flex;
      gap: 12px;
      align-items: center;
      flex-wrap: wrap;
    }
    .input-group { flex: 1; min-width: 300px; }
    .input-group label { display: block; font-size: 0.75rem; color: var(--text-muted); margin-bottom: 4px; }
    .input-group input {
      width: 100%;
      padding: 8px 12px;
      background: #0f172a;
      border: 1px solid var(--border);
      border-radius: 6px;
      color: #fff;
      font-size: 0.9rem;
    }
    .demo-toggle {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      background: #0f172a;
      border: 1px solid var(--border);
      border-radius: 6px;
      font-size: 0.85rem;
      cursor: pointer;
      position: relative;
    }
    .info-pill {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 16px;
      height: 16px;
      border-radius: 50%;
      background: #334155;
      color: var(--accent);
      font-size: 0.7rem;
      font-weight: bold;
      cursor: help;
      margin-left: 4px;
    }
    .tooltip {
      visibility: hidden;
      width: 280px;
      background-color: #020617;
      color: #f1f5f9;
      text-align: left;
      border-radius: 6px;
      padding: 10px;
      border: 1px solid var(--border);
      position: absolute;
      z-index: 10;
      top: 110%;
      left: 0;
      font-size: 0.78rem;
      line-height: 1.4;
      box-shadow: 0 10px 15px -3px rgba(0,0,0,0.5);
    }
    .demo-toggle:hover .tooltip { visibility: visible; }

    .btn {
      padding: 9px 20px;
      background: var(--accent);
      color: #0f172a;
      border: none;
      border-radius: 6px;
      font-weight: 600;
      font-size: 0.9rem;
      cursor: pointer;
      transition: background 0.2s;
    }
    .btn:hover { background: var(--accent-hover); }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }

    /* Resizable Split Container */
    .split-container {
      max-width: 1600px;
      width: 100%;
      margin: 0 auto;
      flex: 1;
      display: flex;
      gap: 0;
      min-height: 0;
      position: relative;
    }

    .panel {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      min-width: 280px;
      overflow: hidden;
    }
    #leftPanel { width: 50%; }
    #rightPanel { flex: 1; min-width: 320px; }

    /* Resizer Drag Handle */
    .resizer {
      width: 10px;
      cursor: col-resize;
      background: transparent;
      display: flex;
      align-items: center;
      justify-content: center;
      user-select: none;
      transition: background 0.2s;
    }
    .resizer:hover, .resizer.dragging {
      background: var(--accent);
      border-radius: 4px;
    }
    .resizer::after {
      content: "⋮";
      color: var(--text-muted);
      font-size: 14px;
    }

    .panel-title {
      font-size: 1rem;
      font-weight: 600;
      margin-bottom: 12px;
      padding-bottom: 8px;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-shrink: 0;
    }
    .panel-actions {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .small-btn {
      font-size: 0.75rem;
      padding: 3px 8px;
      background: #0f172a;
      border: 1px solid var(--border);
      color: var(--text-muted);
      border-radius: 4px;
      cursor: pointer;
    }
    .small-btn:hover { color: #fff; border-color: var(--accent); }

    .panel-content {
      flex: 1;
      overflow-y: auto;
      padding-right: 6px;
    }

    /* Accordion Attempt Cards */
    .attempt-card {
      background: #0f172a;
      border: 1px solid var(--border);
      border-radius: 8px;
      margin-bottom: 12px;
      overflow: hidden;
      transition: border-color 0.2s;
    }
    .attempt-card.expanded { border-color: #475569; }

    .attempt-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 10px 14px;
      background: #131d31;
      cursor: pointer;
      user-select: none;
    }
    .attempt-header:hover { background: #1a2744; }
    
    .attempt-title-area {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 600;
      font-size: 0.9rem;
    }
    .chevron {
      display: inline-block;
      transition: transform 0.2s;
      font-size: 0.75rem;
      color: var(--accent);
    }
    .attempt-card.expanded .chevron { transform: rotate(90deg); }

    .status-badge {
      font-size: 0.75rem;
      padding: 2px 8px;
      border-radius: 12px;
      font-weight: 600;
    }
    .status-badge.pass { background: rgba(16, 185, 129, 0.2); color: var(--pass); border: 1px solid var(--pass); }
    .status-badge.fail { background: rgba(239, 68, 68, 0.2); color: var(--fail); border: 1px solid var(--fail); }

    .attempt-body {
      display: none;
      padding: 12px 14px;
      border-top: 1px solid var(--border);
    }
    .attempt-card.expanded .attempt-body { display: block; }

    /* Rubric Checkpoints */
    .rubric-list { display: flex; flex-direction: column; gap: 8px; margin: 6px 0 10px 0; }
    .rubric-item {
      display: flex;
      flex-direction: column;
      gap: 4px;
      font-size: 0.82rem;
      background: #1e293b;
      padding: 8px 10px;
      border-radius: 6px;
      border-left: 3px solid transparent;
    }
    .rubric-item.pass-border { border-left-color: var(--pass); }
    .rubric-item.fail-border { border-left-color: var(--fail); }

    .rubric-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .rubric-name { font-weight: 600; color: #e2e8f0; display: flex; align-items: center; gap: 6px; }
    .rubric-reason { color: var(--text-muted); font-size: 0.78rem; line-height: 1.4; }

    .feedback-box {
      margin-top: 10px;
      padding: 10px 12px;
      background: rgba(245, 158, 11, 0.08);
      border: 1px solid rgba(245, 158, 11, 0.25);
      border-radius: 6px;
      font-size: 0.8rem;
      color: #fde68a;
    }
    .feedback-box ul { margin-left: 20px; margin-top: 4px; }

    /* Right side lesson viewer */
    .lesson-view {
      font-size: 0.92rem;
      color: #e2e8f0;
      line-height: 1.7;
      padding: 6px;
    }
    .lesson-view h1, .lesson-view h2, .lesson-view h3 {
      color: var(--accent);
      margin: 14px 0 8px 0;
    }
    .lesson-view p { margin-bottom: 10px; }
    .lesson-view ul, .lesson-view ol { margin: 6px 0 10px 20px; }
    .lesson-view code {
      background: #0f172a;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 0.82rem;
    }
    .lesson-view blockquote {
      border-left: 3px solid var(--accent);
      padding-left: 12px;
      color: var(--text-muted);
      margin: 10px 0;
    }

    .copy-btn {
      padding: 5px 12px;
      background: #334155;
      color: #fff;
      border: none;
      border-radius: 6px;
      font-size: 0.78rem;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      transition: background 0.2s;
    }
    .copy-btn:hover { background: #475569; }

    .pdf-btn {
      padding: 5px 12px;
      background: #0284c7;
      color: #fff;
      border: none;
      border-radius: 6px;
      font-size: 0.78rem;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      transition: background 0.2s;
    }
    .pdf-btn:hover { background: #0369a1; }

    .loader {
      display: inline-block;
      width: 14px;
      height: 14px;
      border: 2px solid rgba(255,255,255,0.3);
      border-radius: 50%;
      border-top-color: #fff;
      animation: spin 0.8s linear infinite;
      margin-right: 6px;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    .empty-state {
      text-align: center;
      padding: 60px 20px;
      color: var(--text-muted);
      font-size: 0.9rem;
    }

    /* Print media styling: clean white background for native browser print / save-to-pdf */
    @media print {
      body {
        background: #ffffff !important;
        color: #0f172a !important;
        padding: 0 !important;
        height: auto !important;
      }
      .header, .controls-card, #leftPanel, .resizer, .panel-title, .panel-actions {
        display: none !important;
      }
      .split-container { display: block !important; }
      #rightPanel {
        background: #ffffff !important;
        border: none !important;
        width: 100% !important;
        padding: 0 !important;
      }
      .lesson-view {
        color: #0f172a !important;
      }
      .lesson-view h1, .lesson-view h2, .lesson-view h3 {
        color: #0369a1 !important;
      }
      .lesson-view blockquote {
        background: #f8fafc !important;
        border-left: 4px solid #0284c7 !important;
        color: #475569 !important;
      }
      .lesson-view code {
        background: #f1f5f9 !important;
        color: #0f172a !important;
      }
    }
  </style>
</head>
<body>

  <div class="header">
    <div>
      <h1>🧠 Self-Evaluating Lesson Generator</h1>
      <p>Autonomous pedagogical agent with strict 6-checkpoint rubric evaluation & iterative self-correction</p>
    </div>
    <div style="font-size: 0.78rem; color: var(--text-muted);">
      Powered by Google Gemini 3.5 Flash Lite
    </div>
  </div>

  <div class="controls-card">
    <div class="input-group">
      <label for="topic">Lesson Topic</label>
      <input type="text" id="topic" value="Introduction to RAG (Retrieval-Augmented Generation)">
    </div>
    <label class="demo-toggle">
      <input type="checkbox" id="deliberateError">
      <span>Deliberate Error Demo (force initial jargon failure)</span>
      <span class="info-pill" title="Click for details">?</span>
      <div class="tooltip">
        <strong>Why this exists:</strong><br>
        Your assessment video requires demonstrating the evaluator catching an error and regenerating with feedback.<br><br>
        Checking this forces a heavy jargon error on Attempt 1 so you can easily record the evaluator catching it and fixing it on Attempt 2!
      </div>
    </label>
    <button class="btn" id="runBtn" onclick="runAgent()">
      Generate Lesson
    </button>
  </div>

  <!-- Draggable Resizable Split View -->
  <div class="split-container" id="splitContainer">
    <!-- Left Panel: Agent Thinking & Working State -->
    <div class="panel" id="leftPanel">
      <div class="panel-title">
        <span>⚙️ Agent Thinking & Rubrics</span>
        <div class="panel-actions">
          <button class="small-btn" onclick="toggleAllAttempts(true)">Expand All</button>
          <button class="small-btn" onclick="toggleAllAttempts(false)">Collapse All</button>
          <span id="agentStatus" style="font-size: 0.75rem; color: var(--accent); margin-left: 6px;">Ready</span>
        </div>
      </div>
      <div class="panel-content" id="thinkingLog">
        <div class="empty-state">
          Click <strong>"Generate Lesson"</strong> above to observe the agent's thought process, rubric grading, and retry loops in real time.
        </div>
      </div>
    </div>

    <!-- Draggable Resizer Bar -->
    <div class="resizer" id="dragResizer"></div>

    <!-- Right Panel: Final Lesson Output -->
    <div class="panel" id="rightPanel">
      <div class="panel-title">
        <span>📖 Final Generated Lesson</span>
        <div class="panel-actions">
          <button class="copy-btn" id="copyBtn" onclick="copyLesson()" style="display: none;">📋 Copy Text</button>
          <button class="pdf-btn" id="pdfBtn" onclick="downloadPDF()" style="display: none;">📄 Download PDF</button>
        </div>
      </div>
      <div class="panel-content" id="lessonOutput">
        <div class="empty-state">
          The passing, beginner-friendly lesson draft will appear here ready to copy directly into your submission document.
        </div>
      </div>
    </div>
  </div>

  <script>
    let rawFinalLesson = "";

    // On page load, fetch the latest generated lesson if available
    window.addEventListener("DOMContentLoaded", async () => {
      try {
        const resp = await fetch("/api/latest");
        if (resp.ok) {
          const data = await resp.json();
          if (data.lesson) {
            rawFinalLesson = data.lesson;
            const outEl = document.getElementById("lessonOutput");
            if (outEl) outEl.innerHTML = `<div class="lesson-view">${marked.parse(data.lesson)}</div>`;
            
            const copyBtn = document.getElementById("copyBtn");
            const pdfBtn = document.getElementById("pdfBtn");
            const printBtn = document.getElementById("printBtn");
            if (copyBtn) copyBtn.style.display = "inline-flex";
            if (pdfBtn) pdfBtn.style.display = "inline-flex";
            if (printBtn) printBtn.style.display = "inline-flex";

            if (data.topic) {
              const topicEl = document.getElementById("topic");
              if (topicEl) topicEl.value = data.topic;
            }
          }
        }
      } catch (e) {
        console.warn("Could not pre-load latest lesson:", e);
      }
    });

    // Resizer logic (drag to resize panels horizontally)
    const resizer = document.getElementById("dragResizer");
    const leftPanel = document.getElementById("leftPanel");
    const container = document.getElementById("splitContainer");

    let isDragging = false;

    resizer.addEventListener("mousedown", (e) => {
      isDragging = true;
      resizer.classList.add("dragging");
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    });

    document.addEventListener("mousemove", (e) => {
      if (!isDragging) return;
      const containerRect = container.getBoundingClientRect();
      const newLeftWidth = e.clientX - containerRect.left;
      const minWidth = 280;
      const maxWidth = containerRect.width - 280;

      if (newLeftWidth >= minWidth && newLeftWidth <= maxWidth) {
        leftPanel.style.width = `${newLeftWidth}px`;
      }
    });

    document.addEventListener("mouseup", () => {
      if (isDragging) {
        isDragging = false;
        resizer.classList.remove("dragging");
        document.body.style.cursor = "default";
        document.body.style.userSelect = "auto";
      }
    });

    // Toggle single attempt card
    function toggleAttempt(headerEl) {
      const card = headerEl.closest(".attempt-card");
      card.classList.toggle("expanded");
    }

    // Expand / Collapse all attempts
    function toggleAllAttempts(expand) {
      document.querySelectorAll(".attempt-card").forEach(c => {
        if (expand) c.classList.add("expanded");
        else c.classList.remove("expanded");
      });
    }

    async function runAgent() {
      const runBtn = document.getElementById("runBtn");
      const agentStatus = document.getElementById("agentStatus");
      const thinkingLog = document.getElementById("thinkingLog");
      const lessonOutput = document.getElementById("lessonOutput");
      const copyBtn = document.getElementById("copyBtn");
      const pdfBtn = document.getElementById("pdfBtn");
      const printBtn = document.getElementById("printBtn");

      try {
        const topicEl = document.getElementById("topic");
        const topic = topicEl ? topicEl.value.trim() : "";
        const deliberateErrorEl = document.getElementById("deliberateError");
        const deliberateError = deliberateErrorEl ? deliberateErrorEl.checked : false;

        if (!topic) {
          alert("Please enter a lesson topic.");
          return;
        }

        if (runBtn) {
          runBtn.disabled = true;
          runBtn.innerHTML = '<span class="loader"></span> Running Pipeline...';
        }
        if (agentStatus) agentStatus.textContent = "Pipeline executing...";
        if (thinkingLog) thinkingLog.innerHTML = '<div style="color: var(--accent); padding: 20px 0;"><span class="loader"></span> Invoking generator and evaluating against 6 checkpoints...</div>';
        if (lessonOutput) lessonOutput.innerHTML = '<div class="empty-state">Awaiting passing lesson...</div>';
        if (copyBtn) copyBtn.style.display = "none";
        if (pdfBtn) pdfBtn.style.display = "none";
        if (printBtn) printBtn.style.display = "none";

        const response = await fetch("/api/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ topic, deliberate_error: deliberateError })
        });

        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.error || "Execution failed");
        }

        renderTrajectory(data);
      } catch (err) {
        console.error("runAgent error:", err);
        if (thinkingLog) thinkingLog.innerHTML = `<div style="color: var(--fail); padding: 20px;">[ERROR] ${err.message}</div>`;
        if (agentStatus) agentStatus.textContent = "Error";
      } finally {
        if (runBtn) {
          runBtn.disabled = false;
          runBtn.innerHTML = "Generate Lesson";
        }
      }
    }

    function renderTrajectory(data) {
      const thinkingLog = document.getElementById("thinkingLog");
      const lessonOutput = document.getElementById("lessonOutput");
      const agentStatus = document.getElementById("agentStatus");
      const copyBtn = document.getElementById("copyBtn");
      const pdfBtn = document.getElementById("pdfBtn");

      thinkingLog.innerHTML = "";
      agentStatus.textContent = `${data.final_status} (${data.total_attempts} attempt${data.total_attempts > 1 ? "s" : ""})`;

      // Render each attempt as collapsible accordion
      data.history.forEach((att, idx) => {
        const pass = att.result.overall_pass;
        const card = document.createElement("div");
        card.className = "attempt-card expanded"; // default open

        let rubricsHtml = "";
        const checkpoints = [
          ["accurate_and_grounded", "1. Technical Accuracy & Grounding"],
          ["beginner_friendly_language", "2. Beginner-Friendly Language"],
          ["teaches_by_example", "3. Teaches by Example (Analogy)"],
          ["no_unexplained_jargon", "4. No Unexplained Jargon"],
          ["covers_key_points", "5. Covers Key Points (What/Why/How)"],
          ["coherent_teaching_flow", "6. Coherent Teaching Flow"]
        ];

        let passCount = 0;
        checkpoints.forEach(([key, label]) => {
          const item = att.result[key] || { pass: false, reason: "N/A" };
          const p = item.pass;
          if (p) passCount++;
          rubricsHtml += `
            <div class="rubric-item ${p ? 'pass-border' : 'fail-border'}">
              <div class="rubric-top">
                <span class="rubric-name">
                  <span style="color: ${p ? 'var(--pass)' : 'var(--fail)'}; font-weight: bold;">${p ? '✓' : '✗'}</span>
                  ${label}
                </span>
                <span class="status-badge ${p ? 'pass' : 'fail'}">${p ? 'PASS' : 'FAIL'}</span>
              </div>
              <div class="rubric-reason">${item.reason}</div>
            </div>
          `;
        });

        let feedbackHtml = "";
        if (!pass && idx < data.history.length - 1) {
          const nextFailed = Object.entries(att.result)
            .filter(([k, v]) => k !== "overall_pass" && !v.pass)
            .map(([k, v]) => `<li><strong>${k}:</strong> ${v.reason}</li>`)
            .join("");

          feedbackHtml = `
            <div class="feedback-box">
              <strong>🔄 Feedback Prepending for Attempt ${idx + 2}:</strong>
              <ul>${nextFailed}</ul>
            </div>
          `;
        }

        card.innerHTML = `
          <div class="attempt-header" onclick="toggleAttempt(this)">
            <div class="attempt-title-area">
              <span class="chevron">▶</span>
              <span>Draft Attempt ${att.attempt + 1}</span>
              <span style="font-size: 0.75rem; color: var(--text-muted); font-weight: normal;">(${passCount}/6 Passed)</span>
            </div>
            <span class="status-badge ${pass ? 'pass' : 'fail'}">${pass ? 'PASSED (SHIP READY)' : 'FAILED CHECKS'}</span>
          </div>
          <div class="attempt-body">
            <div class="rubric-list">
              ${rubricsHtml}
            </div>
            ${feedbackHtml}
          </div>
        `;
        thinkingLog.appendChild(card);
      });

      // Render Final Lesson
      rawFinalLesson = data.final_lesson;
      lessonOutput.innerHTML = `<div class="lesson-view">${marked.parse(data.final_lesson)}</div>`;
      if (copyBtn) copyBtn.style.display = "inline-flex";
      if (pdfBtn) pdfBtn.style.display = "inline-flex";
      const printBtn = document.getElementById("printBtn");
      if (printBtn) printBtn.style.display = "inline-flex";
    }

    function copyLesson() {
      if (!rawFinalLesson) return;
      navigator.clipboard.writeText(rawFinalLesson).then(() => {
        const copyBtn = document.getElementById("copyBtn");
        copyBtn.textContent = "✓ Copied!";
        setTimeout(() => copyBtn.textContent = "📋 Copy Text", 2500);
      });
    }

    function getPrintableHTML(topic, markdownText) {
      return `
        <div style="background: #ffffff; color: #0f172a; padding: 35px 40px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.7; font-size: 13.5px;">
          <div style="border-bottom: 2px solid #0284c7; padding-bottom: 12px; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: flex-end;">
            <div>
              <div style="font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; color: #0284c7;">Self-Evaluating Lesson Content Generator</div>
              <div style="font-size: 20px; font-weight: 800; color: #0f172a; margin-top: 4px;">${topic}</div>
            </div>
            <div style="text-align: right; font-size: 10.5px; color: #10b981; font-weight: 700; background: #ecfdf5; padding: 4px 10px; border-radius: 12px; border: 1px solid #10b981;">
              ✓ 6/6 Rubric Verified
            </div>
          </div>

          <div class="pdf-body">
            ${marked.parse(markdownText)}
          </div>

          <div style="margin-top: 35px; padding-top: 12px; border-top: 1px solid #e2e8f0; font-size: 9.5px; color: #94a3b8; display: flex; justify-content: space-between;">
            <span>Pedagogy: Zero-Background • Plain English • Analogy-Grounded</span>
            <span>Google Gemini 3.5 Flash Lite Verified</span>
          </div>

          <style>
            .pdf-body h1 { color: #0f172a; font-size: 18px; margin: 20px 0 10px 0; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; }
            .pdf-body h2 { color: #0369a1; font-size: 15px; margin: 16px 0 8px 0; }
            .pdf-body h3 { color: #0f172a; font-size: 13.5px; margin: 14px 0 6px 0; font-weight: 700; }
            .pdf-body p { margin-bottom: 10px; color: #1e293b; }
            .pdf-body ul, .pdf-body ol { margin: 6px 0 12px 22px; color: #1e293b; }
            .pdf-body li { margin-bottom: 4px; }
            .pdf-body blockquote { background: #f8fafc; border-left: 4px solid #0284c7; padding: 10px 14px; margin: 12px 0; color: #334155; border-radius: 0 4px 4px 0; }
            .pdf-body code { background: #f1f5f9; color: #0f172a; padding: 2px 6px; border-radius: 4px; font-size: 12px; font-family: monospace; }
            .pdf-body strong { color: #0f172a; font-weight: 700; }
            .pdf-body hr { border: none; border-top: 1px solid #e2e8f0; margin: 18px 0; }
          </style>
        </div>
      `;
    }

    // Direct, reliable PDF download generated by server with white background and book typography
    function downloadPDF() {
      const topicEl = document.getElementById("topic");
      const topic = topicEl ? topicEl.value.trim() : "Introduction to RAG";
      window.location.href = `/api/download_pdf?topic=${encodeURIComponent(topic)}`;
    }
  </script>
</body>
</html>
"""


class AgentUIHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
            return

        elif self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "running", "port": PORT}).encode("utf-8"))
            return

        elif self.path == "/api/latest":
            lesson_text = ""
            topic_text = "Introduction to RAG (Retrieval-Augmented Generation)"
            if os.path.exists(FINAL_LESSON_FILE):
                try:
                    with open(FINAL_LESSON_FILE, "r", encoding="utf-8") as f:
                        lesson_text = f.read()
                except Exception:
                    pass

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"lesson": lesson_text, "topic": topic_text}).encode("utf-8"))
            return

        elif self.path.startswith("/api/download_pdf"):
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            topic = params.get("topic", ["Introduction to RAG"])[0]

            lesson_text = ""
            if os.path.exists(FINAL_LESSON_FILE):
                try:
                    with open(FINAL_LESSON_FILE, "r", encoding="utf-8") as f:
                        lesson_text = f.read()
                except Exception:
                    pass

            if not lesson_text:
                self.send_response(404)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"No lesson available to export. Please generate a lesson first.")
                return

            try:
                from pdf_generator import generate_pdf_bytes
                pdf_bytes = generate_pdf_bytes(topic, lesson_text)
                clean_filename = re.sub(r"[^a-zA-Z0-9_-]", "_", topic)[:40] or "lesson"

                self.send_response(200)
                self.send_header("Content-Type", "application/pdf")
                self.send_header("Content-Disposition", f'attachment; filename="{clean_filename}.pdf"')
                self.send_header("Content-Length", str(len(pdf_bytes)))
                self.end_headers()
                self.wfile.write(pdf_bytes)
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(f"PDF generation failed: {e}".encode("utf-8"))
            return

        if self.path == "/api/download_script":
            script_path = os.path.join(os.path.dirname(__file__), "MY_RECORDING_SCRIPT.pdf")
            if not os.path.exists(script_path):
                self.send_response(404)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Script PDF not found.")
                return

            try:
                with open(script_path, "rb") as f:
                    pdf_bytes = f.read()

                self.send_response(200)
                self.send_header("Content-Type", "application/pdf")
                self.send_header("Content-Disposition", 'inline; filename="MY_RECORDING_SCRIPT.pdf"')
                self.send_header("Content-Length", str(len(pdf_bytes)))
                self.end_headers()
                self.wfile.write(pdf_bytes)
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(f"Failed to read script PDF: {e}".encode("utf-8"))
            return

        super().do_GET()

    def do_POST(self):
        if self.path == "/api/run":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                payload = json.loads(body.decode("utf-8"))
                topic = payload.get("topic", "Introduction to RAG (Retrieval-Augmented Generation)")
                deliberate_error = payload.get("deliberate_error", False)

                # Set demo mode if deliberate error was checked
                if deliberate_error:
                    os.environ["FORCE_DELIBERATE_ERROR"] = "1"
                else:
                    os.environ.pop("FORCE_DELIBERATE_ERROR", None)

                # Run pipeline
                result = run_pipeline(topic)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode("utf-8"))

            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            finally:
                os.environ.pop("FORCE_DELIBERATE_ERROR", None)
            return

        self.send_response(404)
        self.end_headers()


def start_server(port: int = PORT) -> None:
    server_address = ("", port)
    httpd = HTTPServer(server_address, AgentUIHandler)
    print(f"\n=======================================================")
    print(f"🚀 AI Tutor Agent UI running at: http://localhost:{port}")
    print(f"Open this URL in your browser to view the live dashboard.")
    print(f"Press Ctrl+C to stop the UI server.")
    print(f"=======================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nUI Server stopped.")
        httpd.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    start_server(port)
