# Tasks Plan — G&M Internal Management Tool

**2026-10-02 — Ronda de permisos y relaciones:** candidatos
`I-S-8cf319c5e61d`, `I-S-cb0850be9bc8` e `I-P-0eadd4c7c87b`.
Denegar mutaciones externas de novedades y finalización de solicitudes ajenas;
conservar operaciones legítimas y el payload del selector con un presupuesto
de consultas constante. La entrega requiere QA del SHA final y PR abierto
con CI verde hacia `master`. Ronda `i3-legal-relationships-20261002`.

## 1. Feature Status

**2026-10-03 — Precargas localizadas:** pagos cargan sus autores; carpetas
reutilizan el plan completo de documentos después de comprobar el propietario;
detalle de servicios y último borrador comparten las precargas de respuestas,
campos, archivos y abogados. Se conserva el payload, incluidos los permisos de
carpetas sin contexto de request. Los tests protegen crecimiento de consultas,
serialización sin SQL, datos anidados y regresiones de acceso y selección.
Los presupuestos absolutos de carpetas y borradores siguen abiertos; no se
declara verificación integral de `i5-query-preloads-20261003`. Evidencia en
`2026-10-03-gym_project-improvement-pass-query-preloads-i5.md` del toolkit.
Sin migraciones, dependencias nuevas ni despliegue.

**2026-10-01 — Mejora transversal:** tres candidatos canónicos: impedir que
registro/perfil asignen autoridad, leer datos largos completos en el directorio
y mantener controles físicos de 44 px pese al zoom. Se ajusta también la fila que
abre la ficha para evitar desborde móvil. Tests de registro, perfil y serializer
verifican intentos de promoción y cuentas internas legítimas; E2E conserva búsqueda
y navegación, con cinco tamaños y controles en móvil/tableta vertical. Los flows
existentes mantienen success y añaden display. CI cubre PRs hacia la base activa.
Los guiones E2E usan el estado público de aplicación previamente instalada para
un abogado recurrente; mantienen navegación y clics reales. El aviso de instalación
que bloquea el menú móvil en la primera visita web queda como obligación separada
para una ronda posterior, sin certificar ese estado en esta entrega.
La evidencia y verificación final pertenecen a `i1-auth-directory-20261001`, en
`2026-10-01-gym_project-improvement-pass-auth-directory-i1.md` del toolkit.
Las otras obligaciones quedan pendientes por cupo; el conflicto comercial de
precios sigue bloqueado. Sin migraciones ni despliegue.

**2026-09-30 — Octava ronda:** reporte de carga agregado, visibilidad por rol con
inserción por lotes y máximo de cien documentos por página (default diez).
Candidatos 21/22 y views-01, PR #131; el 22 queda parcial porque usabilidad mantiene
save/clean. El manual conserva navegación, búsqueda y ejemplos con targets físicos
de 44 px; sus dos flows existentes declaran display a los cinco tamaños estándar.
QA independiente aprobó 19 casos MySQL, 13 E2E nuevos, 18 regresiones del manual y
cinco negativos de permisos. SQLite: 18 aprobados y la carrera excluida por falta
de bloqueo de filas; su ejecución MySQL está verificada. Los tres guards fallan
contra el baseline por consultas o exceso de filas. Auditor/gate focalizado limpios.
Evidencia: `2026-09-30-r8-gym_project-qa.md` del toolkit, junto con los guiones
perf-round8 y responsive-user-guide. Sin migraciones, infraestructura ni despliegue.

**2026-09-27 — Séptima ronda de rendimiento:** candidatos 18/19/20: listado y
actualización de solicitudes legales, autores de publicaciones organizacionales.
Mismo PR #130; siete tests nuevos aprobados en SQLite y MySQL 8.4.11, trece
regresiones y cinco fallos esperados contra el baseline. Consultas constantes para
uno/cincuenta elementos: listado legal una, estado cuatro, posts privados tres y
públicos cuatro. Sin cambios de contrato ni infraestructura. Cierre autorizado
mediante merge-queue; reporte `2026-09-27-r7-gym_project-qa.md` en el toolkit.

**2026-09-27 — Sexta ronda de rendimiento:** candidatos 15/16/17: agregados
organizacionales independientes, precarga de detalle al actualizar solicitudes
corporativas y proyección mínima del export SECOP. PR #130. Contratos conservados;
QA independiente aprobó 16 tests en SQLite y MySQL 8.4, seis regresiones y
la detección de los tres problemas sobre el baseline. Sin migraciones,
infraestructura ni cambios frontend.

