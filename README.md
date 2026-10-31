# Showcase

Showcase is a guide app for NimbleBrain. It teaches how an MCP app works: a person and an agent
call the same tools, and both see one saved guide and practice board. It is a Python FastMCP
server, licensed under the [MIT License](LICENSE).

This stage is the guide server and the hooks a local installer uses. The screen and the release
packaging follow in separate changes.

## Develop

Use Python 3.13 or newer. Prepare the environment from the committed lock with
`uv sync --frozen --dev`, subject to your host's package policy. Then:

```sh
make verify    # formatting, lint, types and tests
make run       # MCP over stdio
make run-http  # MCP over HTTP on 127.0.0.1:27249
```

## Run and connect

The entry point is `python -m synapse_showcase.server`. Stdio is the default. HTTP mode uses
`--http --port 27249` and exposes `/mcp`, `/agent/mcp` and `/health` on loopback only. An HTTP
MCP client sends the header `x-showcase-client: local`; requests with a browser `Origin`, a
non-loopback `Host` or a body over 64 KiB are refused.

The tools are `guide_status`, `guide_step`, `guide_preferences`, `guide_view`, `board_add`,
`board_move` and `catalog_list`. `/agent/mcp` adds `guide_connection_check`, which records that
an external agent called the guide. It does not verify a model provider or a chat reply. The
guide skill is served through the MCP Skills extension at `skill://showcase/guide/SKILL.md`.

Progress and sample cards are stored in one JSON file. Select it with `--data-file` or
`SHOWCASE_DATA_FILE`; otherwise it is `showcase/progress.json` under `MPAK_WORKSPACE`, or under
the current directory. Every process sharing that file sees the same progress, and each saved
change is announced to every open session. The practice board is separate from NimbleBrain
Tasks and installed apps.

A standalone guide works without an installer. A local installer can supply the
optional app planning, installation, status and external-agent setup capabilities through the
server's `--http --host-stdio` mode. The installer owns package approval, processes, source
verification and recovery. Showcase does not acquire apps itself. Unavailable capabilities
are omitted from the tools and shown as unavailable in the guide.
