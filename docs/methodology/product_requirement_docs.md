# Product Requirement Document — G&M Internal Management Tool

## 1. Overview

G&M Internal Management Tool is a full-stack web application for managing legal processes, organizations, subscriptions, and document workflows within a law firm (**G&M Consultores Jurídicos**). It streamlines interactions between lawyers and clients through a role-based system, enabling case tracking, dynamic document generation, electronic signatures, organization management, and subscription-based billing.

The platform is built as a **Progressive Web App (PWA)** with a **Django REST API** backend and a **Vue 3 SPA** frontend.

---

## 2. Problems Solved

| Problem | Solution |
|---------|----------|
| Manual legal case tracking | Digital process management with stages, case files, and activity tracking |
| Paper-based document workflows | Dynamic document builder with template variables, permissions, and electronic signatures |
| Fragmented client-lawyer communication | Centralized dashboard, legal/corporate request workflows, and organization posts |
| No billing automation | Subscription plans with recurring payments via Wompi gateway and Huey scheduled tasks |
| Manual discovery of public procurement opportunities | SECOP II synchronization, search, classification, alerts, saved views, and export |
| Lack of access control | Role-based system (Client, Lawyer, Basic, Corporate Client) with fine-grained document permissions |
| No offline access | PWA with service worker for offline readiness and installable app experience |

---

## 3. Target Users

| Role | Description | Key Capabilities |
|------|-------------|------------------|
| **Lawyer** | Law firm staff who manage cases and documents | Create/edit processes, manage dynamic documents, respond to requests, publish legal updates, generate reports, manage organizations |
| **Admin** | Operations / system administrators (`role='admin'` or `is_staff=true` or `is_superuser=true`) | All lawyer capabilities plus: services catalog admin (`/services_admin`), Django admin panel, user role assignment, override permissions |
| **Client** | End users who track their legal cases | View processes, submit legal requests, fill/sign documents, view legal updates, join organizations |
| **Basic** | Registered users without active subscription | Limited access, can upgrade via subscription |
| **Corporate Client** | Organization administrators | Create organizations, manage members/invitations, handle corporate requests, publish posts |

### Role Hierarchy — `lawyer-like` Predicate

Users that satisfy any of `role === 'lawyer'`, `role === 'admin'`, `is_staff === true`, or `is_superuser === true` are treated as **lawyer-like**. This single predicate (encoded in the `isLawyerLike` getter on `frontend/src/stores/auth/user.js`) drives:

- The Vue Router `requiresLawyer` guard
- The TinyMCE editor toolbar (lawyer-like users see "Continuar"; clients see only "Guardar"/"Regresar")
- Document menu options, variable permissions and tag editing
- Access to the SECOP manual sync trigger
- Access to the Services inbox (lawyer view)
- The synthetic `admin` role used by the in-app User Guide to show admin-only documentation

Any new feature that gates by lawyer privileges **must consume `userStore.isLawyerLike`** rather than checking `role === 'lawyer'` directly — otherwise admin/staff users will lose access silently.

---

## 4. Core Features

### 4.1 User Management
- Role-based access: Client, Lawyer, Basic, Corporate Client
- JWT authentication (SimpleJWT) with 1-day access token lifetime
- Google OAuth and Microsoft Outlook OAuth integration for social login
- reCAPTCHA protection on registration/login
- User profiles with activity feeds and electronic signatures
- Email verification codes and password reset flow
- Idle logout composable for session security
- User archiving (`is_archived`): blocks login on all 3 auth methods, kills live JWTs, excludes archived users from notifications and lawyer/client selectors
- Admin data-reassignment module (`/data_reassignment`, platform admins only): transfer processes and managed documents between lawyers with preview, validation matrix and optional archive/restore

### 4.2 Process Management
- Legal cases with: authority, plaintiff, defendant, case type, subcase, file number
- Timestamped stages (phases) per process
- Attached case files with upload capability
- Recent-process tracking for quick dashboard access
- Process search and filtering

### 4.3 Dynamic Documents
- Template-based document builder with rich text editor (TinyMCE 7)
- Injectable variables: text, date, signature fields
- Visibility and usability permissions (per user, per role, public toggle)
- Document tags and folders for organization
- Document relationships (linking related documents)
- Letterhead support (image and Word template) per document and per user
- PDF and Word download generation
- Email sending with document attachments
- Recent-document tracking

### 4.4 Electronic Signatures
- Draw on canvas or upload image
- Per-user signature storage
- Document signature requests with pending/signed/rejected/archived states
- Signature reopening and removal
- Signatures PDF generation with QR codes

### 4.5 Organizations
- Create and manage organizations with title, description, profile image, cover image
- Invitation system (send, accept, reject, cancel, expire)
- Membership management (add, remove, leave)
- Organization posts (create, edit, delete, pin, toggle active status) with optional hyperlinks
- Organization statistics dashboard

### 4.6 Legal Requests
- Clients submit requests categorized by type and discipline
- File attachments per request
- La carga inicial de adjuntos y el envío de confirmación corresponden únicamente al propietario de la solicitud; los privilegios internos no sustituyen esa propiedad.
- Lawyer responses with conversation thread
- Status tracking (PENDING, IN_REVIEW, RESPONDED, CLOSED)
- Email notifications on status changes and new responses

