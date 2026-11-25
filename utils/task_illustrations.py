"""Rich, colorful SVG vector graphics and illustrations tailored for Restart's ADHD task companion."""

def get_task_illustration(kind: str, width: int = 140, height: int = 110) -> str:
    """Returns standalone colorful vector illustrations of task management concepts."""
    
    if kind == "decomposer":
        # Multi-page dense brief magically decomposed into 3 clean ordered task cards
        return f"""<svg width="{width}" height="{height}" viewBox="0 0 160 120" fill="none" xmlns="http://www.w3.org/2000/svg">
            <!-- Background glow -->
            <rect x="10" y="10" width="140" height="100" rx="16" fill="#FFF0F1"/>
            <!-- Vague dense brief in background -->
            <rect x="22" y="24" width="45" height="60" rx="6" fill="#F87171" fill-opacity="0.2" stroke="#EF4444" stroke-width="1.5" stroke-dasharray="3 3"/>
            <line x1="28" y1="34" x2="58" y2="34" stroke="#DC2626" stroke-width="2" stroke-linecap="round"/>
            <line x1="28" y1="42" x2="52" y2="42" stroke="#DC2626" stroke-width="2" stroke-linecap="round"/>
            <line x1="28" y1="50" x2="60" y2="50" stroke="#DC2626" stroke-width="2" stroke-linecap="round"/>
            <line x1="28" y1="58" x2="48" y2="58" stroke="#DC2626" stroke-width="2" stroke-linecap="round"/>
            
            <!-- Transforming magic arrow -->
            <path d="M72 54 L84 54 M80 49 L85 54 L80 59" stroke="#EA580C" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
            
            <!-- Crisp decomposed steps stack -->
            <g filter="drop-shadow(0px 4px 8px rgba(220, 38, 38, 0.12))">
                <rect x="92" y="22" width="54" height="24" rx="6" fill="#FFFFFF" stroke="#FCA5A5" stroke-width="1.5"/>
                <circle cx="102" cy="34" r="5" fill="#FEE2E2"/>
                <text x="100" y="37" font-family="'JetBrains Mono', monospace" font-size="7" font-weight="bold" fill="#DC2626">1</text>
                <line x1="112" y1="34" x2="136" y2="34" stroke="#475569" stroke-width="2.5" stroke-linecap="round"/>

                <rect x="92" y="50" width="54" height="24" rx="6" fill="#FFFFFF" stroke="#FCA5A5" stroke-width="1.5"/>
                <circle cx="102" cy="62" r="5" fill="#FEE2E2"/>
                <text x="100" y="65" font-family="'JetBrains Mono', monospace" font-size="7" font-weight="bold" fill="#DC2626">2</text>
                <line x1="112" y1="62" x2="132" y2="62" stroke="#475569" stroke-width="2.5" stroke-linecap="round"/>

                <rect x="92" y="78" width="54" height="24" rx="6" fill="#FFFFFF" stroke="#FCA5A5" stroke-width="1.5"/>
                <circle cx="102" cy="90" r="5" fill="#FEE2E2"/>
                <text x="100" y="93" font-family="'JetBrains Mono', monospace" font-size="7" font-weight="bold" fill="#DC2626">3</text>
                <line x1="112" y1="90" x2="138" y2="90" stroke="#475569" stroke-width="2.5" stroke-linecap="round"/>
            </g>
            <!-- Sparkle -->
            <path d="M78 28 L79.5 32.5 L84 34 L79.5 35.5 L78 40 L76.5 35.5 L72 34 L76.5 32.5 Z" fill="#EA580C"/>
        </svg>"""

    elif kind == "start_mode":
        # Giant 2-minute activation target with one clean highlighted path
        return f"""<svg width="{width}" height="{height}" viewBox="0 0 160 120" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="10" y="10" width="140" height="100" rx="16" fill="#EFF6FF"/>
            <!-- Concentric pulse rings -->
            <circle cx="80" cy="58" r="44" stroke="#BFDBFE" stroke-width="1.5" stroke-dasharray="4 4"/>
            <circle cx="80" cy="58" r="32" fill="#DBEAFE" fill-opacity="0.5" stroke="#93C5FD" stroke-width="1.5"/>
            <circle cx="80" cy="58" r="20" fill="#2563EB"/>
            
            <!-- Target play icon & micro badge -->
            <polygon points="76,51 88,58 76,65" fill="#FFFFFF"/>
            
            <g filter="drop-shadow(0px 3px 6px rgba(37, 99, 235, 0.2))">
                <rect x="42" y="86" width="76" height="20" rx="10" fill="#1D4ED8"/>
                <text x="80" y="99" font-family="'Plus Jakarta Sans', sans-serif" font-size="8.5" font-weight="700" fill="#FFFFFF" text-anchor="middle">⚡ 2-MIN START</text>
            </g>
            
            <!-- Lightning sparks -->
            <path d="M40 36 L44 42 L41 43 L46 50" stroke="#2563EB" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M120 36 L116 42 L119 43 L114 50" stroke="#2563EB" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>"""

    elif kind == "interruption":
        # Cognitive Shield preserving active notes from incoming distraction waves
        return f"""<svg width="{width}" height="{height}" viewBox="0 0 160 120" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="10" y="10" width="140" height="100" rx="16" fill="#FEF2F2"/>
            <!-- Distraction bolts bouncing off shield -->
            <path d="M22 35 Q 40 45 48 54" stroke="#DC2626" stroke-width="2" stroke-linecap="round" stroke-dasharray="3 3"/>
            <path d="M22 75 Q 38 65 48 60" stroke="#DC2626" stroke-width="2" stroke-linecap="round" stroke-dasharray="3 3"/>
            
            <!-- Protective glowing shield -->
            <g filter="drop-shadow(0px 4px 10px rgba(220, 38, 38, 0.18))">
                <path d="M80 24 C 62 24 54 32 54 44 C 54 68 80 88 80 88 C 80 88 106 68 106 44 C 106 32 98 24 80 24 Z" fill="#DC2626"/>
            </g>
            
            <!-- Inner preserved notebook page -->
            <rect x="68" y="38" width="24" height="30" rx="4" fill="#FFFFFF"/>
            <line x1="73" y1="45" x2="87" y2="45" stroke="#991B1B" stroke-width="1.8" stroke-linecap="round"/>
            <line x1="73" y1="51" x2="84" y2="51" stroke="#991B1B" stroke-width="1.8" stroke-linecap="round"/>
            <line x1="73" y1="57" x2="88" y2="57" stroke="#991B1B" stroke-width="1.8" stroke-linecap="round"/>
            
            <!-- Floating lock pin -->
            <circle cx="80" cy="74" r="5" fill="#FEF2F2"/>
            <circle cx="80" cy="74" r="2.5" fill="#DC2626"/>

            <rect x="44" y="93" width="72" height="18" rx="9" fill="#991B1B"/>
            <text x="80" y="105" font-family="'Plus Jakarta Sans', sans-serif" font-size="8" font-weight="700" fill="#FFFFFF" text-anchor="middle">STATE FROZEN</text>
        </svg>"""

    elif kind == "context_restore":
        # Brain restoring the train of thought directly into the active document
        return f"""<svg width="{width}" height="{height}" viewBox="0 0 160 120" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="10" y="10" width="140" height="100" rx="16" fill="#F0FDF4"/>
            <!-- Synapse & memory rings -->
            <circle cx="80" cy="50" r="32" stroke="#86EFAC" stroke-width="1.5" stroke-dasharray="3 3"/>
            
            <!-- Stylized Brain Continuity Icon -->
            <g filter="drop-shadow(0px 4px 8px rgba(22, 163, 74, 0.18))">
                <rect x="52" y="26" width="56" height="50" rx="14" fill="#16A34A"/>
                <!-- Synapse nodes inside brain -->
                <circle cx="68" cy="42" r="4" fill="#DCFCE7"/>
                <circle cx="92" cy="42" r="4" fill="#DCFCE7"/>
                <circle cx="80" cy="58" r="4" fill="#DCFCE7"/>
                <line x1="68" y1="42" x2="80" y2="58" stroke="#DCFCE7" stroke-width="2"/>
                <line x1="92" y1="42" x2="80" y2="58" stroke="#DCFCE7" stroke-width="2"/>
            </g>
            
            <!-- Resume badge -->
            <rect x="40" y="86" width="80" height="20" rx="10" fill="#15803D"/>
            <text x="80" y="99.5" font-family="'Plus Jakarta Sans', sans-serif" font-size="8.5" font-weight="700" fill="#FFFFFF" text-anchor="middle">1-CLICK RESUME →</text>
            
            <!-- Star spark -->
            <path d="M124 24 L125.5 28.5 L130 30 L125.5 31.5 L124 36 L122.5 31.5 L118 30 L122.5 28.5 Z" fill="#16A34A"/>
        </svg>"""

    return ""
