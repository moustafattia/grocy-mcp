# Roadmap

This is a practical next-step list for turning `grocy-mcp` into a stronger MCP server and CLI for Grocy.

The goal is not just "more features," but a smoother day-to-day operator experience for both AI agents and humans.

## Priority 1: Close correctness and UX gaps

- [ ] Make sure every CLI and MCP option is actually wired through to the client layer.
- [ ] Remove or implement any advertised behavior that is currently partial or misleading.
- [ ] Audit help text, examples, and runtime errors so they always match real behavior.
- [ ] Add regression tests for argument-heavy commands such as shopping-list notes, list IDs, recipe creation, and chore execution metadata.
- [ ] Standardize command output formatting so confirmations and list views feel consistent across domains.

## Priority 2: Improve the MCP experience for AI agents

- [ ] Review tool names, parameter names, and descriptions for agent readability and predictability.
- [ ] Add clearer parameter docs for JSON-accepting tools such as shopping updates and entity management.
- [ ] Consider returning more structured output for MCP where it helps agents reason better, while keeping the CLI human-friendly.
- [ ] Add examples of high-value agent workflows in the docs.
- [ ] Evaluate whether some large generic operations should be split into safer, more task-specific MCP tools.

## Priority 3: Make the CLI excellent

- [ ] Add shell-friendly output options for users who want scripting and automation support.
- [ ] Add top-level config flags if they are worth supporting consistently.
- [ ] Improve validation and error messaging for malformed JSON arguments.
- [ ] Add command aliases only where they reduce friction without creating ambiguity.
- [ ] Improve list rendering for long outputs, especially stock and shopping views.

## Priority 4: Expand Grocy coverage

Potential feature areas that would make the project much more complete:

- [ ] Product groups and quantity units
- [ ] Locations and stores
- [ ] Meal plans
- [ ] Batteries
- [ ] Equipment
- [ ] Tasks and calendars
- [ ] User management / assignment-aware operations where Grocy supports them
- [ ] Stock journal / history views
- [ ] Purchase and price workflows
- [ ] Better barcode and search flows

## Priority 5: Better recipe and shopping workflows

- [ ] Add richer recipe creation and editing flows.
- [ ] Support recipe ingredient resolution by product name, not only product ID.
- [ ] Improve shopping-list update ergonomics so common edits do not require raw JSON.
- [ ] Add a "plan meal -> add missing items -> review shopping list" end-to-end workflow.
- [ ] Add optional dry-run or preview flows before destructive updates.

## Priority 6: Reliability and testing

- [ ] Add more CLI tests that assert actual async command behavior, not only command registration.
- [ ] Add focused tests for retry logic and transport errors.
- [ ] Add integration-test support against a real Grocy instance behind opt-in environment variables.
- [ ] Add coverage for ambiguous name resolution and edge-case entity payloads.
- [ ] Add CI checks for linting, tests, and package build verification.

## Priority 7: Packaging and release maturity

- [ ] Add a changelog.
- [ ] Add release automation for PyPI publishing.
- [ ] Add GitHub Actions for tests and lint on pull requests.
- [ ] Verify package metadata, classifiers, and long-description rendering on PyPI.
- [ ] Add versioning and release notes discipline before a broader public launch.

## Priority 8: GitHub/project polish

- [ ] Add badges for PyPI, Python versions, tests, and license.
- [ ] Add issue templates for bugs and feature requests.
- [ ] Add a contribution guide.
- [ ] Add architecture diagrams or workflow examples in docs.
- [ ] Add a troubleshooting section for common Grocy URL/auth/config mistakes.

## What "optimal" looks like

An excellent `grocy-mcp` would feel like:

- a dependable MCP server that AI agents can use safely and predictably
- a CLI that is fast, clear, and scriptable
- a project whose docs make onboarding easy
- a tool that covers the Grocy workflows people actually use every day

## Suggested execution order

If working incrementally, the best order is:

1. correctness and CLI/MCP alignment
2. agent ergonomics and CLI usability
3. test and CI maturity
4. broader Grocy feature coverage
5. packaging and project polish