### 4.7 Corporate Requests
- Similar to legal requests but for corporate matters
- Client-side: create requests, view own requests, add responses
- Corporate-side: view received requests, update status, add responses
- Dashboard statistics for corporate clients

### 4.8 Subscriptions & Payments
- Subscription plans with recurring billing via Wompi payment gateway
- Automated monthly payment processing through Huey scheduled tasks
- Payment history tracking
- Automatic role downgrade on payment failure (active → expired → basic)
- Subscription cancellation and payment method update
- Wompi webhook for real-time payment status updates
- Integrity signature verification for transaction security

### 4.9 Dashboard & Activity Feed
- Centralized dashboard with recent processes and recent documents
- Activity feed tracking user actions
- Report generation with Excel export (openpyxl, XlsxWriter)

### 4.10 Intranet
- Internal legal document library
- Intranet profiles for firm staff
- Facturation/report request form

### 4.11 Legal Updates
- Lawyers publish legal updates visible to clients
- Crear, editar y desactivar novedades requiere la política interna compartida; la lectura permanece disponible para usuarios autenticados.
- Active updates listing

### 4.12 PWA Support
- Service worker for offline readiness
- Installable app experience with install prompts
- No-connection fallback page

### 4.13 User Guide
- In-app interactive user guide with module-based navigation
- Role-specific information cards
- Search functionality within the guide
- Quick links and example modals
- Explorador del ecosistema completo para todos los usuarios autenticados: cuatro
  espacios, módulos y capacidades, búsqueda, relaciones y recorridos guiados. El
  acceso a funciones operativas conserva las restricciones del rol y plan.

### 4.14 SECOP Public Procurement
- Daily incremental synchronization from the public Socrata dataset on datos.gov.co
- Search, filters, classifications, saved views, alert rules, and Excel export
- Manual synchronization control visible only to lawyer-like users (lawyer, admin, staff, or superuser)
- Authoritative synchronization status based on backend `SyncLog` records, including safe in-progress and failure states
- Optional Socrata app token with automatic anonymous fallback when the public dataset rejects the configured token

---

## 5. Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| **Performance** | Query profiling via django-silk (dev); slow query alerts (>500ms); N+1 detection |
| **Security** | JWT auth, CSRF protection, reCAPTCHA, Wompi signature verification, file upload validation (python-magic), CORS configuration; backend dependencies must be pinned to non-vulnerable releases, and PDF rendering of user-authored HTML must reject network resources and local files outside approved project roots |
| **Reliability** | Automated daily backups (DB + media) via Huey with 20-backup retention; error logging to file |
| **Scalability** | Redis-backed Huey task queue for async processing; SQLite (dev) / MySQL (prod) |
| **Testing** | pytest (backend), Jest (frontend unit), Playwright (frontend E2E); test quality gate with CI enforcement — junk-test detectors (`.testquality.yml`) block NEW low-value tests while a grandfathered `.junk-baseline.json` holds existing debt |
| **Accessibility** | Responsive design via TailwindCSS; PWA for mobile/tablet |
| **Monitoring** | Silk profiling dashboard (staff only); weekly slow-query reports; silk garbage collection |

---

## 6. Business Rules

1. **Role hierarchy**: Lawyers can access all features; Clients see only their own data; Basic users have limited access; Corporate Clients manage organizations.
2. **Document permissions**: Two-level system — visibility (can see) and usability (can edit/fill). Permissions can be granted per user, per role, or publicly.
3. **Subscription lifecycle**: Active → payment due → Wompi charge → success (renew 30 days) or failure (expire + downgrade to basic).
4. **Organization invitations**: Have expiration; can be accepted, rejected, or cancelled by the corporate client.
5. **Legal request workflow**: Client creates → Lawyer reviews → status updates with email notifications → conversation thread.
6. **Process stages**: Timestamped and ordered; each process tracks its current stage and history.
7. **Electronic signatures**: Once signed, documents maintain audit trail; signatures can be reopened by document owner.
8. **Document formalization**: When a completed document is sent for signatures, the same document transitions state (no copy created). Title is preserved. Correction of rejected documents also operates on the same document instance.
9. **Idle logout**: Automatic session termination after inactivity period for security.
10. **SECOP classifications**: Each user can have one classification per process (unique_together). Classifications are per-user but visible to the team.
11. **SECOP alerts**: Evaluated against new processes after each sync. Frequency determines email delivery: immediate, daily summary, or weekly summary.
12. **SECOP sync**: Daily incremental sync from Socrata API (datos.gov.co). Scheduled and manual executions share a task lock, so they cannot run concurrently. A rejected optional app token falls back once to anonymous access because the dataset is public. The UI polls `SyncLog` and never invents completion locally. Old closed processes without classifications are purged after 30 days.

---

## 7. External Integrations

| Integration | Purpose |
|-------------|---------|
| **Wompi** | Payment gateway for subscription billing (sandbox + production) |
| **Google OAuth** | Social login authentication |
| **Google reCAPTCHA** | Bot protection on auth forms |
| **Gmail SMTP** | Email notifications (verification codes, request updates, document emails) |
| **Redis** | Task queue backend for Huey |
| **TinyMCE** | Rich text editor for dynamic documents |
| **Socrata API (datos.gov.co)** | SECOP II public procurement data — daily sync of open processes |
