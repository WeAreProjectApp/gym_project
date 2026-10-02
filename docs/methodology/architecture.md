# Architecture — G&M Internal Management Tool

## 1. System Overview

```mermaid
flowchart TB
    subgraph Client["Frontend (Vue 3 SPA + PWA)"]
        Router["Vue Router\n69 routes"]
        Views["45 View Pages"]
        Components["115 Components"]
        Stores["46 Pinia Stores"]
        Composables["16 Composables"]
        SW["Service Worker\n(vite-plugin-pwa)"]
    end

    subgraph Server["Backend (Django 6.1)"]
        DRF["Django REST Framework\n~205 API endpoints"]
        Models["56 Models\n(15 model files)"]
        Serializers["13 Serializer files"]
        Views_BE["32 View files"]
        Utils["4 Utility modules"]
        Tasks["Huey Tasks"]
        Admin["Django Admin"]
    end

    subgraph External["External Services"]
        Wompi["Wompi\nPayment Gateway"]
        Google["Google OAuth\n+ reCAPTCHA"]
        SMTP["Gmail SMTP"]
        Redis["Redis\n(Task Queue)"]
        Socrata["Socrata API\n(datos.gov.co SECOP)"]
    end

    subgraph Storage["Data Storage"]
        DB_Dev["SQLite (dev)"]
        DB_Prod["MySQL 8.4+ (prod)"]
        Media["Media Files\n(local filesystem)"]
        Backups["Automated Backups\n(django-dbbackup)"]
    end

    Client -->|"Axios + JWT"| DRF
    DRF --> Models
    DRF --> Serializers
    Models --> DB_Dev
    Models --> DB_Prod
    Models --> Media
    Tasks -->|"Redis broker"| Redis
    Tasks --> Wompi
    Tasks --> Backups
    DRF --> SMTP
    DRF --> Google
    DRF --> Wompi
    Tasks --> Socrata
```

---

## 2. Development Architecture

```mermaid
flowchart LR
    subgraph Dev["Development Environment"]
        Vite["Vite Dev Server\n:5173"]
        Django["Django Dev Server\n:8000"]
        Huey_Imm["Huey (immediate mode)\nNo Redis needed"]
        SQLite["SQLite\ndb.sqlite3"]
    end

    subgraph Test["Testing"]
        Pytest["pytest\n101 test files"]
        Jest["Jest\n208 test files"]
        PW["Playwright\n205 E2E specs"]
        QG["Quality Gate\nscripts/test_quality_gate.py"]
    end

    subgraph CI["CI/CD"]
        GHA["GitHub Actions"]
        PreCommit["Pre-commit Hooks"]
    end

    Vite -->|"proxy /api"| Django
    Django --> SQLite
    Django --> Huey_Imm
    Pytest --> Django
    Jest --> Vite
    PW --> Vite
    PW --> Django
    QG --> Pytest
    QG --> Jest
    QG --> PW
    GHA --> QG
    PreCommit --> QG
```

---

## 3. Request Flow

El historial de procesos aplica la misma política de objeto en escritura y
lectura: internos autorizados, abogado asignado o cliente relacionado. La
lectura reevalúa permisos mediante una subconsulta antes de ordenar y limitar
a diez entradas, preservando precargas sin consultas por expediente. La firma
personal exige propietario antes del lookup; la firma de integridad de pagos
conserva su payload y sólo produce un evento de log sin material criptográfico.

```mermaid
sequenceDiagram
    participant B as Browser (Vue SPA)
    participant R as Vue Router
    participant S as Pinia Store
    participant A as Axios (request_http.js)
    participant D as Django REST API
    participant M as Models / DB
    participant E as External (Wompi/SMTP/Google)

    B->>R: Navigate to route
    R->>R: beforeEach guard (auth + role check)
    R->>B: Render view component
    B->>S: Call store action
    S->>A: HTTP request (JWT in header)
    A->>D: API call (/api/...)
    D->>D: JWT Authentication
    D->>D: Permission check
    D->>M: Query/Mutate data
    M-->>D: Response data
    D-->>A: JSON response
    A-->>S: Update store state
    S-->>B: Reactive UI update

    Note over D,E: For async operations
    D->>E: External API call (Wompi/SMTP)
    E-->>D: Response
```

