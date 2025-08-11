# iTowVMS

Modern impound & vehicle management system built with Flask. Provides end‑to‑end tracking from tow intake through notices, compliance documents, auctions, release, and communication logging (email / future SMS & fax adapters).

---
## Key Features
* Vehicle lifecycle management (intake → notices → auction/release)
* TOP (Tow / Owner Notification) PDF generation & delivery tracking
* Release notice & auction advertisement PDF generation
* Multi‑document email sending with per‑document communication logs
* Contact & jurisdiction routing (auto‑detection helper)
* Auction management (vehicle assignment, document uploads, CSV export)
* Document clustering (batching for jurisdictional submissions)
* Action & compliance suggestions (context endpoint)
* Rich diagnostics & dashboard statistics
* Modular DB helpers + lightweight task scheduler
* Authentication (Flask-Login) with API token guard for programmatic routes

---
## Architecture Overview
Single Flask application (`app.py`) registers modular blueprints & route groups:

| Component | Purpose |
|-----------|---------|
| `app.py` | Primary app + core & UI/API routes, document generation helpers |
| `auction_routes.py` | Auction CRUD, vehicle assignment, exports, doc uploads |
| `cluster_routes.py` | Document clustering & bulk operations |
| `api_routes.py` | Extended reports, search, exports, workflow stats |
| `database/` | Initialization & data access helpers (vehicles, documents, communications, auctions, clusters, contacts, logs) |
| `utils.py` | Email + (placeholder) SMS/Fax senders, env loader, logging, computation helpers |
| `generator.py` | PDF generation (TOP, release, auction ad) |
| `auth.py` | User auth + decorators (`api_login_required`) |
| `scheduler.py` | Background scheduled maintenance / status checks |

Data persistence: SQLite (`vehicles.db`). A `communications` table logs every outbound attempt (email, sms, fax) with status & error diagnostics.

---
## Project Structure (abridged)
```
app.py
auction_routes.py
cluster_routes.py
api_routes.py
auth.py
database/               # DB access + schema creation (init_db)
generator.py            # PDF generation
utils.py                # Utilities + notification sending
static/                 # Assets & generated PDFs (static/generated_pdfs)
templates/              # Jinja2 HTML templates
requirements.txt
```

---
## Quick Start
```bash
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# (Optional) create .env for outbound email
cat > .env <<'EOF'
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_account@gmail.com
SMTP_PASSWORD=your_16_char_app_password
EMAIL_FROM=your_account@gmail.com
EOF

python app.py  # Runs on port 5001 per app.py
```
Navigate to: http://localhost:5001 (login page). Create or seed a user via existing auth utilities if not present.

---
## Environment Variables
| Variable | Description | Default / Notes |
|----------|-------------|-----------------|
| SMTP_HOST | SMTP server hostname | smtp.gmail.com |
| SMTP_PORT | Port (supports 587 STARTTLS, fallback 465) | 587 |
| SMTP_USERNAME | Auth user | — |
| SMTP_PASSWORD | Auth password / app password | — |
| EMAIL_FROM / FROM_EMAIL | From address override | username if unset |
| DATABASE_URL | Path to SQLite DB | auto set to vehicles.db |

The custom loader in `utils.py` re-reads `.env` on each send, enabling hot credential swaps without restart.

---
## Core Data Concepts
| Table | Purpose | Notable Columns |
|-------|---------|-----------------|
| vehicles | Master vehicle records | towbook_call_number, status, tow_date, jurisdiction, documents list (legacy ref) |
| documents | Stored / generated docs | id, vehicle_id, towbook_call_number, document_type (TOP, RELEASE, NEWSPAPER_AD, etc.), file_path, sent_via, sent_to |
| communications | Outbound attempts | document_id, method (email/fax/sms), destination, status, error, attachment_path |
| auctions / auction_vehicles | Auction events & membership | auction_date, auction_house, lot_number |
| document_clusters / cluster_documents | Logical bundling for batch actions | cluster_type, jurisdiction |
| contacts | Jurisdiction / destination routing | email_address, fax_number, preferred_contact_method |
| users | Auth | username, password hash |
| action_logs | Audit trail | action_type, user, details |

---
## Endpoint Catalog (Representative)
Authentication via session (browser) or API decorator (`@api_login_required`). Status codes: 2xx success, 4xx client issue, 5xx server error.

### Vehicles
| Method | Path | Purpose |
|--------|------|---------|
| POST | /api/vehicles/add | Create vehicle (multipart or JSON) |
| GET | /api/vehicles | Filtered vehicle list (query params: status, sort, direction, include_tracking) |
| GET/PUT/DELETE | /api/vehicles/<call_number> | Retrieve / update / delete vehicle |
| GET | /ui/vehicles?scope=active|completed|all | UI oriented vehicle list |
| GET | /ui/vehicles/<call_number>/context | Consolidated context, suggestions, communications |

### Document Generation & Management
| POST | /api/generate-top/<call_number> | Generate TOP PDF, auto-insert document |
| POST | /api/generate-release/<call_number> | Generate release notice (legacy path) |
| POST | /api/generate-release-notice/<call_number> | Generate release notice (helper) |
| POST | /api/generate-auction-ad/<auction_id> | Generate combined auction newspaper ad |
| POST | /api/vehicles/<call_number>/documents | Upload documents to vehicle |
| GET | /api/vehicles/<call_number>/documents | List vehicle documents |
| DELETE | /api/documents/<document_id> | Delete document |

