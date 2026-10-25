# Iteration 1.1 — analyst security console

Date: 2026-10-25

## Iteration goal

Make the Phase 0–8 functionality faster to navigate and easier to assess during long analyst sessions, while preserving the product's evidence boundaries. The visual direction uses familiar security-console patterns—dense navigation, restrained status color, command search, and operational posture graphics—without copying any vendor product.

## User stories and acceptance criteria

### Theme control

As an analyst, I can switch between light and dark modes so the workspace remains comfortable in different environments.

- The initial mode follows a stored preference or the operating-system preference.
- The top-bar control changes the complete application theme and browser theme color.
- The choice persists without storing authentication data.
- Cytoscape node, edge, label, and canvas colors respond to theme changes.
- Keyboard focus, status colors, forms, tables, dialogs, and operational panels retain readable contrast.

### Command navigation

As an analyst, I can reach any workspace quickly without traversing the sidebar.

- `Ctrl/⌘ K` opens a modal command palette.
- Search filters real application routes and describes each destination.
- Enter opens the first result; Escape closes the palette.
- The existing sidebar remains available and responsive.

### Operational posture

As an analyst, I can understand current workload and coverage from observed system state.

- Source availability, settled investigations, detection validation, open cases, active investigations, actionable changes, and demonstration-record counts come from `/api/v1/operations/metrics`.
- Ring and bar graphics expose their meaning in adjacent text and do not imply historical trends.
- Zero denominators render as zero rather than an invented percentage.
- Demonstration data stays visibly separated from production assertions.

## Engineering practices

This iteration is one releasable vertical slice. It adds service-level theme tests, shell interaction tests, strict Angular compilation, bundle budgets, and the full existing backend regression suite. The next iteration should start from analyst feedback and observed usability or performance data rather than expanding the interface speculatively.

## Verification

- 39 backend tests pass, including the complete Phase 0–8 regression suite.
- Ruff passes and strict mypy reports no issues across 56 backend source files.
- 10 frontend tests cover the existing intelligence service plus shell navigation, command-palette behavior, theme persistence, observed dashboard ratios, and explicit telemetry-failure state.
- The Angular production build passes at 348.80 kB initial raw size, below its 500 kB warning budget.
- The production npm dependency audit reports zero vulnerabilities.
- Alembic upgrades PostgreSQL to the migration head and reports no ORM/migration drift.
- Fresh backend and frontend Docker images build successfully; the recreated stack reports healthy API and database services, compiles the Angular development server, and serves direct and proxied 1.1.0 readiness responses.

The full development-tool audit reports advisories in Vitest 3 and its worker pool. Angular 20's supported test-builder peer range prevents taking the patched Vitest major in this iteration. These packages are absent from the production dependency audit and are used only for local build/test work. Upgrading Angular and Vitest together remains a tracked maintenance item rather than an untested forced update.