### 3.1 Rendimiento de listados

Listados optimizados (2026-09-24): organizaciones y solicitudes corporativas
cargan sus FKs en la consulta principal y calculan conteos mediante subconsultas
correlacionadas. Esto evita joins multiplicativos y conserva filtros/orden.
Procesos recientes combina joins de caso/abogado con prefetch de clientes,
archivos y etapas con alerta; conserva el límite de diez. Los serializers mantienen
fallback cuando reciben instancias sin anotaciones. Los presupuestos de queries
viven en los tests de vistas y en `docs/PERFORMANCE_STANDARDS.md`.

La conversación corporativa precarga autores y adjuntos después del filtro de
visibilidad. El listado SECOP anota sus conteos de notificaciones; el serializer
conserva el fallback para instancias sin anotación. El dashboard corporativo
calcula todos sus contadores en un único agregado condicional, con el mismo
alcance por corporativo y las mismas fronteras de recientes y vencidas.

Los listados de procesos SECOP precargan sólo la clasificación del usuario actual
en `_current_user_classifications`; el detalle precarga todas las clasificaciones
del equipo con sus autores en `_detail_classifications`. Los atributos separados
evitan confundir una relación completa con una selección por usuario. Ambos
serializers respetan una precarga vacía y conservan su fallback para instancias
obtenidas directamente. No cambia el contrato de filtros, paginación o respuesta.

El listado general de procesos une el tipo de caso. Los listados de invitaciones
precargan usuarios y organizaciones con conteos anotados; el queryset de
organización se comparte con el listado del propietario. Se evita el manager
inverso al construir las invitaciones para que su instancia conocida no omita
el prefetch anotado. Ambos detalles corporativos precargan sus cinco FKs,
archivos y respuestas con autores/adjuntos. El prefetch normal de respuestas,
sin `to_attr`, permite que `responses.count()` reutilice la caché de la relación.
Estos contratos sin paginación de procesos/respuestas mantienen su payload;
la constancia de consultas no impone un límite de memoria o tamaño de respuesta.

Las organizaciones para crear solicitudes unen su corporativo desde la membresía.
El listado de membresías usa Prefetch de organizaciones anotadas, sin un
select_related competidor, y conserva el orden de ingreso de las membresías.
Los detalles organizacionales reutilizan esos conteos independientes y agregan
solicitudes recientes; precargan miembros activos con usuarios en
`_active_memberships`. El serializer acepta anotaciones cero y precargas vacías,
con fallback para creación, edición e instancias directas. El control de acceso
público conserva su consulta de pertenencia y su distinción entre 403 y 404.

Las estadísticas organizacionales agrupan conteos condicionales sin unir entre sí
relaciones multivaluadas. La actualización corporativa reutiliza el queryset de
detalle y carga el propietario de la organización para la validación del modelo;
el cambio de responsable se refleja en la respuesta después de guardar.
La exportación SECOP proyecta únicamente los campos consumidos por el workbook,
conservando búsquedas por descripción en SQL, orden y tope de quinientas filas.

Los resúmenes de solicitudes legales anotan el número de respuestas y unen cliente
más catálogos; el serializer conserva el cálculo directo como fallback. El PUT de
estado precarga archivos y respuestas con sus autores, además de las relaciones
que consume el email. Los listados paginados de publicaciones unen el autor; mantienen
su filtro de acceso y el máximo de cien filas por página.

