# Command-Line Login System

[Live Frontend](https://command-line-login-system.vercel.app)

---

## Overview

This repository implements a secure **CLI-style authentication system** with a React terminal UI and a Django REST API backend. The application is designed to demonstrate:

- **Secure credential management** with username/password authentication
- **TOTP-based two-factor authentication** for account hardening
- **JWT access and refresh token flow** with client-side refresh retries
- **Backend session persistence and revocation** for strong session control
- **A polished developer experience** with a terminal-inspired frontend

This is more than a toy app: it is built as a production-ready auth system with hardened login flows, session auditing, and a clear separation between frontend interactions and backend security.

## Live Application

- **Frontend URL**: https://command-line-login-system.vercel.app
- **Backend URL**: https://command-line-login-system-api.onrender.com

---

## Tech Stack

- **Frontend**: React + Vite
- **Backend**: Django + Django REST Framework
- **Authentication**: djangorestframework-simplejwt
- **2FA / TOTP**: pyotp + qrcode
- **Database**: SQLite for local development
- **Deployment**: Vercel for frontend, Render for backend

---

## Why This Project Stands Out

- **Terminal-inspired UX**: The frontend mimics a CLI environment, providing a unique user interaction model while remaining accessible and responsive.
- **Robust 2FA implementation**: Supports TOTP onboarding, QR provisioning, verification, and disablement.
- **Server-side session validation**: A custom middleware layer verifies active sessions on every protected request.
- **Automatic token refresh**: The frontend automatically refreshes expired access tokens and retries requests with the new token.
- **Security-first design**: Includes brute-force throttling, lockout controls, and session revocation on logout.

---

## Architecture Overview

### Frontend

- `frontend/src/App.jsx`: orchestrates terminal command flow, multi-step login/register flows, and command output.
- `frontend/src/api/client.js`: Axios client with authorization header injection and 401 retry logic.
- `frontend/src/hooks/useAuth.js`: manages auth state, token storage, session lifecycle, and user actions.
- `frontend/src/hooks/useSessionCountdown.js`: implements countdown and automatic logout when the session expires.
- `frontend/src/utils/commandParser.js`: routes CLI-style commands into typed actions.

### Backend

- `backend/apps/accounts/views.py`: API views for register, login, logout, enable/verify/disable TOTP.
- `backend/apps/accounts/models.py`: custom user model with TOTP state and login audit functions.
- `backend/apps/accounts/serializers.py`: validation and serialization for registration and user details.
- `backend/apps/sessions_app/models.py`: session persistence model for backend session tracking.
- `backend/apps/sessions_app/middleware.py`: middleware enforcing session validity on each request.

---

## Detailed Implementation

### 1. Authentication and Authorization

- Uses Django `authenticate()` for username/password verification.
- Issues JWT `access` and `refresh` tokens at login with `RefreshToken.for_user(user)`.
- Stores the refresh token `jti` in a `UserSession` record for server-side session validation.
- Protects endpoints with DRF `IsAuthenticated` where needed.

### 2. Two-factor Authentication (TOTP)

- `POST /api/auth/2fa/enable/`: generates and stores a new TOTP secret, returns a base64 QR code image.
- `POST /api/auth/2fa/verify/`: verifies the TOTP code and marks the user’s 2FA as confirmed.
- `POST /api/auth/2fa/disable/`: requires both password and current TOTP code to disable 2FA.

This ensures attacker resistance even if credentials are compromised.

### 3. Session Management and Security

- `UserSession` tracks `jti`, `expires_at`, `ip_address`, `user_agent`, and `is_active`.
- A custom middleware checks whether the access token is associated with an active user session.
- If a session is expired or terminated, the middleware returns a clear `401` response.
- Logout blacklists the refresh token and deactivates the backend session.

### 4. Frontend Resilience

- Axios request interceptor adds the current access token to every request.
- If a protected request returns `401`, the response interceptor tries token refresh.
- After refresh, the original request is retried with the new access token.
- If refresh fails, the app clears local storage and triggers logout.

---

## API Reference

### Auth Endpoints

- `POST /api/auth/register/`
  - payload: `{ username, email, password, password_confirm }`
  - success: user details and message

- `POST /api/auth/login/`
  - payload: `{ username, password, totp_code? }`
  - success: `{ access, refresh, user, session_expires_at }`
  - if TOTP-managed account needs code, returns `requires_totp`

- `POST /api/auth/token/refresh/`
  - payload: `{ refresh }`
  - success: `{ access }`

- `POST /api/auth/logout/`
  - payload: `{ refresh }`
  - success: logout confirmation

### 2FA Endpoints

- `POST /api/auth/2fa/enable/`
  - returns a QR code URI and TOTP secret

- `POST /api/auth/2fa/verify/`
  - payload: `{ code }`
  - confirms 2FA setup

- `POST /api/auth/2fa/disable/`
  - payload: `{ password, code }`
  - disables 2FA after validation

---

## Setup Instructions

### Clone repository

```bash
git clone <repo-url>
cd "Osto Assignment"
```

### Backend setup

```bash
cd backend
python -m venv venv
# Windows
.\venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## Environment Configuration

#### Frontend local
- `frontend/.env`
  - `VITE_API_URL=http://localhost:8000`

#### Frontend production
- `frontend/.env.production`
  - `VITE_API_URL=https://command-line-login-system-api.onrender.com`

#### Backend required envs
- `SECRET_KEY`
- `DEBUG=False`
- `ALLOWED_HOSTS=command-line-login-system-api.onrender.com,localhost,127.0.0.1`
- `CORS_ALLOWED_ORIGINS=https://command-line-login-system.vercel.app,http://localhost:3000`
- `TOTP_ISSUER_NAME=Command-Line Login System`
- `SESSION_TIMEOUT_MINUTES=30`
- `ACCOUNT_LOCKOUT_ATTEMPTS=5`
- `ACCOUNT_LOCKOUT_MINUTES=15`

---

## Testing

Run backend tests from the backend directory:

```bash
cd backend
python manage.py test
```

The project is structured so tests can validate auth flows, session behavior, and model logic.

---

## Technical Notes for Senior Engineers

### Security design decisions

- **Server-side session tracking** complements JWT validation and supports revocation.
- **Refresh token lifecycle** is decoupled from the access token, allowing short-lived access and longer refresh validity.
- **TOTP enablement** is intentionally gated by a confirm step to prevent partially enabled 2FA states.
- **Account lockout** protects against brute-force password attacks.

### Maintainability

- The frontend separates concerns with reusable hooks (`useAuth`, `useCommandHistory`, `useSessionCountdown`).
- Backend views are lean and intentionally do not contain UI logic.
- Serializers enforce data integrity and validation for user registration.
- Middleware enforces session policy globally while allowing exempt routes.

### Extensibility

This codebase is designed to extend easily for:

- role-based access control
- password reset flows
- multi-device session management
- PostgreSQL production deployment
- richer CLI command actions and help content

---

## Summary

This project is a secure, production-minded authentication system with a clean terminal UI and a strong backend security posture. It includes the end-to-end pipeline from registration to TOTP-protected login, refresh token handling, and session enforcement.

If you want, I can also add a dedicated section for repository structure, future improvements, and explicit API contract examples.

