"""Generate the Agentix Platform diagrams — dark and light variants.

A single geometry source of truth feeds two palettes, so the dark and
light variants can never drift out of alignment. Regenerate after any
layout change:

    python docs/diagrams/generate.py

Outputs: architecture.svg, architecture-light.svg,
         request-flow.svg, request-flow-light.svg
"""

from pathlib import Path

OUT = Path(__file__).resolve().parent

M = "\u00b7"        # middle dot
EM = "\u2014"       # em dash
AR = "\u2192"       # rightwards arrow

FONT = "'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif"

PALETTES = {
    "dark": {
        "bg": ("#0B0E17", "#080A10"),
        "grad": ("#A78BFA", "#E879F9", "#22D3EE"),
        "glow": ("#A78BFA", "0.10"),
        "subtitle": "#9AA7BC",
        "muted": "#5F6E86",
        "footer": "#4E5B70",
        "band_fill_op": "0.04",
        "band_border_op": "0.18",
        "box_fill": "rgba(255,255,255,0.028)",
        "box_border_op": "0.35",
        "box_title": "#E7ECF4",
        "box_sub": "#93A1B8",
        "edge_label": "#7A8AA0",
        "chip_fill": "#141A26",
        "chip_num": "#E7ECF4",
        "syn_fill": "rgba(167,139,250,0.05)",
        "syn_mod_fill": "rgba(167,139,250,0.07)",
        "syn_mod_border": "rgba(167,139,250,0.45)",
        "syn_sub": "#B9A8E8",
        "mod_title": "#EDE9FE",
        "capsule_fill": "rgba(167,139,250,0.08)",
        "capsule_border": "rgba(167,139,250,0.25)",
        "capsule_text": "#C4B5FD",
        "accents": {
            "blue": "#60A5FA",
            "cyan": "#22D3EE",
            "violet": "#A78BFA",
            "amber": "#FBBF24",
            "emerald": "#34D399",
            "rose": "#FB7185",
            "slate": "#94A3B8",
        },
    },
    "light": {
        "bg": ("#FFFFFF", "#F3F5FA"),
        "grad": ("#7C3AED", "#DB2777", "#0891B2"),
        "glow": ("#7C3AED", "0.08"),
        "subtitle": "#55617A",
        "muted": "#8A94A8",
        "footer": "#9AA3B5",
        "band_fill_op": "0.07",
        "band_border_op": "0.30",
        "box_fill": "rgba(255,255,255,0.78)",
        "box_border_op": "0.45",
        "box_title": "#17203A",
        "box_sub": "#4A5872",
        "edge_label": "#66748C",
        "chip_fill": "#FFFFFF",
        "chip_num": "#17203A",
        "syn_fill": "rgba(124,58,237,0.05)",
        "syn_mod_fill": "rgba(255,255,255,0.85)",
        "syn_mod_border": "rgba(124,58,237,0.45)",
        "syn_sub": "#6D5BA8",
        "mod_title": "#3B2E6E",
        "capsule_fill": "rgba(124,58,237,0.08)",
        "capsule_border": "rgba(124,58,237,0.30)",
        "capsule_text": "#5B21B6",
        "accents": {
            "blue": "#2563EB",
            "cyan": "#0891B2",
            "violet": "#7C3AED",
            "amber": "#D97706",
            "emerald": "#059669",
            "rose": "#E11D48",
            "slate": "#64748B",
        },
    },
}


def hex_rgba(hex_color: str, op: str) -> str:
    return f"rgba({int(hex_color[1:3], 16)},{int(hex_color[3:5], 16)},{int(hex_color[5:7], 16)},{op})"