El reporte de carga de abogados agrupa procesos por abogado, tipo de caso y
existencia de una etapa Fallo mediante Count y Exists, sin materializar procesos
o etapas por abogado. La concesión de visibilidad por rol bloquea el documento,
lee los permisos previos y usa bulk_create en lotes de mil. Una colisión revierte
la transacción antes del fallback get_or_create para conservar la atribución de
permisos concedidos y omitidos. La usabilidad mantiene save/clean y su verificación
de visibilidad previa. El listado de documentos acota la página existente a cien
documentos raíz (default diez), sin acotar sus relaciones anidadas.

### 3.2 Document PDF resource boundary

Security remediation completed on 2026-08-26 after `pip-audit` reported 85
vulnerability records across nine packages. User-authored HTML now reaches a
deny-by-default WeasyPrint 69 fetcher: it keeps inline `data:` assets and
approved local project files, rejects network URLs, remote `file://` hosts and
resolved path/symlink escapes, and routes all PDF reading/writing through
`pypdf` 6. The same boundary now renders dynamic documents and service/trámite
requests; xhtml2pdf is no longer installed. ReportLab 5 remains isolated to
direct canvas/signature/watermark and SVG-backed generation. The deprecated
`PyPDF2` distribution is no longer installed.

### 3.3 Controles responsive del Manual de Usuario

El módulo `/user_guide` conserva navegación móvil y layout basado en el ancho del
contenedor del explorador. Sus controles compensan `--app-zoom` para mantener
44 px físicos y sus inputs 16 px; el panel de ejemplo teleportado comparte esa
regla mediante una clase propia. El cierre reserva espacio junto al título.
La matriz de QA vive en `frontend/e2e/helpers/viewports.js` y los comportamientos
pertenecen a los flows existentes de navegación y layout del explorador.

---

## 4. Entity-Relationship Diagram

```mermaid
erDiagram
    User ||--o{ Process : "lawyer"
    User }o--o{ Process : "clients (M2M)"
    User ||--o{ ActivityFeed : "has"
    User ||--o| UserSignature : "has (OneToOne)"
    User ||--o{ LegalRequest : "creates"
    User ||--o{ CorporateRequest : "sends (client)"
    User ||--o{ CorporateRequest : "receives (corporate_client)"
    User ||--o{ Subscription : "subscribes"
    User ||--o{ DynamicDocument : "creates"
    User ||--o{ DocumentSignature : "signer"
    User ||--o{ DocumentVisibilityPermission : "granted"
    User ||--o{ DocumentUsabilityPermission : "granted"
    User ||--o{ OrganizationMembership : "member of"
    User ||--o{ OrganizationInvitation : "invited_user"
    User ||--o{ OrganizationInvitation : "invited_by"
    User ||--o{ Organization : "corporate_client"
    User ||--o{ RecentProcess : "tracks"
    User ||--o{ RecentDocument : "tracks"
    User ||--o{ PasswordCode : "has"
    User ||--o{ Tag : "created_by"
    User ||--o{ DocumentFolder : "owner"

    Process }o--o{ Stage : "M2M"
    Process }o--o{ CaseFile : "M2M"
    Process }o--|| Case : "belongs to"

    DynamicDocument ||--o{ DocumentVariable : "has"
    DynamicDocument ||--o{ DocumentSignature : "requires"
    DynamicDocument ||--o{ DocumentVisibilityPermission : "has"
    DynamicDocument ||--o{ DocumentUsabilityPermission : "has"
    DynamicDocument }o--o{ Tag : "M2M tags"
    DocumentFolder }o--o{ DynamicDocument : "M2M documents"
    DynamicDocument ||--o{ DocumentRelationship : "source"
    DynamicDocument ||--o{ DocumentRelationship : "target"

    Organization ||--o{ OrganizationInvitation : "sends"
    Organization ||--o{ OrganizationMembership : "has"
    Organization ||--o{ OrganizationPost : "publishes"
    Organization ||--o{ CorporateRequest : "receives"

    LegalRequest }o--|| LegalRequestType : "categorized"
    LegalRequest }o--|| LegalDiscipline : "discipline"
    LegalRequest }o--o{ LegalRequestFiles : "M2M files"
    LegalRequest ||--o{ LegalRequestResponse : "has"

    CorporateRequest }o--|| CorporateRequestType : "categorized"
    CorporateRequest }o--o{ CorporateRequestFiles : "M2M files"
    CorporateRequest ||--o{ CorporateRequestResponse : "has"
    CorporateRequestResponse }o--o{ CorporateRequestFiles : "M2M response_files"

    Subscription ||--o{ PaymentHistory : "has"

    Service ||--o{ ServiceStage : "has"
    ServiceStage ||--o{ ServiceField : "has"
    Service ||--o{ ServiceRequest : "receives"
    User ||--o{ ServiceRequest : "submits"
    ServiceRequest ||--o{ ServiceRequestAnswer : "has"
    ServiceRequest ||--o{ ServiceRequestFieldFile : "has"
    ServiceRequest ||--o{ ServiceRequestLawyerResponse : "has"
    ServiceRequestLawyerResponse ||--o{ ServiceRequestLawyerResponseFile : "has"
```

