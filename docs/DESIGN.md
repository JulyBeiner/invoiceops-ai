# InvoiceOps — Design notes

Screens (v1, 7 artboards, clickable prototype, first palette): https://claude.ai/artifact/39LPv541pVYfRQFnj7eRyk — the layout and the flows are what the app implements; the colors there are the old navy + terracotta ones. The current look is described below.

Target user: the person who runs the administration of a small B2B cleaning or maintenance company in Spain. Closes the month from a laptop, in a hurry, and needs to trust the numbers. The look is clean and light (gray ground, white cards, near-black ink) with one lime accent reserved for the main action of each screen.

## Palette (CSS variables in `src/front/index.css`)

| Variable | Value | Use |
| ---------------- | --------- | ------------------------------------------------ |
| `--io-ink` | `#0e1a2b` | headings, body of primary buttons, brand mark |
| `--io-ink-2` | `#1c2b40` | hover on ink |
| `--io-lime` | `#c8f169` | primary buttons, brand check, current step |
| `--io-lime-2` | `#b5e24f` | primary button hover |
| `--io-lime-soft` | `#edf9d2` | active sidebar item, green badges, selected row |
| `--io-ground` | `#f5f6f8` | page background |
| `--io-surface` | `#ffffff` | cards, tables, inputs, sidebar |
| `--io-border` | `#e6e8ec` | card borders; `--io-line #eef0f3` for table row lines |
| `--io-text` | `#111827` | body text |
| `--io-muted` | `#6b7280` | secondary text, sidebar inactive links |

`--io-navy` and `--io-accent` are kept as aliases of ink and lime so older class names keep working.

Status colors (badge background / text, classes `io-badge io-badge-*`):

| Class | Background | Text | Where |
| ---------------- | --------- | --------- | -------------------------------------- |
| `amber` | `#fdf1d6` | `#8a5a0b` | Pendiente, Borrador, En revisión |
| `green` | `#edf9d2` | `#3b6d11` | Facturada, Aprobada, Activo, Correcta |
| `navy` | `#e5e9f0` | `#0e1a2b` | Cerrado |
| `gray` | `#eceef2` | `#6b7280` | Archivado, Duplicada, "ya lo tienes" |
| `red` | `#fde4e1` | `#9b2c1b` | Error, Sin precio |

Colors that must be told apart also differ in lightness, not only in hue.

## Typography

Google Fonts (one `<link>` in `index.html`): **Plus Jakarta Sans** 400/500/600/700 for everything; titles are 700 with `letter-spacing: -0.02em`. Numbers use `font-variant-numeric: tabular-nums` (`.io-num`) so columns of money line up. Icons: Font Awesome 6 (loaded by the template's `index.html`).

## Layout

- Fixed left sidebar, 232 px, white with a right border: brand (ink circle with a lime check + "InvoiceOps"), five links (Inicio, Clientes, Actividades, Cierre de mes, Ajustes; active item on `--io-lime-soft`), user block at the bottom (initials avatar, name, company) with "Cerrar sesión".
- Main area: padding 32 px 40 px; page header (`.io-page-header`) = title + one-line subtitle on the left, actions on the right.
- Cards: white, 1 px border `--io-border`, radius 12 px, flat (no shadow). Tables inside cards, header row uppercase 12 px muted.
- Buttons: 40 px high, radius 8 px, weight 600. Primary = lime background, ink text; secondary = white with border; link buttons for tertiary actions. One primary button per screen.
- Badges: pill, 24 px high, 12 px bold, colors from the table above.
- Inputs: 40 px high, radius 8 px; money inputs right-aligned.
- Confirmation dialogs (`window.confirm`) before closing a month, approving a proposal and archiving a client.

Bootstrap 5 provides the grid, forms, tables and utilities; `index.css` overrides `--bs-primary`, fonts, radius and the sidebar. No component library beyond Bootstrap.

## Screens

1. **Acceso** (`/login`, `/register`, `/forgot-password`, `/reset-password`): split layout, ink panel with the value proposition on the left, one card form on the right.
2. **Inicio** (`/`): month selector, four KPI cards (`GET /api/dashboard`), the three steps of the month (registrar → cerrar → aprobar) with the primary action for the current step, "Revisar antes de cerrar" with the clients without activity, last activities.
3. **Clientes** (`/clients`): list on the left (name/NIF, email, status, "Ver archivados"), detail panel on the right: editable client data, contract editor (fee, VAT, price per service, "Sin precio · no se factura"), "Nuevo servicio" form and "Añadir del catálogo del sector" (checkboxes; existing services ticked and disabled), Archivar / Reactivar.
4. **Actividades** (`/activities`): one-line quick add form, filters (month, client), table with Pendiente / Facturada per row and the CSV reference.
5. **Importar CSV** (dialog on `/activities`): preview table with Correcta / Error / Duplicada per row, "→ nombre interpretado" when a name was matched loosely, "Importar N actividades" only saves the correct rows.
6. **Cierre de mes** (`/billing`): month input + "Cerrar mes", warning banner with the idle clients, runs table (month, proposals, approved, total, En revisión / Cerrado, Exportar CSV), proposals of the selected run with status and Ver.
7. **Propuesta** (`/proposals/:id`): header with client and status, lines with quantities and prices, totals, activity annex, "Antes de aprobar" box, client card, actions Descargar PDF and Aprobar propuesta.
8. **Ajustes** (`/settings`): company name and NIF (issuer on the PDF).

## Copy conventions (Spanish UI)

- Money: `1.834,36 €` (dot for thousands, comma for decimals, space before the symbol). Dates: `28/09/2026`. Months: `Septiembre 2026`. The PDF prints `580,00 EUR` (Helvetica has no `€`).
- Statuses: Pendiente, Facturada, Borrador, Aprobada, En revisión, Cerrado, Activo, Archivado.
- Actions are verbs: Cerrar mes, Aprobar propuesta, Importar 7 actividades, Guardar contrato, Descargar PDF, Exportar CSV.
- Errors from the API arrive in English; React maps the status code (400 / 401 / 404 / 409) to its own Spanish messages (`errorText` in `src/front/api.js`, plus page-specific texts such as `activityError`).

## Phase 2 (after the capstone)

Visual redesign with a graphic designer's eye: real logo, palette with personality, typography with character, illustration and empty states. Inspiration: Mobbin, Refero, Screenlane, Dribbble/Behance ("invoicing dashboard", "field service app"), Land-book / SaaSpo / Godly for the landing, competitors Holded, Quipu, Pennylane, Jobber; tools Realtime Colors, Fontpair, Fontshare.
