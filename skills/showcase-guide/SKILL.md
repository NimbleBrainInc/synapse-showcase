---
name: showcase-guide
description: Help a person learn an MCP app through Showcase's shared guide and practice board.
---

# Guide someone through Showcase

Read `guide_status` first and continue from the person's chosen chapter. Offer one useful
action, let them try it, then explain the observed result. Questions do not require changing
the screen or saved state.

`guide_step` selects a chapter and can record completion or a skip. A skipped step does not
count as completed. `guide_preferences` saves pace and the guide's own appearance. Use
`guide_view` to focus or pause the illustration; change zoom only when asked.
Chapter completion records progress, not learning or installation verification. Do not use
`guide_step` to claim an external agent connection was verified.

The person may click while you work. Read current state before using a card ID or assuming a
chapter is still selected. `board_add` and `board_move` affect only the practice board. They
do not create real tasks in another app. Read back the changed card before describing success.

For a shared-state exercise, let the person create a uniquely named practice card in the screen.
Read `guide_status`, match that exact card and its ID, then explain the agreed next move.
Use `board_move` with that ID and chosen status, and read back the saved card. Ask the person
to inspect what the screen shows; do not assume a view has refreshed because a write succeeded.
Invite them to move the same card again and describe the result, then read back that change.
Explain that both controllers act on the same saved card. A skipped exercise remains skipped.

All arrows and animations remain inside Showcase. No guide tool controls the host's DOM,
acquires a model key or signs in to an external provider. Keep keys out of messages and tool arguments.

Software preparation, dependencies, catalog changes and server lifecycle belong to the supported
external operator flow. Use the available operator guidance when those steps are needed; do not
invent commands or local paths. People can then use enabled apps and the native Connect/consent
flow for enabled hosted services. Inspect the host's capabilities before choosing a tool.
`catalog_list` describes available choices; it does not prove installation or authorization.

An external coding agent can call `guide_connection_check` when asked. The resulting timestamp
proves a tool call reached this guide. It does not prove a model-provider reply or grant tools
from other connected apps, and it does not establish that the person completed the shared-state
exercise or learned the workflow. Provider setup and connection consent remain with their owner.

For the full tool list, read [the README](../../README.md) from a checkout. Through MCP alone,
use the available guide tools rather than assuming local-file access.
