# Universal local agent connector (architecture proposal)

This is a non-normative architecture sketch for a user-controlled connector
that lets an ASP application involve an agent chosen by the user. It is not a
new ASP profile, a deployed implementation, or an interoperability claim. The
RFC remains unchanged.

## User-facing idea

The user installs or runs one local connector and chooses an agent for it. An
ASP application can ask the connector to start a session with that agent, for
example to help the user complete an in-app workflow. The connector binds the
request to the active application origin and shows the user the application,
proposed task, and relevant data disclosure. The application remains the Grant
Issuer and authoritative session owner; the connector/runtime stores and
enforces the issued Grant locally.

```text
ASP application <-> local connector/runtime <-> user-selected agent
      |                       |                         |
      +-- user task/consent --+--- Grant-bound session -+
      +<------ permitted outcome through authorized paths
```

The application may request a session only after an authenticated user action
or a policy the user authorized independently of the agent. A browser-origin
request is merely a proposal to the connector, not authority to start a session
or invoke an application action. Under the recommended app-issued Grant model,
the application obtains user consent and issues the Grant; the runtime stores
it and mediates agent work. The application independently verifies the current
Grant and session for every action. The page never receives the Grant or its
credential.

This is the ASP two-way application model: an application can involve the
user-owned agent in its workflow, while the agent can call only the
application's separately granted surface through its runtime. The application
delivers any proposed task over an authorized event path and MUST NOT use
session start to bypass the Data Exposure Contract.

## Candidate platform bindings

### iPhone: embedded browser and native bridge

The connector owns an embedded browser. A website request reaches a native
bridge, which checks the active page origin and navigation state before the
connector offers the user a task/session request. The native bridge is not an
authority channel: the runtime must authenticate to the application and the
application must accept the session under the current Grant. Navigation to an
unapproved origin disables the bridge; redirects trigger a fresh origin check.

This keeps the authority-bearing bridge under the connector's control. It does
not make every web page trusted, and it does not make consent equivalent to an
ASP Grant: both the local connector and the application enforce their own
boundaries.

### Mac: external browser and loopback listener (unverified candidate)

An external browser could attempt to reach a listener bound only to
`127.0.0.1` to propose a session start. Loopback binding prevents remote hosts
from connecting directly, but does not authenticate the requesting website or
prevent cross-origin abuse. A viable design would need exact Origin checks, a
privileged, page-inaccessible, short-lived, single-use request proof bound to
origin/session/request/expiry, explicit user consent, and application-side ASP
checks before execution.

This repository has not demonstrated that supported desktop browsers permit
the website-to-loopback transport with the necessary isolation and proof
properties. Browser security policy, secure-context requirements, preflight,
and private-network access behavior need a separate compatibility experiment.
If those properties cannot be established, use a browser-controlled companion
channel or extension instead; do not weaken the authority checks to preserve
the loopback design.

## Shared responsibilities

- **Surface client:** discovers the remote application's curated ASP surface.
- **Origin gate:** binds a request to the exact active site origin; rejects
  opaque origins.
- **Consent broker:** presents the site, selected actions, and disclosed data;
  consent is bounded and revocable.
- **Grant lifecycle:** the ASP application issues the Grant after its consent
  flow (the recommended MVP model); the runtime stores it, enforces it locally,
  and cannot widen it. The page cannot supply authority.
- **Session coordinator:** requests session start as the authenticated runtime;
  application-initiated sessions still require an authenticated user action or
  independently user-authorized policy and an authorized task-delivery path.
- **Local agent runtime:** connects to the user's selected agent without
  exposing connector credentials to page code.
- **Capability dispatcher:** checks origin and current Grant before dispatch;
  undeclared actions are unavailable.
- **Result presenter:** returns only the result permitted by disclosure policy;
  never returns Grant credentials or signing material.
- **Revocation controller:** blocks future calls; it cannot recall data already
  disclosed to an agent or website.
- **ASP application:** verifies the Grant, session, action, and current state
  independently. The connector is not a substitute for application-side
  enforcement.

## Relation to the RFC

The ASP Core explicitly does not require browser-to-localhost communication.
The connector is one possible deployment architecture, not a requirement for
ASP implementations. For an ASP-over-WebMCP deployment, the normative binding
already requires a separate privileged Runtime Bridge and a browser-only,
single-use invocation proof. WebMCP registration, a page-held bearer, or a
page-supplied hidden tool argument does not establish authority. See the
[Runtime Bridge and invocation-proof requirements](../../drafts/modules/bindings/asp-over-mcp.md#browser-topology-and-authority-boundary)
and the [Runtime Bridge Protocol](../../drafts/modules/core.md#3-runtime-bridge-protocol).

The accompanying Hypercode files are an architecture model and explicit
scenario traces. Hypercode validation establishes that those declarations and
contracts resolve; it does not prove that a browser, native bridge, or runtime
implements them safely.

## Files and validation

- `connector.hc` — component hierarchy.
- `connector.hcs` — authority constraints, platform candidates, and explicit
  iPhone/macOS scenario traces.

From a checkout of the Hypercode repository, validate these files with its
compiler:

```sh
swift run hypercode validate /path/to/agent-surface/reference/adoption/local-agent-connector/connector.hc \
  --hcs /path/to/agent-surface/reference/adoption/local-agent-connector/connector.hcs
swift run hypercode validate /path/to/agent-surface/reference/adoption/local-agent-connector/connector.hc \
  --hcs /path/to/agent-surface/reference/adoption/local-agent-connector/connector.hcs --ctx platform=ios
swift run hypercode validate /path/to/agent-surface/reference/adoption/local-agent-connector/connector.hc \
  --hcs /path/to/agent-surface/reference/adoption/local-agent-connector/connector.hcs --ctx platform=macos
```