def defs(p: dict, uid: str) -> str:
    g0, g1, g2 = p["grad"]
    glow_color, glow_op = p["glow"]
    markers = "\n".join(
        f'    <marker id="ar-{name}-{uid}" viewBox="0 0 10 10" refX="9" refY="5" '
        f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">\n'
        f'      <path d="M0 0L10 5L0 10z" fill="{color}"/>\n    </marker>'
        for name, color in p["accents"].items()
    )
    return f"""  <defs>
    <linearGradient id="bgGrad-{uid}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{p['bg'][0]}"/>
      <stop offset="1" stop-color="{p['bg'][1]}"/>
    </linearGradient>
    <linearGradient id="titleGrad-{uid}" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{g0}"/>
      <stop offset="0.55" stop-color="{g1}"/>
      <stop offset="1" stop-color="{g2}"/>
    </linearGradient>
    <linearGradient id="synGrad-{uid}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{g0}"/>
      <stop offset="0.5" stop-color="{g1}"/>
      <stop offset="1" stop-color="{g2}"/>
    </linearGradient>
    <radialGradient id="synGlow-{uid}" cx="0.5" cy="0.45" r="0.55">
      <stop offset="0" stop-color="{glow_color}" stop-opacity="{glow_op}"/>
      <stop offset="1" stop-color="{glow_color}" stop-opacity="0"/>
    </radialGradient>
    <filter id="softGlow-{uid}" x="-15%" y="-15%" width="130%" height="130%">
      <feGaussianBlur stdDeviation="10" result="b"/>
      <feMerge>
        <feMergeNode in="b"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
{markers}
    <style>
      text {{ font-family: {FONT}; }}
      .title {{ font-size: 38px; font-weight: 700; letter-spacing: 1px; }}
      .subtitle {{ font-size: 18px; fill: {p['subtitle']}; }}
      .band-label {{ font-size: 15px; font-weight: 700; letter-spacing: 3px; }}
      .box {{ fill: {p['box_fill']}; stroke-width: 1; }}
      .box-title {{ font-size: 19px; font-weight: 600; fill: {p['box_title']}; }}
      .box-sub {{ font-size: 15px; fill: {p['box_sub']}; }}
      .edge {{ fill: none; stroke-width: 1.6; }}
      .edge-label {{ font-size: 14px; fill: {p['edge_label']}; }}
      .junction {{ fill: {p['accents']['emerald']}; }}
      .mod-title {{ font-size: 19px; font-weight: 600; fill: {p['mod_title']}; }}
      .chip {{ fill: {p['chip_fill']}; stroke-width: 1.4; }}
      .chip-num {{ font-size: 16px; font-weight: 700; fill: {p['chip_num']}; }}
      .flow-label {{ font-size: 13px; fill: {p['edge_label']}; }}
    </style>
  </defs>"""


def box(p: dict, x: int, y: int, w: int, h: int, accent: str,
        title: str, subs: list[str], tx: int | None = None,
        title_dy: int = 30, sub_dys: tuple[int, ...] = (56, 77, 98)) -> str:
    """A box with a vertically balanced text block (26px title gap, 21px lines)."""
    a = p["accents"][accent]
    tx = tx if tx is not None else x + 20
    lines = [
        f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" class="box" '
        f'stroke="{hex_rgba(a, p["box_border_op"])}"/>',
        f'  <rect x="{x}" y="{y}" width="3.5" height="{h}" rx="1.75" fill="{a}"/>',
        f'  <text x="{tx}" y="{y + title_dy}" class="box-title">{title}</text>',
    ]
    for i, sub in enumerate(subs):
        lines.append(
            f'  <text x="{tx}" y="{y + sub_dys[i]}" class="box-sub">{sub}</text>')
    return "\n".join(lines)


def band(p: dict, y: int, h: int, accent: str, label: str,
         x: int = 60, w: int = 1440) -> str:
    a = p["accents"][accent]
    return "\n".join([
        f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" '
        f'fill="{hex_rgba(a, p["band_fill_op"])}" '
        f'stroke="{hex_rgba(a, p["band_border_op"])}"/>',
        f'  <text x="{x + 16}" y="{y + 26}" class="band-label" fill="{a}">{label}</text>',
    ])


def edge(p: dict, d: str, accent: str, uid: str, dashed: bool = False,
         arrow: bool = True) -> str:
    dash = ' stroke-dasharray="5 4"' if dashed else ""
    marker = f' marker-end="url(#ar-{accent}-{uid})"' if arrow else ""
    return (f'  <path class="edge" stroke="{p["accents"][accent]}"'
            f'{dash}{marker} d="{d}"/>')


def label(x: int, y: int, text: str, anchor: str | None = None,
          cls: str = "edge-label", fill: str | None = None) -> str:
    a = f' text-anchor="{anchor}"' if anchor else ""
    f = f' fill="{fill}"' if fill else ""
    return f'  <text x="{x}" y="{y}"{a} class="{cls}"{f}>{text}</text>'


# ---------------------------------------------------------------- architecture