---

## 5. Model Details

### 5.1 Users Domain (4 models)

| Model | Key Fields | Relationships |
|-------|-----------|---------------|
| `User` | email, first_name, last_name, contact, birthday, identification, document_type (NIT/CC/NUIP/EIN), role (admin/client/lawyer/corporate_client/basic, default='basic'; 5 roles total, 4 client-facing), photo_profile, letterhead_image, letterhead_word_template, is_gym_lawyer, is_profile_completed, is_archived (archive() clears is_active → kills live JWTs; login blocked on all 3 auth methods), created_at | Custom `UserManager`; USERNAME_FIELD='email'; no username/groups/user_permissions |
| `ActivityFeed` | action_type (create/edit/finish/delete/update/download/other), description, created_at | FK → User; max 20 per user (auto-cleanup on save) |
| `UserSignature` | signature_image, method (upload/draw), ip_address, created_at | OneToOne → User |
| `TourProgress` | module_name (dynamic_documents), completed_at (STALE_AFTER_DAYS=30 → tour re-offered) | FK → User (CASCADE); one row per user/module |

### 5.2 Processes Domain (5 models)

| Model | Key Fields | Relationships |
|-------|-----------|---------------|
| `Case` | type | — (lookup table for case types) |
| `Process` | authority, authority_email, plaintiff, defendant, ref, subcase, progress (0-100), created_at | FK → Case, FK → User (lawyer, PROTECT — reassign via admin module before deleting a lawyer), M2M → User (clients), M2M → Stage, M2M → CaseFile |
| `Stage` | status, date, created_at | No FK — linked via Process M2M |
| `CaseFile` | file, created_at | No FK — linked via Process M2M; physical file deleted on model delete (signal) |
| `RecentProcess` | last_viewed | FK → User, FK → Process; unique_together=[user, process] |

### 5.3 Dynamic Documents Domain (10 models)

| Model | Key Fields | Relationships |
|-------|-----------|---------------|
| `Tag` | name (unique), color_id | FK → User (created_by, SET_NULL) |
| `DynamicDocument` | title, content, is_public, letterhead_image, letterhead_word_template | FK → User (created_by, immutable), FK → User (managed_by, SET_NULL — current manager; backfilled from created_by; lawyer scope + minuta rights follow this field), M2M → Tag (tags) |
| `DocumentVariable` | name, type (input/text_area/number/date/email/select), value, summary_field (none/counterparty/object/value/term/subscription_date/start_date) | FK → DynamicDocument |
| `DocumentSignature` | signed (bool), signed_at, rejected (bool), rejected_at | FK → DynamicDocument, FK → User (signer) |
| `DocumentVisibilityPermission` | — | FK → DynamicDocument, FK → User |
| `DocumentUsabilityPermission` | — | FK → DynamicDocument, FK → User |
| `RecentDocument` | viewed_at | FK → User, FK → DynamicDocument |
| `DocumentFolder` | name, color_id | FK → User (owner), M2M → DynamicDocument (documents) |
| `DocumentRelationship` | (no extra fields) | FK → DynamicDocument (source_document), FK → DynamicDocument (target_document); bidirectional |
| `DocumentPaymentRecord` | installment_number, file, original_name, amount, notes, status (uploaded/accepted/rejected), rejection_reason, uploaded_at | FK → DynamicDocument (document), FK → User (uploaded_by); cuenta de cobro per installment of a fully signed contract |

