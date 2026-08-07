"""``synapse`` command-line interface.

    synapse new my-agent --template deep-research   # scaffold an agent project
    synapse serve my_agent:graph                    # run the A2A server locally
    synapse export my_agent:graph --image ...       # emit the Agent manifest
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

from synapse.constants import DEFAULT_PORT

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def _load_graph(spec: str):
    """Resolve ``module:attr`` to a compiled graph."""
    if ":" not in spec:
        raise SystemExit(f"graph spec must be module:attribute, got {spec!r}")
    module_name, attr = spec.split(":", 1)
    sys.path.insert(0, str(Path.cwd()))
    module = importlib.import_module(module_name)
    graph = getattr(module, attr)
    if not callable(getattr(graph, "ainvoke", None)):
        raise SystemExit(f"{spec!r} is not a compiled graph (no ainvoke)")
    return graph


def cmd_new(args: argparse.Namespace) -> None:
    target = Path(args.name)
    if target.exists():
        raise SystemExit(f"{target} already exists")
    (target / "tests").mkdir(parents=True)
    (target / "agent.py").write_text(
        f'''"""{args.name} — a Synapse agent."""

from synapse.graphs import create_react_agent
from synapse.llm import GatewayChatModel

graph = create_react_agent(
    model=GatewayChatModel(),
    tools=[],
    prompt="You are {args.name}, a helpful platform agent.",
    name="{args.name}",
)
'''
    )
    (target / "README.md").write_text(
        f"# {args.name}\n\nA Synapse agent. Run locally:\n\n"
        f"```bash\nsynapse serve agent:graph\n```\n"
    )
    print(f"created {target}/ — edit agent.py,")
    print(f"then run `cd {args.name} && synapse serve agent:graph`")


def cmd_serve(args: argparse.Namespace) -> None:
    from synapse.runtime import AgentServer
    from synapse.runtime.server import AgentCard

    graph = _load_graph(args.graph)
    card = AgentCard(
        name=args.name or getattr(graph, "name", None) or "synapse-agent",
        description=args.description or "A Synapse agent",
        version=args.version,
    )
    AgentServer(graph, card).run(host=args.host, port=args.port)


def cmd_export(args: argparse.Namespace) -> None:
    from synapse.runtime.crd import build_agent_manifest

    graph = _load_graph(args.graph)
    manifest = build_agent_manifest(
        name=args.name or getattr(graph, "name", None) or "synapse-agent",
        namespace=args.namespace,
        image=args.image,
        description=args.description or "A Synapse agent",
    )
    if args.output:
        Path(args.output).write_text(manifest)
        print(f"wrote {args.output}")
    else:
        print(manifest, end="")


def main() -> None:
    parser = argparse.ArgumentParser(prog="synapse", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_new = sub.add_parser("new", help="scaffold a new agent project")
    p_new.add_argument("name")
    p_new.add_argument("--template", default="react")
    p_new.set_defaults(func=cmd_new)

    p_serve = sub.add_parser("serve", help="run the A2A server locally")
    p_serve.add_argument("graph", help="module:attribute of a compiled graph")
    p_serve.add_argument("--host", default="0.0.0.0")
    p_serve.add_argument("--port", type=int, default=DEFAULT_PORT)
    p_serve.add_argument("--name")
    p_serve.add_argument("--description")
    p_serve.add_argument("--version", default="0.1.0")
    p_serve.set_defaults(func=cmd_serve)

    p_export = sub.add_parser("export", help="emit a platform Agent manifest")
    p_export.add_argument("graph", help="module:attribute of a compiled graph")
    p_export.add_argument("--image", required=True)
    p_export.add_argument("--namespace", default="default")
    p_export.add_argument("--name")
    p_export.add_argument("--description")
    p_export.add_argument("--output", "-o")
    p_export.set_defaults(func=cmd_export)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