def architecture(p: dict, uid: str) -> str:
    s: list[str] = [
        f'<svg width="1920" height="1280" viewBox="0 0 1920 1280" '
        f'xmlns="http://www.w3.org/2000/svg">',
        defs(p, uid),
        f'  <rect width="1920" height="1280" rx="18" fill="url(#bgGrad-{uid})"/>',
        # header
        f'  <text x="60" y="62" class="title" fill="url(#titleGrad-{uid})">'
        f'AGENTIX PLATFORM</text>',
        label(60, 90, f"Multi-tenant Kubernetes infrastructure for AI agents {EM} "
                      f"with a LangGraph-native intelligence layer", cls="subtitle"),
        label(1860, 58, f"EKS {M} Istio Ambient {M} AgentGateway {M} kagent {M} "
                        f"LangGraph {M} MongoDB Atlas", anchor="end",
              cls="edge-label", fill=p["muted"]),
        # band 1 — EXPERIENCE (y 100-208)
        band(p, 100, 108, "blue", "EXPERIENCE", w=1480),
        box(p, 60, 136, 464, 60, "blue", "Observability UIs",
            [f"Langfuse {M} Grafana {M} Kiali"], title_dy=27, sub_dys=(49,)),
        box(p, 568, 136, 464, 60, "blue", "Consumer Apps &amp; A2A Clients",
            ["any A2A-compatible agent or application"],
            title_dy=27, sub_dys=(49,)),
        box(p, 1076, 136, 464, 60, "blue", f"synapse CLI {M} GitOps",
            [f"synapse export {AR} Agent CR {AR} kubectl apply"],
            title_dy=27, sub_dys=(49,)),
        # band 2 — GATEWAY & IDENTITY (y 236-344)
        band(p, 236, 108, "cyan", "GATEWAY &amp; IDENTITY", w=1480),
        box(p, 60, 272, 337, 60, "cyan", "Keycloak",
            [f"JWT {M} organization claims"], title_dy=27, sub_dys=(49,)),
        box(p, 441, 272, 337, 60, "cyan", "AgentGateway Ingress",
            [f"NLB {M} :80 {M} JWT-strict"], title_dy=27, sub_dys=(49,)),
        box(p, 822, 272, 337, 60, "cyan", "OpenFGA",
            ["fine-grained authorization"], title_dy=27, sub_dys=(49,)),
        box(p, 1203, 272, 337, 60, "cyan", "Tenant Waypoints",
            [f"L7 policy {M} credential injection"], title_dy=27, sub_dys=(49,)),
        # band 3 — SYNAPSE (y 384-636)
        f'  <rect x="60" y="384" width="1480" height="252" rx="14" '
        f'fill="url(#synGlow-{uid})"/>',
        f'  <rect x="60" y="384" width="1480" height="252" rx="14" '
        f'fill="{p["syn_fill"]}" stroke="url(#synGrad-{uid})" stroke-width="2" '
        f'filter="url(#softGlow-{uid})"/>',
        f'  <text x="84" y="422" style="font-size:20px; font-weight:700; '
        f'letter-spacing:2.5px;" fill="url(#titleGrad-{uid})">'
        f'SYNAPSE {EM} INTELLIGENCE PLANE</text>',
        f'  <text x="84" y="446" style="font-size:15.5px; fill:{p["syn_sub"]};">'
        f'LangGraph-native orchestration {EM} author agents as graphs, run them '
        f'as platform-native workloads</text>',
    ]
    modules = [
        ("Agent Graph Templates",
         [f"ReAct {M} Plan-Execute", f"Supervisor {M} Deep Research"]),
        ("GatewayChatModel",
         ["LLM calls via gateway", "zero API keys in pods"]),
        ("MemoryStore",
         ["Atlas Vector Search default", "EverMemOS pluggable"]),
        ("MCP Tooling",
         ["load_mcp_tools()", "servers proxied by gateway"]),
        ("A2A AgentServer",
         [f"agent.json {M} tasks/send", "SSE streaming"]),
    ]
    for i, (title, subs) in enumerate(modules):
        x = 84 + i * 293
        s.append(f'  <rect x="{x}" y="468" width="257" height="92" rx="10" '
                 f'fill="{p["syn_mod_fill"]}" stroke="{p["syn_mod_border"]}"/>')
        s.append(f'  <rect x="{x}" y="468" width="3.5" height="92" rx="1.75" '
                 f'fill="{p["accents"]["violet"]}"/>')
        s.append(f'  <text x="{x + 18}" y="498" class="mod-title">{title}</text>')
        for j, sub in enumerate(subs):
            s.append(f'  <text x="{x + 18}" y="{524 + j * 21}" '
                     f'class="box-sub">{sub}</text>')
    s += [
        f'  <rect x="84" y="578" width="1432" height="32" rx="16" '
        f'fill="{p["capsule_fill"]}" stroke="{p["capsule_border"]}"/>',
        f'  <text x="800" y="599" text-anchor="middle" '
        f'style="font-size:14.5px; fill:{p["capsule_text"]};">'
        f'Deployed as type: BYO Agent pods in tenant namespaces {EM} '
        f'ambient-mesh enrolled {M} Kyverno auto-exposed at '
        f'/a2a/{{ns}}/{{name}}</text>',
        # band 4 — CONTROL PLANE (y 664-772)
        band(p, 664, 108, "amber", "CONTROL PLANE", w=1480),
        box(p, 60, 700, 337, 60, "amber", "kagent controller",
            [f"Agent {M} ModelConfig {M} MCP CRDs"], title_dy=27, sub_dys=(49,)),
        box(p, 441, 700, 337, 60, "amber", "mycelium",
            [f"KRT reconciler {M} ecosystem CRDs"], title_dy=27, sub_dys=(49,)),
        box(p, 822, 700, 337, 60, "amber", "Kyverno",
            [f"auto-HTTPRoutes {M} scheduling"], title_dy=27, sub_dys=(49,)),
        box(p, 1203, 700, 337, 60, "amber", "AgentRegistry",
            [f"agent &amp; skill catalog {M} discovery"],
            title_dy=27, sub_dys=(49,)),
        # band 5 — DATA & OBSERVABILITY (y 856-992)
        band(p, 856, 136, "emerald", "DATA &amp; OBSERVABILITY", w=1480),
        box(p, 60, 892, 267, 88, "emerald", "AWS",
            ["RDS PostgreSQL", f"ElastiCache {M} S3"], tx=78,
            title_dy=30, sub_dys=(56, 77)),
        box(p, 363, 892, 267, 88, "emerald", "ClickHouse",
            ["Langfuse analytics", "trace storage"], tx=381,
            title_dy=30, sub_dys=(56, 77)),
        box(p, 666, 892, 267, 88, "emerald", "Agent Memory",
            ["MongoDB Atlas (default)", "EverMemOS (paved-road)"], tx=684,
            title_dy=30, sub_dys=(56, 77)),
        box(p, 969, 892, 267, 88, "emerald", "Tracing",
            [f"LangSmith {M} Phoenix", f"Langfuse {M} OTEL :4317"], tx=987,
            title_dy=30, sub_dys=(56, 77)),
        box(p, 1272, 892, 267, 88, "emerald", "Prom + Grafana",
            [f"metrics {M} dashboards", "Kiali topology"], tx=1290,
            title_dy=30, sub_dys=(56, 77)),
        # band 6 — INFRASTRUCTURE (y 1020-1156)
        band(p, 1020, 136, "slate", "INFRASTRUCTURE", w=1480),
        box(p, 60, 1056, 337, 88, "slate", "EKS Cell Clusters",
            ["ambient mesh, no sidecars", "multi-cell via CAPI"],
            title_dy=30, sub_dys=(56, 77)),
        box(p, 441, 1056, 337, 88, "slate", "Node Groups",
            [f"platform {M} agents {M} gateway", "tainted + autoscaled"],
            title_dy=30, sub_dys=(56, 77)),
        box(p, 822, 1056, 337, 88, "slate", "ztunnel",
            ["L4 mTLS everywhere", "SPIFFE identity"],
            title_dy=30, sub_dys=(56, 77)),
        box(p, 1203, 1056, 337, 88, "slate", "Management Cluster",
            [f"CAPI {M} CAAPH {M} ArgoCD", "Transit Gateway"],
            title_dy=30, sub_dys=(56, 77)),
        # external column
        label(1600, 210, "EXTERNAL", cls="band-label",
              fill=p["accents"]["rose"]),
        box(p, 1600, 236, 260, 108, "rose", "LLM Providers",
            [f"Anthropic {M} OpenAI", "AI backends on gateway"], tx=1618,
            title_dy=32, sub_dys=(58, 79)),
        box(p, 1600, 856, 260, 136, "rose", "MongoDB Atlas",
            ["Vector Search", "Voyage AI embeddings",
             f"managed {M} TLS :443"], tx=1618,
            title_dy=36, sub_dys=(62, 83, 104)),
        # edges
        edge(p, "M670 196 V272", "blue", uid),
        label(682, 230, f"HTTPS {M} JWT"),
        edge(p, "M397 302 H441", "cyan", uid),
        label(419, 294, "JWKS", anchor="middle"),
        edge(p, "M610 332 V384", "violet", uid),
        label(622, 372, f"A2A {M} /a2a/{{ns}}/{{agent}}"),
        edge(p, "M1370 384 V332", "cyan", uid),
        label(1382, 372, f"LLM {M} MCP egress"),
        edge(p, "M1540 302 H1600", "rose", uid),
        label(1570, 294, "TLS", anchor="middle"),
        # telemetry trunk
        edge(p, "M20 166 V844", "emerald", uid, arrow=False),
        edge(p, "M60 166 H20", "emerald", uid, dashed=True, arrow=False),
        '  <circle cx="20" cy="166" r="3.2" class="junction"/>',
        edge(p, "M60 496 H20", "emerald", uid, arrow=False),
        '  <circle cx="20" cy="496" r="3.2" class="junction"/>',
        edge(p, "M60 531 H20", "emerald", uid, arrow=False),
        '  <circle cx="20" cy="531" r="3.2" class="junction"/>',
        edge(p, "M20 796 H799 V892", "emerald", uid),
        '  <circle cx="20" cy="796" r="3.2" class="junction"/>',
        label(32, 788, "memory r/w"),
        edge(p, "M20 820 H1102 V892", "emerald", uid),
        '  <circle cx="20" cy="820" r="3.2" class="junction"/>',
        label(32, 812, f"traces {M} OTLP gRPC :4317"),
        edge(p, "M20 844 H1405 V892", "emerald", uid, dashed=True),
        label(32, 836, "dashboards"),
        edge(p, "M60 730 H44 V546 H60", "amber", uid, dashed=True),
        f'  <text x="34" y="638" class="edge-label" '
        f'fill="{p["accents"]["amber"]}" transform="rotate(-90 34 638)" '
        f'text-anchor="middle">kagent reconciles</text>',
        edge(p, "M799 980 V1004 H1730 V992", "rose", uid),
        label(1265, 996, f"vector search {M} embeddings", anchor="middle"),
        # legend
        f'  <line x1="60" y1="1200" x2="100" y2="1200" '
        f'stroke="{p["accents"]["blue"]}" stroke-width="1.6"/>',
        label(108, 1204, "request path"),
        f'  <line x1="240" y1="1200" x2="280" y2="1200" '
        f'stroke="{p["accents"]["amber"]}" stroke-width="1.6" '
        f'stroke-dasharray="5 4"/>',
        label(288, 1204, "control / management"),
        f'  <line x1="480" y1="1200" x2="520" y2="1200" '
        f'stroke="{p["accents"]["emerald"]}" stroke-width="1.6"/>',
        '  <circle cx="500" cy="1200" r="3.2" class="junction"/>',
        label(528, 1204, "telemetry &amp; memory bus"),
        label(1860, 1204, f"All east-west traffic is mTLS-encrypted via ztunnel "
                          f"(SPIFFE identity) {EM} tenants never hold provider "
                          f"credentials.", anchor="end"),
        label(60, 1250, f"Agentix Platform {EM} engineered for production "
                        f"agentic workloads", fill=p["footer"]),
        "</svg>",
    ]
    return "\n".join(s) + "\n"