### 5.4 Organizations Domain (4 models)

| Model | Key Fields | Relationships |
|-------|-----------|---------------|
| `Organization` | title, description, profile_image, cover_image, is_active, created_at, updated_at | FK → User (corporate_client, limit_choices_to={'role': 'corporate_client'}) |
| `OrganizationInvitation` | invitation_token (UUID), message, status (PENDING/ACCEPTED/REJECTED/EXPIRED/CANCELLED), expires_at, responded_at, created_at | FK → Organization, FK → User (invited_user), FK → User (invited_by); unique_together=[organization, invited_user, status] |
| `OrganizationMembership` | role (LEADER/ADMIN/MEMBER), joined_at, is_active, deactivated_at | FK → Organization, FK → User; unique_together=[organization, user] |
| `OrganizationPost` | title, content, link_name, link_url, is_active, is_pinned, created_at, updated_at | FK → Organization, FK → User (author, limit_choices_to={'role': 'corporate_client'}) |

### 5.5 Legal Requests Domain (5 models)

| Model | Key Fields | Relationships |
|-------|-----------|---------------|
| `LegalRequestType` | name (unique) | — |
| `LegalDiscipline` | name (unique) | — |
| `LegalRequest` | request_number (auto-gen SOL-YYYY-NNN), description, status (PENDING/IN_REVIEW/RESPONDED/CLOSED), status_updated_at, created_at | FK → User, FK → LegalRequestType, FK → LegalDiscipline, M2M → LegalRequestFiles |
| `LegalRequestFiles` | file, created_at | No FK — linked via LegalRequest M2M; physical file deleted on model delete (signal) |
| `LegalRequestResponse` | response_text, user_type (lawyer/client), created_at | FK → LegalRequest, FK → User |

### 5.6 Corporate Requests Domain (4 models)

| Model | Key Fields | Relationships |
|-------|-----------|---------------|
| `CorporateRequestType` | name (unique) | — |
| `CorporateRequest` | request_number (auto-gen CORP-YYYY-NNN), title, description, priority (LOW/MEDIUM/HIGH/URGENT), status (PENDING/IN_REVIEW/RESPONDED/RESOLVED/CLOSED), status_updated_at, estimated_completion_date, actual_completion_date, created_at | FK → User (client), FK → User (corporate_client), FK → User (assigned_to, nullable), FK → Organization, FK → CorporateRequestType, M2M → CorporateRequestFiles |
| `CorporateRequestFiles` | file, created_at | No FK — linked via CorporateRequest M2M; physical file deleted on model delete (signal) |
| `CorporateRequestResponse` | response_text, user_type (corporate_client/client), is_internal_note, created_at | FK → CorporateRequest, FK → User, M2M → CorporateRequestFiles (response_files) |

### 5.7 Subscriptions Domain (2 models)

| Model | Key Fields | Relationships |
|-------|-----------|---------------|
| `Subscription` | plan_type (basico/cliente/corporativo), amount, status (active/cancelled/expired), payment_source_id, next_billing_date, created_at, updated_at | FK → User |
| `PaymentHistory` | amount, status (approved/declined/pending/error), transaction_id, reference, payment_date, error_message | FK → Subscription |

### 5.8 Intranet Domain (2 models)

| Model | Key Fields | Relationships |
|-------|-----------|---------------|
| `LegalDocument` | name, file | — |
| `IntranetProfile` | cover_image, profile_image | Singleton (no FK to User) |