**2026-09-25 — Quinta ronda de rendimiento:** candidatos 12/13/14 aplicados en
el PR #128: organizaciones para solicitudes, resúmenes de membresías y detalles
organizacionales. Presupuestos constantes de máximo seis consultas por listado
y cuatro por detalle, conservando payloads, permisos y fallbacks del serializer.
QA independiente aprobó dieciséis casos nuevos y cinco regresiones en MySQL 8.4
aislado, incluyendo el consumo de precargas vacías y la frontera de solicitudes
recientes. Auditor y gate canónico aprobados; evidencia en
`vps-ops-toolkit/docs/audits/2026-09-25-r5-gym_project-qa.md`.
Los candidatos 15–17 se verificaron en la sexta ronda; no se agregan paginación,
migraciones ni cambios de infraestructura.

**2026-09-24 — Rendimiento:** tres candidatos de consultas por fila aplicados
(organizaciones, solicitudes corporativas y procesos recientes); presupuestos
constantes comprobados en SQLite y MySQL 8.4 aislados. Seguimiento en el ledger
`gym_project` del toolkit y PR #128 de sesión `perf-bounded-lists`.
No incluye cambios de infraestructura ni despliegue.

**2026-09-24 — Segunda ronda de rendimiento:** conversación corporativa, alertas
SECOP y dashboard aplicados en la misma sesión. Presupuestos constantes de 3, 1
y 1 consultas, respectivamente, comprobados en SQLite y MySQL 8.4 aislados.
Los cuatro guards nuevos detectan la regresión contra `ac3178f`; los cuatro
anteriores siguen pasando. Nueve tests nuevos/reforzados cubren también payloads,
visibilidad, aislamiento y fronteras temporales. Auditor dedicado aprobado.
Seguimiento: candidatos P-backend-queries-04/05/06 y PR #128.

**2026-09-24 — Tercera ronda de rendimiento:** candidatos 07/08 aplicados en SECOP.
Listados con precarga de clasificación personal y detalle con precarga de autores
reutilizada. Seis tests backend nuevos protegen consultas constantes, filas cargadas,
payload y listas vacías; los tests directos existentes conservan el fallback.
Presupuestos y evidencia independiente en el reporte QA de ronda 3 del toolkit.
Los candidatos 09/10/11 se trabajan en la cuarta ronda descrita abajo.

**2026-09-24 — Cuarta ronda de rendimiento:** procesos, invitaciones y detalles
corporativos precargan sus relaciones manteniendo contratos y permisos. Se
reutilizan las anotaciones de organizaciones y la caché de respuestas de Django.
Presupuestos: consultas constantes con uno y cincuenta registros, máximo seis
por listado y cuatro por detalle. QA y mediciones de esta ronda en el reporte
`2026-09-24-r4-gym_project-qa.md` del toolkit. Candidatos 12–15 quedan pendientes
en el ledger; la paginación de procesos/respuestas requiere otra tarea de contrato.

**2026-09-19 — Manual de Usuario:** explorador orbital del ecosistema implementado
con catálogo completo, permisos independientes de la visibilidad, recorridos,
búsqueda, relaciones y adaptación a móvil. Validación focalizada y siete flujos E2E
registrados; entrega mediante PR de sesión, sin despliegue en esta tarea.

