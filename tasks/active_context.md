# Active Context — G&M Internal Management Tool

## 1. Current State

### Solicitudes legales y publicaciones — ronda 7 (2026-09-27)

Candidatos P-backend-queries-18/19/20 sobre el mismo PR #130. El listado legal une
cliente y catálogos, calcula respuestas mediante anotación y evita cargar archivos
innecesarios; el serializer mantiene el fallback para instancias sin anotación.
La actualización de estado precarga el detalle consumido por la respuesta y la
notificación. Ambos listados de publicaciones unen su autor sin cambiar permisos.
QA independiente aprobó siete tests nuevos en SQLite y MySQL 8.4.11, trece
regresiones existentes y cinco controles que fallan sobre el baseline por consultas.
Al pasar de uno a cincuenta elementos, el listado legal mantiene una consulta,
el PUT cuatro y las publicaciones privadas/públicas tres/cuatro. Memoria y payload
de las solicitudes legales siguen sujetos a la conversación/lista completa.
Guion: `vps-ops-toolkit/docs/audits/2026-09-27-gym_project-perf-legal-posts.md`.
Evidencia: `vps-ops-toolkit/docs/audits/2026-09-27-r7-gym_project-qa.md`.
El cierre autorizado incluye merge-queue después del CI verde.

### Estadísticas, actualización corporativa y exportación SECOP (2026-09-27)

Sexta ronda: candidatos P-backend-queries-15/16/17 en la rama propia
`fix/27092026-perf-stats-update-export`, PR #130 hacia `master`.
Estadísticas organiza los conteos en cuatro consultas independientes;
la actualización corporativa reutiliza la precarga del detalle y del propietario
organizacional; SECOP carga sólo los campos consumidos por el Excel.
Se conservan permisos, filtros, ventanas temporales, payloads y límite de exportación.
QA independiente: 16 tests nuevos aprobados en SQLite y MySQL 8.4, seis
regresiones existentes aprobadas y tres controles que fallan contra el baseline.
Presupuestos verificados: estadísticas <=4 consultas, actualización <=8, exportación
una consulta con proyección limitada. No se midieron latencia ni memoria. La respuesta
corporativa mantiene la conversación completa: reducir consultas no limita su tamaño.
Guion: `vps-ops-toolkit/docs/audits/2026-09-27-gym_project-perf-stats-update-export.md`.

### Limpieza del repositorio (2026-09-25)

Auditoría de 1.309 archivos versionados: sin artefactos HIGH detectados. El lote
MEDIUM aprobado elimina el store de documentos recientes sin consumidores, su
test exclusivo y las dos excepciones de calidad de ese test; conserva los
endpoints backend. Corrige el filtro del hook de
calidad para incluir `backend/gym_app/tests/` y las excepciones de `.gitignore`
para fixtures de media, `.gitkeep` de logs y extensiones compartidas de VS Code.
El diagrama de stores refleja la eliminación. Sin cambios de API ni flujos UX.

Fuera del lote: revisar roles/versiones del README, instrucciones antiguas del
manual de usuario y la tabla del estándar arquitectónico. Se conserva el comando
`clean_service_notifications`: no se ha demostrado su obsolescencia operativa.
Validación local: dashboard 2/2, build frontend correcto, seis escenarios de
selección/propagación de fallos del hook y once casos de ignore correctos.
El hook real con Ruff analiza once tests backend: cero errores y una advertencia
preexistente por exceso de aserciones. Configuración pre-commit y diff válidos.

### Membresías y detalles organizacionales (2026-09-25)

Quinta ronda en el PR #128, candidatos P-backend-queries-12/13/14. Las
organizaciones disponibles para solicitudes unen su corporativo; las membresías
precargan resúmenes anotados sin cambiar el orden de ingreso. Ambos detalles de
organización cargan conteos independientes y miembros activos con sus usuarios.
El serializer reconoce ceros y listas vacías precargadas, conservando el fallback
para creación, edición e instancias directas. Se mantienen roles, permisos y las
organizaciones inactivas visibles mediante una membresía activa en los listados.
QA independiente verificó los dieciséis casos nuevos y cinco regresiones en
MySQL 8.4 aislado: consultas constantes con uno y cincuenta registros (listados
una/dos; detalles dos/dos/tres), payloads, frontera de solicitudes recientes y
acceso. Auditor y gate canónico aprobados. El contrato sigue sin paginación:
la mejora de queries no garantiza límites de memoria o payload al techo del dataset.
Guion: `vps-ops-toolkit/docs/audits/2026-09-25-gym_project-perf-memberships-organization-details.md`.
Verificación: `vps-ops-toolkit/docs/audits/2026-09-25-r5-gym_project-qa.md`.

### Procesos, invitaciones y detalles corporativos (2026-09-24)

Cuarta ronda en el PR #128, candidatos P-backend-queries-09/10/11. El listado de
procesos une su tipo de caso; las invitaciones precargan usuarios y organizaciones
con conteos independientes; ambos detalles corporativos precargan relaciones,
respuestas, autores y adjuntos. El conteo de respuestas reutiliza la caché normal
del manager, sin modificar el serializer ni la visibilidad actual.
QA verifica consultas constantes con uno y cincuenta registros, máximo seis
por listado y cuatro por detalle, además de payloads y permisos.
Guion: `vps-ops-toolkit/docs/audits/2026-09-24-gym_project-perf-processes-invitations-details.md`.
Verificación: `vps-ops-toolkit/docs/audits/2026-09-24-r4-gym_project-qa.md`.
Procesos y respuestas siguen sin paginación: esta ronda no garantiza un límite de
memoria/payload al techo del dataset. Esa evolución del contrato queda separada.

### Clasificaciones SECOP (2026-09-24)

Tercera ronda en el PR #128, candidatos P-backend-queries-07/08. Los dos listados
SECOP cargan sólo la clasificación del usuario actual; el detalle carga todas las
clasificaciones con sus autores y reutiliza esa precarga. Se conservan filtros,
paginación, campos, permisos y los fallbacks de los serializers directos.
Los guards exigen consultas constantes con uno y cincuenta registros (listados
máximo seis, detalle máximo dos), además de una clasificación cargada por proceso
propio mostrado, sin materializar clasificaciones ajenas. La cobertura contempla
precargas vacías, identidad del autor, notas, estados y fechas del payload.
Guion: `vps-ops-toolkit/docs/audits/2026-09-24-gym_project-perf-secop-classifications.md`.
Verificación independiente: `vps-ops-toolkit/docs/audits/2026-09-24-r3-gym_project-qa.md`.
Sin cambios de UX, infraestructura, dependencias o migraciones.

### Conversaciones, alertas y dashboard (2026-09-24)

Segunda ronda en el PR #128: precarga de autores y archivos de conversación,
conteo anotado de notificaciones SECOP y agregado condicional del dashboard.
Se conservan payloads, visibilidad y filtros. QA independiente confirma consultas
constantes con uno y cincuenta registros: conversación 3, alertas 1 y dashboard 1.
Los nueve tests nuevos/reforzados pasan en SQLite y MySQL 8.4 aislados; el lote
MySQL también conserva los cuatro presupuestos anteriores y las regresiones de
permisos y CRUD. Los cuatro presupuestos nuevos fallan por aserciones contra
`ac3178f`. Auditor dedicado y gate estricto aprobados; sin cambios en flujos frontend.
Guion: `vps-ops-toolkit/docs/audits/2026-09-24-gym_project-perf-conversations-alerts-dashboard.md`.
Verificación: `vps-ops-toolkit/docs/audits/2026-09-24-r2-gym_project-qa.md`.

### Rendimiento de listados (2026-09-24)

Ronda `perf-bounded-lists` sobre `master`: organizaciones, solicitudes corporativas
y procesos recientes conservan su contrato y cargan los datos relacionados sin
consultas por fila. Los conteos usan subconsultas independientes para evitar
multiplicación de relaciones y conservar el orden de prioridad. Recientes mantiene
el límite de diez y las etapas con/sin alerta. Presupuesto: queries constantes y
máximo seis por listado. QA mide 2 consultas en organizaciones y solicitudes
y 4 en recientes; verifica los presupuestos en SQLite y MySQL 8.4 aislados,
además de los conteos, la prioridad y el contenido relacionado.
Perfil y guion: `vps-ops-toolkit/docs/audits/2026-09-24-gym_project-perf-bounded-lists.md`.
Sin migraciones, dependencias nuevas ni cambios en flujos frontend.

### Explorador del manual (2026-09-19)

Nueva subsección del Manual de Usuario basada en el explorador orbital de Project Apps:
cuatro espacios, catálogo completo para usuarios autenticados, búsqueda, relaciones,
recorridos y enlaces a las guías existentes. Los accesos operativos conservan las
restricciones vigentes. Tarjetas en contenedores menores a 1024 px; órbita con teclado,
arrastre, zoom y pausa; estado compartible en query params. Trabajo aislado en
`feat/19092026-user-guide-explorer`, base `master` tras el cierre de la release de septiembre.
34 pruebas unitarias nuevas del catálogo, permisos, URL, inventario y ciclo de
animación; 16 E2E nuevas y 18 E2E de regresión del manual aprobadas. Build Vite
verificado; quality gate focalizado 100/100. Siete flujos registrados, con sus diez
outcomes cubiertos; sin cambios backend, migraciones ni refresh de fake data.
Hallazgo del inventario: el manual antiguo describe gestión de suscripción desde
el perfil y publicación de novedades en Inicio que no existen en esas pantallas.
El explorador describe planes/checkout y ubica la administración de novedades en el
panel administrativo; la actualización general de ese contenido antiguo queda fuera
de esta tarea.

The application is **feature-complete** with all 18 major features implemented, tested, and operational:

