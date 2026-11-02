# Showcase

Showcase is a guide app for NimbleBrain. It teaches how an MCP app works: a person uses the
app's screen while an agent calls the same tools, and both see one saved guide and practice
board. It is a Python FastMCP server with a React UI, licensed under the [MIT License](LICENSE).

The release packaging follows in a separate change.

## Develop

Use Python 3.13 or newer and Node.js 24 or newer. Build the UI first with
`npm --prefix ui ci --ignore-scripts` and `make build`, because the Python package includes
`ui/dist/index.html` and `uv sync` stops without it. Then prepare the Python environment from
the committed lock with `uv sync --frozen --dev`, subject to your host's package policy, and:

```sh
make dev       # Vite preview at /__preview, with a stdio Python server
make verify    # Python formatting, lint, types and tests; UI types and build
make run       # standalone MCP over stdio
make run-http  # MCP over HTTP on 127.0.0.1:27249
```

The build creates one HTML file in `ui/dist/index.html`. Build it before making a Python wheel.
The wheel includes this HTML and the guide skills, so an installed package needs no source
checkout or Node runtime to serve its screen. `SHOWCASE_UI_DIR` can select a different
directory containing `index.html`.

## Run and connect

The package entry point is `python -m synapse_showcase.server`. Stdio is the default. HTTP mode
uses `--http --port 27249` and exposes `/mcp`, `/agent/mcp` and `/health` on loopback only. An
HTTP MCP client sends the header `x-showcase-client: local`; requests with a browser `Origin`, a
non-loopback `Host` or a body over 64 KiB are refused.

The tools are `guide_status`, `guide_step`, `guide_preferences`, `guide_view`, `board_add`,
`board_move` and `catalog_list`. `/agent/mcp` adds `guide_connection_check`, which records that
an external agent called the guide. It does not verify a model provider or a chat reply. The
guide skill is served through the MCP Skills extension (`skills/list`, `skills/get` and
`resources/read`) at `skill://showcase-guide/SKILL.md`. FastMCP binds those two methods to the
2026-07-28 protocol era; Showcase answers them on the 2025-11-25 handshake era as well, which is
what NimbleBrain negotiates today. Each folder under `skills/` is one skill and is named after
its frontmatter `name`.

The screen is the MCP resource `ui://showcase/guide`, served as
`text/html;profile=mcp-app`. A host must support MCP Apps to render it; opening the built HTML
directly does not supply the MCP bridge.

Progress and sample cards are stored in one JSON file. Select it with `--data-file` or
`SHOWCASE_DATA_FILE`; otherwise it is `showcase/progress.json` under `MPAK_WORKSPACE`, or under
the current directory. Every process sharing that file sees the same progress, and each saved
change is announced to every connection that negotiated the 2025-11-25 handshake era; a
sessionless 2026-07-28 connection has no standing channel for a notice and reads again on its own. The practice board is separate from NimbleBrain
Tasks and installed apps.

A standalone guide works without an installer. A local installer can supply the
optional app planning, installation, status and external-agent setup capabilities through the
server's `--http --host-stdio` mode. In that mode an HTTP MCP client sends
`x-nimble-bootstrap: local` in place of `x-showcase-client: local`. The installer owns package
approval, processes, source verification and recovery. Showcase does not acquire apps itself.
Unavailable capabilities are omitted from the tools and shown as unavailable in the guide.

The installer's tools are `app_plan`, `app_install`, `app_status`, `app_lifecycle` and
`guide_agent_setup`, each present only when the installer reports it, plus `app_job_status`.
`app_install` is for Showcase's own screen; `/agent/mcp` leaves it out. The add-app skill is
served at `skill://showcase-add-app/SKILL.md`.