| # | Feature | Status | Notes |
|---|---------|--------|-------|
| 1 | User Management (JWT, Google OAuth, reCAPTCHA, profiles) | ✅ Complete | 3 models, 2 view files, 1 serializer |
| 2 | Process Management (cases, stages, files, recent) | ✅ Complete | 5 models, 1 view file, 1 serializer |
| 3 | Dynamic Documents (editor, variables, permissions, tags, folders, relationships, letterhead, PDF/Word export) | ✅ Complete | 9 models, 5 view files (sub-package), 1 serializer |
| 4 | Electronic Signatures (draw/upload, request/sign/reject/archive, PDF generation) | ✅ Complete | Integrated into dynamic documents |
| 5 | Organizations (CRUD, invitations, memberships, posts) | ✅ Complete | 4 models, 2 view files, 1 serializer |
| 6 | Legal Requests (create, files, responses, status tracking, emails) | ✅ Complete | 5 models, 1 view file, 1 serializer |
| 7 | Corporate Requests (client/corporate sides, responses, dashboard stats) | ✅ Complete | 4 models, 1 view file, 1 serializer |
| 8 | Subscriptions & Payments (Wompi, recurring billing, webhook) | ✅ Complete | 2 models, 1 view file, 1 serializer, 1 task file |
| 9 | Dashboard & Activity Feed (recent items, reports, Excel export) | ✅ Complete | 4 dashboard stores, 1 reports package (5 domain modules) |
| 10 | Intranet (legal documents, profiles, facturation) | ✅ Complete | 2 models, 1 view file, 1 serializer |
| 11 | Legal Updates | ✅ Complete | 1 model, 1 view file, 1 serializer |
| 12 | PWA Support (service worker, install prompts, offline page) | ✅ Complete | vite-plugin-pwa, 3 PWA components |
| 13 | User Guide (interactive, module-based, role-specific) | ✅ Complete — extended 2026-04-22 + 2026-04-29 | 8 view files, 1 store (sub-module pattern: index, modules, getters, 7 content files). Audit + extension in `tasks/user_guide_gap_audit.md`: added modules **SECOP** (`content/secop.js`, 6 sections) and **Servicios y Trámites** (`content/services_tramites.js`, 10 sections after 2026-04-29 update); added sections `featured-services`, `variables-config`, `document-permissions`, `user-signature`, `payment-method-update`, `payment-history`; corrected tab labels to `Dcs. Por Firmar / Dcs. Formalizados / Dcs. Archivados` (commit `d60eeb4`); rewrote appointments section to match real Calendly-only implementation. **2026-04-29**: new **`admin_staff` module** (5 sections covering `isLawyerLike`, services catalog admin, dynamic documents privileges, transversal SECOP/Services visibility, Django admin); `documents.js` adds "Botones del Editor según tu Rol" + "Modos del DocumentForm" + explicit "Continuar" step; `secop.js` clarifies alert frequency + lawyer-only sync trigger; `services_tramites.js` adds status lifecycle table + tracking format `YYYY-NNNNN`. `getters.js` `roleMatches` aliases `admin` → lawyer modules; `UserGuideMain.vue` maps is_staff/is_superuser to synthetic `admin` role. Tests: 17/17 passing. |
| 14 | Automated Backups (daily, retention, manual trigger) | ✅ Complete | Huey periodic task |
| 15 | Query Profiling (django-silk, opt-in, GC, weekly reports) | ✅ Complete | Huey periodic tasks + management command |
| 16 | Test Quality Gate (backend + frontend + E2E, CI integration) | ✅ Complete | Custom analyzer + GitHub Actions |
| 17 | SECOP Public Procurement (Socrata API, classifications, alerts, Excel export) | ✅ Complete — sync hardened 2026-08-21 | 6 models, 1 view file, 1 serializer, 3 services, 1 task file, 6 components, 2 views, 1 store, 1 sync-polling composable. Optional-token 401/403 fallback, shared manual/scheduled lock, lawyer-like manual authorization, and authoritative `SyncLog` UI state. Live staging recovery processed 20,129 records successfully. |
| 18 | Servicios y Trámites (catálogo, formularios por etapas, radicado, PDF, bandejas por rol) | ✅ Complete | 9 models, 1 view file, 1 serializer, 2 services (PDF + notifications), 1 template PDF, 2 migrations (schema + seed Registro Marcario), 7 frontend views (incl. ServicesHub.vue), 1 store, 1 dashboard component, sidebar/router integration, backend tests passing. Sprint Abril 2026: 11 mejoras (admin icon preview, validación, errores, help_text UX, multi-file UI, PDF rediseño, tabs navigation, header corporativo, emails sin emojis, estado destacado, adjuntos automáticos) |

---

## 2. Planned Features (from docs/next_requirements/)