### 5.9 SECOP Public Procurement Domain (6 models)

| Model | Key Fields | Relationships |
|-------|-----------|---------------|
| `SECOPProcess` | process_id (unique), reference, entity_name, entity_nit, department, city, entity_level, procedure_name, description, phase, status, procurement_method, contract_type, base_price, closing_date, publication_date, process_url, raw_data (JSON) | — |
| `ProcessClassification` | status (INTERESTING/UNDER_REVIEW/DISCARDED/APPLIED), notes, created_at, updated_at | FK → SECOPProcess, FK → User (unique_together) |
| `SECOPAlert` | name, keywords, entities, departments, min_budget, max_budget, procurement_methods, frequency (IMMEDIATE/DAILY/WEEKLY), is_active | FK → User |
| `AlertNotification` | is_sent, sent_at, created_at | FK → SECOPAlert, FK → SECOPProcess (unique_together) |
| `SyncLog` | started_at, finished_at, status (IN_PROGRESS/SUCCESS/FAILED), records_processed/created/updated, error_message | — |
| `SavedView` | name, filters (JSON), created_at | FK → User (unique_together with name) |

### 5.10 Servicios y Trámites Domain (9 models)

| Model | Key Fields | Relationships |
|-------|-----------|---------------|
| `Service` | title, description, is_active, is_featured, icon, created_at | — |
| `ServiceStage` | name, order, description | FK → Service |
| `ServiceField` | label, field_type, is_required, order, options (JSON) | FK → ServiceStage |
| `ServiceRequestSequence` | year, last_number | — (auto-increment tracking per year) |
| `ServiceRequest` | tracking_number (YYYY-NNNNN), status, current_stage, submitted_at | FK → Service, FK → User (requester) |
| `ServiceRequestAnswer` | value | FK → ServiceRequest, FK → ServiceField |
| `ServiceRequestFieldFile` | file, original_filename | FK → ServiceRequest, FK → ServiceField |
| `ServiceRequestLawyerResponse` | response_text, new_status, created_at | FK → ServiceRequest, FK → User (responder) |
| `ServiceRequestLawyerResponseFile` | file, original_filename | FK → ServiceRequestLawyerResponse |

### 5.11 Notifications & Alerts Domain (2 models)

| Model | Key Fields | Relationships |
|-------|-----------|---------------|
| `Notification` | title, message, category (`signature_request`/`signature_completed`/`signature_rejected`/`signature_expired`/`signature_reopened`/`signature_reminder`/`process_alert`/`general`), priority (low/medium/high), is_read, is_archived, is_deleted (soft-delete), snoozed_until, link_type (`process`/`document`/`service_request`/`""`), link_id, created_at | FK → User |
| `StageAlert` | days_before, notify_clients, last_3_day_sent_at, last_1_day_sent_at | OneToOne → Stage (CASCADE) |

Created by `services/notification_service.py` (`create_notification`, `create_bulk_notifications`, `get_unread_count`); consumed by 7 REST endpoints in `views/notification.py`. Snooze reactivation runs every 15 min via `notification_tasks.reactivate_snoozed_notifications`. Stage alerts evaluated daily at 14:00 UTC by `process_alert_tasks.send_process_alerts` (creates email + in-app notifications). Signature lifecycle via `services/signature_notification_service.py` (request/progress/completed/rejected/expired/reopened/daily reminders, all dual-channel).

### 5.12 Other Models (3 models)

| Model | Key Fields | Relationships |
|-------|-----------|---------------|
| `LegalUpdate` | title, content, image, link_text, link_url, is_active, created_at, updated_at | No FK (standalone) |
| `PasswordCode` | code (6-digit), created_at, used (bool) | FK → User |
| `EmailVerificationCode` | email, code (6-digit), created_at, used (bool) | No FK to User — stores email directly (pre-registration) |

---