- User management with JWT + Google OAuth + reCAPTCHA
- Process management with stages, case files, and recent tracking
- Dynamic documents with full editor, variables, permissions, tags, folders, relationships, letterhead, PDF/Word export
- Electronic signatures with draw/upload, request/sign/reject/archive workflow
- Organizations with invitations, memberships, posts, and corporate requests
- Legal requests with file attachments, responses, and email notifications
- Subscription billing via Wompi with automated Huey tasks
- Dashboard with activity feed, recent items, and Excel reports
- Intranet, legal updates, PWA support, and interactive user guide
- Automated backups, query profiling (django-silk), and test quality gate
- **SECOP Public Procurement** ✅: Socrata API integration, process listing/detail, classifications, alerts, saved views, Excel export, professional UI/UX
- **Servicios y Trámites** ✅: catálogo de servicios, formularios dinámicos por etapas, guardado en borrador, radicado `AÑO-CONSECUTIVO`, PDF automático, notificaciones por correo, bandeja de solicitudes para abogados/admin y seguimiento para clientes
- **Notification Center (Req #5)** ✅: `Notification` model + `notification_service` (`create_notification`/`create_bulk_notifications`/`get_unread_count`), in-app center with categories (`signature_*`, `process_alert`, `general`), priorities, snooze, archive, deep-link via `link_type`/`link_id`.
- **Process Alerts (Req #7)** ✅: `StageAlert` (OneToOne with `Stage`, CASCADE), auto-created for ALL stages on `create_process`/`update_process` (last stage gets user-config, others get defaults), daily Huey task at 14:00 UTC sends 3-day & 1-day reminders via email + in-app, configurable recipients (`notify_clients`).

### Codebase Metrics (re-verified 2026-07-24 — structural counts held since 2026-07-22; only test-function counts grew)

| Metric | Count |
|--------|-------|
| Backend model files | 15 |
| Backend model classes | 56 (55 models.Model subclasses + User via AbstractUser; UserManager excluded) |
| Backend view files | 32 |
| Backend serializer files | 13 |
| Backend URL patterns | 205 |
| Backend test files | 103 (3208 test functions, 583 `Test*` classes, 18 parametrize uses) |
| Backend Huey periodic tasks | 11 |
| Frontend Vue components | 115 |
| Frontend view pages | 45 |
| Frontend Pinia store files | 46 |
| Frontend composables | 16 |
| Frontend unit test files | 208 (2296 test cases) |
| Frontend E2E spec files | 205 (650 test cases) |
| Frontend E2E flows (flow-definitions.json) | 164 (v1.12.1) |

---

## 2. Recent Focus Areas

- **Final backend major resolution — Django 6.1 + ReportLab 5 (2026-08-27, complete in PR #118)**:
  - Upgraded Django 5.2.17→6.1 and ReportLab 4.5.1→5.0.1. The final service/trámite HTML-to-PDF path now reuses the existing restricted WeasyPrint renderer, allowing xhtml2pdf 0.2.17 and its `reportlab<5` ceiling to be removed.
  - Migrated the deprecated Django email settings to `MAILERS` while preserving the existing `EMAIL_*` environment-variable contract, and removed explicit `fail_silently=False` arguments that Django 7 deprecates.
  - Added a GitHub Actions MySQL 8.4 compatibility job that applies all migrations, asserts the server version, runs Django database checks and exercises the health endpoint on the supported engine.
  - A fresh full developer environment reports no broken requirements, no known vulnerabilities and zero outdated packages. Focused WeasyPrint, ReportLab, mailer, SECOP email and Django checks pass under isolated settings.
  - **Deployment prerequisite:** the active host remains on MySQL 8.0.46. Upgrade it to MySQL 8.4+ before deploying this release; no deployed database, runtime venv or service was changed here.

- **Backend developer-tooling refresh (2026-08-27, complete)**:
  - Updated pre-commit 3.7.1->4.6.2 and Ruff 0.6.8->0.16.4, and made the existing `pip-audit` 2.10.1 installation reproducible through `requirements-dev.txt`.
  - A clean full developer environment advanced the six related transitive packages and reduced `pip list --outdated` from 10 packages to two temporary Django/ReportLab holds; the final major-resolution follow-up above later cleared both.
  - Pre-commit config validation, Ruff's real curated-selector integration, 8 focused quality-gate tests, Django check, 3,187-test collection and 11 health tests passed under isolated SQLite. Production pins, databases and services were untouched.

- **Gradual backend major upgrades — svglib (2026-08-27, complete)**:
  - Upgraded svglib 1.5.1→2.2.0 after confirming that the current release moved `rlpycairo` to the optional `bitmaps` extra; the default installation no longer requires pycairo and resolves with reportlab 4.5.1.
  - The cumulative clean environment passed installation, `pip check`, Django check and a zero-finding `pip-audit`; SVG/CSS conversion honored the 2.x 96 px→72 pt scale, produced a readable ReportLab PDF, and remained embeddable through xhtml2pdf.
  - Thirteen service/trámite PDF tests and four xhtml2pdf/current-color tests passed under isolated SQLite. No application migration, native package installation, database command or staging/production service ran.

- **Gradual backend major upgrades — Django 6.1 former infrastructure hold (2026-08-27, resolved)**:
  - Installed Django 6.1 with the complete cumulative requirements; dependency resolution, `pip check`, Django's SQLite system check, `pip-audit`, 11 health tests and 3 email-path tests all passed.
  - Restored Django 5.2.17 because Django 6.1's MySQL backend requires MySQL 8.4+, while the active server on this host is MySQL 8.0.46 and CI exercises only SQLite. A green SQLite CI would therefore be insufficient deployment evidence.
  - The final follow-up pinned Django 6.1, migrated email configuration to `MAILERS`, and added a real MySQL 8.4 CI gate. Deployment remains blocked until the active MySQL 8.0.46 server itself is upgraded.

- **Gradual backend major upgrades — ReportLab 5 former standalone hold (2026-08-27, resolved)**:
  - Attempted reportlab 4.5.1→5.0.1 against the complete cumulative requirements; pip rejected it because xhtml2pdf 0.2.17 explicitly requires `reportlab>=4.0.4,<5`.
  - The final follow-up migrated the service/trámite renderer to WeasyPrint, removed xhtml2pdf and pinned ReportLab 5.0.1. Direct PDF and readable service-PDF regressions pass in the clean environment.

- **Gradual backend major upgrades — pyHanko validation stack (2026-08-27, complete)**:
  - Upgraded pyHanko 0.25.3→0.36.2 and `pyhanko-certvalidator` 0.26.8→0.31.4 atomically, resolving the standalone validator hold through the compatibility range declared by pyHanko 0.36.2.
  - The cumulative clean environment passed installation, `pip check`, Django check and a zero-finding `pip-audit`; xhtml2pdf produced a real, readable service-style PDF and the validator accepted a locally generated root/signer RSA chain with network fetching disabled.
  - Thirteen service/trámite PDF tests, four signature-PDF tests and four xhtml2pdf/current-color tests passed under isolated SQLite. No application migration, database command or staging/production service ran.

- **Gradual backend major upgrades — OpenCV headless (2026-08-27, complete)**:
  - Upgraded the exact backend pin from `opencv-python-headless` 4.14.0.94 to 5.0.0.93; repository search found no direct `cv2` imports, so no application migration was required.
  - The cumulative clean environment passed installation, `pip check`, Django check and a zero-finding `pip-audit`; OpenCV 5/NumPy 2 passed color conversion, resize, blur, PNG encode/decode and contour operations.
  - The 11 health tests passed under isolated SQLite. No migration or staging database command ran; the unused direct pin should be reevaluated for removal in a later cleanup.

- **Gradual backend major upgrades — pandas (2026-08-27, complete)**:
  - Upgraded the exact backend pin from pandas 2.3.3 to 3.0.5 for the report-generation subsystem; no application code migration was required.
  - The cumulative clean environment passed installation, `pip check`, Django check and a zero-finding `pip-audit`; text dtype, missing values, timezone removal, grouping and round-trip Excel output passed with both XlsxWriter and openpyxl.
  - Ten report-function tests and 19 report-view tests passed under isolated SQLite (one pre-existing conditional skip and one deliberate deselection kept the batches within the 20-test limit). No migration or staging database command ran.

- **Gradual backend major upgrades — Huey (2026-08-27, complete)**:
  - Upgraded the exact backend pin from Huey 2.6.0 to 3.3.4 while preserving all 14 registered project tasks, Django's `run_huey` consumer and the existing decorators, schedules and locks.
  - Materialized `REDIS_URL` once in Django settings so Huey and the health endpoint share the same configured source without depending on storage implementation attributes.
  - The cumulative clean environment passed installation, `pip check`, Django check and a zero-finding `pip-audit`; an ephemeral Redis smoke validated enqueue, execution, result retrieval and lock contention. The 11 health and 19 focused task tests passed under isolated SQLite. No staging/production Redis connection, migration or staging database command ran.

- **Gradual backend major upgrades — redis (2026-08-27, complete)**:
  - Upgraded the exact backend pin from `redis` 5.3.1 to 8.1.0 while preserving `Redis.from_url` health checks and Huey 2.6.0's connection-pool integration.
  - The cumulative clean environment passed installation, `pip check`, Django check and a zero-finding `pip-audit`; direct client, pipeline, queue, result-store and scheduled-task Lua operations passed against an ephemeral Redis server.
  - The real health endpoint reported SQLite and Redis healthy, and the 11 health tests passed. No staging/production Redis connection, migration or staging database command ran.

- **Gradual backend major upgrades — django-dbbackup (2026-08-27, complete)**:
  - Upgraded the exact backend pin from `django-dbbackup` 4.3.0 to 5.3.0 and migrated its removed legacy storage settings to `STORAGES["dbbackup"]`, preserving the existing filesystem path and Django's default/staticfiles aliases.
  - The cumulative clean environment passed installation, `pip check`, Django check and a zero-finding `pip-audit`; both management commands retained compression/cleanup options and the scheduled dispatcher retained its two calls.
  - A real isolated SQLite backup produced valid compressed data and metadata; 11 health tests passed. No migration or staging database command ran.

- **Gradual backend major upgrades — django-cleanup (2026-08-27, complete)**:
  - Upgraded the exact backend pin from `django-cleanup` 8.1.0 to 9.0.0 without registering or activating its automatic signals; repository-specific cleanup behavior remains authoritative.
  - The cumulative clean environment passed installation, `pip check`, Django check and a zero-finding `pip-audit`; package import/version metadata and the intentionally inactive app state were confirmed.
  - Four physical-file deletion tests and two replacement-cleanup tests passed under SQLite. No migration or staging database command ran.

- **Gradual backend major upgrades — gunicorn (2026-08-27, complete)**:
  - Upgraded the exact backend pin from `gunicorn` 23.0.0 to 26.2.0 while retaining the three-worker Unix-socket systemd command and WSGI entry point.
  - The cumulative clean environment passed installation, `pip check`, Django check and a zero-finding `pip-audit`; Gunicorn configuration check/print modes accepted every deployed argument.
  - The 11 health tests passed under SQLite. No service restart, migration or staging database command ran.

- **Gradual backend major upgrades — cssselect2 (2026-08-27, complete)**:
  - Upgraded the exact backend pin from `cssselect2` 0.8.0 to 0.9.0 for its direct consumers WeasyPrint and svglib.
  - The cumulative clean environment passed installation, `pip check`, Django check and a zero-finding `pip-audit`; compound selectors, SVG CSS conversion and styled WeasyPrint output remained valid.
  - The 2 document-render and 7 service/trámite PDF-generation tests passed under SQLite. No migration or staging database command ran.

- **Gradual backend major upgrades — pyphen (2026-08-27, complete)**:
  - Upgraded the exact backend pin from `pyphen` 0.17.2 to 0.18.1 for its direct consumer WeasyPrint 69.0.
  - The cumulative clean environment passed installation, `pip check`, Django check and a zero-finding `pip-audit`; Spanish dictionary fallback, splitting and automatic-hyphenation PDF rendering remained valid.
  - The 2 document-render and 7 service/trámite PDF-generation tests passed under SQLite. No migration or staging database command ran.

- **Gradual backend major upgrades — pydyf (2026-08-27, complete)**:
  - Upgraded the exact backend pin from `pydyf` 0.11.0 to 0.12.1 for its direct consumer WeasyPrint 69.0.
  - The cumulative clean environment passed installation, `pip check`, Django check and a zero-finding `pip-audit`; real PDF output retained its header, page, title metadata and link annotation.
  - The 2 document-render and 7 service/trámite PDF-generation tests passed under SQLite. No migration or staging database command ran.

- **Gradual backend major upgrades — cachetools (2026-08-27, complete)**:
  - Upgraded the exact backend pin from `cachetools` 5.5.2 to 7.1.7; no repository import or installed reverse dependency required migration.
  - The cumulative clean environment passed installation, `pip check`, Django check and a zero-finding `pip-audit`; TTL, LRU and memoization behavior remained valid.
  - The 10 Google-login and 11 health tests passed under SQLite. No migration or staging database command ran.

- **Gradual backend major upgrades — zopfli (2026-08-27, complete)**:
  - Upgraded the exact backend pin from `zopfli` 0.2.3.post1 to 0.4.3 for the optional FontTools WOFF-compression path.
  - The cumulative clean environment passed installation, `pip check`, Django check and a zero-finding `pip-audit`; zlib/gzip round trips and FontTools compression remained valid.
  - The 2 document-render and 7 service/trámite PDF-generation tests passed under SQLite. No migration or staging database command ran.

- **Gradual backend major upgrades — pycparser (2026-08-27, complete)**:
  - Upgraded the exact backend pin from `pycparser` 2.23 to 3.0 for its cffi consumer.
  - The cumulative clean environment passed installation, `pip check`, Django check and a zero-finding `pip-audit`; C AST parsing, cffi calls and Ed25519 sign/verify remained valid.
  - The 4 signature PDF and 7 service/trámite PDF-generation tests passed under SQLite. No migration or staging database command ran.

- **Gradual backend major upgrades — uritools (2026-08-27, complete)**:
  - Upgraded the exact backend pin from `uritools` 4.0.3 to 6.1.3 for its pyhanko-certvalidator consumer.
  - The cumulative clean environment passed installation, `pip check`, Django check and a zero-finding `pip-audit`; HTTPS/LDAP parsing and certificate URI name-tree behavior remained valid.
  - The 4 signature PDF tests and 11 health tests passed under SQLite. No migration or staging database command ran.

- **Gradual backend major upgrades — webencodings (2026-08-27, complete)**:
  - Upgraded the exact backend pin from `webencodings` 0.5.1 to 0.6.1 for cssselect2, html5lib, tinycss2 and tinyhtml5.
  - The cumulative clean environment passed installation, `pip check`, Django check and a zero-finding `pip-audit`; encoding aliases, HTML/CSS parsing and selector behavior remained valid.
  - Direct WeasyPrint rendering, 2 document-render tests and 13 service/trámite PDF tests passed under SQLite. No migration or staging database command ran.

- **Gradual backend major upgrades — chardet (2026-08-27, complete)**:
  - Upgraded the exact backend pin from `chardet` 5.2.0 to 7.6.0; the repository has no direct imports or reverse package dependencies requiring migration.
  - The cumulative clean environment passed installation, `pip check`, Django check and a zero-finding `pip-audit`; UTF-8 and legacy-byte detection plus the CLI remained operational.
  - The supported top-level `UniversalDetector` API and the 11 health tests passed under SQLite. No migration or staging database command ran.

- **Gradual backend major upgrades — termcolor (2026-08-27, complete)**:
  - Upgraded the exact backend pin from `termcolor` 2.5.0 to 3.3.0 for its direct consumer Fire 0.7.1.
  - The cumulative clean environment passed installation, `pip check`, Django check and a zero-finding `pip-audit`; ANSI color, no-color and Fire dispatch behavior remained valid.
  - Django's command registry loaded normally and the 11 health tests passed under SQLite. No migration or staging database command ran.

- **Gradual backend major upgrades — packaging (2026-08-27, complete)**:
  - Upgraded the exact backend pin from `packaging` 24.2 to 26.3 for its direct consumers pytest and Gunicorn.
  - The cumulative clean environment passed installation, `pip check`, Django check and a zero-finding `pip-audit`; version/specifier parsing and both consumer imports remained valid.
  - Gunicorn accepted the existing WSGI configuration and the 11 health tests passed under SQLite. No migration or staging database command ran.

- **Gradual backend major upgrades — pytz (2026-08-27, complete)**:
  - Upgraded the exact backend pin from `pytz` 2025.2 to 2026.3.post1 for the consumers pandas and django-dbbackup.
  - The cumulative clean environment passed installation, `pip check`, Django check and a zero-finding `pip-audit`; Bogotá UTC offsets remained `-05:00` through both pytz and pandas.
  - The dbbackup management command loaded normally and 10 report-model tests passed under SQLite. No backup or database-writing command ran.

- **Gradual backend major upgrades — tzdata (2026-08-27, complete)**:
  - Upgraded the exact backend pin from `tzdata` 2025.3 to 2026.3, preserving it as the cross-platform IANA fallback consumed by pandas and Python's `zoneinfo`.
  - A clean Python 3.12 environment passed the cumulative install, `pip check`, Django check and zero-finding `pip-audit`; the packaged `America/Bogota` resource loaded successfully.
  - Report-model tests (10) and process-alert scheduling tests (16) passed under an isolated SQLite test database. No staging database command ran.

- **Gradual backend major upgrades — certifi (2026-08-27, complete)**:
  - Upgraded the exact backend pin from `certifi` 2024.12.14 to 2026.7.22; no application code or Requests configuration changed.
  - A clean Python 3.12 environment installed the cumulative requirements and passed `pip check`, Django's system check and a zero-finding `pip-audit`.
  - The CA bundle loaded into an SSL context with 121 certificate authorities, Requests resolved the same bundle path, and the health plus SECOP client regression slices passed.

- **Gradual backend major upgrades — Faker (2026-08-27, complete)**:
  - Upgraded the exact backend pin from `Faker` 25.9.2 to 40.37.0 in isolation. Faker imports remain confined to fake-data management commands; application runtime behavior and seeder business rules are unchanged.
  - Reviewed the intervening major release notes against the project's provider surface. Python 3.12 remains supported, the temporary `date_time_between` boundary changes from Faker 34 were reverted in Faker 35, and the default plus `es_CO` providers used by the seeders remain available.
  - Verification used a clean Python 3.12 venv: full requirements installation and `pip check` passed, Django reported zero issues, all 3,187 tests collected, and the 12 focused service/corporate/intranet seeder tests passed both before and after the upgrade.
  - A direct smoke exercised every Faker API used by the project, including the `es_CO` company providers. `pip-audit` remained at zero known vulnerabilities; no fake-data refresh or database-writing command was run.

- **Gradual backend major upgrades — pytest-cov (2026-08-27, complete)**:
  - Upgraded the exact backend pin from `pytest-cov` 6.3.0 to 7.1.0 as the first isolated major step in the dependency roadmap; application runtime code and coverage configuration are unchanged.
  - Reviewed the 7.x breaking change that removes automatic Python subprocess coverage. The repository's subprocess-based tests execute Node tooling, while CI covers only `gym_app`, so enabling Coverage.py's subprocess patch would add behavior without preserving any currently measured path.
  - Verification used a clean Python 3.12 venv: full requirements installation and `pip check` passed, Django reported zero issues, 3,187 tests collected, and the 11-test health slice passed under xdist while producing terminal/XML/JSON coverage reports.
  - Baseline parity was exact between 6.3.0 and 7.1.0: 10,877 statements, 3,441 covered lines, 2,918 branches, 2 covered branches and 25% slice coverage. `pip-audit` remained at zero known vulnerabilities across 92 installed packages.

- **Focused contract-execution walkthrough (2026-08-26, complete)**:
  - Added `docs/reports/Guia_Prueba_Cuentas_De_Cobro_26082026.md`, a standalone Spanish walkthrough that leads with the four deterministic `[QA Cuentas de Cobro]` contracts and keeps the from-scratch setup as an optional path.
  - Re-verified staging without mutations: `lawyer1@example.com` and `client1@example.com` are active with the documented test password; all four contracts remain fully signed and visible, with the expected empty, accepted, uploaded and rejected installment states. No fake-data refresh was needed.
  - Published an identical draft to the Document Manager in `Requerimientos 2026` as document `161`; private client metadata contains only the approved WhatsApp message, with both email fields empty.

- **Backend vulnerability remediation (2026-08-26, complete)**:
  - Upgraded `cryptography` 50.0.1, `lxml` 6.1.2, Pillow 12.3.0, `pypdf` 6.16.2, pytest 9.1.1, `sqlparse` 0.6.0, and WeasyPrint 69.0, with required companion pins CFFI 2.0.0 and cssselect2 0.8.0. Deprecated `PyPDF2` was removed and its consumers migrated.
  - Dynamic-document HTML now uses a deny-by-default WeasyPrint fetcher that permits inline data and approved local roots while blocking network URLs, remote file hosts, traversal and symlink escapes. The pypdf footer path now attaches pages before merging content, avoiding its pypdf 7 deprecation.
  - Pytest 9 compatibility removed 170 fixture-level `django_db` marks across 36 files; official pytest behavior confirms those marks never affected fixture access. Verification: clean install, `pip check`, zero-vulnerability `pip-audit` with pip 26.2.1, Django check, 16 targeted backend cases, cryptographic sign/verify smoke, Ruff, and test quality gate 100/100.
  - `svglib` stays at 1.5.1 because 1.6.0 introduces an unprovisioned `pycairo` native build dependency without reducing the vulnerability count.

- **SECOP staging sync recovery + hardening (2026-08-21, complete)**:
  - **Incident/recovery**: staging had no successful live sync since 2026-08-11 because Socrata rejected the optional `SECOP_APP_TOKEN` with 403, although the public query worked anonymously. The invalid staging token was blanked, `gym-staging-huey` restarted, and the normal incremental task queued.
  - **Verified live result**: `SyncLog` 619 finished `SUCCESS` at 18:53:23 UTC — 20,129 processed, 17,115 created, 3,014 updated, 1,143 stale closed; 15,992 active opportunities remained and the newest source update was 2026-08-19. Alert evaluation created 827 notification rows.
  - **Backend hardening**: token-authenticated 401/403 responses retry once anonymously without logging the credential; the real `sync_secop_data` task owns the lock shared by scheduled/manual entry points; manual triggering now uses `is_gym_staff` for lawyer/admin/staff/superuser consistency.
  - **Frontend hardening**: `useSecopSyncPolling` follows `SyncLog` every 5 seconds (bounded to 5 minutes), resumes an existing run, prevents duplicate local triggers, refreshes processes/filters after a newer success, and leaves safe server-derived failure state visible inside SECOP. The former fixed 180-second spinner is removed.
  - **Verification**: targeted Ruff, 39 backend cases, 17 Jest tests, Vite production build, and 5 Playwright SECOP tests passed. The immediate-alert email path logged an SMTP connection-close warning during the live evaluation; alert row creation completed and SMTP follow-up remains operationally separate.

- **Report-only test-audit + methodology campaign (2026-07-24)**:
  - **Phase 1 — Memory Bank refresh (✅ this update)**: recounted all codebase/test metrics as of 2026-07-24 and recorded the new test-quality gate + CI regime (below). Phases 2–4 of the same run are report-only: fake-data refresh, USER_FLOW_MAP ↔ flow-definitions reconciliation, and a whole-corpus junk-test audit report. No test files or runtime touched in Phase 1.
  - **New test-quality gate + CI regime** (commits `7c3af01` adopt canonical core, `7395579` block new junk in CI + grandfather debt, `ed9eb07` align testing skills, `ac17e4f` merge-when-green guards release branches): a per-project `.testquality.yml` gate with junk detectors (thresholds `max_test_lines 50`, `max_assertions_per_test 7`, `min_test_lines 3`, `max_timeout_ms 100`, `banned_tokens: batch/coverage/cov/deep`). A grandfathered `.junk-baseline.json` holds **553** findings (frontend-unit **382**, frontend-e2e **171**, backend **0**); CI blocks NEW junk while the baseline stays a warning-only debt that may only shrink. Current gate score **98** with **557 warnings** (weak_assertion 371, flow_tag_mismatch 81, no_user_interaction 73, global_state_leak 60, no_data_assertion 14, duplicate_coverage 14, too_many_assertions 4).
  - **SECOP manual-sync button fixed** (`17491a6`): the round-6 "product bug" (inert `SyncStatus.vue` with no `defineEmits`, 180s fake spinner) is now resolved — the button emits `trigger-sync`, so `POST secop/sync/trigger/` actually schedules the Huey sync (disabled window kept as a re-trigger cooldown). Signature "clear" button a11y gap also fixed (`1092803`).
  - **Two tooling defects found this session** (report-only, recorded in lessons-learned): (a) `scripts/maintenance/resolve-work-coordinate.sh` referenced by the `test-audit` skill does not exist in this repo; (b) the `backend-test-coverage` / `frontend-unit-test-coverage` / `frontend-e2e-test-coverage` skills invoke a `--files` gate flag that does not exist — the real flags are `--include-file` / `--include-glob`.
  - **Flow-map drift noted** (Phase 3 reconciles it): USER_FLOW_MAP.md **168** vs flow-definitions.json **164** (v1.12.0) vs coverage snapshots **150–153**.

- **Real-interaction audit (2026-07-23, ronda 6)**:
  - New criterion, sharper than R5's: does the test DRIVE the user action, or does it pre-cook a mock, `goto()` the end state and assert what it cooked? Measured by `scripts/audit_e2e_interactions.py` (persisted, exits 1 while suspects remain — usable as a CI/pre-commit gate).
  - **159 suspects → 0**; interactive tests 394 → 544; 11 genuine load-only flows (guards/empty states) marked `// audit: load-only flow (reason)`. Criterion written into `docs/TESTING_QUALITY_STANDARDS.md` § "Drive the Interaction, Assert the Transition".
  - **Mutation-validated**: removing `pageSize` from the `SecopList.vue` watcher turns the page-size test red; restoring it returns green. The suite now detects real breakage.
  - **Product bugs found (both now FIXED)**: SECOP sync button was inert (`SyncStatus.vue` had no `defineEmits` → `POST secop/sync/trigger/` never fired; 180s fake spinner) — **fixed 2026-07-23 in `17491a6`**: the button now emits `trigger-sync` and actually schedules the Huey sync (disabled window kept as a re-trigger cooldown). Signature "clear" button had no accessible name (its test was dead because the locator never matched) — **fixed in `1092803`**.
  - **Phantom coverage**: `document-key-fields.spec.js` tested an `is_key` field that exists nowhere in `src/`; another test faked navigation with `page.evaluate(router.push)`; one was fully redundant with three siblings.
  - **Unreachable routes/dead branches catalogued**: `/signed-documents`, `/subscriptions`, `/legal_requests` (sidebar filters both entries), `/no_connection`; `GuideNavigation` sub-sections, the "Firmantes requeridos" alert, `deleteOrganization`.
- **Depth round: anti-synthetic E2E pass (2026-07-23, ronda 5)**:
  - **47 specs rewritten, 135 synthetic assert sites → 0** (4 parallel agents): conditional asserts, swallowed failures and un-failable `#app` asserts replaced by driven interactions with observable outcomes (waitForRequest, stateful mocks, DOM results). ~215 tests green.
  - **Structural findings**: 10+ tests hit phantom routes (`/process`, `/organizations`, `/subscription`, `/privacy-policy` → catch-all redirect) without anyone noticing; nonexistent states/labels/selectors made asserts dead since creation; fixtures with invalid shapes left lists empty. Additional dead code confirmed: subscription management UI (cancel/reactivate/update-payment) and legal-updates CRUD have no components.
  - **Role/mobile variants**: SECOP basic-role upgrade overlays and notification-center mobile covered. Practical rule recorded: data-testid does not pass through Heroicons components (put it on native elements).
  - Gate stays 0/0/0.
- **Full user-flow coverage round (2026-07-22, ronda 4)**:
  - **Exhaustive dual-source flow audit**: frontend interaction sweep + classification of all 205 backend endpoints vs registry v1.11.0 → 11 unregistered flows found, all implemented and registered (`flow-definitions.json` v1.12.0, **164/164 covered**): notification item actions ×5, service-admin delete, process participants modal, signatures-certificate download, corporate dashboard KPIs (tag on existing stats spec), directory→process navigation, SECOP list retry (`df716f9`). Orphan endpoints without component consumers documented as non-flows in USER_FLOW_MAP (legal-updates CRUD, corporate dashboard-stats, org public detail, user Word-letterhead, recent-docs/processes widgets — dead-code candidates worth a product decision).
  - **Bug found by new E2E**: notification snooze menu was unusable on non-last rows — hover-out faded the actions bar (open menu invisible) and its mid-transition opacity buried the dropdown under the next row; actions bar now pins visible+z-20 while its menu is open (`5f3f692`).
  - **DataReassignment CI flake root fix**: untilEnabled() active wait absorbs degraded scheduling of full-suite coverage runs (`d2d1ff5`).
  - Gate remains 0/0/0. E2E spec files 201 → 203.
- **Total debt close-out (2026-07-22, ronda 3)**:
  - **Gate strict 100% clean across ALL severities: 0 errors / 0 warnings / 0 info** (`af446f1`): 66 it→test renames, nested service payloads → named builders, frozen clock on the future-due-date prefill (fake timers with doNotFake), justified markers (`disable network_dependency` for the pure-orchestration outlook helper, `disable fragile_test_data` mock emails, `disable wait_for_timeout` bounded non-occurrence wait), stale eslint-disable removed.
  - **DocumentEditor.vue 96.25→96.91%** (`caeb5e2`, 45 tests): the "0% / 909 stmts" note below is OBSOLETE — the 2026-07-16 initiative already brought it to 96% with 41 tests; ronda 3 closed the reachable residual branches (string-id coercion, no-id creation error, save without document, draft variable sync). Remainder: TinyMCE DOM handlers + unreachable defensive code.
  - Round touched only tests/docs — no runtime change, staging deploy from ronda 2 (`987952e` runtime) remains current.
- **Quality-debt round + CI green on release-* (2026-07-22, ronda 2)**:
  - **CI on release branches**: first CI cycle on PR #95 exposed and fixed three latent issues — 36 Jest failures (card tests missing stubs for the cuentas-de-cobro modals, `241478c`), a two-leaf migration graph (base's `0067_servicerequest...` vs v2's 0067-0070 chain → merge of base + `0071_merge`, `de27658`/`06711e4`), and a real UI overlap: the floating notification bell covered module-header actions at lg+, making the docs tour help button unclickable (`ec25149`, ModuleHeader `lg:pr-24`).
  - **Quality gate strict fully green: score 100, status passed, 0 errors, 0 warnings** (`a87b82a`, `7340db6`): 46 docstrings + import sorts (payment/minuta/process test files), freeze_time on the 9 tour-progress tests, tightened payment asserts, `allow-fragile-selector` markers on useGuidedTour's popover-contract asserts, role-based SweetAlert selectors in 2 E2E specs. Remaining debt: 80 info-level suggestions.
  - **ProcessForm.vue 100% statements/functions** (+11 Jest tests: stage-alert prefill, submit validations, edit submit path, search filters, 200MB file limit, helpers).
- **Release close-out pipeline (2026-07-22)** — 5-phase skill pipeline over `admin-data-reassignment` on `release-august-2026-c-v2` (methodology refresh → feature checklist + coverage → E2E audit → fake-data refresh → staging deploy):
  - **Memory Bank refreshed**: counts recounted across architecture/technical/PRD/tasks_plan (`201a901`); PRD 4.1 now lists Outlook OAuth, archiving and the reassignment module.
  - **Coverage closed**: backend `views/admin_reassignment.py` 91→100% (+10 edge-case tests); `DataReassignment.vue` 100% stmts+branches; SlideBar admin nav and ProcessForm `filteredLawyers` (incl. archived prefill) asserted (`8ef0f24`). Quality gate: 0 findings on the 6 touched test files (34 pre-existing docstring errors cleared, broad `pytest.raises` narrowed, asserts ≤7).
  - **Fake data fix**: template-derived docs in `create_dynamic_documents` now set `managed_by` (`10983cc`) — the strict `managed_by_id` lawyer scope left them orphaned. Post-reseed verified: 1210 docs, 0 with `managed_by` NULL, archived-lawyer seed intact.
  - **Bug found by new E2E (RESOLVED-020)**: admin dashboard rendered blank — FeaturedServicesGrid "Ver todos" linked dead route name `services_list`; fixed to `services_hub` (`984f07b`). E2E flow now has 5 tests (quick-action entry + execute-error added, `55d0df2`).
  - **Deployed to staging**: post-deploy-check PASS=16/0 FAIL, health 200 (app/db/redis ok) @ `55d0df2`.
- **Phased quality initiative (2026-07-16)** — 20+ commits on `release-august-2026-c`:
  - **Memory Bank refreshed** (drift 04-07 → 16-07 closed) + `USER_FLOW_MAP` matrix resynced.
  - **Backend coverage** (fresh baseline 96.22%): 10 batches — `signature_notification_service` 82→98%, `views/notification` →100%, `utils/documents` letterhead/snapshot edges, `views/secop` →98%, `process_alert_tasks` →99%, `service_tramite` serializer →95%, process alert validation/badge, prefetched permission chain, formalize/correct race 409s + audit PDF variants, Word-export table guards. Migrations excluded via `.coveragerc`.
  - **Bugs fixed**: 4 MySQL-only test failures (collation sorts + `action_type` overflow, `31c7249`) and a real 500 — renaming a SECOP saved view to a duplicate name (RESOLVED-019, `d781e7f`).
  - **Frontend unit coverage** (baseline 89.22%): 8 batches — 13 files 0%→100% (`msal_config`, `ScheduleAppointment`, user_guide×5, `DirectoryList`, `IntranetGyM`, `SignaturesList`, `DocumentTagsManager`, store shim) + `App.vue` 98%. Jest-only babel plugin (`test/babel/vite-meta-env.cjs`) unlocks `import.meta` — `DocumentEditor.vue` is now testable.
  - **Quality gate STRICT: score 100, 0 errors, exit 0** (`83f0eed`) — 236 docstrings added, imports sorted, 13 assertion-less tests converted to plain asserts; warnings 17→13 (rest pre-date the session).
  - **E2E flow coverage 150/150 (100%)**: `process-alert-configure` got its dedicated spec (data-testids added to ProcessForm alert controls) and `process-alerts` completed 3/3 specs (`3746a43`). flow-definitions v1.9.4.
  - **Fake data refreshed** (delete + create completed after clearing two v2-schema landmines: orphan `gym_app_documentpaymentrecord` rows and `gym_app_user.is_archived` missing DB default — see lessons-learned). Post-seed counts verified: 34 users, 86 processes/249 stages (1 StageAlert each), 1190 documents, 60 legal requests, 30 SECOP, 6 services/24 requests, 9 subscriptions, 264 notifications. Next coverage targets: `DocumentEditor.vue` (909 stmts, 0%), large partials (`DocumentListTable` 75.9%, `SignaturesListTable` 77.4%), 13 pre-existing gate warnings.

- **PDF/WeasyPrint overhaul + UI zoom + cleanup (2026-07-07 → 2026-07-15)**:
  - **Dynamic-document PDF stack migrated to WeasyPrint** (`2d390fa`): exports now match the editor rendering. Root sequence: 500 crash on editor-created tables fixed with markup normalization (`2ba6d77`), duplicated PDF stylesheet consolidated into a shared builder in `gym_app/utils/documents.py` consumed by both `document_views.py` and `signature_views.py` (`65c48ce`), then rendering switched from xhtml2pdf to WeasyPrint 63.1. The 2026-08-27 dependency follow-up also moved service/trámite PDFs to this renderer and removed xhtml2pdf. Details in `error-documentation.md` → RESOLVED-018.
  - **Global app zoom** (`cc92301`): `frontend/src/style.css` forces 80% desktop / 75% mobile zoom for a wider UI — pixel-based test assertions see zoomed geometry.
  - **Unused frontend components removed** (`9ec8737`): components 117 → 111; 3 orphan unit test suites deleted.
  - **Quality gate false positives fixed** (`c054df1`): `pytest.raises` now counts as assertion; commands test area recognized (`scripts/quality/backend_analyzer.py`).
  - **Ops**: rotated logs gitignored (`6cba400`); deploy-and-check skill hardened + prod `DJANGO_SETTINGS_MODULE` fix synced from toolkit (`3da7668`, `b0d9c7b`); task-queue docs corrected celery→huey (`1a66b4f`).
- **Lawyer Data Reassignment + Admin Module — Req #1 (2026-07-07, branch `release-august-2026-c-v2`)**:
  - **Archiving**: `User.is_archived` + `archive()`/`unarchive()` (archive also clears `is_active` so simplejwt's `CHECK_USER_IS_ACTIVE` rejects already-issued tokens at request time — no refresh route exists). The 3 login views build tokens manually (bypass `authenticate()`), so an explicit archived check sits in each: `sign_in` INSIDE the password-success branch (no state leak on wrong password), `google_login`/`outlook_login` after `get_or_create` (existing users only). Django admin `login_as_user` impersonation of archived users blocked. Gotcha: is_archived alone would NOT invalidate tokens — flipping is_active is what does it.
  - **Data model**: `Process.lawyer` CASCADE→PROTECT (a lawyer with processes can't be deleted — archive instead). `DynamicDocument.managed_by` FK (SET_NULL) = current responsible lawyer; `created_by` stays immutable (audit). Migration 0070 backfills managed_by=created_by (verified: 1190 docs, 0 mismatch). The list `lawyer_id` param now scopes by `managed_by` (backfill keeps it equivalent for old data; transferred minutas move scope). `can_modify_minuta` grants the manager full rights (edit/state/delete). Serializer auto-inits managed_by=creator on every creation path; update endpoint strips managed_by.
  - **API**: `is_platform_admin` helper (superuser/staff/role=admin — deliberately NOT `is_gym_staff`, which includes lawyers). `admin_reassignment.py`: summary (processes + eligible/ineligible docs with Spanish reasons), execute (validation matrix + atomic transfer — process.lawyer:=target, docs managed_by:=target, assigned_to:=target ONLY when it was the source, 2 ActivityFeed rows, optional archive), archive/unarchive. Archived-user notification exclusion at 4 points (create_notification in-app choke, build_process_recipients, process_alert _build_recipients, daily signature-reminder query). Excluded signature states: all 4 (PendingSignatures/FullySigned/Rejected/Expired — user confirmed Expired too).
  - **Frontend**: user store getters lawyers/archivedLawyers/allLawyers + archived excluded from clients/allClientTypes/clientsAndLawyers (covers Directory + ContactsWidget). `admin_reassignment` store. ProcessForm "Abogado responsable" combobox (default = logged user on create, prefills assigned incl. archived on edit; removed the two hardcodes forcing the current user). `DataReassignment.vue` (source/target selectors, preview + select-all, non-eligible docs with reason, archive checkbox, ConfirmationModal, archived-lawyers restore card). Route `requiresAdmin` + SlideBar item + dashboard quick action + `LawyerMetricsWidget`. Minutas confirmed transferable (user decision).
  - **Tests**: F1 82 pytest / F2 74 pytest / F3 16 pytest, ~22 Jest (getters, store, DataReassignment, ProcessForm selector, QuickActionButtons admin, metrics), 3 E2E (`admin-data-reassignment` P1, flow-definitions v1.11.0, 153 flows). Fake data: 1 archived lawyer seeded (`abogado.archivado@example.com`). E2E mock fix: `dynamicDocumentMocks` lawyer_id filter now `managed_by ?? created_by` (kept minutas-shared-visibility green). Docs: user guide `admin-data-reassignment` section. **Deploy note: production needs `migrate` (0069 + 0070).**

- **Contract Execution / Cuentas de Cobro — Req #11 (2026-07-07, branch `release-august-2026-c-v2`)**:
  - **Backend**: `DocumentPaymentRecord` (migración `0068`; unique doc+cuota; lazy — sin filas hasta el primer upload, slots `pending` sintetizados por la API; re-upload tras rechazo actualiza el MISMO registro y conserva `rejection_reason` como audit trail; el archivo físico viejo se borra manualmente porque post_delete no dispara en updates). Nuevo summary type `payment_installments` — los summaries siguen siendo `SerializerMethodField` computados, cero columnas; parser estricto (`parse_payment_installments`) compartido entre modelo y serializer. 5 endpoints `payment-records/*` function-based con **shape de respuesta único** (`can_upload/can_review/next_uploadable/slots`) para que el FE nunca calcule reglas; secuencial autoritativo (409 fuera de orden o con cuota en revisión); validación inline 20MB/ext; download con record scoped al documento (anti-IDOR). `payment_notification_service` espejo del de firmas (email+in-app `general`+`link_type document`; skip si sube el creador o si assigned_to es el revisor). Prefetch `payment_records` en `get_optimized_document_queryset`.
  - **Frontend**: store module `paymentRecords` (toda mutación devuelve el payload refrescado), opción "Forma de pago (N cuotas)" en DocumentVariablesConfig (auto field_type number), fila en DocumentSummaryModal via `formatInstallments` (1→"Pago único"), menú "Subir/Ver Cuentas de Cobro" gated por `summary_payment_installments` + `payments_summary.next_uploadable` en cardConfigs signatures/lawyer-locked/client-locked, `PaymentRecordsModal` (barra de progreso, total aceptado, badges por estado, hint "Rechazo anterior", panel aceptar/rechazar con textarea obligatoria) y `UploadPaymentRecordModal` (drag&drop 1 archivo, cuota auto-seleccionada, monto/notas opcionales, `detail` del backend en 400/409).
  - **Gotcha (cazado por E2E)**: `showNotification` (SweetAlert2) resuelve SOLO cuando el usuario cierra el toast — emitir eventos/encadenar modales ANTES de notificar, nunca `await showNotification` antes de un emit. Además el backdrop de swal intercepta clicks en E2E: descartar con `.swal2-confirm` antes del siguiente click.
  - **Tests**: 22 modelo + 24 vistas + 3 serializer (pytest) + Jest en 6 suites + `contract-execution-flow.spec.js` (5 tests, mock stateful que replica las reglas secuenciales). Flow `docs-contract-execution` (P1) — flow-definitions v1.10.0 (152 flows). Fake data: 2 planes seeded y ciclo delete/create verificado en staging (migraciones 0067/0068 aplicadas). Guía de usuario: sección `contract-execution`.

- **Guided Tour UI/UX polish (2026-07-06, branch `release-august-2026-c-v2`, second pass)**:
  - **Framing cards**: element-less welcome card ("Comenzar recorrido" / "Ahora no", desktop keyboard hint ← →) + functional finale highlighting the "?" help button ("Entendido"). Content counts stay exactly 10/7/3: driver.js ORs per-step `showProgress` with the global flag, so the global is `false` and content steps opt in with a LITERAL per-step `progressText: 'Paso N de T'` computed post-filter in `buildSteps()` (do not "fix" this inversion).
  - **Motion/visuals**: brand overlay `#141E30` @ 0.7, `stageRadius 12`, `smoothScroll`, 180ms pop-in, eyebrow "Guía · Archivos Jurídicos", animated 4px progress bar (rAF width transition), two-row popover footer (visual QA caught text wrapping at 22rem), focus-visible outlines, `prefers-reduced-motion` disables all motion.
  - **Confetti** (`canvas-confetti ^1.9`, `shared/tours/confetti.js`): fires ONLY via driver.js `onDoneClick` (real end) — never on skip/✕/overlay; double reduced-motion guard; try/catch so it can never break the completion POST.
  - **Branded stale re-offer** `showTourOfferAlert()` (`shared/tours/tour_offer_alert.js`, SweetAlert2 customClass `gyj-tour-offer*`; compound selectors out-specify the `.swal2-*` globals in `src/style.css`); `confirmation_alert.js` untouched.
  - **Help-button ping**: `motion-safe:animate-ping` dot while `tourStatus ∈ {never, stale}`; clears on any completion path. `InfoTooltip` gained fade/scale `<Transition>` + directional arrow (textless span — text selectors stay safe).
  - **Decorator pattern**: single global `onPopoverRender` (`decoratePopover`) reads `state.activeStep.data.kind` (welcome|content|finale) — per-step hooks would override the global one. Registry entries gained optional `{eyebrow, intro, finale}`.
  - **Tests**: 51 Jest (tours) + 13 (InfoTooltip) + 7 E2E green; screenshot self-review loop via a temporary (deleted) Playwright spec caught the footer wrap.

- **Guided Tour / Interactive Onboarding — Req #4 (2026-07-06, branch `release-august-2026-c-v2`)**:
  - **Backend**: `TourProgress` model (`models/tour_progress.py`, migration `0067`, `unique_together user+module_name`, explicit `completed_at` refreshed per completion, `STALE_AFTER_DAYS = 30` + `is_stale` property — the 30-day rule lives on the backend clock). Endpoints `GET /api/tour-progress/?module=` → `never|recent|stale` and `POST /api/tour-progress/complete/` (`update_or_create`), both JWT + user-scoped. Registered in admin (Notifications section) and wiped by `delete_fake_data` (no create seeder — the empty state IS the correct demo state). 17 pytest tests.
  - **Frontend core**: `driver.js ^1.6` (new dep). `shared/tours/` — `dynamic_documents_steps.js` (lawyer 10 / client 7 steps, Spanish copy, conditional pending-signatures closing step via `usePendingSignatures().hasPending`), `index.js` module registry (extensible to Procesos/Solicitudes), `tour.css` (brand-styled popover, plain CSS since driver.js renders into `<body>`). `useGuidedTour` composable: status fetch (fail-safe: empty/unknown response → no-op, which keeps the ~60 existing document E2E specs green with their `{}` mock fallback), auto-start on `never` (~500ms), SweetAlert2 re-offer on `stale` (declining also POSTs to reset the clock), tab switching via injected `setActiveTab` callback (driver.js global `onNextClick`/`onPrevClick` overrides + `nextTick` + rAF), visibility-aware dual desktop/mobile `data-tour` selectors (`offsetParent` check), `desktopOnly` steps dropped under md.
  - **Gotcha (caught by E2E)**: driver.js only fires `onDestroyed` after the first highlight transition (~400ms) settles — an early "Omitir guía"/✕ click closed the tour without POSTing. Fix: `completeOnce()` (idempotent) called directly from the skip/close handlers, with `onDestroyed` as backstop.
  - **Dashboard integration**: `data-tour` attrs on tabs nav + tab buttons + 4 action buttons (desktop AND mobile variants share values), "?" help button in `ModuleHeader` `#actions` slot (relaunch anytime), auto-trigger at the END of `onMounted` (after the pending-signatures redirect; suppressed on `?tab=`/`?lawyerTab=` deep links), new `InfoTooltip.vue` (group-hover pattern) beside the desktop action buttons.
  - **Tests/docs**: 28 Jest (composable 16, steps config, InfoTooltip) + `docs-guided-tour-flow.spec.js` (6 E2E tests incl. tab auto-switch assertion, skip POST, help-button relaunch, stale modal, mobile short tour). Flow `docs-guided-tour` (P2) in `flow-definitions.json` v1.9.4 (150→151 flows) + `USER_FLOW_MAP.md` v1.9.4. User guide section `guided-tour` in `user_guide/content/documents.js` (all roles).

- **Memory Bank refresh + E2E flow-map reconciliation (2026-07-04)**:
  - **Methodology refresh** (`/methodology-setup`): realigned drifted counts and stack versions across `architecture.md`, `technical.md`, `tasks_plan.md`, and this file to the verified codebase (model classes 55→54; backend tests →92; components →117; composables 11→14; routes 66→67; unit tests →177; E2E specs →195; Django 5.0.6→5.2.14, DRF →3.17.1, Vue →3.5, Vite →6.4.2, Playwright →1.60). Created the two missing Memory Bank dirs `docs/literature/` and `tasks/rfc/`.
  - **E2E flow-map reconciliation** (`/e2e-user-flows-check`): retagged `process-alert-recipients.spec.js` `@flow:process-alert-configure`→`@flow:process-alerts` (it exercises the display indicator, not the toggle) — `process-alerts` had been a false-`missing`, `process-alert-configure` a false-`covered`. Added `knownGaps` to `process-alert-configure` + `service-admin-edit`; flipped the stale `legal-files-*` ❌→✅ markers in `USER_FLOW_MAP.md` and regenerated its coverage matrix from `flow-definitions.json`.
  - **Roles**: confirmed **5 roles** (`admin` + 4 client-facing: `client`, `lawyer`, `corporate_client`, `basic`); the "4 roles" phrasing elsewhere refers to the client-facing set only.

- **Release Agosto 2026 (worked in June) — two requirements, on branch `release-august-2026-c`, deployed to staging**:
  - **Minutas shared visibility** ✅ (commit `d595ae0`): removed the per-creator restriction so every lawyer sees/manages all minutas (Draft/Published). Added serializer field `created_by_name` (informational, `select_related('created_by')` → no N+1), a "Creado por" column gated by `isLawyerMinutasContext`, a "Todas / Solo mías" toggle (`onlyMine` reuses the backend `lawyer_id` param), and creator-name search. Replaced the orphaned `getDocumentsByLawyerId` getter with `allMinutas`. Tests: backend serializer/view, store + component unit. Flow `minutas-shared-visibility` (P2) registered.
  - **Microsoft/Outlook login** ✅ (commit `0494ec5`): `outlook_login` endpoint mirroring `google_login`, server-side ID token verification (`_verify_microsoft_id_token` via cached `PyJWKClient`, multi-tenant `common` authority). **nOAuth hardening**: email trusted only when verified (`xms_edov` true, the personal-accounts tenant, or `MICROSOFT_TRUSTED_TENANTS` allowlist); `preferred_username` never used as identity. Frontend uses `@azure/msal-browser` (`msal_config.js`, `login_with_outlook.js`, `OutlookLoginButton.vue`, 4 auth views, `/auth/outlook/callback`). Tests: backend (`TestOutlookLogin` + `TestVerifyMicrosoftIdToken`), frontend unit, E2E (`outlook-login-flow.spec.js`). Flow `auth-login-outlook` (P1) registered. **Pending operator step**: set `MICROSOFT_CLIENT_ID`/`VITE_MICROSOFT_CLIENT_ID` and enable the `xms_edov` optional claim in Azure (or `MICROSOFT_TRUSTED_TENANTS`).
  - **Microsoft login popup fix (2026-07-27)**: the popup came back from Microsoft and rendered our own sign-in form in a stray window, then every retry threw `interaction_in_progress`. Root cause was client-side: the redirect URI `/auth/outlook/callback` was routed to `SignIn.vue`, so an orphaned MSAL interaction (no double-click guard, instance memoized instead of its promise) left the popup open booting the SPA, and the stale `msal.<clientId>.interaction.status` key in `sessionStorage` locked the tab out. Fix: the redirect URI is now served as a minimal page by `outlook_callback` (`gym_app/views/spa.py`, registered before the SPA catch-all, plus a Vite dev middleware and a SW `navigateFallbackDenylist`); the Vue route was removed; `msal_config.js` memoizes the init promise, calls `handleRedirectPromise()`, guards concurrent sign-ins, and clears + retries once on `interaction_in_progress`; `prompt: select_account` restores the account picker (Google parity); `logout()` drops the `msal.*` cache; `settings_dev.py` now sets `SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin-allow-popups'` (Django's `same-origin` default broke the popup in local dev). Azure verified remotely as correct: client id + staging redirect URI registered, personal Microsoft accounts accepted, no `AADSTS9002326` (SPA platform).

- **Hotfix 2026-06-11 — client editor blocked on documents with orphan `{{tokens}}` (RESOLVED-016)**:
  - **Bug**: 53 documents of coordinacion@estrategiaypoder.com could not be text-edited by the client — the `DocumentEditor.vue` integrity guard counted raw `{{...}}` tokens in saved content vs rendered `variable-protected` spans and reverted every keystroke when an orphan token (content `{{Numero_ contrato}}` vs variable `Numero_contrato`, typo inherited from an old version of template 580) never produced a span.
  - **Fix**: protection logic extracted to `shared/document_utils.js` (`replaceVariablesWithProtectedSpans` now protects orphan tokens too, shown as `[token]`; `countProtectedVariableSpans`); guard baseline switched to `initialProtectedCount` captured at load. New backend command `repair_orphan_variable_tokens` (dry-run default, `--apply`) rewrites whitespace-mismatched tokens to the exact variable name.
  - **Tests**: 8 pytest (command) + 8 Jest (new helpers) + regression on `document_utils`/`DocumentForm`/`DocumentVariablesConfig` suites — all green. Details in `docs/methodology/error-documentation.md` → RESOLVED-016.

- **Sprint 2026-04-29 — `isLawyerLike` propagation + User Guide refresh**:
  - **Bug fix**: "Continuar" button missing in TinyMCE editor for `Nueva Minuta` and `Editar` flows. Root causes: (a) `toolbar` config passed as array combined with `toolbar_mode: 'wrap'` and custom `setup` buttons caused the `save/continue/return` slots to drop silently in TinyMCE 7 cloud; (b) `isClient` predicate in `DocumentEditor.vue` checked `role === 'lawyer'` only, so users with `is_staff=true` and `role='client'` passed the route guard but lost the button. Fix: revert toolbar to single string + align `isClient` with the lawyer-guard predicate.
  - **`isLawyerLike` getter**: Centralized in `frontend/src/stores/auth/user.js` as the single source of truth (lawyer / admin / is_staff / is_superuser). Five inlined callsites refactored to consume it: `router/index.js` (route guard), `views/dynamic_document/DocumentEditor.vue`, `views/dynamic_document/Dashboard.vue`, `client/UseDocumentTable.vue`, `composables/document-variables/useDocumentPermissions.js`, `composables/document-variables/useDocumentTags.js`, `cards/menuOptionsHelper.js`.
  - **User Guide audit + refresh**: New module `admin_staff` covering admin/staff/superuser capabilities with `isLawyerLike` explanation. Existing modules updated: `documents.js` (new sections "Botones del Editor según tu Rol" + "Modos del DocumentForm" + explicit "Continuar" step), `secop.js` (alert frequency options + lawyer-only sync trigger), `services_tramites.js` (status lifecycle table DRAFT→OPEN→IN_STUDY→IN_PROGRESS→ANSWERED→FINALIZED + tracking format `YYYY-NNNNN` + inbox filter coverage). Manual infrastructure: `getters.js` `roleMatches` helper aliases `admin` → lawyer modules + admin-only modules; `UserGuideMain.vue` maps `is_staff/is_superuser/role==='admin'` to synthetic `admin` role.
  - **Methodology docs**: `lessons-learned.md` adds "`isLawyerLike` Predicate — Single Source of Truth" subsection. `product_requirement_docs.md` adds Admin role row + "Role Hierarchy — `lawyer-like` Predicate" subsection. Future role gating must consume the getter.

- **Legal Files Alerts (Req #6) audit + remediation + simplify + E2E coverage (2026-04-28)**:
  - **Audit verdict**: implementation was ~75% complete — endpoint, model, hooks, Huey daily task, composable, SlideBar pulse, Dashboard auto-redirect were correct. **7 spec gaps closed**:
    - **B5** `notify_signature_reopened` was sending email; matrix says in-app only → email block removed.
    - **B6** Daily reminder did not exclude documents created in the last 24h → `cutoff = now - 24h` filter added to both queries (outer `signer_id` distinct + per-user pending fetch).
    - **F5** Pulse on `SignaturesListTable.vue` was infinite (`animate-pulse` with no timeout) → added `PULSE_DURATION_MS = 8000` with `setTimeout` in `onMounted` and cleanup in `onBeforeUnmount`.
    - **F6** `auth.logout()` did not clear `sessionStorage.pendingSignaturesAlerted` → flag now removed on logout.
    - **F8 (surfaced by E2E spec)** `Dashboard.vue` auto-redirect was overriding explicit `?tab=`/`?lawyerTab=` URL params, contradicting the spec section "Respeto a Parámetros Explícitos" → guard `hasExplicitTabParam` added at `views/dynamic_document/Dashboard.vue:1066-1080` so the auto-redirect is suppressed when the URL has a tab param.
  - **Simplify pass on the patch**: fixed N+1 in `notify_daily_pending_reminders` (was looping `User.objects.get(id=user_id)` per user — replaced with `User.objects.filter(id__in=user_ids).exclude(email__isnull=True).exclude(email='')`); exported `PENDING_SIGNATURES_ALERTED_KEY` constant from `composables/usePendingSignatures.js` and reused in `auth.js` to remove stringly-typed duplication; removed redundant `isPulseActive.value = true` in `onMounted` (ref already initializes to `true`).
  - **Tests added (all green)**: 6 backend tests in `test_signature_notification_service.py` (progress, expired, reopened-no-email, daily reminder excludes/skips/aggregates) + new `test/composables/usePendingSignatures.test.js` (6 tests) + 1 sessionStorage-cleanup test in `test/stores/auth/auth.test.js`. **3 new E2E specs (5 tests, all passing in Desktop Chrome)**: `legal-files-menu-pulse.spec.js`, `legal-files-auto-redirect.spec.js`, `legal-files-table-pulse.spec.js`. Total: 12/12 backend + 28/28 frontend unit + 5/5 E2E.
  - **Flows registered** in `frontend/e2e/flow-definitions.json`, `frontend/e2e/helpers/flow-tags.js`, and `docs/USER_FLOW_MAP.md`: `legal-files-menu-pulse` (P1), `legal-files-auto-redirect` (P2), `legal-files-table-pulse` (P2). Total flows: 145 → 148. Signatures module: 9 → 12 flows.
  - **Test infrastructure**: extended `frontend/e2e/helpers/dynamicDocumentMocks.js` with `pendingSignaturesCount` parameter and mock for `dynamic-documents/pending-signatures-count/`. Added `data-testid="signatures-list-row-{id}"` to `SignaturesListTable.vue` rows and `pending-signatures-indicator-mobile`/`pending-signatures-count-mobile` to `SlideBar.vue` mobile spans (desktop testids already existed).

- **Notification Center audit + simplify pass (2026-04-28)**:
  - **Audit context**: a prior plan claimed 2 bugs and 4 missing backend test files in the Notification Center. Line-by-line verification refuted **all 5 claims** — the deep-link param mismatch did not exist (`NotificationsList.vue:280` already used `id`), `NotificationSummaryCard.vue` already handled `service_request`, `service_tramite_notifications.py` already created in-app notifications, and the 4 backend test files already existed (332 + 116 + 76 + 141 LOC, plus an extra `test_service_tramite_notifications.py` of 363 LOC).
  - **Real gap discovered**: `ServiceRequestDetail.vue` had no pulse/highlight effect for deep-link from notifications (Process and Document had it; service_request was the only one missing).
  - **Implemented**: 5s `animate-pulse` highlight on `ServiceRequestDetail.vue` with `clearTimeout` cleanup on `onUnmounted` to avoid stale `router.replace` after the user navigates away. Both `NotificationsList.vue:280` and `NotificationSummaryCard.vue:78` now pass `query: { highlight: notif.link_id }` for service_request (parity with process/document).
  - **Simplify pass**: extracted duplicated `link_type` if/else-if chain from `NotificationsList.vue` and `NotificationSummaryCard.vue` into a single `navigateToNotificationTarget(router, notif)` action on `stores/notification.js`. Parallelized `NotificationSummaryCard` mount fetches with `Promise.all`. Added change-detection guard in `fetchUnreadCount` to skip wasted reactive re-renders during 60s polling when the count hasn't changed.
  - **New tests**: 4 frontend unit suites (47 tests across `notification.js` store, `NotificationBell.vue`, `NotificationsList.vue`, `NotificationSummaryCard.vue`) + 14 tests for `ServiceRequestDetail.vue` (incl. 3 highlight pulse tests with spy on `setTimeout`/`clearTimeout` to verify timer cleanup) + 4 E2E (bell+badge, empty state, list+tabs, **service request pulse + URL cleanup verification**). All green. Backend tests already existed and were verified as passing.
  - Implements planned feature **#5 Notification Center**.

- **Process Alerts audit + fixes (2026-04-28)**:
  - **Audit verified 6 issues** in the StageAlert implementation: (1) StageAlert was created only for the LAST stage instead of ALL stages, (2) `process.stages.clear()` left orphan `Stage` rows because `Process.stages` is a `ManyToManyField`, (3) N+1 in `process_list` due to missing `'stages__alert'` in `prefetch_related`, (4) UI did not show recipient info (`notify_clients`), (5) duplicate `send_template_email` import, (6) zero backend test coverage.
  - **Fixes applied** (`backend/gym_app/views/process.py`, `process_alert_tasks.py`, `frontend/src/views/process/ProcessDetail.vue`, `frontend/src/components/process/ProcessHistoryModal.vue`): extracted `_create_stage_alerts(created_stages, main_data)` helper, wrapped stage replacement in `transaction.atomic()`, used `Prefetch('stages', queryset=Stage.objects.order_by('id').select_related('alert'))` to keep prefetch effective, added recipient text to alert indicator + tooltip computed (`alertTitle`).
  - **Tests added**: `tests/models/test_stage_alert.py` (9), `tests/tasks/test_process_alert_tasks.py` (11), `tests/views/test_process_alerts.py` (5), plus `e2e/process/process-alert-recipients.spec.js` (3) — total 28 new tests, all green; 41/41 existing process tests still pass (no regressions).

- **User Guide gap audit (2026-04-22)**: Systematic comparison of `frontend/src/stores/user_guide/` content (10 modules, 65 sections, ~2.8k lines) against real system (63 routes, 181 backend endpoints). Critical gaps: **SECOP** and **Servicios y Trámites** are entire modules missing from `modules.js` despite being full features in production. Also: outdated tab labels (`Firmados` vs real `Dcs. Formalizados` post commit d60eeb4), missing sections (variables-config, document-permissions, user-signature, payment-method-update, payment-history, featured-services), and inaccurate `appointments` content describing features that don't exist (Calendly iframe only). Full plan in `tasks/user_guide_gap_audit.md`.

- **Sprint Abril 2026 — Servicios y Trámites: 11 mejoras (2026-04-15)**:
  - **1.1 ServicesAdmin — Vista previa de icono**: Campo `icon_image_url` en `editor` reactive, miniatura 80×80px con gradiente, validación 5MB.
  - **1.2 ServicesAdmin — Validación exhaustiva**: Nueva función `validateEditor()` cubre nombre, etapas, campos, claves duplicadas, opciones de selección, extensiones de archivo.
  - **1.3 ServicesAdmin — Manejo de errores**: Bloque `catch` extrae `error.response.data` y muestra mensaje específico del backend.
  - **1.4 ServiceDetail — Help text reposicionado**: `field.help_text` ahora aparece ANTES del input (después del label) para mejor UX.
  - **1.5 ServiceDetail — UI archivos múltiples**: Tarjetas con icono, nombre truncado, tamaño formateado, botón `×` eliminar individual, contador X/10, input deshabilitado al alcanzar límite, selección incremental.
  - **1.6 PDF — Rediseño corporativo**: Header «G&M CONSULTORES JURIDICOS», metadatos inline, secciones con subrayado azul #5B7C99, aviso aclaratorio legal en bloque gris, footer corporativo.
  - **1.7 Navegación — ServicesHub.vue**: Nuevo componente unifica «Servicios» y «Mis Solicitudes» con tabs desktop + dropdown mobile. Prop `embedded` en ServicesList/MyServiceRequests. Router redirects legacy paths. Menú lateral simplificado (1 ítem).
  - **1.8 Header azul corporativo**: `ModuleHeader` integrado en ServicesHub con título «Servicios y Solicitudes».
  - **1.9 Emails — Sin emojis**: Eliminado div circular con emoji de `notification.html` y `.mjml`. Removidos campos `"icon"` de contextos Python.
  - **1.10 Emails — Estado destacado**: Estado en `<strong style='font-weight:700;text-transform:uppercase'>`. Fix crítico: `|safe` agregado al `{{message}}` en ambas plantillas (Django auto-escapa HTML sin este filtro).
  - **1.11 Emails — Archivos adjuntos**: `notify_service_request_status_change` recopila archivos de la respuesta más reciente del abogado y los pasa como `attachments`. Llamada movida DESPUÉS del `refetch` para garantizar que `lawyer_responses__files` estén disponibles.
  - **Archivos afectados**: `ServicesAdmin.vue`, `ServiceDetail.vue`, `service_request_pdf.html`, `ServicesHub.vue` (nuevo), `ServicesList.vue`, `MyServiceRequests.vue`, `SlideBar.vue`, `router/index.js`, `ServiceDetail.vue`, `ServiceRequestDetail.vue`, `notification.html`, `notification.mjml`, `service_tramite_notifications.py`, `service_tramite.py`.

- **Codex configuration normalization (2026-04-09)**:
  - **Repo config simplified**: Reduced `.codex/config.toml` to project-scoped settings that materially change behavior (`model`, reasoning effort, approval policy, sandbox mode, web search).
  - **Skills auto-discovery confirmed**: Codex reads `.agents/skills/` from the repository root automatically — no installer needed. `scripts/install-codex-skills.sh` was removed.
  - **User-level cleanup completed**: Removed duplicate repo-managed `gym-*` symlinks from `~/.codex/skills`; system skills under `~/.codex/skills/.system` remain untouched.
  - **Scope boundary preserved**: No Claude or Windsurf configuration was changed as part of this normalization.

- **In-Place Document Formalization (2026-04-08)**:
  - **Problem**: Formalization created a copy of the document instead of transitioning the same document, causing duplication, title modification (`_firma` suffix), and user confusion.
  - **New `formalize_document` endpoint**: `POST /api/dynamic-documents/{id}/formalize/` — transitions Completed → PendingSignatures on the same document. No copy, no title change, creates DocumentSignature records for selected signers.
  - **New `correct_document` endpoint**: `POST /api/dynamic-documents/{id}/correct/` — combines content update + signature reopening into a single atomic call for Rejected/Expired documents (previously required two separate HTTP calls).
  - **Optimistic locking**: Both endpoints use `filter(state=...).update()` instead of `select_for_update()` — no row lock held during signer validation. Returns 409 on concurrent state conflicts.
  - **Frontend**: New `formalizeDocument` and `correctDocument` store actions. `DocumentForm.vue` formalize and correction branches refactored to use single-endpoint calls.
  - **Tests**: 30 new backend tests (16 formalize + 14 correct) covering happy path, validation, permissions, optimistic lock mechanism, title preservation, same-document-ID verification.
  - Implements planned feature #12 (In-Place Formalize) from `docs/next_requirements/`.

- **Servicios y Trámites module implemented (2026-04-08)**:
  - **Backend models**: `Service`, `ServiceStage`, `ServiceField`, `ServiceRequest`, `ServiceRequestSequence`, `ServiceRequestAnswer`, file/response models; includes yearly sequential tracking number format `YYYY-00001`.
  - **Backend APIs**: service catalog (featured + list + detail), admin service management, draft/save/submit flow, my requests, inbox requests, request detail, lawyer/admin status management, and secure file/PDF downloads.
  - **Document + notifications**: PDF generation with submission summary and legal note; email notifications for submission and status updates to requester/managers.
  - **Seed data**: migration seeds initial `Registro Marcario` service with 4 stages and required fields/files.
  - **Frontend**: new `services_tramites` store, dashboard featured services grid, services list/detail, my requests, inbox, request detail, and admin builder view; router + sidebar role-based navigation integrated.
  - **Testing**: backend tests added for create/list/submit/manage/permissions and oversized attachment validation; feature test suite passing.

- **Dynamic Documents N+1 Query Fix (2026-03-29)**:
  - **Root cause**: Silk profiling reported 170–255 DB queries per request on `GET /api/dynamic-documents/` and related signature endpoints.
  - **Fix 1 — Shared helper**: Created `get_optimized_document_queryset()` in `document_views.py` — single source of truth for all `select_related`/`prefetch_related` calls needed by `DynamicDocumentSerializer`.
  - **Fix 2 — Tags N+1**: Changed `prefetch_related('tags')` → `Prefetch('tags', queryset=Tag.objects.select_related('created_by'))` to eliminate per-tag lazy-load of `created_by` FK.
  - **Fix 3 — Queryset-level visibility filter**: Replaced post-serialization `filter_documents_by_visibility` decorator with `apply_visibility_filter()` using Q objects — eliminates redundant DB round-trip for non-lawyers.
  - **Fix 4 — Signature views**: Refactored `get_pending_signatures`, `get_user_pending_documents_full`, `get_user_archived_documents`, `get_user_signed_documents` to use the shared helper + `apply_visibility_filter` instead of per-document `can_view()` calls with zero prefetch.
  - **Fix 5 — Detail view**: Added missing prefetches (`visibility_permissions`, `usability_permissions`, `relationships_as_*`) via shared helper.
  - **Fix 6 — List serializer**: Created `DynamicDocumentListSerializer` excluding `content` field for list endpoints (reduces payload).
  - **Expected result**: ~10 queries per request (down from 170–255). All 846 dynamic document tests pass (2 pre-existing sort failures unrelated).
- **SECOP Module — Stale data fix (2026-03-20)**:
  - **Root cause**: SECOP API (datos.gov.co) returns 26 records marked "Abierto" with publication dates from Jan 2023 and closing dates from Jan–Feb 2023 — all expired. The SECOPClient `_build_query` had no publication date floor, and the sync service had no post-sync stale cleanup.
  - **Fix 1 — API filter**: Added `DEFAULT_PUBLICATION_LOOKBACK_DAYS = 730` (~2 years) to `SECOPClient`. `_build_query` now always appends `fecha_de_publicacion_del >= '<floor>'` to exclude old records at the API level.
  - **Fix 2 — Post-sync cleanup**: Added `close_stale_processes()` static method to `SECOPSyncService` that marks "Abierto" processes with past `closing_date` as "Cerrado". Called automatically at the end of every `synchronize()`.
  - **DB cleanup**: Ran `close_stale_processes()` on staging DB → 24 stale processes closed, 2 remain "Abierto" (null `closing_date`).
  - **Tests**: 6 new tests added (3 client query + 1 sync integration + 4 close_stale_processes edge cases). All 51 SECOP service tests passing.
- **SECOP Module — Deep code review, bug fixes & UI/UX overhaul**:
  - **Backend bug fixes**: Fixed `is_open` filter logic (BUG-1), `page_size` crash on invalid input (BUG-2), normalized role check (BUG-3), `SavedViewSerializer` duplicate name 500→400 (BUG-4), datetime parsing regex (EDGE-1), shared filter helper to eliminate duplication (EDGE-2), `prefetch_related` for N+1 query (EDGE-3), `bulk_update` for alert notifications (EDGE-4)
  - **Second review bug fixes (2026-03-19)**: Fixed serializer N+1 query using Python iteration over prefetch cache (ISSUE-004), alert `evaluate_process` false positives for None `base_price` (ISSUE-005), `_parse_date` returning string instead of `datetime.date` (ISSUE-006), `secop_my_classified` missing `prefetch_related` and `page_size` (ISSUE-007), `exportExcel` blob URL memory leak (ISSUE-008)
  - **UI/UX redesign**: All 8 SECOP components + 2 views redesigned with gradient headers, rounded-xl cards, ring borders, skeleton loading, terciary bg chips, improved empty states, consistent design system, and `data-testid` attributes throughout
  - **Store fix**: Added `ordering` param to `exportExcel` action (EDGE-8), debounced filter watcher, `URL.revokeObjectURL` in export, `page_size` from API response
  - **Backend tests**: 120/120 passing (33 models + 27 services + 7 alert service + 15 serializers + 30 views + 8 tasks)
  - **Frontend unit tests**: 53/53 passing (27 store + 26 components) — fixed 13 failures from UI text/class changes
  - **E2E improvements**: Eliminated all `waitForLoadState("networkidle")` from 8 spec files, replaced with `data-testid` waits
  - **Fake data**: Validated idempotency (`update_or_create`, `random.seed(42)`) and business rule compliance
  - **SECOP Saved Views**: Added ability to edit existing saved views (rename and update filters) — requested by user (2026-03-22)
- **SECOP UNSPSC filter (2026-03-26)**: Migrated UNSPSC filter from single-select to multi-select with union behavior combined with keyword search. Affected: `SavedViewsList.vue`, `SavedViewModal.vue`, `secop/index.js` store, `SecopList.vue`, `SecopDetail.vue`. +3 E2E specs added to SECOP suite.
- **E2E/Flow coverage audit (2026-03-26)**: Added `secop-edit-saved-view` flow (P3) to flow-definitions, USER_FLOW_MAP, and flow-tags. Created `secop-edit-saved-view-flow.spec.js` (4 tests). Fixed all 12 SECOP spec files to use inline `@flow:` tags (coverage scanner requires literal strings, not JS constants). **Flow coverage: 123/123 (100%).** Quality gate: 99/100.
- **E2E coverage audit — 100% flow coverage achieved (2026-03-19)**:
  - **Flow coverage: 107/107 covered**, 0 failing, 0 missing, 0 unmapped
  - **Quality Gate: 100/100** — 0 errors, 0 warnings, 0 infos
- **Previous E2E audit (2026-03-18)**: 4-phase audit that deepened P1 gaps, added missing P2 specs, split `router_guards` test, removed all 9 `knownGaps`
- **Memory Bank Windsurf adaptation**: Adapted methodology rules from Cursor format to Windsurf-compatible paths
- **Test quality gate**: Custom analyzer integrated with pre-commit and GitHub Actions CI
- **E2E flow coverage**: Playwright E2E tests with flow definitions and coverage reporting

---

## 3. Active Decisions & Considerations

| Decision | Status | Context |
|----------|--------|---------|
| 12 planned features in `docs/next_requirements/` | 6 complete (#4 Guided Tour, #5 Notification Center, #6 Legal Files Alerts, #7 Process Alerts, #11 Contract Execution, #12 In-Place Formalize; #8 Outlook Auth also shipped in Release Agosto 2026) | Remaining: Reassignment, minutas, preview, marketplace, optional signature |
| Memory Bank methodology | ✅ Complete | Persistent documentation for AI context fully set up for Claude Code and Codex |
| Large file modularization | Under consideration | `user_guide.js` (143KB), `reports.py` (74KB) could be split |

---

## 4. Development Environment Summary

| Component | Detail |
|-----------|--------|
| Backend | Django 6.1 + DRF 3.18.0, SQLite (dev), MySQL 8.4+ (prod), Python 3.12 |
| Frontend | Vue 3.5 + Vite 6 + Pinia + TailwindCSS 3, Node 22.13.0 |
| Task Queue | Huey 2.6.0 (immediate mode in dev, Redis in prod) |
| Testing | pytest 9.1.1, Jest 29, Playwright |
| CI | GitHub Actions (quality gate on PR/push + MySQL 8.4 compatibility) |
| Pre-commit | Ruff lint + test quality gate |

---

## 5. Next Steps

0. **Phased quality initiative IN PROGRESS (2026-07-16)** — running on `release-august-2026-c`: Memory Bank refresh (✅ this update) → new-feature-checklist audit → e2e-user-flows-check → fake-data-refresh (staging) → iterative backend/frontend-unit coverage to 100% → quality gate strict → iterative E2E flow coverage. Plan: `~/.claude/plans/ejecuta-en-un-plan-sequential-koala.md`.
1. **SECOP Module** ✅ — Fully complete: implementation, bug fixes, UI/UX redesign, backend tests, frontend tests, E2E, fake data, and live staging synchronization verified. The 2026-08-21 hardening adds optional-token fallback, shared task locking, authoritative status polling, and lawyer-like manual authorization.
   - **Fixed (2026-03-19)**: E2E `secop-alert-create-flow.spec.js` — 2 `data-testid` mismatches (`alert-form` → `alert-form-modal`, `alert-name-input` → `alert-name`)
2. **Review and prioritize** the 12 planned features in `docs/next_requirements/`
3. **Address tech debt** — Clean up backup files, modularize large files
4. **Continue test coverage** — Maintain and expand backend/frontend/E2E test suites
5. **Production hardening** — Log rotation, secret key enforcement, backup verification