| # | Requirement | Plan Document | Status |
|---|------------|---------------|--------|
| 1 | Process Reassignment | `Requirement_01_reassignment` (Release Agosto 2026, branch `release-august-2026-c-v2`) | ✅ Complete (2026-07-07) | Módulo admin de reasignación de datos. Backend: `User.is_archived` + `archive()/unarchive()` (archive limpia `is_active` → simplejwt mata tokens vivos), bloqueo de login en los 3 métodos (sign_in/google/outlook), `Process.lawyer` CASCADE→PROTECT (migración 0069/0070), `DynamicDocument.managed_by` (SET_NULL, backfill=created_by; `lawyer_id` scope pasa a managed_by; `can_modify_minuta` extiende derechos al gestor; created_by inmutable). API `admin/reassignment/*` (summary + execute atómico con matriz de validación + archive/unarchive) gated por `is_platform_admin` (no incluye abogados); exclusión de archivados en 4 puntos de notificación. Frontend: getters lawyers/archivedLawyers/allLawyers (+ exclusión de archivados en selectores existentes), store `admin_reassignment`, selector de abogado en ProcessForm (default = usuario logueado; quita hardcodes), vista `DataReassignment.vue` (preview + select-all + no-elegibles con motivo + archivar + restaurar), ruta requiresAdmin + item SlideBar + quick action + `LawyerMetricsWidget`. Tests: 82 pytest F1 + 74 F2 + 16 F3 + ~22 Jest + 3 E2E (`admin-data-reassignment` P1, flow-definitions v1.11.0). Fake data: 1 abogado archivado seeded; migraciones aplicadas y backfill verificado (1190 docs managed_by=created_by). Decisiones del usuario: excluir también estado Vencido; minutas SÍ se transfieren. |
| 2 | Minutas (Meeting Minutes) | `Plan_02_minutas.md` / `Requirement_02_minutas.md` | 📋 Planned |
| 3 | Document Preview | `Plan_03_preview.md` / `Requirement_03_preview.md` | 📋 Planned |
| 4 | Guided Tour | `Requirement_04_guided_tour` (Release Agosto 2026, branch `release-august-2026-c-v2`) | ✅ Complete (2026-07-06) | `TourProgress` model (`unique_together user+module`, 30-day staleness on backend, migration `0067`), `GET /api/tour-progress/?module=` + `POST /api/tour-progress/complete/` (JWT, user-scoped), driver.js ^1.6 tour: `useGuidedTour` composable + `shared/tours/` registry (lawyer 10 / client 7 steps, conditional pending-signatures closer, Spanish copy, brand-styled `tour.css`), `data-tour` attrs + "?" help button + `InfoTooltip.vue` in `Dashboard.vue`, auto-start on first visit / SweetAlert2 re-offer after 30 days / manual relaunch. Tests: 17 pytest + 28 Jest (composable, steps, InfoTooltip) + 6-test E2E spec. Flow `docs-guided-tour` (P2). User guide section `guided-tour`. Extensible to other modules via `tourRegistry`. |
| 5 | Notification Center | `Plan_05_notification_center.md` / `Requirement_05_notification_center.md` | ✅ Complete | `Notification` model + `notification_service` (`create_notification`/`create_bulk_notifications`/`get_unread_count`), categories with `process_alert`/`signature_*`, snooze + archive |
| 6 | Legal Files Alerts | `Plan_06_legal_files_alerts.md` / `Requirement_06_legal_files_alerts.md` | ✅ Complete (audited 2026-04-28) | `signature_reminder_task.py` (Huey periodic, 14:00 UTC = 9 AM Colombia). Audit closed 7 spec gaps: removed email from `notify_signature_reopened` (in-app only per matrix), added 24h-cutoff exclusion to daily reminder queries, fixed N+1 in user fetch loop, added 8s pulse timeout in `SignaturesListTable`, added `sessionStorage` cleanup on logout, exported `PENDING_SIGNATURES_ALERTED_KEY` constant, **respected explicit `?tab=`/`?lawyerTab=` URL params over auto-redirect in `Dashboard.vue` (bug surfaced by E2E spec)**. 12 backend tests + 6 composable tests + 1 logout test + 3 E2E specs (5 tests) added. Flows registered: `legal-files-menu-pulse` (P1), `legal-files-auto-redirect` (P2), `legal-files-table-pulse` (P2). |
| 7 | Process Alerts | `Plan_07_process_alerts.md` / `Requirement_07_process_alerts.md` | ✅ Complete (audited 2026-04-28) | `StageAlert` (OneToOne with `Stage`), `process_alert_tasks.py` Huey task at 14:00 UTC, 3-day & 1-day reminders, configurable recipients (`notify_clients`); 25 backend tests + 3 E2E specs |
| 8 | Outlook Auth Integration | `Plan_08_outlook_auth.md` / `Requirement_08_outlook_auth.md` | ✅ Complete (Release Agosto 2026, commit `0494ec5`) | `outlook_login` endpoint mirroring `google_login` with server-side ID token verification (`_verify_microsoft_id_token`, cached `PyJWKClient`, multi-tenant `common`). **nOAuth hardening**: email trusted only via `xms_edov` / consumers tenant / `MICROSOFT_TRUSTED_TENANTS`; `preferred_username` never used as identity. Frontend `@azure/msal-browser` (`msal_config.js`, `login_with_outlook.js`, `OutlookLoginButton.vue` "Continuar con Microsoft", 4 auth views, `/auth/outlook/callback`). Tests: `TestOutlookLogin` + `TestVerifyMicrosoftIdToken` (backend), `login_with_outlook.test.js` (unit), `outlook-login-flow.spec.js` (E2E). Flow `auth-login-outlook` (P1). Pending operator: set `MICROSOFT_CLIENT_ID`/`VITE_MICROSOFT_CLIENT_ID` + enable `xms_edov` claim in Azure. |
| 8b | Minutas — Visibilidad compartida entre abogados (enhancement) | `Requirement_minutas_shared_visibility` | ✅ Complete (Release Agosto 2026, commit `d595ae0`) | Removed per-creator filter so all lawyers see/manage every minuta (Draft/Published). Serializer `created_by_name` (`select_related`, no N+1), "Creado por" column, "Todas / Solo mías" toggle (reuses backend `lawyer_id`), creator-name search; `allMinutas` getter replaces orphaned `getDocumentsByLawyerId`. Backend serializer/view tests + store/component unit tests. Flow `minutas-shared-visibility` (P2). |
| 9 | Marketplace | `Plan_09_marketplace.md` / `Requirement_09_marketplace.md` | 📋 Planned |
| 10 | Optional Signature | `Plan_10_firma_opcional.md` / `Requirement_10_firma_opcional.md` | 📋 Planned |
| 11 | Contract Execution | `Requirement_11_contract_execution` (Release Agosto 2026, branch `release-august-2026-c-v2`) | ✅ Complete (2026-07-07) | `DocumentPaymentRecord` (1 fila por doc+cuota, lazy — slots `pending` sintetizados; estados uploaded/accepted/rejected; re-upload sobre el MISMO registro conservando `rejection_reason` como historial; signal post_delete limpia archivos), summary type `payment_installments` ("Forma de pago (N cuotas)", parser estricto compartido modelo/serializer), migración `0068`. API: 5 endpoints `dynamic-documents/<pk>/payment-records/*` (shape único con `can_upload/can_review/next_uploadable` — el FE nunca calcula reglas; secuencial autoritativo con 409; archivos PDF/JPG/PNG/DOCX ≤20MB; download anti-IDOR). `payment_notification_service` (email+in-app, skip auto-notificación). FE: store `paymentRecords`, opción en DocumentVariablesConfig (auto number), fila en DocumentSummaryModal (`formatInstallments`), menú "Subir/Ver Cuentas de Cobro" en 3 configs, `PaymentRecordsModal` (progreso, contabilidad, panel aceptar/rechazar con motivo obligatorio) + `UploadPaymentRecordModal` (drag&drop). Tests: 22 modelo + 24 vistas + 3 serializer (pytest) + ~55 Jest + 5 E2E (`docs-contract-execution` P1, flow-definitions v1.10.0). Fake data: doc con progreso 1/3 + doc fresco; verificado ciclo delete/create en staging. Gotcha: emitir eventos ANTES de `showNotification` (SweetAlert resuelve al cerrar). |
| 12 | In-Place Formalize | `Plan_12_in_place_formalize.md` / `Requirement_12_in_place_formalize.md` | ✅ Complete |

