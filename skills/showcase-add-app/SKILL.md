---
name: showcase-add-app
description: Help a person check and use an enabled app, and hand off preparation to its external operator.
---

# Use an available app

Read `guide_status` to learn which apps and capabilities the host actually supplies. A standalone
guide may have none. Use available operator guidance for setup; do not invent a shell command,
checkout path, endpoint or permission.

1. Let the person choose an app from the available list. A catalog listing or prepared server
   does not prove that this workspace can use it.
2. If `app_status` is available, check the chosen app. Report only the process, connection,
   tools and UI results the host actually verified. If it is unavailable or the app is not ready,
   explain the reported gap and hand preparation or repair to the supported external operator.
3. Once ready, guide the person to the returned app link or existing host navigation. Try one
   small intended action and inspect its visible result. App-status success alone does not
   verify the person's workflow. Use that app's own skills and advertised tools for agent actions.
4. Read current state before repeating a check. An old failed job is history once the current
   app is verified; an old ready job is not proof the connection still works. Do not restart an
   installation merely because a prior job or screen is stale.

Some hosts advertise `app_plan`, `app_install` or `app_lifecycle`. During this walkthrough,
use the supported external operator flow for software acquisition, dependency installation,
catalog enablement, instance configuration and server lifecycle. Do not invoke `app_install`
or `app_lifecycle` from the walkthrough. A local app connection that changes configuration or
restarts the runtime belongs to that operator flow too. Missing prerequisites and refused
package policy need the operator's next step. Keep existing policy and access boundaries.

Using an enabled app and native Connect/consent for an enabled hosted connector remain product
actions. A workspace role requirement alone does not turn that supported flow into software
installation. Adding a local app grants no external account or data-source access; provider
consent stays in the connector's native consent flow.
