# 📦 RFID Inventory Management System

A browser-based inventory management dashboard built with **Django** and **PostgreSQL**, secured by physical **RFID card authentication**. Users tap their RFID card on a USB reader to unlock the terminal — no passwords required.

---

## ✨ Features

- 🔒 **RFID Authentication** — USB HID card reader acts as a keyboard; card tap auto-submits the login form
- 📦 **Inventory Management** — Browse products, view stock levels, and take items
- 🛒 **Cart & Checkout** — Select quantities, review cart, and confirm checkout atomically
- 📋 **Transaction Log** — Full history of every checkout with user, timestamp, and items
- 🔍 **Access Log** — Security audit trail of every scan attempt (granted & denied)
- ⚠️ **Low Stock Alerts** — Dashboard highlights products below reorder threshold
- 🛡️ **Role-Based Access** — Technician, Engineer, Supervisor, and Admin roles
- 🗄️ **PostgreSQL Backend** — Production-ready relational database

---

## 🖥️ Tech Stack

| Layer | Technology |
|---|---|
| Web Framework | Django 4.2+ |
| Database | PostgreSQL 15+ |
| DB Adapter | psycopg2-binary |
| Server | Django dev server (WSGI) |
| Frontend | Django Templates + Vanilla JS |
| Auth | RFID USB HID (keyboard emulation) + Django sessions |

---

## 🔌 Hardware Requirements

| Component | Recommendation | Notes |
|---|---|---|
| RFID Reader (dev) | ACR122U USB NFC Reader | Plug-and-play USB HID, ~$30–50 |
| RFID Reader (production) | ZKTeco CR10M | Wall-mountable, LED ring + beeper, ~$40–80 |
| RFID Cards | Mifare Classic 1K (13.56 MHz) | Must match reader frequency |
| Host Machine | Any Windows/Linux PC or Raspberry Pi | Running the Django server |

> **Windows users:** The USB reader registers as a HID keyboard device automatically — no drivers needed.

---

## 📁 Project Structure

```
rfid_inventory/
├── manage.py
├── requirements.txt
├── rfid_reader.py                  ← Optional: WebSocket bridge for Method B
├── rfid_inventory/                 ← Django project config
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── inventory/                      ← Main application
    ├── models.py                   ← RFIDUser, Product, Transaction, AccessLog
    ├── views.py                    ← All view logic + RFID authentication
    ├── forms.py                    ← RFIDLoginForm
    ├── urls.py                     ← URL routing
    ├── admin.py                    ← Django admin configuration
    ├── management/
    │   └── commands/
    │       ├── seed.py             ← Sample data seeder
    │       └── run_rfid_reader.py  ← Management command for reader bridge
    └── templates/
        └── inventory/
            ├── base.html
            ├── login.html
            ├── dashboard.html
            ├── inventory_list.html
            ├── product_detail.html
            ├── cart.html
            ├── checkout_confirm.html
            ├── checkout_success.html
            ├── transaction_log.html
            └── access_log.html
```

---

## ⚙️ Installation & Setup

### Prerequisites

- Python 3.10+
- PostgreSQL 13+ installed and running
- A USB RFID reader (or use manual code entry for testing)

### 1. Clone the repository

```bash
git clone https://github.com/your-username/rfid-inventory.git
cd rfid-inventory
```

### 2. Create and activate a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up PostgreSQL

Open `psql` or pgAdmin and run:

```sql
CREATE DATABASE rfid_inventory;
CREATE USER rfid_user WITH PASSWORD 'yourpassword';
GRANT ALL PRIVILEGES ON DATABASE rfid_inventory TO rfid_user;
```

### 5. Configure the database

Edit `rfid_inventory/settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.postgresql',
        'NAME':     'rfid_inventory',
        'USER':     'rfid_user',
        'PASSWORD': 'yourpassword',   # ← change this
        'HOST':     'localhost',
        'PORT':     '5432',
    }
}
```

### 6. Apply migrations

```bash
python manage.py makemigrations inventory
python manage.py migrate
```

### 7. Seed sample data

```bash
python manage.py seed
```

This creates 3 RFID users, 5 product categories, and 6 sample products.

### 8. Create a Django admin superuser

```bash
python manage.py createsuperuser
```

### 9. Start the server

```bash
python manage.py runserver
```

Open your browser at **http://127.0.0.1:8000**

---

## 🔑 Default RFID Test Codes

Use these to log in during development (type manually or scan if reader is connected):