---

## 3. Known Issues & Tech Debt

| # | Issue | Severity | Area |
|---|-------|----------|------|
| 1 | SQLite used in development — limited concurrent write support | Low | Backend / Dev only |
| 2 | `DJANGO_SECRET_KEY` has insecure default in settings.py | Medium | Security (dev only, overridden in production) |
| 3 | `debug.log` is 6.7MB — gitignored (rotated `debug.log.N` files also ignored since `6cba400`), but no `RotatingFileHandler` found in repo settings; rotation config still pending | Low | Operations |
| 5 | Pre-registered flow `minutas-columns` (P2, documents) corresponds to planned feature #2 Minutas — not yet implemented. Will get its spec when feature lands. | Low | Testing / Planned features |

### Completed Maintenance

| Date | Task | Result |
|------|------|--------|
| 2026-08-27 | Final backend major resolution | Django 5.2.17→6.1 + `MAILERS`, ReportLab 4.5.1→5.0.1, service/trámite PDF migration to restricted WeasyPrint, xhtml2pdf removal and real MySQL 8.4 CI gate; clean full environment has zero outdated packages; live MySQL 8.0.46 must be upgraded before deploy |
| 2026-08-27 | Backend developer-tooling refresh | pre-commit 3.7.1->4.6.2, Ruff 0.6.8->0.16.4 and pip-audit 2.10.1 pinned in dev tooling; clean full environment reduced outdated packages from ten to two temporary Django/ReportLab holds, later cleared by the final major resolution |
| 2026-08-27 | Gradual backend major upgrades — svglib | svglib 1.5.1→2.2.0; Cairo is now optional, clean audit/checks passed, SVG/CSS 96 px→72 pt conversion + ReportLab/xhtml2pdf output and 17 focused PDF tests remained healthy |
| 2026-08-27 | Gradual backend major upgrades — Django 6.1 | ✅ Resolved: Django 6.1 pinned, email configuration moved to `MAILERS`, and CI now exercises migrations/checks/health on MySQL 8.4; deploy remains gated on upgrading the live MySQL 8.0.46 host |
| 2026-08-27 | Gradual backend major upgrades — ReportLab 5 | ✅ Resolved: service/trámite HTML-to-PDF moved to WeasyPrint, xhtml2pdf removed and ReportLab 5.0.1 pinned with direct/rendered-PDF regressions green |
| 2026-08-27 | Gradual backend major upgrades — pyHanko validation stack | pyHanko 0.25.3→0.36.2 + `pyhanko-certvalidator` 0.26.8→0.31.4 as a resolver-required unit; clean audit, real xhtml2pdf output, offline RSA chain validation and 21 focused tests passed |
| 2026-08-27 | Gradual backend major upgrades — OpenCV headless | `opencv-python-headless` 4.14.0.94→5.0.0.93; clean resolution/audit, NumPy-backed image operation smoke and 11 health tests passed; no direct repository imports found |
| 2026-08-27 | Gradual backend major upgrades — pandas | pandas 2.3.3→3.0.5; clean resolution/audit, dual-engine Excel round-trip, string/missing/date/grouping smoke, 10 report-function and 19 report-view tests passed |
| 2026-08-27 | Gradual backend major upgrades — Huey | Huey 2.6.0→3.3.4; shared explicit `REDIS_URL`, 14-task registry + consumer validation, real ephemeral-Redis queue/result/lock smoke, 11 health tests and 19 focused task tests passed |
| 2026-08-27 | Gradual backend major upgrades — redis | `redis` 5.3.1→8.1.0; clean resolution/audit, real redis-py + Huey queue/result/schedule operations, real health endpoint, and 11 health tests passed against isolated services |
| 2026-08-27 | Gradual backend major upgrades — django-dbbackup | `django-dbbackup` 4.3.0→5.3.0; migrated to `STORAGES["dbbackup"]`, preserved command scheduling, created a real compressed SQLite backup + metadata, and passed 11 health tests |
| 2026-08-27 | Gradual backend major upgrades — django-cleanup | `django-cleanup` 8.1.0→9.0.0; clean resolution/audit, app intentionally remained inactive, and 6 application-specific file cleanup tests passed |
| 2026-08-27 | Gradual backend major upgrades — gunicorn | `gunicorn` 23.0.0→26.2.0; clean resolution/audit, deployed WSGI/worker/socket config accepted, and 11 health tests passed without starting services |
| 2026-08-27 | Gradual backend major upgrades — cssselect2 | `cssselect2` 0.8.0→0.9.0; clean resolution/audit, compound selector + WeasyPrint + svglib smoke, 2 document-render and 7 service/trámite PDF tests passed |
| 2026-08-27 | Gradual backend major upgrades — pyphen | `pyphen` 0.17.2→0.18.1; clean resolution/audit, Spanish fallback + splitting + WeasyPrint hyphenation smoke, 2 document-render and 7 service/trámite PDF tests passed |
| 2026-08-27 | Gradual backend major upgrades — pydyf | `pydyf` 0.11.0→0.12.1; clean resolution/audit, real PDF structure/metadata/link smoke, 2 document-render and 7 service/trámite PDF tests passed |
| 2026-08-27 | Gradual backend major upgrades — cachetools | `cachetools` 5.5.2→7.1.7; clean resolution/audit, TTL + LRU + memoization smoke, 10 Google-login and 11 health tests passed |
| 2026-08-27 | Gradual backend major upgrades — zopfli | `zopfli` 0.2.3.post1→0.4.3; clean resolution/audit, zlib/gzip + FontTools compression smoke, 2 document-render and 7 service/trámite PDF tests passed |
| 2026-08-27 | Gradual backend major upgrades — pycparser | `pycparser` 2.23→3.0; clean resolution/audit, C parser + cffi + Ed25519 smoke, 4 signature PDF and 7 service/trámite PDF tests passed |
| 2026-08-27 | Gradual backend major upgrades — uritools | `uritools` 4.0.3→6.1.3; clean resolution/audit, HTTPS/LDAP + certificate name-tree smoke, 4 signature PDF and 11 health tests passed |
| 2026-08-27 | Gradual backend major upgrades — webencodings | `webencodings` 0.5.1→0.6.1; clean resolution/audit, encoding + HTML/CSS/PDF smoke, 2 document-render and 13 service/trámite PDF tests passed |
| 2026-08-27 | Gradual backend major upgrades — chardet | `chardet` 5.2.0→7.6.0; clean resolution/audit, supported detector API + CLI smoke, and 11 health tests passed; no direct consumers required migration |
| 2026-08-27 | Gradual backend major upgrades — termcolor | `termcolor` 2.5.0→3.3.0; clean resolution/audit, ANSI/no-color + Fire dispatch smoke, command-registry load, and 11 health tests passed |
| 2026-08-27 | Gradual backend major upgrades — packaging | `packaging` 24.2→26.3; clean resolution/audit, version and specifier smoke, Gunicorn WSGI config validation, and 11 health tests passed |
| 2026-08-27 | Gradual backend major upgrades — pytz | `pytz` 2025.2→2026.3.post1; pandas/Bogotá conversion smoke, dbbackup command discovery and 10 report-model tests passed with clean resolution and audit |
| 2026-08-27 | Gradual backend major upgrades — tzdata | `tzdata` 2025.3→2026.3; packaged Bogotá zone smoke, report models and process-alert scheduling passed under SQLite, with clean resolution and zero-finding audit |
| 2026-08-27 | Gradual backend major upgrades — certifi | `certifi` 2024.12.14→2026.7.22; clean resolution, CA-bundle/Requests smoke, health and SECOP client regression, Django check and zero-finding `pip-audit` passed |
| 2026-08-27 | Gradual backend major upgrades — Faker | `Faker` 25.9.2→40.37.0; clean Python 3.12 resolution, provider/locale smoke, 12 focused seeder tests, full collection and `pip-audit` all passed without changing fake-data logic |
| 2026-08-27 | Gradual backend major upgrades — pytest-cov | `pytest-cov` 6.3.0→7.1.0; isolated install and `pip check` passed, 3,187 tests collected, health slice preserved identical coverage totals, and `pip-audit` remained at 0 findings |
| 2026-08-26 | Backend dependency vulnerability remediation | 85 audit records reduced to 0; security-major pins applied, `PyPDF2` removed, WeasyPrint resource fetching restricted, and pytest 9 fixture compatibility completed |