### Communications & Delivery
| POST | /api/documents/<document_id>/send | Send single document via email/fax/sms |
| GET | /api/documents/<document_id>/communications | List comm logs for doc |
| POST | /api/vehicles/<call_number>/send-documents | Batch email multiple docs (one email, multi attachments) |
| POST | /api/top-forms/<call_number>/send | Mark TOP as sent (delivery tracking update) |
| POST | /api/release-forms/<call_number>/send | Send / log release notice |

### Auctions
| GET | /api/auctions | List auctions |
| POST | /api/auctions | Create auction (supports file upload) |
| POST | /api/auctions/<id>/vehicles | Add vehicle to auction |
| DELETE | /api/auctions/<id>/vehicles/<call_number> | Remove vehicle |
| GET | /api/auctions/<id>/eligible-vehicles | List eligible candidates |
| GET | /api/auctions/<id>/export-csv-detailed | Detailed CSV export |
| POST/GET | /ui/auctions/<id>/documents | Upload / list auction docs (UI endpoints) |

### Document Clusters
| GET | /api/document-clusters | List clusters (optional jurisdiction filter) |
| POST | /api/document-clusters | Create cluster |
| GET/POST | /api/document-clusters/<id>/documents | List / add documents to cluster |
| POST | /api/document-clusters/<id>/auto-populate | Criteria-based bulk add |

### Search / Reports / Dashboard
| GET | /api/vehicles/search | Multi-field vehicle search |
| GET | /api/vehicles/export/<csv|json> | Export vehicles |
| GET | /api/statistics | Global statistics |
| GET | /api/workflow-counts | Workflow counters |
| GET | /api/reports?start_date=&end_date=&type= | Time‑bounded status & processing metrics |
| GET | /api/dashboard/summary | Lightweight KPI summary |

### Diagnostics / Misc
| GET | /api/diagnostic | DB + path health summary |
| GET | /debug/context/<call_number> | (Debug) raw vehicle context (unauth) |

UI endpoints (`/dashboard`, `/document-management`, `/auction-management`, `/tracking`, etc.) render templates and rely on logged-in session.

---
## Email & Future Notification Abstraction
`utils.send_email_notification(recipient, subject, body, attachment|attachments=[])` auto:
* Reloads SMTP settings from `.env`
* Classifies auth vs transport failures
* Tries STARTTLS then SSL fallback
* Supports single path or list of attachment file paths

Placeholders: `send_sms_notification`, `send_fax_notification` — currently stubs; integrate provider SDK (e.g., Twilio, Phaxio) behind same signature returning `(success, message_or_error)`.

`communications` table rows flow:
1. Pending row inserted (method, destination, attachment reference)
2. Send attempt executed
3. Status updated to `sent` or `failed` with error text

---
## Suggested Operational Workflow
1. Intake vehicle via `/api/vehicles/add`
2. Generate TOP form → `/api/generate-top/<call_number>`
3. Send TOP (or batch multiple docs) → `/api/documents/<id>/send` or `/api/vehicles/<call_number>/send-documents`
4. Monitor `/ui/vehicles/<call_number>/context` for suggested next actions
5. Assign vehicle to auction when eligible → `/api/auctions/<id>/vehicles`
6. Generate auction ad + cluster docs for jurisdictional packet
7. Generate & send release notice upon disposition

---
## Development Notes
* Avoid committing secrets: `.env`, `*.db`, generated PDFs & logs are ignored via `.gitignore`.
* Legacy `database.py` exists alongside `database/` package; imports use the package (`from database import ...`).
* Communication logging expects `init_db()` run on startup (already invoked in `app.py`).
* Generated PDFs stored under `static/generated_pdfs/` (file_path stored as relative name when added via `add_document`).

### Running Tests
If test files are present (e.g., `test_*.py`) run:
```bash
pytest -q
```

---
## Future Enhancements (Planned / Suggested)
* Real SMS / Fax provider integration (Twilio / Phaxio) with retry + backoff
* Async send queue (RQ / Celery) for large batches
* Granular role-based permissions
* ZIP bundling for batch document deliveries
* Metrics dashboard with streaming updates (WebSocket)
* Data migration scripts for legacy document schema normalization
* PII redaction / structured audit export

---
## Contributing
1. Fork & branch (`feat/<topic>`)
2. Add/adjust tests for changes
3. Ensure lint & tests pass
4. Open PR with concise summary; include endpoints or schema changes

See `CONTRIBUTING.md` for broader guidelines.

---
## License
Not specified. Add a LICENSE file if open sourcing (MIT recommended for simplicity).

---
## Support / Diagnostics Cheat Sheet
| Task | Command / Action |
|------|------------------|
| DB health | GET /api/diagnostic |
| Vehicle context | GET /ui/vehicles/<call_number>/context |
| Re-run TOP generation | POST /api/generate-top/<call_number> |
| Batch email docs | POST /api/vehicles/<call_number>/send-documents |
| List comms for doc | GET /api/documents/<doc_id>/communications |

---
## Disclaimer
This system is provided as-is. Verify statutory notice timing (e.g., MCL 257.252b) against local legal counsel before production use.

