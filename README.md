# Qatar Foundation — Admin Portal

A full-stack web application providing an admin portal for managing opportunities at Qatar Foundation. Built with a Python/Flask REST API backend and a pre-built frontend UI.

---

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Features](#features)
- [Security](#security)

---

## Overview

The Qatar Foundation Admin Portal allows registered admins to securely log in and manage internship/volunteer opportunities. Each admin account is isolated — admins can only view, create, edit, and delete opportunities they personally created.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10+, Flask |
| Database | SQLite via Flask-SQLAlchemy |
| Auth | Session-based (Werkzeug password hashing) |
| CORS | Flask-CORS |
| Frontend | Pre-built UI (HTML/CSS/JS) |

---

## Project Structure

```
├── app.py               # Main Flask application — all routes
├── models.py            # SQLAlchemy database models
├── config.py            # App configuration
├── requirements.txt     # Python dependencies
├── instance/
│   └── database.db      # SQLite database (auto-created on first run)
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- pip

### Installation

**1. Clone the repository**

```bash
git clone https://github.com/Neerajvs32/Test1.git
cd Test1
```

**2. Create and activate a virtual environment**

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Run the application**

```bash
python app.py
```

The backend will start at `http://localhost:5000`.

The SQLite database (`database.db`) is created automatically on first run — no setup required.

---

## Environment Variables

The app works out of the box with defaults. For production, set the following:

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `change-this-in-production-abc123xyz` | Flask session secret key — **must be changed in production** |

---

## API Reference

### Auth

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| POST | `/signup` | Register a new admin account | No |
| POST | `/login` | Log in and start a session | No |
| POST | `/logout` | End the current session | Yes |
| POST | `/forgot-password` | Request a password reset link | No |
| POST | `/reset-password` | Reset password using a token | No |

### Opportunities

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| GET | `/opportunities` | List all opportunities for the logged-in admin | Yes |
| POST | `/opportunities` | Create a new opportunity | Yes |
| GET | `/opportunities/<id>` | Get full details of a single opportunity | Yes |
| PUT | `/opportunities/<id>` | Update an existing opportunity | Yes |
| DELETE | `/opportunities/<id>` | Permanently delete an opportunity | Yes |

---

### Request & Response Examples

#### POST `/signup`

```json
// Request
{
  "full_name": "Sarah Ahmed",
  "email": "sarah@example.com",
  "password": "securepass123",
  "confirm_password": "securepass123"
}

// Response 201
{
  "message": "Account created successfully. Please log in."
}
```

#### POST `/login`

```json
// Request
{
  "email": "sarah@example.com",
  "password": "securepass123",
  "remember_me": true
}

// Response 200
{
  "message": "Login successful.",
  "admin": {
    "id": 1,
    "full_name": "Sarah Ahmed",
    "email": "sarah@example.com"
  }
}
```

#### POST `/opportunities`

```json
// Request
{
  "name": "Full Stack Development Internship",
  "category": "Technology",
  "duration": "3 months",
  "start_date": "2025-09-01",
  "description": "Work alongside senior engineers on real products.",
  "skills": "React, Node.js, PostgreSQL",
  "future_opportunities": "Full-time offer upon completion",
  "max_applicants": 10
}

// Response 201
{
  "message": "Opportunity created.",
  "opportunity": { ... }
}
```

---

## Features

### Task 1 — Authentication

- **Sign Up** — Full validation: email format, minimum 8-character password, confirm password match, duplicate email detection
- **Login** — Generic error messages to prevent user enumeration. Remember Me keeps session active for 30 days; without it the session ends when the browser closes
- **Forgot Password** — Generates a secure token (valid for 1 hour) and logs the reset link internally. Always returns the same response regardless of whether the email exists, protecting user privacy
- **Reset Password** — Validates the token, checks expiry, and updates the password securely

### Task 2 — Opportunity Management

- **View Opportunities** — Loads all opportunities created by the logged-in admin from the database. Shows an empty state when none exist
- **Create Opportunity** — Saves all fields: name, category, duration, start date, description, skills, future opportunities, and optional max applicants
- **View Details** — Full detail view for any single opportunity
- **Edit Opportunity** — Pre-fills the form with existing data. Same validations apply as on creation
- **Delete Opportunity** — Requires ownership — admins can only delete their own opportunities
- **Data Isolation** — Admins cannot view or access opportunities created by other accounts

---

## Security

- Passwords are hashed using **Werkzeug's PBKDF2-SHA256** — never stored in plain text
- Session data is server-side; session cookies are `HttpOnly` and `SameSite=Lax`
- All opportunity endpoints verify **ownership** before allowing edit or delete — a 403 is returned if the logged-in admin does not own the resource
- Forgot password always returns the same response to prevent **email enumeration**
- Password reset tokens are single-use, expire after **1 hour**, and are invalidated on use

---

## HTTP Status Codes

| Code | Meaning |
|---|---|
| 200 | Success |
| 201 | Resource created |
| 400 | Validation error / bad request |
| 401 | Not authenticated |
| 403 | Authenticated but not authorised |
| 404 | Resource not found |
| 409 | Conflict (e.g. email already registered) |