---

## 4. Testing Status

### Test Quality Gate & CI Regime (adopted 2026-07-23/24)

The canonical test-quality core was adopted (`7c3af01`) with a per-project `.testquality.yml`:
thresholds `max_test_lines 50`, `max_assertions_per_test 7`, `min_test_lines 3`,
`max_timeout_ms 100`, and `banned_tokens: batch/coverage/cov/deep`. Junk detectors classify
weak assertions, missing user interaction, global-state leaks, flow-tag mismatches, etc.

- **Grandfathered debt**: `.junk-baseline.json` holds **553** pre-existing findings
  (frontend-unit **382**, frontend-e2e **171**, backend **0**). CI blocks any NEW junk while the
  baseline stays warning-only and may only shrink (`7395579`).
- **Testing skills** realigned to the new gate (`ed9eb07`); **merge-when-green** now guards
  release branches (`ac17e4f`).
- **Current gate score: 98** with **557 warnings** — weak_assertion 371, flow_tag_mismatch 81,
  no_user_interaction 73, global_state_leak 60, no_data_assertion 14, duplicate_coverage 14,
  too_many_assertions 4.

### Backend Tests (101 files / 3176 test functions, 582 `Test*` classes — verified 2026-07-24)

> Markers actually applied: `django_db` 995, `edge` 151, `contract` 64, `integration` 60.
> Only 16 `parametrize` uses across the suite. `rest` is declared in `pytest.ini` but used **0** times.