## 6. Service Layer (Huey Tasks)

```mermaid
flowchart TD
    subgraph Business["gym_app/tasks.py"]
        T1["process_monthly_subscriptions\n(on-demand task)"]
        T2["cancel_subscription\n(on-demand task)"]
    end

    subgraph Infra["gym_project/tasks.py"]
        T3["scheduled_backup\n(daily @ 3AM)"]
        T4["silk_garbage_collection\n(daily @ 4AM)"]
        T5["weekly_slow_queries_report\n(Monday @ 8AM)"]
        T6["silk_reports_cleanup\n(monthly, 1st @ 5AM)"]
        T7["manual_backup\n(on-demand)"]
    end

    subgraph SECOP["gym_app/secop_tasks.py"]
        S1["sync_secop_daily\n(daily @ 6AM)"]
        S2["sync_secop_data\n(manual/scheduled, retries=3, locked)"]
        S3["evaluate_secop_alerts\n(after sync, delayed 5s)"]
        S4["send_secop_daily_summaries\n(daily @ 7AM)"]
        S5["send_secop_weekly_summaries\n(Monday @ 7AM)"]
        S6["purge_old_secop_processes\n(daily @ 3:30AM)"]
    end

    T1 -->|"charges via"| Wompi["Wompi API"]
    T1 -->|"on failure"| Downgrade["User role → basic"]
    T3 -->|"django-dbbackup"| Storage["Backup Storage"]
    T5 -->|"reads"| Silk["Silk DB records"]
    S1 -->|"calls"| S2
    S2 -->|"fetches from"| Socrata["Socrata API\n(datos.gov.co)"]
    S2 -->|"on new records"| S3
    S3 -->|"sends email"| SMTP2["Gmail SMTP"]
    S4 -->|"sends email"| SMTP2
```

The lock is attached to `sync_secop_data`, the real worker task, so both the
periodic wrapper and manual endpoint use the same concurrency guard. The
Socrata client sends `SECOP_APP_TOKEN` only when configured; a 401/403 disables
that header for the rest of the client run and retries the public dataset once
anonymously. `SyncLog` is the source of truth consumed by
`useSecopSyncPolling`: the SECOP page polls while work is active, refreshes
processes and filters only after a newer successful log, and shows safe failure
copy without exposing backend diagnostics.

---

## 7. Frontend Page Routing

```mermaid
flowchart TD
    Root["/"] -->|"redirect"| SignIn["/sign_in"]
    
    subgraph Public["Public Routes (no auth)"]
        SignIn
        SignOn["/sign_on"]
        Forget["/forget_password"]
        Home["/home"]
        Privacy["/policies/privacy_policy"]
        Terms["/policies/terms_of_use"]
        NoConn["/no_connection"]
        Subs["/subscriptions"]
        SubSignIn["/subscription/sign_in"]
        SubSignUp["/subscription/sign_up"]
        GoogleCB["/auth/google/callback"]
    end

    subgraph Auth["Authenticated Routes (SlideBar layout)"]
        Dashboard["/dashboard"]
        ProcessList["/process_list/:user_id?"]
        ProcessDetail["/process_detail/:process_id"]
        ProcessForm["/process_form/:action 🔒"]
        Directory["/directory_list 🔒"]
        LegalReq["/legal_request"]
        LegalReqList["/legal_requests"]
        LegalReqCreate["/legal_request_create"]
        LegalReqDetail["/legal_request_detail/:id"]
        Intranet["/intranet_g_y_m 🔒"]
        Schedule["/schedule_appointment"]
        OrgDash["/organizations_dashboard"]
        DocDash["/dynamic_document_dashboard"]
        Checkout["/checkout/:plan"]
        SecopList["/secop 🔒"]
        SecopDetail["/secop/:id 🔒"]
        UserGuide["/user_guide"]
    end

    DocDash -->|"children"| DocEditor["editor/create/:title 🔒\neditor/edit/:id 🔒\nclient/editor/edit/:id\ndocument/use/:mode/:id/:title\nvariables-config 🔒\nsigned-documents"]
```