| Name | RFID Code | Role | Department |
|---|---|---|---|
| Andi Pratama | `RFID-A1B2` | Technician | Maintenance |
| Sari Dewi | `RFID-C3D4` | Supervisor | Operations |
| Budi Santoso | `RFID-E5F6` | Engineer | R&D |

---

## 🌐 URL Reference

| URL | Page | Access |
|---|---|---|
| `/login/` | RFID login terminal | Public |
| `/dashboard/` | Main dashboard | RFID authenticated |
| `/inventory/` | Product list | RFID authenticated |
| `/inventory/<id>/` | Product detail + add to cart | RFID authenticated |
| `/cart/` | Cart review | RFID authenticated |
| `/checkout/` | Checkout confirmation | RFID authenticated |
| `/log/` | Transaction history | RFID authenticated |
| `/access-log/` | RFID scan audit log | Supervisor / Admin only |
| `/admin/` | Django admin panel | Django superuser |

---

## 🔌 RFID Integration — How It Works

This project uses **Method A: USB HID Keyboard Emulation** — the simplest and most reliable approach for Windows.

```
Card tap
  ↓
USB Reader types card ID as keystrokes into the browser input field
  ↓
JavaScript detects the input and auto-submits the form
  ↓
Django view queries PostgreSQL: does this RFID code exist?
  ↓
  ├── Found & active   → create session → redirect to /dashboard/
  ├── Found & inactive → log denial    → show "Access revoked" error
  └── Not found        → log denial    → show "Card not registered" error
  ↓
Every attempt is recorded in RFIDAccessLog with timestamp + IP address
```

### Why Method A and not WebSockets?

| | Method A (HID) | Method B (WebSocket) |
|---|---|---|
| Setup | Plug reader in, done | Requires Django Channels + Daphne |
| Works on Windows | ✅ Native HID support | ⚠️ Extra dependencies |
| Browser focus needed | Yes — login page must be open | No — push from server |
| Suitable for | Single-terminal kiosk | Multi-terminal enterprise |

---

## 🗄️ Database Schema

```
RFIDUser          ← People with RFID cards
  ├── rfid_code   (unique, indexed)
  ├── full_name
  ├── role        (technician / supervisor / engineer / admin)
  ├── department
  ├── is_active
  └── last_seen_at / login_count

RFIDAccessLog     ← Every scan attempt (granted or denied)
  ├── rfid_code
  ├── rfid_user   (FK → RFIDUser, nullable for unknown cards)
  ├── result      (granted / denied)
  ├── scanned_at
  └── ip_address

Category          ← Product categories
Product           ← Inventory items
  ├── stock / max_stock / reorder_threshold
  └── location (e.g. "Rack A-1")

Transaction       ← A checkout event
  └── rfid_user, checked_out_at

TransactionItem   ← Line items inside a transaction
  └── product, quantity, product_name_snapshot
```

---

## 🛡️ Security Notes

- Every RFID scan (successful or denied) is written to `RFIDAccessLog` with timestamp and IP — providing a full audit trail
- Inactive users are blocked even if their card code exists in the database
- Sessions expire when the browser closes (`SESSION_EXPIRE_AT_BROWSER_CLOSE = True`) and have a 1-hour hard limit
- The login form strips non-printable characters to handle reader encoding quirks
- Only Supervisors and Admins can view the `/access-log/` page
- In production, set `DEBUG = False` and use a strong random `SECRET_KEY`

---

## 🚀 Production Checklist

Before deploying to a real environment:

- [ ] Set `DEBUG = False` in `settings.py`
- [ ] Generate a new `SECRET_KEY` — never use the default
- [ ] Set `ALLOWED_HOSTS` to your actual domain or IP
- [ ] Use environment variables for database credentials (e.g. `python-decouple` or `django-environ`)
- [ ] Serve static files via WhiteNoise or a proper web server (Nginx)
- [ ] Run behind Gunicorn + Nginx instead of `manage.py runserver`
- [ ] Use Redis as the session backend for multi-server setups
- [ ] Enable HTTPS — RFID codes travel in POST body, protect them in transit

---

## 🧪 Running Without a Physical RFID Reader

You can test the full system manually:

1. Open `http://127.0.0.1:8000/login/`
2. Click the input field (it auto-focuses)
3. Type any seeded RFID code (e.g. `RFID-A1B2`)
4. Press **Enter** or click **Unlock**

The system behaves identically — the only difference is a human types the code instead of the reader.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙋 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you'd like to change.

1. Fork the repo
2. Create your feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request