Latest additions (2026-04-28):
- `tests/models/test_stage_alert.py` (9 tests)
- `tests/tasks/test_process_alert_tasks.py` (11 tests)
- `tests/views/test_process_alerts.py` (5 tests)
- `tests/services/test_notification_service.py`, `test_signature_notification_service.py`
- `tests/tasks/test_notification_tasks.py`
- `tests/views/test_notification_views.py`

| Directory | Purpose |
|-----------|---------|
| `tests/models/` | Model unit tests |
| `tests/serializers/` | Serializer tests |
| `tests/views/` | API view tests (incl. formalize + correct endpoint tests, process alerts, notifications) |
| `tests/utils/` | Utility function tests |
| `tests/tasks/` | Huey task tests (incl. `test_process_alert_tasks.py`) |
| `tests/services/` | Service layer tests (incl. `test_notification_service.py`) |
| `tests/commands/` | Management command tests |

### Frontend Unit Tests (208 files / 2296 test cases — updated 2026-08-21)

| Directory | Purpose |
|-----------|---------|
| `test/stores/` | Pinia store tests |
| `test/components/` | Component tests |
| `test/composables/` | Composable tests |
| `test/views/` | View component tests |
| `test/router/` | Router tests |
| `test/animations/` | Animation tests |
| `test/shared/` | Shared utility tests |
| `test/scripts/` | Script tests |
| `test/e2e/` | E2E helper tests |
| `test/utils/` | Utility tests |
| `test/data_sample/` | Test data samples |

### Frontend E2E Tests (204 spec files / 633 test cases — verified 2026-07-24) — **164 flows registered in flow-definitions.json (v1.12.0)**

> **Flow-map drift (Phase 3 of the 2026-07-24 campaign reconciles it):** USER_FLOW_MAP.md lists **168** flows, flow-definitions.json registers **164**, and the coverage snapshots report **150–153** — the three sources have drifted apart.