# ---------------------------------------------------------------- request flow

def request_flow(p: dict, uid: str) -> str:
    stages = [
        ("blue", "Client", ["A2A tasks/send", f"HTTPS {M} JWT"]),
        ("cyan", "Ingress Gateway",
         ["verify JWT (JWKS)", "route /a2a/{ns}/{agent}"]),
        ("cyan", "Tenant Waypoint",
         [f"L7 policy {M} HBONE mTLS", "namespace isolation"]),
        ("violet", "Synapse Agent",
         ["LangGraph loop", f"plan {M} act {M} observe"]),
        ("cyan", "Egress Gateway",
         ["injects real API key", f"prompt guards {M} PII"]),
        ("rose", "LLM Provider", [f"Anthropic {M} OpenAI", "completion"]),
    ]
    xs = [110, 390, 670, 950, 1230, 1510]
    s: list[str] = [
        f'<svg width="1840" height="700" viewBox="0 0 1840 700" '
        f'xmlns="http://www.w3.org/2000/svg">',
        defs(p, uid),
        f'  <rect width="1840" height="700" rx="18" fill="url(#bgGrad-{uid})"/>',
        f'  <text x="60" y="48" style="font-size:28px; font-weight:700; '
        f'fill:{p["box_title"]};">One request through the platform</text>',
        label(60, 78, f"A2A in {AR} LangGraph reasoning loop {AR} governed LLM "
                      f"egress {EM} with memory and tracing on the side channels",
              cls="subtitle"),
        edge(p, "M1620 102 H220", "blue", uid, dashed=True),
        label(920, 94, f"response {M} SSE stream", anchor="middle",
              cls="flow-label"),
    ]
    for i, (accent, title, subs) in enumerate(stages):
        a = p["accents"][accent]
        cx = xs[i] + 110
        s.append(f'  <circle cx="{cx}" cy="126" r="15" class="chip" '
                 f'stroke="{a}"/>')
        s.append(f'  <text x="{cx}" y="131.5" text-anchor="middle" '
                 f'class="chip-num">{i + 1}</text>')
        if accent == "violet":
            s.append(f'  <rect x="{xs[i]}" y="152" width="220" height="108" '
                     f'rx="12" fill="{p["syn_mod_fill"]}" '
                     f'stroke="url(#synGrad-{uid})" stroke-width="2" '
                     f'filter="url(#softGlow-{uid})"/>')
        else:
            s.append(f'  <rect x="{xs[i]}" y="152" width="220" height="108" '
                     f'rx="12" class="box" '
                     f'stroke="{hex_rgba(a, p["box_border_op"])}"/>')
            s.append(f'  <rect x="{xs[i]}" y="152" width="3.5" height="108" '
                     f'rx="1.75" fill="{a}"/>')
        s.append(f'  <text x="{xs[i] + 20}" y="186" class="box-title">'
                 f'{title}</text>')
        for j, sub in enumerate(subs):
            s.append(f'  <text x="{xs[i] + 20}" y="{212 + j * 21}" '
                     f'class="box-sub">{sub}</text>')
    hops = [("blue", "HTTPS"), ("cyan", "HBONE"), ("violet", "invoke"),
            ("cyan", f"LLM{M}MCP"), ("rose", "TLS")]
    for i, (accent, text) in enumerate(hops):
        x0 = xs[i] + 220
        s.append(edge(p, f"M{x0} 206 H{x0 + 60}", accent, uid))
        s.append(label(x0 + 30, 198, text, anchor="middle", cls="flow-label"))
    s += [
        # side channel: memory + tools
        box(p, 950, 408, 220, 92, "emerald", "Agent Memory",
            ["MongoDB Atlas", "vector recall"], title_dy=30, sub_dys=(56, 77)),
        box(p, 1230, 408, 220, 92, "emerald", "MCP Tool Servers",
            ["via gateway", "no tool credentials"], title_dy=30,
            sub_dys=(56, 77)),
        edge(p, "M1060 260 V408", "emerald", uid),
        label(1072, 340, "memory r/w", cls="flow-label"),
        edge(p, "M1340 260 V408", "emerald", uid),
        label(1352, 340, "tool calls", cls="flow-label"),
        # tracing bar
        box(p, 110, 528, 1620, 88, "emerald",
            f"Tracing {EM} LangSmith {M} Phoenix {M} Langfuse (OTEL)",
            [f"every span: gateway {M} agent {M} tool {M} LLM {EM} cost, "
             f"latency, prompts, tokens"], tx=130, title_dy=34, sub_dys=(60,)),
        edge(p, "M500 260 V528", "emerald", uid, dashed=True),
        edge(p, "M1010 260 V292 H760 V528", "emerald", uid, dashed=True),
        edge(p, "M1400 260 V300 H1560 V528", "emerald", uid, dashed=True),
        label(920, 662, f"Every hop traced {M} every credential injected at "
                        f"the proxy {M} every tenant isolated", anchor="middle",
              fill=p["muted"]),
        "</svg>",
    ]
    return "\n".join(s) + "\n"


def main() -> None:
    for name, palette in PALETTES.items():
        suffix = "" if name == "dark" else f"-{name}"
        (OUT / f"architecture{suffix}.svg").write_text(
            architecture(palette, name))
        (OUT / f"request-flow{suffix}.svg").write_text(
            request_flow(palette, name))
        print(f"wrote *{suffix or '-dark'}.svg")


if __name__ == "__main__":
    main()