> 🔒 = `requiresLawyer: true` (Client/Basic/Corporate redirected to dashboard)

---

## 8. Store Architecture

### Explorador del Manual de Usuario (2026-09-19)

`UserGuideMain` carga bajo demanda `explorer/GuideExplorer.vue` al abrir
`?view=explorer`. El catálogo descriptivo local (`spaces.js` + `catalog.js`) es
visible para todos los roles y no consulta registros de negocio. `ExplorerContext`
resuelve accesos con el usuario actual, el getter `isLawyerLike`, el router y las
guías filtradas por rol. `useGuideExplorer` usa la URL como estado de navegación
(`node`, `tour`, `relations`); `useGuideOrbit` adapta el contenedor y administra
animación, preferencias de movimiento y limpieza al desmontar. El inventario de
rutas se verifica contra el router en pruebas para detectar módulos omitidos.

```mermaid
flowchart TD
    subgraph AuthStores["Auth"]
        AS["auth.js — JWT tokens, login/logout"]
        CS["captcha.js — reCAPTCHA"]
        US["user.js — current user, profile"]
    end

    subgraph DashStores["Dashboard"]
        AF["activity_feed.js"]
        RP["recentProcess.js"]
        RE["reports.js"]
    end

    subgraph DocStores["Dynamic Documents"]
        DD["documents.js — CRUD"]
        DF["filters.js — search/filter"]
        DG["getters.js"]
        DS["state.js"]
        DI["index.js — main store"]
        DT["tags.js"]
        DP["permissions.js"]
        DR["relationships.js"]
        FF["folders/ — actions, getters, state, utilities, index"]
    end

    subgraph LegalStores["Legal"]
        CT["case_type.js"]
        IG["intranet_gym.js"]
        LR["legal_request.js"]
        LRM["legal_requests_management.js"]
        LU["legalUpdate.js"]
    end

    subgraph OrgStores["Organizations"]
        OI["organizations/index.js"]
        OCR["organizations/corporate_requests.js"]
        OP["organization_posts/index.js"]
    end

    subgraph SecopStores["SECOP Public Procurement"]
        SC["secop/index.js — processes, classifications, alerts, saved views, sync"]
    end

    subgraph Other["Other Stores"]
        PR["process.js"]
        SUB["subscriptions/index.js"]
        UG["user_guide.js"]
        UGU["user_guide_updates.js"]
        RH["services/request_http.js — Axios instance"]
    end
```

---

## 9. Deployment Architecture

```mermaid
flowchart TD
    subgraph Production
        Gunicorn["Gunicorn\n(WSGI server)"]
        Django["Django 6.1"]
        MySQL["MySQL 8.4+"]
        RedisQ["Redis\n(Huey broker)"]
        HueyW["Huey Worker\n(consumer)"]
        Media["Media Files\n(local disk)"]
        Backup["Backup Storage\n(/var/backups/gym_project)"]
    end

    subgraph Frontend_Build
        ViteBuild["Vite Build\n(npm run build)"]
        StaticFiles["Static files\n(served by Django)"]
    end

    Internet["Internet"] -->|"HTTPS"| Gunicorn
    Gunicorn --> Django
    Django --> MySQL
    Django --> Media
    Django --> RedisQ
    RedisQ --> HueyW
    HueyW --> Backup
    ViteBuild --> StaticFiles
    StaticFiles -->|"served by"| Django
```

> Frontend is built and served as static files through Django in production. The `npm run build` command also runs `scripts/generate-django-template.cjs` to create a Django-compatible template.
>
> **Deployment gate:** the currently deployed server still runs MySQL 8.0.46.
> Upgrade it to MySQL 8.4+ before deploying the Django 6.1 release. GitHub
> Actions separately applies all migrations and runs the health regression on
> a real MySQL 8.4 service.