Latest additions (2026-04-28):
- `e2e/process/process-alert-recipients.spec.js` (3 tests)
- `e2e/notifications/notification-center.spec.js` (4 tests — bell+badge, empty state, list+tabs, service request pulse + URL cleanup)
- `e2e/signatures/legal-files-menu-pulse.spec.js` (2 tests — Req #6 menu pulse + sessionStorage flag)
- `e2e/signatures/legal-files-auto-redirect.spec.js` (2 tests — Req #6 auto-redirect + URL param override)
- `e2e/signatures/legal-files-table-pulse.spec.js` (1 test — Req #6 8-second pulse on pending rows)

| Directory | Specs | Flows Covered |
|-----------|-------|---------------|
| `e2e/auth/` | 11 | Login, registration, password reset, Google OAuth |
| `e2e/dashboard/` | 11 | Dashboard interactions |
| `e2e/documents/` | 38 | Document CRUD, editor, permissions, tags, folders, relationships, letterhead, formalize-in-place, correct |
| `e2e/organizations/` | 50 | Organization CRUD, invitations, memberships, posts, corporate requests, cross-role flows |
| `e2e/process/` | 12 | Process CRUD, case files, search, history, process-alert-recipients |
| `e2e/legal-requests/` | 10 | Legal request creation, management, responses |
| `e2e/secop/` | 12 | SECOP browse, classify, alerts, saved views (create/edit/delete/favorites), export, sync, UNSPSC multi-select |
| `e2e/signatures/` | 10 | Signature flows, pending/archived documents, legal-files alerts (menu pulse, auto-redirect, table pulse) |
| `e2e/subscriptions/` | 7 | Checkout, cancellation, payment updates |
| `e2e/intranet/` | 3 | Intranet page interactions |
| `e2e/profile/` | 2 | Profile completion, updates |
| `e2e/notifications/` | 1 | Notification Center (bell+badge, empty state, list+tabs, service-request pulse) |
| `e2e/basic-user/` | 1 | Basic user restrictions |
| `e2e/checkout/` | 1 | Checkout flow |
| `e2e/directory/` | 1 | Directory listing |
| `e2e/electronic-signature/` | 1 | Electronic signature modal |
| `e2e/error-handling/` | 1 | Error handling flows |
| `e2e/misc/` | 1 | Miscellaneous flows |
| `e2e/policies/` | 1 | Policy page navigation |
| `e2e/router-guards/` | 1 | Auth and role guard testing |
| `e2e/schedule/` | 1 | Appointment scheduling |
| `e2e/user-guide/` | 1 | User guide navigation |

> **E2E Flow Coverage (2026-06-23):** `flow-definitions.json` has 150 flows. August release added `auth-login-outlook` (P1) and `minutas-shared-visibility` (P2), both registered in `flow-definitions.json` + `USER_FLOW_MAP.md`. Earlier baseline (2026-04-08): 138 flows, all covered (0 missing).

---

## 5. Documentation Status

| Document | Path | Status |
|----------|------|--------|
| README | `README.md` | ✅ Comprehensive (913 lines) |
| Codex Setup | `docs/CODEX_SETUP.md` | ✅ Updated — skills auto-discovered from `.agents/skills/`, install script removed |
| Codex Methodology Guide | `docs/CODEX_METHODOLOGY_GUIDE.md` | ✅ Updated — removed install step, reflects auto-discovery model |
| Codex Migration Map | `docs/CODEX_MIGRATION_MAP.md` | ✅ Updated — removed install script references |
| Architecture Standard | `docs/DJANGO_VUE_ARCHITECTURE_STANDARD.md` | ✅ Complete |
| Testing Quality Standards | `docs/TESTING_QUALITY_STANDARDS.md` | ✅ Complete |
| Test Quality Gate Reference | `docs/TEST_QUALITY_GATE_REFERENCE.md` | ✅ Complete |
| Coverage Report Standard | `docs/BACKEND_AND_FRONTEND_COVERAGE_REPORT_STANDARD.md` | ✅ Complete |
| E2E Flow Coverage Standard | `docs/E2E_FLOW_COVERAGE_REPORT_STANDARD.md` | ✅ Complete |
| Functional Guide by Role | `docs/FUNCTIONAL_GUIDE_BY_ROLE.md` | ✅ Complete |
| User Flow Map | `docs/USER_FLOW_MAP.md` | ✅ Complete |
| Global Rules Guidelines | `docs/GLOBAL_RULES_GUIDELINES.md` | ✅ Complete |
| Deployment Guide | `docs/deployment-guide.md` | ✅ Complete |
| Subscription API | `backend/SUBSCRIPTION_API.md` | ✅ Complete |
| Subscription Setup | `backend/SUBSCRIPTION_SETUP.md` | ✅ Complete |
| Wompi Signature Debug | `backend/WOMPI_SIGNATURE_DEBUG.md` | ✅ Complete |
| Requirement Template | `docs/Requirement_template.md` | ✅ Complete |
| Requirements & Prices Mapping | `docs/Requirements_prices_mapping.md` | ✅ Complete |
| Next Requirements (12 plans + 12 requirements) | `docs/next_requirements/` | ✅ Complete |
| Memory Bank (PRD) | `docs/methodology/product_requirement_docs.md` | ✅ Complete |
| Memory Bank (Technical) | `docs/methodology/technical.md` | ✅ Complete |
| Memory Bank (Architecture) | `docs/methodology/architecture.md` | ✅ Complete |

---

## 6. Potential Improvements

| # | Improvement | Priority | Effort |
|---|------------|----------|--------|
| 1 | Add S3/cloud storage option for media files and backups | Low | High |
| 2 | Implement WebSocket for real-time notifications | Medium | High |
| 3 | Add database connection pooling for production | Low | Low |
| 4 | Add log rotation for `debug.log` | Low | Low |
| 5 | Consider TypeScript migration for frontend | Low | Very High |
