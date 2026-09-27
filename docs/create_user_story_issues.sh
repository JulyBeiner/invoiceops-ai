#!/usr/bin/env bash
# Creates one GitHub issue per user story from docs/SPECS.md.
# Run once from the repo root inside the Codespace:  bash docs/create_user_story_issues.sh
# Requires the GitHub CLI (gh), already installed and logged in on Codespaces.
set -e

REPO="JulyBeiner/invoiceops-ai"

gh label create "user-story" --repo "$REPO" --color 0E8A16 --description "Product backlog item" --force
gh label create "stretch" --repo "$REPO" --color FBCA04 --description "Only if time allows" --force

create_issue() {  # $1 = title, $2 = body, $3 = extra labels (optional), $4 = "close" to close it
  local url
  url=$(gh issue create --repo "$REPO" --title "$1" --body "$2" --label "user-story${3:+,$3}")
  echo "Created: $url"
  if [ "$4" = "close" ]; then
    gh issue close "$url" --repo "$REPO" --comment "Done in block 2/3."
  fi
}

create_issue "US-01: As a business owner, I can register my company and my account so that I can start using InvoiceOps." \
"**Acceptance criteria**
- [x] Creates the company (tenant) and the owner user in one step.
- [x] Email already in use -> error 409, nothing is created.
- [x] Password shorter than 8 characters -> error 400." "" close

create_issue "US-02: As a user, I can log in with email and password so that I access my company's data." \
"**Acceptance criteria**
- [x] Correct credentials -> access token.
- [x] Wrong password or unknown email -> error 401 with a generic message.
- [x] Every request with the token only returns data from my company." "" close

create_issue "US-03: As a user, I can request a password reset link by email so that I recover access." \
"**Acceptance criteria**
- [x] Email sent through a third-party email API (Brevo).
- [x] Unknown email -> same success message (no account enumeration).
- [x] Link expires after 1 hour." "" close

create_issue "US-04: As a user, I can set a new password from the reset link." \
"**Acceptance criteria**
- [x] Valid link -> password updated, old one stops working.
- [x] Expired or tampered link -> error 400." "" close

create_issue "US-05: As an admin, I can create, edit, list and archive clients so that I can bill them." \
"**Acceptance criteria**
- [x] Name is required; tax id and email optional.
- [x] Archived clients are hidden from the month close.
- [x] I never see clients from another company." "" close

create_issue "US-06: As an admin, I can define a client's contract (fixed monthly fee, price per service, VAT) so that billing is automatic." \
"**Acceptance criteria**
- [x] A contract belongs to one client; one active contract per client.
- [x] Prices have 2 decimals; VAT rate defaults to 21 %.
- [x] A service without a price in the contract cannot be billed." "" close

create_issue "US-07: As an admin, I can record a completed service for a client (date, service, quantity) so that it gets billed." \
"**Acceptance criteria**
- [ ] Quantity must be greater than 0; date is required.
- [ ] Cannot add activity to a month that is already closed."

create_issue "US-08: As an admin, I can import activities from a CSV file so that I don't type them one by one." \
"**Acceptance criteria**
- [ ] Shows a preview with errors per row before importing.
- [ ] Rows with an already imported external id are skipped (no duplicates).
- [ ] Malformed file -> clear error, nothing imported."

create_issue "US-09: As an admin, I can generate the billing proposals for a month so that every client gets its invoice draft." \
"**Acceptance criteria**
- [ ] One proposal per client with activity or with a fixed fee.
- [ ] Every proposal line links to the activities it comes from.
- [ ] Totals include subtotal, VAT and total.
- [ ] Running the close twice for the same month does not duplicate proposals."

create_issue "US-10: As an admin, I can review a proposal, see the activities behind each line, and approve it." \
"**Acceptance criteria**
- [ ] Approving locks its activities so they cannot be billed again.
- [ ] An approved proposal cannot be edited.
- [ ] Clients with a contract but no activity in the month are flagged."

create_issue "US-11: As an admin, I can download a proposal as PDF so that I can send it to my client." \
"**Acceptance criteria**
- [ ] PDF contains company data, lines, totals and an annex with the activity dates."

create_issue "US-12: As an admin, I can export the approved proposals of a month as CSV so that I can import them into my invoicing tool." \
"**Acceptance criteria**
- [ ] CSV with one row per approved proposal (client, subtotal, VAT, total).
- [ ] Importable into the company's invoicing tool (Holded, Quipu...)."

create_issue "US-13: As a user, I can see a dashboard with this month's activities, pending proposals and totals so that I know where billing stands." \
"**Acceptance criteria**
- [ ] Shows this month's activity count, pending proposals and totals.
- [ ] Only data from my company."

create_issue "US-14: As an admin, I can paste WhatsApp messages and get suggested activities to confirm, so that I don't retype them." \
"**Acceptance criteria**
- [ ] Suggestions come from an AI API; nothing is saved until I confirm.
- [ ] The AI never calculates prices or totals; the billing engine does." "stretch"

echo "All 14 issues created. Now open https://github.com/$REPO/projects, create a Board and add these issues to it."
