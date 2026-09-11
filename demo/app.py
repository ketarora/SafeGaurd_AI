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
    <title>SafeGuard AI — Ops Console</title>
    <!-- Premium sans & mono fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        /* ═══ Core Design System ═══ */
        :root {
            --bg-master:      #ffffff;
            --bg-panel:       #fcfcfc;
            --bg-card:        #ffffff;
            
            --border-subtle:  #f3f4f6;
            --border-base:    #e5e7eb;
            --border-hover:   #d1d5db;
            --border-strong:  #111827;
            
            --text-heading:   #111827;
            --text-body:      #374151;
            --text-muted:     #6b7280;
            --text-ghost:     #9ca3af;
            
            --focus-ring:     rgba(17, 24, 39, 0.1);
            
            /* Semantic */
            --safe-dot:       #10b981;
            --safe-bg:        #ecfdf5;
            --safe-border:    #a7f3d0;
            --safe-text:      #047857;
            
            --warn-dot:       #f59e0b;
            --warn-text:      #b45309;
            
            --critical-dot:   #ef4444;
            --critical-bg:    #fef2f2;
            --critical-border:#fecaca;
            --critical-text:  #b91c1c;

            /* Shadows */
            --shadow-sm:      0 1px 2px rgba(0, 0, 0, 0.04);
            --shadow-md:      0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
            --shadow-lg:      0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.02);
            --shadow-float:   0 20px 25px -5px rgba(0, 0, 0, 0.08), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: 'Inter', -apple-system, system-ui, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background-color: var(--bg-master);
            color: var(--text-body);
            height: 100vh;
            overflow: hidden;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }

        /* ═══ Ultra-Premium Auto-Loader Splash Screen ═══ */
        #splash-screen {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: #ffffff;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            transition: opacity 0.8s cubic-bezier(0.16, 1, 0.3, 1), transform 0.8s cubic-bezier(0.16, 1, 0.3, 1), visibility 0.8s;
            overflow: hidden;
        }

        #splash-screen.hide {
            opacity: 0;
            transform: scale(1.02);
            visibility: hidden;
        }

        .splash-logo-container {
            position: relative;
            display: flex; flex-direction: column; align-items: center;
            animation: floatLogo 4s ease-in-out infinite;
        }

        /* The Custom AI-Shield SVG Logo */
        .brand-logo-svg {
            stroke-dasharray: 150;
            stroke-dashoffset: 150;
            animation: drawShield 1.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
        
        .brand-logo-nodes circle {
            opacity: 0;
            transform: scale(0.5);
            transform-origin: center;
            animation: popNode 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
        }
        
        .brand-logo-nodes path {
            stroke-dasharray: 20;
            stroke-dashoffset: 20;
            animation: drawLink 0.6s ease-out forwards;
        }
        
        .brand-logo-nodes circle:nth-child(1) { animation-delay: 0.8s; } /* Core node */
        .brand-logo-nodes path:nth-child(4) { animation-delay: 1.1s; }   /* Link 1 */
        .brand-logo-nodes circle:nth-child(2) { animation-delay: 1.3s; } /* Escalate node */
        .brand-logo-nodes path:nth-child(5) { animation-delay: 1.4s; }   /* Link 2 */
        .brand-logo-nodes circle:nth-child(3) { animation-delay: 1.6s; } /* Safe node */

        .splash-text {
            font-size: 20px; font-weight: 700; color: var(--text-heading);
            letter-spacing: -0.02em; margin-top: 24px;
            opacity: 0; animation: fadeUpReveal 0.8s ease-out 0.6s forwards;
        }

        .splash-sub {
            font-size: 13px; color: var(--text-muted);
            margin-top: 6px;
            opacity: 0; animation: fadeUpReveal 0.8s ease-out 0.8s forwards;
        }

        .loading-bar-container {
            width: 200px; height: 2px;
            background: var(--border-base);
            border-radius: 2px;
            margin-top: 40px;
            overflow: hidden;
            opacity: 0; animation: fadeIn 0.4s ease-out 1s forwards;
        }

        .loading-bar-fill {
            height: 100%; width: 0;
            background: var(--text-heading);
            border-radius: 2px;
            animation: loadBar 2s cubic-bezier(0.25, 1, 0.5, 1) 1s forwards;
        }

        @keyframes drawShield { to { stroke-dashoffset: 0; } }
        @keyframes popNode { to { opacity: 1; transform: scale(1); } }
        @keyframes drawLink { to { stroke-dashoffset: 0; } }
        @keyframes fadeUpReveal { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes floatLogo { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-4px); } }
        @keyframes loadBar { 0% { width: 0; } 50% { width: 60%; } 100% { width: 100%; } }
        @keyframes fadeIn { to { opacity: 1; } }

        /* ═══ App Skeleton ═══ */
        .app-layout {
            display: grid;
            grid-template-columns: 440px 1fr;
            height: 100vh;
            filter: blur(8px);
            opacity: 0.5;
            transform: scale(0.98);
            transition: all 1s cubic-bezier(0.16, 1, 0.3, 1);
        }
        
        .app-layout.revealed {
            filter: blur(0);
            opacity: 1;
            transform: scale(1);
        }

        /* ═══ LEFT PANEL (Input & Architecture) ═══ */
        .panel-nav {
            background-color: var(--bg-master);
            border-right: 1px solid var(--border-base);
            display: flex;
            flex-direction: column;
            position: relative;
            z-index: 10;
            box-shadow: 1px 0 0 rgba(0,0,0,0.02);
        }

        .nav-header {
            padding: 32px 32px 16px;
        }

        .brand-lockup {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 8px;
        }

        .brand-title {
            font-size: 18px;
            font-weight: 700;
            color: var(--text-heading);
            letter-spacing: -0.02em;
        }

        .nav-desc {
            font-size: 13px;
            color: var(--text-muted);
            line-height: 1.5;
        }

        /* Input Card */
        .input-section {
            padding: 16px 32px;
            flex: 1;
            display: flex;
            flex-direction: column;
        }

        .editor-container {
            background: var(--bg-card);
            border: 1px solid var(--border-base);
            border-radius: 12px;
            box-shadow: var(--shadow-sm);
            transition: all 0.2s ease;
            position: relative;
            display: flex;
            flex-direction: column;
        }

        .editor-container:focus-within {
            border-color: var(--border-strong);
            box-shadow: 0 0 0 3px var(--focus-ring);
        }

        .editor-header {
            padding: 12px 16px;
            border-bottom: 1px solid var(--border-subtle);
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .pulse-dot {
            width: 6px; height: 6px;
            background: var(--safe-dot);
            border-radius: 50%;
            box-shadow: 0 0 0 2px var(--safe-bg);
        }

        textarea.editor-input {
            width: 100%;
            height: 120px;
            border: none;
            padding: 16px;
            font-family: inherit;
            font-size: 14px;
            color: var(--text-heading);
            resize: none;
            background: transparent;
            line-height: 1.6;
        }

        textarea.editor-input::placeholder { color: var(--text-ghost); }
        textarea.editor-input:focus { outline: none; }

        .editor-toolbar {
            padding: 12px 16px;
            border-top: 1px solid var(--border-subtle);
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #fafafa;
            border-bottom-left-radius: 12px;
            border-bottom-right-radius: 12px;
        }

        .demo-chip-group {
            display: flex;
            gap: 6px;
        }

        .demo-chip {
            background: var(--bg-card);
            border: 1px solid var(--border-base);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 500;
            color: var(--text-body);
            cursor: pointer;
            transition: all 0.15s;
            box-shadow: var(--shadow-sm);
        }

        .demo-chip:hover {
            border-color: var(--border-hover);
            color: var(--text-heading);
            transform: translateY(-1px);
        }

        .btn-primary {
            background: var(--text-heading);
            color: #fff;
            border: none;
            height: 32px;
            padding: 0 16px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            box-shadow: var(--shadow-sm);
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .btn-primary:hover {
            background: #000;
            transform: translateY(-1px);
            box-shadow: var(--shadow-md);
        }
        
        .btn-primary:active { transform: translateY(0); }
        .btn-primary:disabled { opacity: 0.5; cursor: wait; transform: none; box-shadow: none; }

        /* Architecture Map */
        .arch-map {
            padding: 32px;
            margin-top: auto;
            border-top: 1px solid var(--border-subtle);
            background: var(--bg-panel);
        }

        .arch-title {
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-ghost);
            margin-bottom: 20px;
        }

        .arch-list {
            display: flex;
            flex-direction: column;
            gap: 0;
            position: relative;
        }

        /* Connecting line */
        .arch-list::before {
            content: '';
            position: absolute;
            left: 10px;
            top: 12px;
            bottom: 12px;
            width: 2px;
            background: var(--border-base);
            z-index: 0;
        }

        .arch-node {
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 12px 0;
            position: relative;
            z-index: 1;
        }

        .node-circle {
            width: 22px; height: 22px;
            border-radius: 50%;
            background: var(--bg-card);
            border: 2px solid var(--text-ghost);
            display: flex; align-items: center; justify-content: center;
            transition: all 0.3s;
        }

        .node-circle.active {
            border-color: var(--text-heading);
            background: var(--text-heading);
        }
        
        .node-circle.active::after {
            content: '';
            width: 6px; height: 6px;
            background: #fff;
            border-radius: 50%;
        }

        .node-label {
            font-size: 13px;
            font-weight: 500;
            color: var(--text-body);
        }
        
        .node-label.active {
            font-weight: 600;
            color: var(--text-heading);
        }

        .node-meta {
            margin-left: auto;
            font-size: 11px;
            font-family: 'JetBrains Mono', monospace;
            color: var(--text-ghost);
            background: var(--border-subtle);
            padding: 2px 6px;
            border-radius: 4px;
        }


        /* ═══ RIGHT PANEL (Results Feed) ═══ */
        .panel-content {
            background-color: var(--bg-panel);
            overflow-y: auto;
            padding: 0;
            position: relative;
        }

        .content-scroll-area {
            padding: 48px;
            max-width: 800px;
            margin: 0 auto;
        }

        /* 3D Animated Empty State */
        .empty-canvas {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            text-align: center;
        }

        /* Glassmorphic 3D Cube */
        .cube-wrapper {
            width: 120px; height: 120px;
            perspective: 800px;
            margin-bottom: 40px;
            display: flex; align-items: center; justify-content: center;
        }

        .cube {
            width: 60px; height: 60px;
            position: relative;
            transform-style: preserve-3d;
            animation: rotateCube 8s linear infinite;
        }
        
        .cube-face {
            position: absolute;
            width: 60px; height: 60px;
            border: 2px solid rgba(17, 24, 39, 0.1);
            background: rgba(255, 255, 255, 0.6);
            backdrop-filter: blur(8px);
            display: flex; align-items: center; justify-content: center;
        }
        
        .cube-face.front  { transform: rotateY(  0deg) translateZ(30px); }
        .cube-face.right  { transform: rotateY( 90deg) translateZ(30px); }
        .cube-face.back   { transform: rotateY(180deg) translateZ(30px); }
        .cube-face.left   { transform: rotateY(-90deg) translateZ(30px); }
        .cube-face.top    { transform: rotateX( 90deg) translateZ(30px); }
        .cube-face.bottom { transform: rotateX(-90deg) translateZ(30px); }

        .cube-core {
            position: absolute;
            width: 16px; height: 16px;
            background: var(--text-heading);
            border-radius: 4px;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            box-shadow: 0 0 30px rgba(17,24,39,0.3);
        }

        @keyframes rotateCube {
            0%   { transform: rotateX(-20deg) rotateY(0deg); }
            100% { transform: rotateX(-20deg) rotateY(360deg); }
        }

        .empty-text {
            font-size: 16px;
            font-weight: 600;
            color: var(--text-heading);
            margin-bottom: 8px;
        }

        .empty-subtext {
            font-size: 14px;
            color: var(--text-muted);
            max-width: 300px;
            line-height: 1.5;
        }

        /* Diagnostics Feed */
        .feed-header {
            display: none;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 32px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border-base);
        }
        
        .feed-header.visible {
            display: flex;
            animation: slideDown 0.4s ease forwards;
        }

        .feed-title {
            font-size: 18px;
            font-weight: 600;
            color: var(--text-heading);
            letter-spacing: -0.01em;
        }

        .feed-meta {
            font-size: 12px;
            font-family: 'JetBrains Mono', monospace;
            color: var(--text-muted);
        }

        /* Stage Cards - Controlled by JS Guided Steps */
        .metric-card {
            background: var(--bg-card);
            border: 1px solid var(--border-base);
            border-radius: 12px;
            margin-bottom: 24px;
            box-shadow: var(--shadow-sm);
            display: none; 
        }

        .metric-card.visible {
            display: block;
            animation: slideUpSpring 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }

        .metric-header {
            padding: 16px 24px;
            border-bottom: 1px solid var(--border-subtle);
            display: flex;
            align-items: center;
            gap: 12px;
            background: #fdfdfd;
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
        }

        .step-index {
            width: 24px; height: 24px;
            border-radius: 6px;
            background: var(--border-subtle);
            color: var(--text-muted);
            font-size: 12px;
            font-weight: 600;
            display: flex; align-items: center; justify-content: center;
            font-family: 'JetBrains Mono', monospace;
        }

        .metric-title {
            font-size: 14px;
            font-weight: 600;
            color: var(--text-heading);
            flex: 1;
        }
        
        .metric-status {
            font-size: 11px;
            font-weight: 600;
            padding: 4px 10px;
            border-radius: 100px;
            letter-spacing: 0.02em;
        }
        
        .status-neutral { background: var(--border-subtle); color: var(--text-body); }
        .status-good { background: var(--safe-bg); color: var(--safe-text); border: 1px solid var(--safe-border); }
        .status-bad { background: var(--critical-bg); color: var(--critical-text); border: 1px solid var(--critical-border); }

        .metric-body {
            padding: 0;
        }

        /* Key-Value Rows */
        .kv-table {
            width: 100%;
            border-collapse: collapse;
        }

        .kv-row {
            display: flex;
            padding: 16px 24px;
            border-bottom: 1px solid var(--border-subtle);
        }
        
        .kv-row:last-child {
            border-bottom: none;
        }

        .kv-key {
            width: 140px;
            font-size: 13px;
            font-weight: 500;
            color: var(--text-muted);
            flex-shrink: 0;
        }

        .kv-val {
            flex: 1;
            font-size: 14px;
            color: var(--text-heading);
        }

        .kv-val.mono {
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
            line-height: 1.5;
        }
        
        .kv-val.prose {
            line-height: 1.6;
            color: var(--text-body);
        }

        /* Custom UI Micro-components */
        .confidence-meter {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .cm-track {
            flex: 1;
            height: 6px;
            background: var(--border-base);
            border-radius: 3px;
            overflow: hidden;
            max-width: 200px;
        }

        .cm-fill {
            height: 100%;
            border-radius: 3px;
            transition: width 1s cubic-bezier(0.16, 1, 0.3, 1);
        }

        /* Document/Precedent Card inside body */
        .doc-list {
            padding: 16px 24px;
            background: var(--bg-panel);
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .doc-item {
            background: var(--bg-card);
            border: 1px solid var(--border-base);
            border-radius: 8px;
            padding: 16px;
            display: flex;
            gap: 16px;
            transition: box-shadow 0.2s;
        }
        
        .doc-item:hover { box-shadow: var(--shadow-sm); border-color: var(--border-hover); }

        .doc-meta {
            width: 60px;
            flex-shrink: 0;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        
        .doc-score {
            font-family: 'JetBrains Mono', monospace;
            font-size: 14px;
            font-weight: 600;
            color: var(--safe-dot);
        }
        
        .doc-id {
            font-family: 'JetBrains Mono', monospace;
            font-size: 10px;
            color: var(--text-ghost);
        }

        .doc-text {
            font-size: 13px;
            line-height: 1.6;
            color: var(--text-body);
        }

        /* Code/Blockquote area */
        .code-block-wrapper {
            padding: 16px 24px;
        }
        
        .code-block {
            background: var(--text-heading);
            color: #fff;
            padding: 20px;
            border-radius: 8px;
            font-size: 13px;
            line-height: 1.6;
            position: relative;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.5);
        }
        
        .code-label {
            position: absolute;
            top: 0; right: 20px;
            transform: translateY(-50%);
            background: var(--border-strong);
            color: #fff;
            font-size: 10px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 100px;
            letter-spacing: 0.1em;
            text-transform: uppercase;
        }

        /* Alert Box */
        .alert-box {
            margin: 16px 24px 0;
            padding: 16px;
            background: var(--critical-bg);
            border: 1px solid var(--critical-border);
            border-radius: 8px;
            display: flex;
            gap: 12px;
            align-items: flex-start;
        }
        
        .alert-box svg { color: var(--critical-text); flex-shrink: 0; }
        
        .alert-box div h4 {
            font-size: 13px;
            font-weight: 600;
            color: var(--critical-text);
            margin-bottom: 4px;
        }
        
        .alert-box div p {
            font-size: 13px;
            color: var(--critical-text);
            line-height: 1.5;
            opacity: 0.9;
        }

        /* Loading Overlay for Trace Execution */
        .loading-overlay {
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(252,252,252,0.8);
            backdrop-filter: blur(2px);
            z-index: 50;
            display: none;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            gap: 16px;
        }
        
        .loading-overlay.active { display: flex; }
        
        .spinner {
            width: 24px; height: 24px;
            border: 3px solid var(--border-base);
            border-top-color: var(--text-heading);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }

        /* Step progression button */
        .step-next-container {
            display: none;
            justify-content: flex-end;
            margin-top: 16px;
            margin-bottom: 32px;
        }

        .step-next-container.visible {
            display: flex;
            animation: slideUpSpring 0.4s ease forwards;
        }
        
        .btn-next-step {
            background: #fff;
            border: 1px solid var(--border-base);
            color: var(--text-heading);
            padding: 10px 20px;
            border-radius: 100px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            box-shadow: var(--shadow-sm);
            transition: 0.2s;
        }

        .btn-next-step:hover {
            background: #fafafa;
            border-color: var(--border-hover);
            transform: translateY(-1px);
            box-shadow: var(--shadow-md);
        }

        @keyframes slideDown { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes slideUpSpring { 
            0% { opacity: 0; transform: translateY(20px); } 
            100% { opacity: 1; transform: translateY(0); } 
        }
        @keyframes spin { to { transform: rotate(360deg); } }

    </style>
</head>
<body>
    
    <!-- ═══ ULTRA-CLEAN AUTO-LOADER SPLASH SCREEN ═══ -->
    <div id="splash-screen">
        <div class="splash-logo-container">
            <!-- Professional Custom "AI Routing Shield" SVG Logo -->
            <svg width="72" height="72" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" class="brand-logo-svg">
                <!-- Outer minimal shield -->
                <path d="M24 6L6 14V26C6 36 14 42 24 46C34 42 42 36 42 26V14L24 6Z" stroke="#111827" stroke-width="3" stroke-linejoin="round" />
                <!-- Inner Neural Routes -->
                <g class="brand-logo-nodes">
                    <circle cx="24" cy="20" r="4" fill="#111827"/>
                    <circle cx="16" cy="30" r="3" fill="#111827"/>
                    <circle cx="32" cy="30" r="3" fill="#10B981"/> <!-- Green safe path -->
                    <path d="M22 23L17 28" stroke="#111827" stroke-width="2.5" stroke-linecap="round"/>
                    <path d="M26 23L31 28" stroke="#111827" stroke-width="2.5" stroke-linecap="round"/>
                </g>
            </svg>
            <div class="splash-text">SafeGuard AI</div>
            <div class="splash-sub">Booting securely...</div>
        </div>
        
        <div class="loading-bar-container">
            <div class="loading-bar-fill"></div>
        </div>
    </div>

    <!-- ═══ MAIN APP LAYOUT ═══ -->
    <div class="app-layout" id="main-app">
        
        <!-- ═══ LEFT PANEL ═══ -->
        <nav class="panel-nav">
            <div class="nav-header">
                <div class="brand-lockup">
                    <div class="logo-box">
                        <!-- Tiny clean version of the logo for nav -->
                        <svg width="22" height="22" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M24 6L6 14V26C6 36 14 42 24 46C34 42 42 36 42 26V14L24 6Z" stroke="#111827" stroke-width="4" stroke-linejoin="round" />
                            <circle cx="24" cy="20" r="4" fill="#111827"/>
                            <circle cx="16" cy="30" r="3" fill="#111827"/>
                            <circle cx="32" cy="30" r="3" fill="#10B981"/>
                            <path d="M22 23L17 28" stroke="#111827" stroke-width="3" stroke-linecap="round"/>
                            <path d="M26 23L31 28" stroke="#111827" stroke-width="3" stroke-linecap="round"/>
                        </svg>
                    </div>
                    <div class="brand-title">SafeGuard AI</div>
                </div>
                <p class="nav-desc">Operations dashboard for autonomous support routing and safety classification.</p>
            </div>

            <form method="POST" id="main-form" class="input-section">
                <div class="editor-container">
                    <div class="editor-header">
                        <div class="pulse-dot"></div> Live Analysis Environment
                    </div>
                    <textarea name="message" id="input-msg" class="editor-input" placeholder="Paste a customer support tweet to trace the decision pipeline..." required>{{ message }}</textarea>
                    
                    <div class="editor-toolbar">
                        <div class="demo-chip-group">
                            <button type="button" class="demo-chip" data-txt="Driver was totally erratic, ran a red light and I felt incredibly unsafe @Uber_Support">Safety 🚨</button>
                            <button type="button" class="demo-chip" data-txt="Applied SAVE20 promo but was still charged full price on my trip @Uber_Support">Promo 🎟️</button>
                        </div>
                        <button type="submit" class="btn-primary" id="btn-submit">
                            Run Trace
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                        </button>
                    </div>
                </div>
            </form>

            <div class="arch-map">
                <div class="arch-title">Pipeline Architecture</div>
                <div class="arch-list">
                    <div class="arch-node">
                        <div class="node-circle" id="node-1"></div>
                        <div class="node-label" id="label-1">Intent Classification</div>
                        <div class="node-meta">Classifier</div>
                    </div>
                    <div class="arch-node">
                        <div class="node-circle" id="node-2"></div>
                        <div class="node-label" id="label-2">Precedent Retrieval</div>
                        <div class="node-meta">Vector DB</div>
                    </div>
                    <div class="arch-node">
                        <div class="node-circle" id="node-3"></div>
                        <div class="node-label" id="label-3">Routing Decision</div>
                        <div class="node-meta">Escalator</div>
                    </div>
                </div>
            </div>
        </nav>

        <!-- ═══ RIGHT PANEL ═══ -->
        <main class="panel-content" id="scroll-target">
            
            <div class="loading-overlay" id="loader">
                <div class="spinner"></div>
                <div style="font-size:13px; font-weight:500; color:var(--text-muted);">Executing pipeline trace...</div>
            </div>

            {% if not result %}
            <div class="empty-canvas">
                <div class="cube-wrapper">
                    <div class="cube">
                        <div class="cube-face front"></div>
                        <div class="cube-face back"></div>
                        <div class="cube-face right"></div>
                        <div class="cube-face left"></div>
                        <div class="cube-face top"></div>
                        <div class="cube-face bottom"></div>
                        <div class="cube-core"></div>
                    </div>
                </div>
                <div class="empty-text">Awaiting input stream</div>
                <div class="empty-subtext">Submit a customer payload from the editor to inspect the multi-stage neural routing decisions.</div>
            </div>
            {% else %}
            <div class="content-scroll-area">
                
                <div class="feed-header" id="feed-header">
                    <h2 class="feed-title">Execution Trace</h2>
                    <span class="feed-meta">ID: trc_req_0x{{ range(1000, 9999)|random }}</span>
                </div>

                <!-- Stage 1 -->
                <div class="metric-card" id="card-1">
                    <div class="metric-header">
                        <div class="step-index">1</div>
                        <div class="metric-title">Intent Classification</div>
                        <div class="metric-status status-neutral">DONE</div>
                    </div>
                    <div class="metric-body">
                        <div class="kv-table">
                            <div class="kv-row">
                                <div class="kv-key">Detected class</div>
                                <div class="kv-val mono">{{ result.classification.intent }}</div>
                            </div>
                            <div class="kv-row">
                                <div class="kv-key">Confidence score</div>
                                <div class="kv-val">
                                    {% set conf = (result.classification.confidence * 100)|round(1) %}
                                    <div class="confidence-meter">
                                        <div class="cm-track">
                                            <div class="cm-fill" style="width: {{ conf }}%; background: {% if conf >= 70 %}var(--safe-dot){% elif conf >= 40 %}var(--warn-dot){% else %}var(--critical-dot){% endif %};"></div>
                                        </div>
                                        <span class="mono" style="font-size: 13px;">{{ conf }}%</span>
                                    </div>
                                </div>
                            </div>
                            <div class="kv-row">
                                <div class="kv-key">LLM Reasoning</div>
                                <div class="kv-val prose">{{ result.classification.reasoning }}</div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Interactive "Next" Button -->
                <div class="step-next-container" id="next-1">
                    <button class="btn-next-step" onclick="revealStep(2)">
                        Proceed to Memory Retrieval &rarr;
                    </button>
                </div>

                <!-- Stage 2 -->
                <div class="metric-card" id="card-2">
                    <div class="metric-header">
                        <div class="step-index">2</div>
                        <div class="metric-title">Precedent Retrieval & Synthesis</div>
                        <div class="metric-status {% if result.draft.grounding_quality == 'strong' %}status-good{% elif result.draft.grounding_quality == 'moderate' %}status-neutral{% else %}status-bad{% endif %}" style="font-family:'JetBrains Mono', monospace; font-size:10px;">
                            GROUNDING: {{ result.draft.grounding_quality | upper }}
                        </div>
                    </div>
                    <div class="metric-body">
                        <div class="doc-list">
                            {% for p in result.draft.precedents %}
                            <div class="doc-item">
                                <div class="doc-meta">
                                    <span class="doc-score">{{ (p.similarity * 100)|round(0)|int }}%</span>
                                    <span class="doc-id">{{ p.id }}</span>
                                </div>
                                <div class="doc-text">{{ p.brand_reply }}</div>
                            </div>
                            {% else %}
                            <div style="padding: 24px; text-align:center; color:var(--text-ghost); font-size:13px; font-family:'JetBrains Mono', monospace;">
                                NULL: No precedents cleared similarity thresholds.
                            </div>
                            {% endfor %}
                        </div>
                        
                        <div class="code-block-wrapper">
                            <div class="code-block">
                                <div class="code-label">Synthesized Draft</div>
                                {{ result.draft.draft_reply }}
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Interactive "Next" Button -->
                <div class="step-next-container" id="next-2">
                    <button class="btn-next-step" onclick="revealStep(3)">
                        Evaluate Escalation Rules &rarr;
                    </button>
                </div>

                <!-- Stage 3 -->
                <div class="metric-card" id="card-3">
                    <div class="metric-header">
                        <div class="step-index">3</div>
                        <div class="metric-title">Routing Decision</div>
                        <div class="metric-status {% if result.escalation.decision == 'escalate' %}status-bad{% else %}status-good{% endif %}">
                            {{ result.escalation.decision | upper }}
                        </div>
                    </div>
                    <div class="metric-body">
                        
                        {% if result.escalation.hard_rule_triggered %}
                        <div class="alert-box">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                            <div>
                                <h4>Deterministic Safety Guardrail Engaged</h4>
                                <p>This escalation was enforced by hard-coded system rules, superseding LLM logic due to safety keywords and intent classifications.</p>
                            </div>
                        </div>
                        {% endif %}

                        <div class="kv-table">
                            <div class="kv-row">
                                <div class="kv-key">Decision context</div>
                                <div class="kv-val prose">{{ result.escalation.reason }}</div>
                            </div>
                        </div>
                    </div>
                </div>
                
            </div>
            {% endif %}
        </main>
    </div>

    <script>
        // Apple/Vercel Auto-Loader Session Logic
        window.addEventListener('DOMContentLoaded', () => {
            const hasResult = {{ 'true' if result else 'false' }};
            const splash = document.getElementById('splash-screen');
            const appLayout = document.getElementById('main-app');

            // If we are viewing a result, bypass the loader entirely
            if (hasResult) {
                splash.style.transition = 'none';
                splash.style.display = 'none';
                appLayout.style.transition = 'none';
                appLayout.classList.add('revealed');
            } else {
                // Force play splash intro for 3 seconds on fresh load, then natively fade out.
                setTimeout(() => {
                    splash.classList.add('hide');
                    appLayout.classList.add('revealed');
                    
                    // Actually remove it from flow after fade
                    setTimeout(() => {
                        splash.style.display = 'none';
                    }, 800);
                }, 3000);
            }
        });

        // Preset inputs
        document.querySelectorAll('.demo-chip').forEach(btn => {
            btn.addEventListener('click', () => {
                const ta = document.getElementById('input-msg');
                ta.value = btn.dataset.txt;
                ta.focus();
            });
        });

        // Form submission loading state
        document.getElementById('main-form').addEventListener('submit', () => {
            const btn = document.getElementById('btn-submit');
            btn.disabled = true;
            btn.innerHTML = 'Running...';
            document.getElementById('loader').classList.add('active');
        });

        // Interactive Guided Step Logic
        function revealStep(stepNum) {
            // Hide the previous next button
            const prevNextBtn = document.getElementById(`next-${stepNum - 1}`);
            if (prevNextBtn) prevNextBtn.classList.remove('visible');

            const card = document.getElementById(`card-${stepNum}`);
            if (card) {
                card.classList.add('visible');
                
                // Highlight architecture map
                document.getElementById(`node-${stepNum}`).classList.add('active');
                document.getElementById(`label-${stepNum}`).classList.add('active');
                
                card.scrollIntoView({ behavior: 'smooth', block: 'end' });
            }

            // Bring in the next step button if one exists
            const nextBtn = document.getElementById(`next-${stepNum}`);
            if (nextBtn) {
                setTimeout(() => nextBtn.classList.add('visible'), 500); 
            }
        }

        // On load tracing reveal
        window.addEventListener('load', () => {
            const hasResult = {{ 'true' if result else 'false' }};
            if (hasResult) {
                document.getElementById('feed-header').classList.add('visible');
                // Automatically show the first step after a tiny delay
                setTimeout(() => revealStep(1), 300);
            }
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
