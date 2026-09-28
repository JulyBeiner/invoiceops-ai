# InvoiceOps — Design notes

Screens (v1, 7 artboards, clickable prototype): https://claude.ai/artifact/39LPv541pVYfRQFnj7eRyk

Target user: the person who runs the administration of a small B2B cleaning or maintenance company in Spain. Closes the month from a laptop, in a hurry, and needs to trust the numbers. The look is sober and trustworthy (deep navy) with one warm accent (terracotta) reserved for the main action of each screen.

## Palette (CSS variables in `src/front/index.css`)

| Variable | Value | Use |
| ---------------- | --------- | ------------------------------------------------ |
| `--io-navy` | `#17334F` | sidebar, headings, secondary button text |
| `--io-navy-2` | `#2A4D74` | avatar, hover on navy |
| `--io-accent` | `#B4531E` | primary buttons, brand mark, current step |
| `--io-accent-2` | `#98441A` | primary button hover |
| `--io-ground` | `#F4F2EC` | page background |
| `--io-surface` | `#FFFFFF` | cards, tables, inputs |
| `--io-border` | `#E3DFD5` | card borders; `#EEEBE3` for table row lines |
| `--io-text` | `#1B2430` | body text |
| `--io-muted` | `#566070` | secondary text (4.5:1 on white) |
| `--io-nav-text` | `#B9C7D6` | sidebar inactive links |

Status colors (badge background / text):

| Status | Background | Text | Where |
| ------------------------ | --------- | --------- | -------------------------------------- |
| Pendiente / Borrador / En revisión | `#FCF0D6` | `#7A4E0B` | unbilled activity, draft proposal, open run |
| Facturada / Aprobada / Activo | `#E1F2E8` | `#1F6B45` | billed activity, approved proposal |
| Cerrado | `#E4EBF3` | `#17334F` | closed run |
| Archivado / Duplicada | `#ECEAE3` | `#566070` | archived client, duplicate CSV row |
| Error / Sin precio | `#FBE5E1` | `#9B2C1B` | CSV error row, unpriced activity |

Colors that must be told apart also differ in lightness (amber vs green vs navy), not only in hue.

## Typography

Google Fonts (one `<link>` in `index.html`): **Fraunces** 600/700 for page titles, card titles and big figures; **IBM Plex Sans** 400/500/600 for everything else. Numbers use `font-variant-numeric: tabular-nums` so columns of money line up.

## Layout

- Fixed left sidebar, 232 px, navy: brand (check mark in an accent square + "InvoiceOps"), five links (Inicio, Clientes, Actividades, Cierre de mes, Ajustes), user block at the bottom with "Cerrar sesión".
- Main area: padding 32 px 40 px; page header = title (30 px Fraunces) + one-line subtitle on the left, actions on the right.
- Cards: white, 1 px border `--io-border`, radius 12 px, flat (no shadow). Tables inside cards, header row uppercase 12 px muted.
- Buttons: 40 px high, radius 8 px, weight 600. Primary = accent background, white text; secondary = white with border; ghost = no border. One primary button per screen.
- Badges: pill, 24 px high, 12 px bold, colors from the table above.
- Inputs: 40 px high, radius 8 px, border `#CFC9BC`; money inputs right-aligned with the unit (`€`, `%`) inside the field.

Bootstrap 5 provides the grid, forms, tables and utilities; `index.css` overrides `--bs-primary`, fonts, radius and the sidebar. No component library beyond Bootstrap.

## Screens

1. **Acceso** (`/login`, `/register`, `/forgot-password`, `/reset-password`): split layout, navy panel with the value proposition on the left, one card form on the right.
2. **Inicio** (`/`): month selector, four counters (`GET /api/dashboard`), the three steps of the month (register → close → approve) with the primary action for the current step, "Revisar antes de cerrar" warnings, last activities.
3. **Clientes** (`/clients`): list on the left (name, contract summary, activities this month, status), detail panel on the right with the contract editor (fee, VAT, price per service, "Sin precio · no se factura").
4. **Actividades** (`/activities`): one-line quick add form, filters (month, client, status), table with billing status per row.
5. **Importar CSV** (dialog on `/activities`): preview table with Correcta / Error / Duplicada per row, message under the row, "Importar N actividades" only saves the correct rows.
6. **Cierre de mes** (`/billing`): runs table (month, proposals, approved, total, status, Exportar CSV when closed), proposals of the selected run with status and Ver / PDF.
7. **Propuesta** (`/proposals/:id`): lines with quantities and prices, totals, activity annex, "Antes de aprobar" box, actions Descargar PDF and Aprobar propuesta.

## Copy conventions (Spanish UI)

- Money: `1.834,36 €` (dot for thousands, comma for decimals, space before the symbol). Dates: `28/09/2026`. Months: `Septiembre 2026`.
- Statuses: Pendiente, Facturada, Borrador, Aprobada, En revisión, Cerrado, Activo, Archivado.
- Actions are verbs: Cerrar septiembre, Aprobar propuesta, Importar 9 actividades, Guardar contrato, Descargar PDF, Exportar CSV.
- Errors from the API arrive in English; React maps the status code (400 / 401 / 404 / 409) to its own Spanish messages.
