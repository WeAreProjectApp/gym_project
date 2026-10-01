# Mapa de Flujos de Navegabilidad — G&M Abogados

Documento exhaustivo que mapea todos los flujos end-to-end que un usuario puede realizar en la plataforma, organizados por rol, con ramificaciones para cada variante de formulario o camino alternativo.

**Fecha:** September 27, 2026
**Versión:** 1.13.4
**Fuentes:** `src/router/index.js`, `src/views/`, `src/components/`, `e2e/flow-definitions.json`, `docs/FUNCTIONAL_GUIDE_BY_ROLE.md`

---

## Tabla de Contenido

1. [Roles del Sistema](#roles-del-sistema)
2. [Convenciones](#convenciones)
3. [Flujos Compartidos (sin rol)](#flujos-compartidos-sin-rol)
4. [Flujos — Lawyer](#flujos--lawyer)
5. [Flujos — Client](#flujos--client)
6. [Flujos — Corporate Client](#flujos--corporate-client)
7. [Flujos — Basic](#flujos--basic)
8. [Flujos — Lawyer G&M (is_gym_lawyer)](#flujos--lawyer-gm-is_gym_lawyer)
9. [Flujos — SECOP (Contratación Estatal)](#flujos--secop-contratación-pública)
10. [Flujos — Servicios y Tramites](#flujos--servicios-y-tramites)
11. [Resumen de Cobertura E2E](#resumen-de-cobertura-e2e)

---

## Roles del Sistema

| Rol | Descripción | Módulos exclusivos |
|-----|-------------|-------------------|
| **Lawyer** | Gestión completa de procesos, clientes y documentos | Directorio, Gestión de Solicitudes |
| **Client** | Ver procesos propios, solicitar servicios, usar documentos | Solicitudes (crear), Agendar Cita, Organizaciones (lectura) |
| **Corporate Client** | Todo de Client + gestión completa de Organizaciones | Organizaciones (CRUD completo) |
| **Basic** | Acceso limitado, sin firma electrónica ni membrete | — |
| **Lawyer G&M** | Lawyer con `is_gym_lawyer=true`, acceso a Intranet | Intranet G&M |

---

## Convenciones

- **Ramificaciones:** `├──` variante intermedia, `└──` última variante
- **Flow ID:** alineado con `e2e/flow-definitions.json` cuando existe
- **Prioridad:** P1 (crítico) → P4 (cosmético)
- **Cobertura E2E:** ✅ cubierto | ⚠️ parcial | ❌ sin cobertura

---

## Flujos Compartidos (sin rol)

### auth-login-email: Iniciar sesión con email
- **Módulo:** auth | **Prioridad:** P1 | **Ruta:** `/sign_in` | **E2E:** ✅
- **Descripción:** Usuario inicia sesión con correo y contraseña

**Pasos:**
1. Navega a `/sign_in`
2. Ingresa email y contraseña
3. Completa reCAPTCHA
4. Click "Iniciar Sesión"

**Ramificaciones:**
- ├── **Éxito:** Redirect a `/dashboard`
- ├── **Credenciales inválidas:** Mensaje de error, permanece en `/sign_in`
- └── **Bloqueo progresivo** (→ auth-login-attempts): Tras 3 intentos → espera 60s, luego 120s, 240s...

---

### auth-login-google: Iniciar sesión con Google
- **Módulo:** auth | **Prioridad:** P1 | **Ruta:** `/sign_in` | **E2E:** ✅
- **Descripción:** Usuario accede mediante OAuth con cuenta de Google

**Pasos:**
1. Navega a `/sign_in`
2. Click "Continuar con Google"
3. Selecciona cuenta Google en popup
4. Autoriza acceso

**Ramificaciones:**
- ├── **Usuario existente:** Redirect a `/dashboard`
- ├── **Usuario nuevo:** Se crea cuenta automáticamente → redirect a `/dashboard`
- └── **Error token/popup cerrado:** Mensaje de error

---

### auth-login-outlook: Iniciar sesión con Microsoft/Outlook
- **Módulo:** auth | **Prioridad:** P1 | **Ruta:** `/sign_in`, `/sign_on`, suscripción | **E2E:** ✅
- **Descripción:** Usuario accede o se registra mediante MSAL con cuenta de Microsoft (personal o corporativa). El ID token se verifica server-side; el correo se acepta solo si está verificado (xms_edov / tenant de consumidores / allowlist) para prevenir nOAuth.

**Pasos:**
1. Navega a `/sign_in` (o `/sign_on`, o el flujo de suscripción)
2. Click "Continuar con Microsoft" (el botón queda deshabilitado mientras el popup está abierto)
3. Elige la cuenta en el selector de Microsoft (`prompt: select_account`)
4. El popup vuelve a `/auth/outlook/callback`, servido como página mínima por el backend
   (no monta la SPA), y MSAL lo cierra
5. El backend verifica el ID token y el correo

**Ramificaciones:**
- ├── **Usuario existente:** Redirect a `/dashboard` (o checkout en suscripción)
- ├── **Usuario nuevo:** Se crea cuenta `basic` automáticamente → redirect
- ├── **Correo no verificado (tenant no confiable):** 401, no se crea/enlaza cuenta
- └── **Popup cancelado / error:** Notificación, permanece en la vista

---

### auth-register: Registrar nueva cuenta
- **Módulo:** auth | **Prioridad:** P1 | **Ruta:** `/sign_on` | **E2E:** ✅
- **Descripción:** Crear cuenta nueva con verificación de email por passcode

**Pasos:**
1. Navega a `/sign_on`
2. Llena formulario: nombre, apellido, email, contraseña, confirmar contraseña
3. Acepta políticas de privacidad
4. Completa reCAPTCHA
5. Click "Registrarse" → envía passcode al email
6. Ingresa código de verificación recibido
7. Click "Verificar" → cuenta creada

**Ramificaciones:**
- ├── **Registro con formulario:** Paso 1 (datos) → Paso 2 (passcode) → Registro completo
- ├── **Registro con Google:** Click "Continuar con Google" → misma lógica que auth-login-google
- ├── **Email ya registrado (409):** Notificación de email duplicado
- ├── **Passcode inválido:** Mensaje de error
- └── **Email cambiado después de enviar passcode:** Advertencia, debe regenerar código

---

### auth-forgot-password: Recuperar contraseña
- **Módulo:** auth | **Prioridad:** P2 | **Ruta:** `/forget_password` | **E2E:** ✅
- **Descripción:** Restablecer contraseña olvidada

**Pasos:**
1. Navega a `/forget_password`
2. Ingresa email registrado
3. Click "Enviar código"
4. Ingresa código de verificación
5. Crea nueva contraseña + confirmación
6. Contraseña actualizada → redirect a `/sign_in`

---

### auth-subscription-signin: Login vía suscripción
- **Módulo:** auth | **Prioridad:** P1 | **Ruta:** `/subscription/sign_in` | **E2E:** ✅
- **Descripción:** Login desde flujo de suscripción, redirige a checkout con plan seleccionado

**Pasos:**
1. Usuario no autenticado selecciona plan en `/subscriptions`
2. Redirect a `/subscription/sign_in?plan=<plan>`
3. Ingresa email, contraseña, reCAPTCHA
4. Click "Iniciar Sesión"
5. Redirect a `/checkout/<plan>`

**Ramificaciones:**
- ├── **Éxito:** Redirect a checkout con plan preservado
- ├── **Error credenciales:** Mensaje de error, permanece en form
- └── **Link a registro:** Navega a `/subscription/sign_up?plan=<plan>`

---

### auth-subscription-signup: Registro vía suscripción
- **Módulo:** auth | **Prioridad:** P1 | **Ruta:** `/subscription/sign_up` | **E2E:** ✅
- **Descripción:** Registro desde flujo de suscripción, redirige a checkout

**Pasos:**
1. Navega a `/subscription/sign_up?plan=<plan>`
2. Mismo formulario que auth-register (datos + passcode)
3. Cuenta creada → redirect a `/checkout/<plan>`

---

### auth-logout: Cerrar sesión
- **Módulo:** auth | **Prioridad:** P2 | **Ruta:** N/A | **E2E:** ✅
- **Descripción:** Cierre manual de sesión

**Pasos:**
1. Click en nombre de usuario en sidebar
2. Selecciona "Cerrar Sesión"
3. Limpieza de sesión local → redirect a `/sign_in`

---

### auth-idle-logout: Cierre por inactividad
- **Módulo:** auth | **Prioridad:** P2 | **Ruta:** N/A | **E2E:** ✅
- **Descripción:** Cierre automático tras 15 minutos sin actividad

**Pasos:**
1. Usuario deja de interactuar (mouse, teclado, scroll, touch)
2. Tras 15 minutos → cierre automático de sesión
3. Redirect a `/sign_in`

---

### auth-login-attempts: Protección contra accesos no autorizados
- **Módulo:** auth | **Prioridad:** P2 | **Ruta:** `/sign_in` | **E2E:** ✅
- **Descripción:** Bloqueo progresivo tras intentos fallidos

**Ramificaciones:**
- ├── **3 intentos fallidos:** Bloqueo 60 segundos
- ├── **4 intentos fallidos:** Bloqueo 120 segundos
- └── **5+ intentos fallidos:** Bloqueo 240 segundos (progresivo)

---

### auth-router-guards: Guardias de navegación
- **Módulo:** auth | **Prioridad:** P2 | **Ruta:** N/A | **E2E:** ✅
- **Descripción:** Protección de rutas por autenticación y rol

**Ramificaciones:**
- ├── **Ruta `requiresAuth` sin sesión:** Redirect a `/sign_in`
- ├── **Ruta `requiresLawyer` con rol client/basic/corporate:** Redirect a `/dashboard`
- └── **Ruta raíz `/`:** Autenticado → `/dashboard`, No autenticado → `/sign_in`

---

### subscriptions-view-plans: Ver planes de suscripción
- **Módulo:** subscriptions | **Prioridad:** P2 | **Ruta:** `/subscriptions` | **E2E:** ✅
- **Descripción:** Comparar planes y seleccionar uno

**Pasos:**
1. Navega a `/subscriptions`
2. Ve 3 planes en grid

**Ramificaciones al seleccionar plan:**
- ├── **Plan Básico** (gratuito): `selectPlan('basico')`
- ├── **Plan Cliente** ($59.900/mes): `selectPlan('cliente')`
- └── **Plan Corporativo** ($149.900/mes): `selectPlan('corporativo')`

**Ramificaciones por autenticación:**
- ├── **Autenticado:** Redirect directo a `/checkout/<plan>`
- └── **No autenticado:** Redirect a `/subscription/sign_in?plan=<plan>`

---

### subscriptions-checkout-free: Checkout plan gratuito
- **Módulo:** subscriptions | **Prioridad:** P1 | **Ruta:** `/checkout/basico` | **E2E:** ✅
- **Descripción:** Activar plan gratuito sin pago

**Pasos:**
1. Navega a `/checkout/basico`
2. Ve resumen del plan (precio: Gratuito)
3. **No se muestra formulario de tarjeta** (`planDetails.amountInCents === 0`)
4. Click "Confirmar Suscripción"
5. Plan activado inmediatamente

---

### subscriptions-checkout-paid: Checkout plan pago
- **Módulo:** subscriptions | **Prioridad:** P1 | **Ruta:** `/checkout/<plan>` | **E2E:** ✅
- **Descripción:** Pagar suscripción con tarjeta vía Wompi

**Pasos:**
1. Navega a `/checkout/cliente` o `/checkout/corporativo`
2. Ve resumen del plan con precio
3. **Se muestra formulario de tarjeta** (`planDetails.amountInCents > 0`):
   - Nombre del titular
   - Número de tarjeta
   - Mes/Año de expiración
   - CVC
4. Click "Guardar método de pago" → tokenización Wompi
5. Ve confirmación "Método de pago guardado"
6. Click "Confirmar Suscripción"
7. Plan activado

**Ramificaciones:**
- ├── **Tokenización exitosa:** Muestra badge verde "Método de pago guardado" + botón "Cambiar"
- ├── **Error de tokenización:** Mensaje de error, puede reintentar
- └── **Cambiar tarjeta:** Click "Cambiar" → limpia datos y muestra formulario de nuevo

---

### subscriptions-management: Gestión de suscripción
- **Módulo:** subscriptions | **Prioridad:** P2 | **Ruta:** N/A | **E2E:** ✅
- **Descripción:** Cancelar o mejorar plan actual

**Ramificaciones:**
- ├── **Cancelar:** Plan activo hasta fin de período → transición automática a plan gratuito
- └── **Upgrade:** Seleccionar plan superior → completar pago → beneficios activados inmediatamente

---

### subscriptions-cancel: Cancelar suscripción
- **Módulo:** subscriptions | **Prioridad:** P2 | **Ruta:** N/A | **E2E:** ✅
- **Descripción:** Cancelar suscripción activa, plan vigente hasta fin de período, transición a plan gratuito

**Pasos:**
1. En gestión de suscripción, click "Cancelar suscripción"
2. Modal de confirmación
3. Plan permanece activo hasta fin del período de facturación
4. Al expirar → transición automática a plan gratuito

---

### subscriptions-update-payment: Actualizar método de pago
- **Módulo:** subscriptions | **Prioridad:** P2 | **Ruta:** N/A | **E2E:** ✅
- **Descripción:** Cambiar tarjeta de pago en suscripción activa vía tokenización Wompi

**Pasos:**
1. En gestión de suscripción, click "Cambiar método de pago"
2. Formulario de tarjeta (nombre, número, expiración, CVC)
3. Tokenización vía Wompi
4. Confirmación de actualización

---

### profile-view-edit: Ver y editar perfil
- **Módulo:** profile | **Prioridad:** P2 | **Ruta:** N/A (modal desde sidebar) | **E2E:** ✅
- **Descripción:** Actualizar información personal

**Pasos:**
1. Click en nombre en sidebar → menú → "Perfil"
2. Modal muestra datos actuales
3. Click "Editar"
4. Modifica: nombre, apellido, contacto, identificación, fecha nacimiento, foto
5. Click "Guardar"

---

### profile-complete: Completar perfil (primer login)
- **Módulo:** profile | **Prioridad:** P2 | **Ruta:** N/A (modal automático) | **E2E:** ✅
- **Descripción:** Modal obligatorio si perfil está incompleto

**Ramificaciones:**
- ├── **Perfil incompleto:** Modal aparece automáticamente al entrar al dashboard
- └── **Perfil completo:** No se muestra modal

---

### misc-policies: Políticas y páginas informativas
- **Módulo:** misc | **Prioridad:** P4 | **Ruta:** `/policies/privacy_policy`, `/policies/terms_of_use` | **E2E:** ✅
- **Descripción:** Páginas estáticas de políticas de privacidad y términos de uso

---

### misc-pwa-install: Instalar PWA
- **Módulo:** misc | **Prioridad:** P4 | **Ruta:** N/A | **E2E:** ✅
- **Descripción:** Prompt de instalación de la app como PWA

---

### user-guide-navigation: Navegación del Manual de Usuario
- **Módulo:** user-guide | **Prioridad:** P3 | **Ruta:** `/user_guide` | **E2E:** ✅ `success` y `display` verificados en los anchos estándar; dos specs
- **Descripción:** Navegación por módulos y secciones filtradas por rol, búsqueda local, quick links y ejemplos. A 412×915 y 835×1194 se abre el menú, se selecciona Procesos, se busca y limpia la búsqueda y se abre/cierra un ejemplo con controles de al menos 44×44 px efectivos, títulos conservados y sin overflow horizontal.

### Explorador del manual — actualización 2026-09-19

Ruta: `/user_guide?view=explorer`. El catálogo completo es visible para **client,
basic, corporate_client, lawyer y admin/staff/superuser**. El acceso al módulo
operativo se calcula por separado; no modifica los guards ni carga datos privados.

| Interacción / flow | Clase | Inicio → interacción → resultado | Evidencia E2E |
|---|---|---|---|
| `user-guide-explorer-navigation` | success, display | Manual → Explorar la plataforma → espacios completos, selección, breadcrumbs, historial, recarga y vínculo a guía | `user-guide-explorer.spec.js` |
| `user-guide-explorer-search` | success, display | Escribir término → elegir capacidad; término inexistente → mensaje sin coincidencias | `user-guide-explorer.spec.js` |
| `user-guide-explorer-access` | success, error | Cliente → función administrativa → requisito explícito sin acceso; staff → Abrir módulo → destino permitido | `user-guide-explorer.spec.js` |
| `user-guide-explorer-tour` | success | Espacio → Iniciar recorrido → Siguiente / Salir → capacidad seleccionada | `user-guide-explorer.spec.js` |
| `user-guide-explorer-relations` | success | Explorador → Ocultar relaciones → conexiones ocultas y URL actualizada | `user-guide-explorer.spec.js` |
| `user-guide-explorer-responsive` | success, display | A 412×915 y 835×1194 → Colaboración → Notificaciones conserva tarjetas y título sin overflow; a 1195×835, 1440×900 y 2560×1440 conserva navegación y el layout correspondiente al contenedor, con controles operables | `user-guide-explorer-layout.spec.js` |
| `user-guide-explorer-orbit` | success | Escritorio → Girar a la derecha → cambio de posición observable | `user-guide-explorer-layout.spec.js` |

**Outcomes del módulo `user-guide`:** `success` cubre navegación, búsqueda,
ejemplos y controles del explorador; `error` aplica a restricciones de acceso
explicadas sin enlace operativo; `display` cubre el contenido y el layout
responsive. **Failure:** n/a para las interacciones del manual: su contenido es
local y no hay una acción de negocio ni una respuesta fallida visible al usuario.
La carga de usuarios al montar la vista no expone un estado de fallo del manual;
los fallos de autenticación y de destinos pertenecen a sus flujos respectivos.

**Por rol:** todos recorren el mismo catálogo. Clientes y básicos ven las
restricciones de funciones del equipo; abogados tienen acceso según su pertenencia
a G&M; corporativos conservan sus acciones de organizaciones; admin/staff usan sus
destinos administrativos. Las pruebas unitarias cubren las variantes de estas reglas.

**Outcome failure:** n/a para las interacciones del explorador: catálogo local sin
solicitudes de negocio ni formularios de escritura. Fallos de autenticación y de
los módulos de destino pertenecen a sus flujos existentes. **Error** sólo aplica a
la explicación de restricciones; búsqueda vacía es **display** y URL inválida se
normaliza al ecosistema (cubierto por unit tests). La animación se detiene con
movimiento reducido, foco, hover, recorrido, contenedor estrecho o pestaña oculta.

**Inventario:** `explorer/routeInventory.js` relaciona todas las pantallas del
router con nodos del catálogo y documenta las exclusiones de callbacks/redirects.
`explorerInventory.test.js` detecta rutas nuevas sin explicación o referencias
obsoletas. Estas verificaciones de datos son unitarias, no crédito E2E.

**Índice del cambio:** 7 flujos nuevos, 10 combinaciones flow/outcome, 16 pruebas
E2E ejecutadas. El resumen histórico global más abajo conserva su fecha de auditoría;
la fuente actualizada para el total es `flow-definitions.json`.

---

### process-alert-configure: Configurar destinatarios de alerta de proceso
- **Módulo:** processes | **Prioridad:** P2 | **Ruta:** `/process_form`, `/process_form/:process_id` | **E2E:** ⏳ Pendiente — toggle interactivo `notify_clients` en ProcessForm; coverage actual (`process-alert-recipients.spec.js`) sólo prueba display read-only.
- **Descripción:** Abogado activa la alerta del último estado procesal y alterna el toggle "Notificar también a los clientes" (`alertNotifyClients`); opcionalmente añade descripción. Al guardar, persiste en `StageAlert.notify_clients`.

**Ramificaciones:**
- ├── **`alertIsActive=false`**: la alerta no se crea / queda desactivada; toggle de recipients oculto.
- ├── **`notify_clients=true`**: emails + notificaciones in-app llegan a abogado y clientes del proceso (3 días y 1 día antes de la fecha).
- └── **`notify_clients=false`**: solo abogado recibe alertas.

**Conocido como gap:** el test E2E del toggle requiere mocking pesado de ProcessForm (case types, lawyers, clients) y `data-testid` en el botón aún no añadidos — registrado como deuda en `tasks/tasks_plan.md`.

---

### notification-center: Centro de Notificaciones
- **Módulo:** notifications | **Prioridad:** P2 | **Ruta:** `/notifications` | **E2E:** ✅
- **Descripción:** Campana flotante con badge de no leídas, vista tipo bandeja con tabs (todas/no leídas/archivadas), gestión (marcar leída, archivar, snooze 1h/3h/1d/3d, eliminar) y deep-link al recurso con efecto pulse de 5s.

**Ramificaciones (deep-link según `link_type`):**
- ├── **`process`** → `/process_detail/:process_id?highlight=:id` → card con `animate-pulse` 5s, luego `router.replace` limpia el query param.
- ├── **`document`** → `/dynamic_document_dashboard?highlight=:id` → tab "Por firmar" + 3-color pulse en BaseDocumentCard.
- ├── **`service_request`** → `/service_requests/:id?highlight=:id` → card del detalle parpadea 5s con cleanup.
- └── **`link_id` ausente o `link_type` desconocido** → fallback a `/notifications`.

**Polling:** la campana llama `fetchUnreadCount` cada 60s (con guard de cambio para evitar re-renders no-op).
**Snooze reactivation:** Huey `notification_tasks.reactivate_snoozed_notifications` corre cada 15 min.

---

### auth-edge-cases: Casos borde de autenticación
- **Módulo:** auth | **Prioridad:** P2 | **Ruta:** N/A | **E2E:** ✅
- **Descripción:** Token expirado, OAuth callback, credenciales inválidas, captcha

**Ramificaciones:**
- ├── **Token expirado:** Sesión se cierra → redirect a `/sign_in`
- ├── **OAuth callback error:** Mensaje de error → permanece en login
- ├── **Credenciales inválidas:** Error inline + no limpia formulario
- └── **reCAPTCHA no completado:** Botón deshabilitado

---

### misc-error-handling: Manejo de errores
- **Módulo:** misc | **Prioridad:** P3 | **Ruta:** N/A | **E2E:** ✅
- **Descripción:** Páginas de error 404, 401, 403, 500, errores de red

**Ramificaciones:**
- ├── **Sin conexión:** Redirect a `/no_connection`
- ├── **Ruta no encontrada:** Redirect a `/sign_in` (catch-all)
- └── **Error en router guard:** Redirect a `/sign_in`

### misc-offline: Página sin conexión
- **Módulo:** misc | **Prioridad:** P4 | **Ruta:** `/no_connection` | **E2E:** ✅
- **Descripción:** Página mostrada cuando el dispositivo pierde la conexión a internet (`views/offline/NoConnection.vue`). Ruta pública, sin autenticación.

**Ramificaciones:**
- └── **Reconexión:** El usuario recupera internet y vuelve a navegar por la app

---

## Flujos — Admin

### admin-data-reassignment: Reasignación de datos de abogado
- **Módulo:** admin | **Prioridad:** P1 | **Ruta:** `/data_reassignment` | **E2E:** ✅ (`data-reassignment-flow.spec.js` — 5 tests: transferencia+archivado, restauración, entrada por quick action del dashboard, error de backend en execute, guard no-admin)
- **Descripción:** Módulo exclusivo de administradores para transferir procesos y documentos de un abogado a otro y archivar cuentas de abogados. Acceso desde el menú lateral "Reasignación de Datos" (solo admin) y el botón rápido del dashboard. La transferencia es atómica: los procesos pasan al destino, la gestión de documentos (`managed_by`) también, y `assigned_to` migra solo cuando era el abogado origen; `created_by` nunca cambia (auditoría). Los documentos en estados de firma (Pendiente/Firmado/Rechazado/Vencido) no son transferibles. Archivar un abogado bloquea su login por todos los métodos, lo excluye de listados y notificaciones, y es reversible.

**Pasos:**
1. El administrador entra a `/data_reassignment` (guard `requiresAdmin`; los no-admin son redirigidos al dashboard)
2. Selecciona el abogado origen → el sistema carga la vista previa (procesos + documentos elegibles + no elegibles con motivo)
3. Selecciona el abogado destino (excluye al origen y a los archivados)
4. Marca procesos/documentos (o "Seleccionar todos"); opcionalmente "Archivar abogado origen al finalizar"
5. Confirma en el modal → transferencia atómica → toast de éxito con el resumen (y aviso de archivado si aplica)
6. Los abogados archivados pueden restaurarse desde la card "Abogados archivados"

**Ramificaciones:**
- ├── **Documentos en firma:** listados como no transferibles con motivo (En proceso de firma / Firmado / Rechazado / Vencido); excluidos del "Seleccionar todos"
- ├── **Documentos personales del abogado (assigned_to = origen):** su `assigned_to` migra al destino; los asignados a clientes conservan su cliente
- ├── **Minutas:** su gestión (`managed_by`) migra, por lo que aparecen en el scope "Mías" del destino y desaparecen del origen
- ├── **Archivar origen:** bloqueo total de login (tradicional + Google/Outlook), exclusión de listados y notificaciones; reversible vía "Restaurar"
- ├── **Error en la transferencia:** si el backend rechaza (400), el modal se cierra y el toast de error muestra el motivo devuelto
- └── **No-admin:** el guard redirige al dashboard; el ítem de menú y el botón rápido no se muestran

---

## Flujos — Lawyer

### dashboard-welcome-card: Tarjeta de bienvenida
- **Módulo:** dashboard | **Prioridad:** P2 | **Ruta:** `/dashboard` | **E2E:** ✅
- **Descripción:** Panel principal con saludo, estadísticas y acciones rápidas

**Contenido para Lawyer:**
- Saludo personalizado con nombre
- Contador de procesos activos
- Botones de acción rápida: Todos los Procesos, Radicar Proceso, Nueva Minuta, Radicar Informe

---

### dashboard-activity-feed: Feed de actividad
- **Módulo:** dashboard | **Prioridad:** P2 | **Ruta:** `/dashboard` | **E2E:** ✅
- **Descripción:** Historial cronológico de acciones con scroll infinito

**Tipos de actividad:**
- Creación/actualización de procesos
- Firma de documentos
- Creación de minutas
- Edición de contenido de documentos
- Rechazo de documentos y correcciones reenviadas
- Actualización de perfil

---

### dashboard-legal-updates: Actualizaciones legales
- **Módulo:** dashboard | **Prioridad:** P3 | **Ruta:** `/dashboard` | **E2E:** ✅
- **Descripción:** Carrusel con noticias del sector legal

**Ramificaciones (solo admin/lawyer):**
- ├── **Ver actualizaciones:** Carrusel con título, contenido y enlaces
- ├── **Crear actualización:** Formulario con título + contenido + estado (activo/inactivo)
- ├── **Editar actualización:** Modificar datos existentes
- └── **Eliminar actualización:** Confirmación + eliminación

---

### dashboard-reports: Generar reporte
- **Módulo:** dashboard | **Prioridad:** P2 | **Ruta:** `/dashboard` | **E2E:** ✅
- **Descripción:** Generar reporte Excel de actividad

**Pasos:**
1. Click en botón de reportes en dashboard
2. Selecciona tipo de reporte (Procesos Activos, Usuarios Registrados, etc.)
3. Opcionalmente define rango de fechas (inicio, fin)
4. Click "Generar y Descargar Reporte"
5. Descarga archivo Excel

---

### dashboard-reports-advanced-filters: Filtros avanzados de reportes
- **Módulo:** dashboard | **Prioridad:** P2 | **Ruta:** `/dashboard` (tab Reportes) | **E2E:** ✅
- **Descripción:** Filtrar reporte de Usuarios Registrados por rol, estado de perfil y tipo de documento (commit `8e0e3fa`)

**Condición:** Los filtros avanzados solo aparecen al seleccionar tipo "Usuarios Registrados".

**Filtros disponibles:**
- **Rol:** Todos / Cliente / Abogado / Cliente Corporativo / Básico
- **Estado del Perfil:** Todos / Completo / Incompleto
- **Tipo de Documento:** Todos / NIT / CC / NUIP / EIN

**Ramificaciones:**
- ├── **Filtrar por rol** → generar reporte con usuarios de ese rol
- ├── **Filtrar por estado de perfil** → generar reporte filtrado
- ├── **Filtrar por tipo de documento** → generar reporte filtrado
- ├── **Cambiar tipo de reporte** → filtros avanzados desaparecen y se resetean
- └── **Sin filtros** (todos en "Todos") → reporte sin filtro adicional

---

### dashboard-quick-actions: Acciones rápidas del dashboard
- **Módulo:** dashboard | **Prioridad:** P3 | **Ruta:** `/dashboard` | **E2E:** ✅
- **Descripción:** Accesos directos contextuales filtrados por rol

---

### dashboard-navigation: Navegación del sidebar
- **Módulo:** dashboard | **Prioridad:** P2 | **Ruta:** N/A | **E2E:** ✅
- **Descripción:** Menú lateral filtrado por rol con navegación a todos los módulos

**Ramificaciones por rol (sidebar):**
- ├── **Lawyer:** Dashboard, Directorio, Procesos, Documentos, Gestión de Solicitudes, Manual de Usuario
- ├── **Lawyer G&M:** Todo de Lawyer + Intranet G&M
- ├── **Client:** Dashboard, Procesos, Documentos, Solicitudes, Agendar Cita, Organizaciones, Manual de Usuario
- ├── **Corporate Client:** Igual que Client
- └── **Basic:** Igual que Client

---

### dashboard-folder-components: Carpetas y contactos en dashboard
- **Módulo:** dashboard | **Prioridad:** P3 | **Ruta:** `/dashboard` | **E2E:** ✅
- **Descripción:** Pestañas de carpetas y contactos rápidos en el dashboard

---

### directory-search: Buscar en directorio
- **Módulo:** directory | **Prioridad:** P2 | **Ruta:** `/directory_list` | **E2E:** ✅
- **Descripción:** Buscar y consultar usuarios del sistema (solo Lawyer)
- **Outcomes:** success, display. El detalle permite leer datos largos completos
  en compact, portrait, landscape, desktop y wide, sin desbordamiento horizontal.

**Pasos:**
1. Navega a `/directory_list`
2. Usa barra de búsqueda (nombre, email, identificación, rol)
3. Click en tarjeta de usuario → modal con info + procesos
4. Click "Ver proceso" → navega al detalle
5. O click "Ver todos en Procesos" → lista filtrada

---

### process-list-view: Ver lista de procesos
- **Módulo:** processes | **Prioridad:** P1 | **Ruta:** `/process_list` | **E2E:** ✅
- **Descripción:** Lista de procesos con tabs y filtros

**Tabs para Lawyer:**
- ├── **Mis Procesos:** Casos asignados
- ├── **Todos los Procesos:** Vista completa del sistema (exclusivo Lawyer)
- └── **Procesos Archivados:** Casos finalizados

**Filtros disponibles:**
- Búsqueda texto: referencia, demandante, demandado, autoridad, cliente
- Filtro por Tipo de Caso: Civil, Penal, Laboral, Familia, Administrativo, etc.
- Filtro por Autoridad: Juzgados, Tribunales, Cortes
- Filtro por Etapa Procesal: Admisión, Pruebas, Alegatos, Sentencia
- Ordenamiento: Más recientes / Nombre A-Z

---

### process-create: Radicar proceso
- **Módulo:** processes | **Prioridad:** P1 | **Ruta:** `/process_form/create` | **E2E:** ✅
- **Descripción:** Crear nuevo proceso judicial (solo Lawyer)

**Pasos:**
1. Click "Radicar Proceso"
2. Llena formulario:
   - **Tipo de caso** (Combobox con búsqueda)
   - Subcaso (texto libre)
   - Demandante, Demandado
   - Autoridad, Referencia/Radicado
   - **Clientes** (multi-select con búsqueda)
   - Abogado responsable
   - **Etapas procesales** (tabla dinámica, agregar N etapas con fecha)
   - Archivos del expediente (upload múltiple)
3. Click "Guardar"

**Ramificaciones — Tipo de caso:**
- ├── **Civil:** Subclases específicas (Ordinario, Ejecutivo, etc.)
- ├── **Penal:** Subclases específicas
- ├── **Laboral:** Subclases específicas
- ├── **Familia:** Subclases específicas
- └── **Otros tipos:** Administrativo, Constitucional, etc.

**Ramificaciones — Clientes:**
- ├── **Un solo cliente:** Selección simple
- └── **Múltiples clientes:** Multi-select, tabla con lista de seleccionados + botón eliminar

**Ramificaciones — Etapas procesales:**
- ├── **Con fecha definida:** Usuario selecciona fecha del calendario
- ├── **Sin fecha:** Sistema usa fecha actual por defecto
- ├── **Agregar etapa:** Botón "+" añade fila a la tabla
- └── **Eliminar etapa:** Botón trash (deshabilitado para primera etapa)

**Ramificaciones — Archivos:**
- ├── **Sin archivos:** Formulario se envía sin adjuntos
- └── **Con archivos:** Drag & drop o selección manual, múltiples archivos

---

### process-edit: Editar proceso
- **Módulo:** processes | **Prioridad:** P2 | **Ruta:** `/process_form/edit/:process_id` | **E2E:** ✅
- **Descripción:** Editar proceso existente (precarga datos)

Mismas ramificaciones que process-create, con datos precargados.

---

### process-detail: Ver detalle de proceso
- **Módulo:** processes | **Prioridad:** P1 | **Ruta:** `/process_detail/:process_id` | **E2E:** ✅
- **Descripción:** Información completa del caso

**Contenido:**
- Avatar del cliente con nombre y rol
- Tarjeta de información: tipo, autoridad, radicado, partes
- Barra de progreso tipo chevron (Inicio → Etapa Actual → Fin)
- Botón "Histórico Procesal" → modal con timeline de etapas
- Tarjeta de expediente digital: tabla de archivos, búsqueda, descarga individual, paginación (10/página)
- Botón "Ver usuarios" → modal con todos los clientes asociados

---

### process-case-file-upload: Subir archivos al expediente
- **Módulo:** processes | **Prioridad:** P2 | **Ruta:** `/process_detail/:process_id` | **E2E:** ✅
- **Descripción:** Upload múltiple de archivos al expediente digital

---

### process-request-info: Request process information (client)
- **Módulo:** processes | **Prioridad:** P2 | **Ruta:** `/process_detail/:process_id` | **E2E:** ✅
- **Descripción:** Client requests information about a process from detail view, pre-filled form sent to responsible lawyer

**Pasos:**
1. Client navigates to process detail view
2. Clicks "Solicitar Información" button
3. Form is pre-filled with process context
4. Client adds specific question/request
5. Submit sends request to responsible lawyer

---

### process-search: Buscar procesos
- **Módulo:** processes | **Prioridad:** P3 | **Ruta:** `/process_list` | **E2E:** ✅
- **Descripción:** Búsqueda por texto en la lista de procesos

---

### process-history: Histórico procesal
- **Módulo:** processes | **Prioridad:** P2 | **Ruta:** N/A (modal) | **E2E:** ✅
- **Descripción:** Modal con timeline de etapas procesales ordenadas cronológicamente

---

### process-alerts: Alertas de proceso por estado procesal
- **Módulo:** processes | **Prioridad:** P2 | **Ruta:** `/process_detail/{id}` (indicador) y modal de historial | **E2E:** ✅
- **Descripción:** Sistema de recordatorios automáticos para fechas de estados procesales.

**Configuración (al crear/editar proceso):**
- Toggle activar/desactivar alerta del último estado
- Toggle destinatarios: solo abogado o abogado + clientes (default: ambos)
- Descripción personalizable (default: auto-generada por estado y fecha)

**Visualización:**
- En `ProcessDetail`: indicador con `BellAlertIcon` que muestra "Notifica al abogado" o "Notifica al abogado y clientes" cuando `is_active=true`
- En `ProcessHistoryModal`: badge "Alerta" / "Inactiva" por etapa, con tooltip (`title`) que indica destinatarios

**Backend automático:**
- `StageAlert` se crea automáticamente para CADA etapa al crear/editar el proceso
- Solo el último estado se evalúa por la tarea Huey diaria (14:00 UTC = 9:00 AM Colombia)
- Se envían recordatorios en `T-3 días` y `T-1 día` (fijos, no configurables)
- Doble canal: email (`send_template_email`) + notificación in-app (`category='process_alert'`)
- Anti-duplicación: flags `notified_3_days` / `notified_1_day` en `StageAlert`

---

### process-form-validation: Validación del formulario de procesos
- **Módulo:** processes | **Prioridad:** P2 | **Ruta:** `/process_form/*` | **E2E:** ✅
- **Descripción:** Validación de campos requeridos, habilitación de botón guardar, agregar/eliminar etapas

---

### docs-dashboard-lawyer: Dashboard de documentos (Lawyer)
- **Módulo:** documents | **Prioridad:** P1 | **Ruta:** `/dynamic_document_dashboard` | **E2E:** ✅
- **Descripción:** Vista principal de documentos para abogados

**Tabs disponibles:**
1. **Minutas** — Plantillas creadas (Published, Draft)
2. **Mis Documentos** — Documentos propios (completados y en progreso)
3. **Carpetas** — Organización en carpetas personalizadas
4. **Dcs. Por Firmar** — Estado PendingSignatures
5. **Dcs. Firmados** — Estado FullySigned
6. **Dcs. Archivados** — Rechazados y Expirados (Rejected, Expired)
7. **Dcs. Clientes (Completados)** — Finalizados por clientes
8. **Dcs. Clientes (En Progreso)** — En proceso de completado

**Acciones en la barra superior:**
- Botón "Firma Electrónica" → modal de configuración de firma
- Botón "Membrete Global" → configuración de encabezado/pie
- Botón "Nueva Minuta" (solo en tab Minutas) → modal nombre → editor
- Botón "Nuevo Documento" (solo en tab Mis Documentos) → seleccionar plantilla

**Cobertura E2E añadida (fix 1.6):** `docs-dashboard-lawyer-flow.spec.js` verifica que al abrir una carpeta, el FolderDetailsModal muestra las columnas Contraparte/Objeto/Fechas con datos reales (no "-") cuando el backend provee campos `summary_*`.

**Cobertura E2E añadida (fix 1.7):** `docs-dashboard-lawyer-flow.spec.js` verifica que al hacer click en un doc `PendingSignatures` o `FullySigned` dentro de una carpeta, el modal se cierra y el tab activo cambia al correspondiente (Dcs. Por Firmar / Dcs. Firmados).

---

### docs-create-template: Crear minuta (plantilla)
- **Módulo:** documents | **Prioridad:** P1 | **Ruta:** `/dynamic_document_dashboard/lawyer/editor/create/:title` | **E2E:** ✅
- **Descripción:** Crear nueva plantilla de documento

**Pasos:**
1. Click "Nueva Minuta"
2. Modal: ingresa nombre de la minuta
3. Abre editor TinyMCE
4. Redacta contenido con formato enriquecido
5. Inserta variables con sintaxis `{{nombreVariable}}`
6. Guardar como Draft o Published

---

### docs-editor: Editor de documentos
- **Módulo:** documents | **Prioridad:** P1 | **Ruta:** `/dynamic_document_dashboard/lawyer/editor/edit/:id` | **E2E:** ✅
- **Descripción:** Editar contenido de documento en TinyMCE

**Ramificaciones por contexto:**
- ├── **Editar minuta (Lawyer):** Editor completo, puede modificar todo
- ├── **Editar documento completado por cliente:** Variables protegidas (subrayadas amarillo), solo contenido libre editable
- └── **Vista de solo lectura:** Preview sin edición

---

### docs-variables-config: Configurar variables
- **Módulo:** documents | **Prioridad:** P1 | **Ruta:** `/dynamic_document_dashboard/lawyer/variables-config` | **E2E:** ✅
- **Descripción:** Definir tipo y comportamiento de cada variable del documento

**Cobertura E2E:** `document-variables-config-interactions.spec.js` verifica que la página renderiza las variables con heading, botones de acción, y que seleccionar la clasificación "Valor" revela el selector de moneda (COP/USD/EUR).

**Campos por variable:**
- Nombre (ES/EN)
- Tooltip explicativo
- **Tipo de campo** (field_type) — ver ramificaciones
- Clasificación (summary_field)
- Moneda (si clasificación = value)

**Ramificaciones — Tipo de campo (field_type):**
- ├── **input:** Texto simple, una línea
- ├── **text_area:** Texto largo, múltiples líneas
- ├── **number:** Numérico con formato de miles y moneda opcional
- ├── **date:** Selector de fecha del calendario
- ├── **email:** Input con validación de formato email
- └── **select:** Dropdown con opciones personalizadas (opciones separadas por coma)

**Ramificaciones — Clasificación (summary_field):**
- ├── **none:** Sin clasificación especial
- ├── **title:** Usuario/Contraparte
- ├── **subscription_date:** Fecha de suscripción (auto-ajusta field_type a date)
- ├── **start_date:** Fecha de inicio (auto-ajusta field_type a date)
- ├── **end_date:** Fecha de fin (auto-ajusta field_type a date)
- └── **value:** Valor monetario (auto-ajusta field_type a number) + selector de moneda (COP, USD, EUR)

---

### docs-use-template: Usar documento (DocumentForm)
- **Módulo:** documents | **Prioridad:** P1 | **Ruta:** `/dynamic_document_dashboard/document/use/:mode/:id/:title` | **E2E:** ✅
- **Descripción:** Formulario para completar documentos con campos variables

**Ramificaciones — Modo del formulario (route.params.mode):**
- ├── **creator:** Llenar documento nuevo desde plantilla. Botones: "Guardar progreso" + "Generar"
- ├── **editor:** Editar borrador existente. Botones: "Guardar cambios como Borrador" + "Completar y Generar"
- ├── **formalize:** Agregar firmas a documento completado. Botones: "Formalizar y Agregar Firmas". Sección adicional: seleccionar firmantes + fecha límite de firma + gestionar asociaciones
- └── **correction:** Corregir documento rechazado/expirado y reenviar. Botón: "Guardar y reenviar para firma"

**Ramificaciones — Campos variables (6 tipos):**
- ├── **input** (`field_type='input'`): `<input type="text">`
- ├── **text_area** (`field_type='text_area'`): `<textarea>` (ocupa ancho completo)
- ├── **number** (`field_type='number'`): Input numérico con prefijo de moneda si `variable.currency` existe
- ├── **date** (`field_type='date'`): `<input type="date">` con calendario
- ├── **email** (`field_type='email'`): `<input type="email">` con validación
- └── **select** (`field_type='select'`): `<select>` con opciones de `variable.select_options`

**Ramificaciones — Modo formalize (firmantes):**
- ├── **Buscar firmante:** Input de búsqueda por nombre/email → dropdown con resultados
- ├── **Agregar firmante:** Click en usuario → se añade a lista numerada
- ├── **Remover firmante:** Botón eliminar en cada firmante
- └── **Fecha límite:** Input date con mínimo = fecha actual

---

### docs-permissions: Asignar documentos a clientes
- **Módulo:** documents | **Prioridad:** P1 | **Ruta:** N/A (modal) | **E2E:** ✅
- **Descripción:** Configurar permisos de acceso al documento

---

### docs-card-actions: Acciones sobre documentos
- **Módulo:** documents | **Prioridad:** P2 | **Ruta:** N/A (menú contextual) | **E2E:** ✅
- **Descripción:** Menú de acciones disponibles por documento

**Acciones (10):**
1. 👁️ Ver/Editar → abre editor
2. 📋 Duplicar → crea copia
3. 👤 Asignar a Cliente → modal permisos
4. ⚙️ Configurar Variables → ruta variables-config
5. 🏷️ Gestionar Etiquetas → modal tags
6. 🗑️ Eliminar → confirmación
7. 📄 Descargar PDF → export directo
8. 📁 Mover a Carpeta → modal selección carpeta
9. ✍️ Firmar → flujo de firma
10. 👀 Vista Previa → modal readonly

**Acciones adicionales en Archivados:**
- ↩️ Editar y reenviar para firma (documentos Rejected/Expired)
- ✏️ Editar contenido (documentos completados por clientes)

**Cobertura E2E añadida (fix 1.8):** `docs-card-actions-flow.spec.js` verifica el atajo "Agregar a Carpeta" desde el modal de acciones, asegurando el PATCH a `dynamic-documents/folders/<id>/update/` con el `document_ids` correcto.

---

### sign-electronic-signature: Firma electrónica
- **Módulo:** signatures | **Prioridad:** P1 | **Ruta:** N/A (modal) | **E2E:** ✅
- **Descripción:** Crear y guardar firma electrónica

**Ramificaciones — Método de firma:**
- ├── **Dibujar:** Canvas con mouse o touch → dibujar firma
- └── **Subir imagen:** Seleccionar archivo de imagen escaneada

---

### sign-document-flow: Firmar documento
- **Módulo:** signatures | **Prioridad:** P1 | **Ruta:** N/A | **E2E:** ✅
- **Descripción:** Proceso de firma de un documento pendiente

**Ramificaciones:**
- ├── **Firmar:** Aplica firma guardada → actualiza estado (parcial o FullySigned si es último firmante)
- └── **Rechazar** (→ sign-reject): Modal con campo motivo opcional → documento pasa a Rejected

---

### sign-reject: Rechazar documento
- **Módulo:** signatures | **Prioridad:** P1 | **Ruta:** N/A (modal) | **E2E:** ✅
- **Descripción:** Rechazar documento con motivo

**Pasos:**
1. Click "Rechazar documento"
2. Modal con campo de motivo (opcional)
3. Confirmar rechazo
4. Documento pasa a estado Rejected → pestaña Archivados

---

### sign-reopen: Reabrir documento rechazado
- **Módulo:** signatures | **Prioridad:** P1 | **Ruta:** N/A | **E2E:** ✅
- **Descripción:** Abogado reabre documento Rejected/Expired para corrección

**Pasos:**
1. En Dcs. Archivados, click "Editar y reenviar para firma"
2. Abre DocumentForm en modo `correction`
3. Corrige contenido
4. Click "Guardar y reenviar para firma"
5. Documento vuelve a PendingSignatures

---

### formalize-in-place: Formalizar documento sin copia
- **Módulo:** documents | **Prioridad:** P1 | **Ruta:** `/dynamic_document_dashboard/document/use/formalize/:id/:title` | **E2E:** ✅
- **Descripción:** Transicionar documento Completado a PendingSignatures en el mismo registro (sin crear copia)

**Pasos:**
1. En Mis Documentos o tabla de documentos, click "Formalizar y Agregar Firmas" en documento Completed
2. Se navega a DocumentForm en modo `formalize`
3. Seleccionar firmantes + fecha límite de firma
4. Click "Formalizar y Agregar Firmas"
5. `POST /api/dynamic-documents/:id/formalize/` con `{ signers, signature_due_date }`
6. Mismo documento transiciona a PendingSignatures (sin `_firma` suffix en título, sin duplicación)
7. Redirección a pestaña "Dcs. Por Firmar"

**Diferencia con flujo anterior:**
- Antes: `POST /api/dynamic-documents/create/` creaba copia con sufijo `_firma`
- Ahora: `POST /api/dynamic-documents/:id/formalize/` transiciona el mismo documento
- Usa bloqueo optimista (`filter(state='Completed').update(...)`) → 409 si hay conflicto concurrente

---

### correct-document: Corregir documento rechazado/expirado
- **Módulo:** documents | **Prioridad:** P1 | **Ruta:** `/dynamic_document_dashboard/document/use/correction/:id/:title` | **E2E:** ✅
- **Descripción:** Corregir y reenviar documento rechazado o expirado en un solo endpoint atómico

**Pasos:**
1. En Dcs. Archivados, click "Editar y reenviar para firma" en documento Rejected/Expired
2. Se navega a DocumentForm en modo `correction`
3. Editar contenido y/o variables
4. (Opcional) Fijar "Fecha límite para firmar" (input `correction-signature-due-date`; se precarga sólo si la fecha guardada es futura — una fecha vencida re-expiraría el documento)
5. Click "Guardar y reenviar para firma"
6. `POST /api/dynamic-documents/:id/correct/` con `{ content, variables, signature_due_date }` (`''` limpia la fecha)
7. Backend: actualiza contenido, recrea variables, resetea firmas, transiciona a PendingSignatures
8. Redirección a pestaña "Dcs. Por Firmar"

**Diferencia con flujo anterior:**
- Antes: dos llamadas HTTP (`PUT update` + `POST reopen-signatures`)
- Ahora: una sola llamada atómica (`POST correct`)
- Usa bloqueo optimista (`filter(state__in=['Rejected','Expired']).update(...)`) → 409 si hay conflicto

---

### docs-state-transitions: Estados y transiciones de documentos
- **Módulo:** documents | **Prioridad:** P2 | **Ruta:** N/A | **E2E:** ✅
- **Descripción:** Ciclo de vida del documento

**Diagrama de estados:**
```
Draft → Published (publicar minuta)
Published → Progress (cliente empieza a llenar)
Progress → Completed (cliente termina de llenar)
Completed → PendingSignatures (formalizar con firmas)
PendingSignatures → FullySigned (todos firmaron)
PendingSignatures → Rejected (algún firmante rechazó)
PendingSignatures → Expired (pasó fecha límite)
Rejected → PendingSignatures (abogado corrige y reenvía)
Expired → PendingSignatures (abogado corrige y reenvía)
```

---

### docs-tags: Gestionar etiquetas
- **Módulo:** documents | **Prioridad:** P2 | **Ruta:** N/A (modal) | **E2E:** ✅
- **Descripción:** Crear, editar y asignar etiquetas de colores

---

### docs-folders: Gestionar carpetas
- **Módulo:** documents | **Prioridad:** P2 | **Ruta:** `/dynamic_document_dashboard` (tab Carpetas) | **E2E:** ✅
- **Descripción:** Organizar documentos en carpetas

**Acciones:**
- Crear carpeta (nombre + color)
- Mover documentos a carpeta
- Ver contenido (grid o tabla)
- Editar nombre/descripción
- Eliminar carpeta (con confirmación)

**Cobertura E2E añadida (fix 1.5):** `add-documents-modal-flow.spec.js` protege la vista tabla del modal "Agregar documentos" (columnas Documento/Estado/Etiquetas) contra una regresión al grid de tarjetas.

---

### docs-folder-crud: Document folder CRUD
- **Módulo:** documents | **Prioridad:** P2 | **Ruta:** `/dynamic_document_dashboard` (tab Carpetas) | **E2E:** ✅
- **Descripción:** Folder list rendering, empty folders state, create/edit folder modal

---

### docs-letterhead: Membrete global
- **Módulo:** documents | **Prioridad:** P2 | **Ruta:** N/A (modal) | **E2E:** ✅
- **Descripción:** Configurar encabezado y pie de página global

**Cobertura E2E añadida (fix 1.4):** `docs-letterhead-locked-flow.spec.js` garantiza que documentos en `PendingSignatures` y `FullySigned` no expongan la acción "Editar membrete" en los tabs Dcs. Por Firmar / Dcs. Firmados.

---

### docs-send-email: Enviar documento por email
- **Módulo:** documents | **Prioridad:** P2 | **Ruta:** N/A (modal) | **E2E:** ✅
- **Descripción:** Enviar documento a un email con anexos opcionales

**Pasos:**
1. Click acción "Enviar por email"
2. Modal: ingresa email destinatario
3. Opcionalmente adjunta archivos adicionales
4. Click "Enviar"

---

### docs-download: Descargar documento
- **Módulo:** documents | **Prioridad:** P2 | **Ruta:** N/A | **E2E:** ✅
- **Descripción:** Exportar documento como PDF o Word

---

### docs-duplicate: Duplicar documento
- **Módulo:** documents | **Prioridad:** P3 | **Ruta:** N/A | **E2E:** ✅

---

### docs-delete: Eliminar documento
- **Módulo:** documents | **Prioridad:** P3 | **Ruta:** N/A | **E2E:** ✅
- **Descripción:** Eliminar con confirmación (solo documentos Draft)

---

### docs-preview: Previsualizar documento
- **Módulo:** documents | **Prioridad:** P3 | **Ruta:** N/A (modal) | **E2E:** ✅

**Cobertura E2E añadida (fix 1.3):** `document-preview-modal.spec.js` verifica que el modal de preview realiza un fetch del detalle del documento (`dynamic-documents/<id>/`) cuando la lista omite el campo `content`, protegiendo contra regresión al comportamiento anterior que mostraba contenido vacío.

---

### docs-key-fields: Campos clave del documento
- **Módulo:** documents | **Prioridad:** P3 | **Ruta:** N/A (modal) | **E2E:** ✅
- **Descripción:** Modal con información clave sin abrir documento completo

**Tipos de campo clave:**
- ├── **title:** Usuario/Contraparte
- ├── **value:** Valor monetario con moneda
- ├── **subscription_date / start_date / end_date:** Fechas formateadas
- └── **none:** No se muestra en el modal

---

### docs-relationships: Asociar documentos
- **Módulo:** documents | **Prioridad:** P3 | **Ruta:** N/A (modal) | **E2E:** ✅
- **Descripción:** Vincular documentos relacionados entre sí

**Ramificaciones por estado:**
- ├── **Documento Completed:** Puede crear y eliminar asociaciones
- ├── **Documento en firma (PendingSignatures):** Asociaciones de solo lectura
- └── **Minuta (Draft/Published):** No tiene opción de asociaciones

---

### docs-form-interactions: Interacciones en formularios de documentos
- **Módulo:** documents | **Prioridad:** P2 | **Ruta:** N/A | **E2E:** ✅
- **Descripción:** Campos, botones, validación y tipos de campo en formularios de documentos

---

### docs-form-field-types: Document form field types
- **Módulo:** documents | **Prioridad:** P2 | **Ruta:** N/A | **E2E:** ✅
- **Descripción:** Rendering 6 field types (input, textarea, number, date, email, select), currency prefix, generate button state, cancel navigation, select options

---

### docs-filters: Filtros y búsqueda en documentos
- **Módulo:** documents | **Prioridad:** P2 | **Ruta:** `/dynamic_document_dashboard` | **E2E:** ✅
- **Descripción:** Filtros avanzados, búsqueda por texto, menús jerárquicos de documentos

---

### docs-summary: Resumen de documento
- **Módulo:** documents | **Prioridad:** P3 | **Ruta:** N/A (modal) | **E2E:** ✅
- **Descripción:** Modal de resumen con campos clave del documento (alias de docs-key-fields)

---

### docs-list-table: Tabla de documentos
- **Módulo:** documents | **Prioridad:** P3 | **Ruta:** `/dynamic_document_dashboard` | **E2E:** ✅
- **Descripción:** Ordenamiento, export, interacciones de tabla en la lista de documentos

---

### minutas-columns: Columnas de tabla en vista Minutas
- **Módulo:** documents | **Prioridad:** P2 | **Ruta:** `/dynamic_document_dashboard` (tab Minutas) | **E2E:** ✅
- **Descripción:** La tabla de Minutas no muestra las columnas de campos clave (Contraparte, Objeto, Valor, Plazo, fechas) que son irrelevantes para plantillas sin datos de contrato

**Pasos:**
1. Lawyer navega a `/dynamic_document_dashboard`
2. Click en tab "Minutas"
3. La tabla renderiza sin las columnas: Contraparte, Objeto, Valor, Plazo, Fecha Suscripción, Fecha Inicio, Fecha Terminación

---

### minutas-shared-visibility: Visibilidad compartida y edición colaborativa de minutas
- **Módulo:** documents | **Prioridad:** P2 | **Ruta:** `/dynamic_document_dashboard` (tab Minutas) | **E2E:** ✅ (`minutas-shared-visibility.spec.js`)
- **Descripción:** Todos los abogados ven todas las minutas (Draft/Published) sin importar quién las creó, con columna informativa "Creado por" y filtro de tres alcances "Todas / Compartidas / Mías" (params backend `shared` y `lawyer_id`). Solo el creador modifica/elimina/publica su minuta, salvo por el flag `allow_shared_edit` (**activado por defecto** para promover la colaboración), que habilita a los demás abogados a editar contenido/nombre/variables (nunca eliminar ni cambiar estado; el grant es solo para abogados, no clientes). El creador puede desactivarlo con "Dejar de compartir". Los no creadores siempre pueden previsualizar y crear una copia.

**Pasos:**
1. Lawyer A navega a `/dynamic_document_dashboard` → tab "Minutas"
2. La tabla lista minutas creadas por cualquier abogado (no solo las propias)
3. La columna "Creado por" muestra el nombre del abogado creador; las minutas con edición compartida llevan badge "Compartida"
4. Click en "Mías" → la tabla se reduce a las minutas creadas por el abogado actual
5. Click en "Compartidas" → la tabla se reduce a las minutas con `allow_shared_edit=true`
6. Click en "Todas" → vuelve a mostrar todas las minutas del equipo
7. Minuta propia: menú de acciones completo (editar, permisos, eliminar, publicar/borrador, membrete, copiar, "Compartir edición"/"Dejar de compartir")
8. Minuta ajena NO compartida: solo previsualizar, crear copia y agregar a carpeta (+ descargas si está publicada)
9. Minuta ajena compartida: además puede editar (nombre/documento/variables), pero no eliminar, cambiar estado, permisos ni membrete
10. El backend rechaza con 403 cualquier update/delete que viole estas reglas (incl. intento de cambiar `state` o `allow_shared_edit` por un no creador)

---

### docs-empty-states: Estados vacíos
- **Módulo:** documents | **Prioridad:** P4 | **Ruta:** `/dynamic_document_dashboard` | **E2E:** ✅
- **Descripción:** UI cuando no hay documentos, carpetas, tags u otros elementos

---

### docs-multiple: Renderizado múltiple
- **Módulo:** documents | **Prioridad:** P4 | **Ruta:** N/A | **E2E:** ✅
- **Descripción:** Renderizado correcto con múltiples documentos simultáneos

---

### docs-profile-navigation: Navegación documentos-perfil
- **Módulo:** documents | **Prioridad:** P4 | **Ruta:** N/A | **E2E:** ✅
- **Descripción:** Navegación entre documentos y perfil de usuario

---

### docs-contract-execution: Ejecución del contrato — cuentas de cobro
- **Módulo:** documents | **Prioridad:** P1 | **Ruta:** `/dynamic_document_dashboard` (tab Dcs. Formalizados) | **E2E:** ✅ (`contract-execution-flow.spec.js`)
- **Descripción:** Los documentos completamente firmados con una variable clasificada como "Forma de pago (N cuotas)" habilitan el submódulo de ejecución del contrato: registro secuencial de cuentas de cobro por cuota. El menú del documento firmado gana "Subir Cuenta de Cobro" (cuando hay cuota disponible) y "Ver Cuentas de Cobro" (modal con barra de progreso X/N, total de montos aceptados, estado por cuota — Pendiente/Cargada/Aceptada/Rechazada — descarga de comprobantes y panel de revisión del abogado). Reglas autoritativas en backend: la cuota N+1 se habilita solo cuando N fue aceptada; una cuota en revisión bloquea nuevas cargas (409); el rechazo exige motivo y reabre el mismo slot conservando el historial.

**Pasos:**
1. Abogado clasifica una variable de la minuta como "Forma de pago (N cuotas)" (field_type number, valor entero ≥1); el dato aparece en el resumen del documento
2. Con el documento `FullySigned`, cliente asignado (o abogado creador) abre "Subir Cuenta de Cobro": cuota auto-seleccionada, archivo PDF/JPG/PNG/DOCX ≤20MB, monto y notas opcionales
3. El abogado recibe notificación (correo + campana) y revisa en "Ver Cuentas de Cobro": descarga el archivo y acepta o rechaza con motivo obligatorio
4. Aceptar habilita la siguiente cuota; rechazar notifica al cliente con el motivo y reabre el mismo slot para re-carga
5. Ambas partes consultan el historial (progreso, contabilidad de montos, quién cargó y cuándo) y descargan comprobantes

**Ramificaciones:**
- ├── **Cliente asignado:** puede cargar y consultar; nunca revisar
- ├── **Abogado creador:** puede cargar en nombre del cliente (sin auto-notificación), revisar y consultar
- ├── **Cuota en revisión:** nadie puede cargar hasta la decisión (409 en backend, CTA oculto en UI)
- ├── **Cuota rechazada:** re-carga sobre el MISMO registro; el motivo anterior queda visible como historial
- ├── **Documento sin forma de pago:** el submódulo no aparece (fail-safe, docs existentes intactos)
- └── **Terceros:** 403 en API y sin acciones en el menú

---

### docs-guided-tour: Tour guiado del módulo Archivos Jurídicos
- **Módulo:** documents | **Prioridad:** P2 | **Ruta:** `/dynamic_document_dashboard` | **E2E:** ✅ (`docs-guided-tour-flow.spec.js`)
- **Descripción:** Tour interactivo (driver.js) que orienta al usuario paso a paso por el dashboard: overlay tintado de marca con spotlight redondeado, popover con eyebrow "Guía · Archivos Jurídicos", barra de progreso animada + conteo "Paso X de Y", botones "Siguiente"/"Anterior"/"Omitir guía" y navegación por teclado (← →). Abre con una tarjeta de bienvenida ("Comenzar recorrido" / "Ahora no") y cierra resaltando el botón "?" del header ("Entendido"), con una breve celebración de confetti solo al completarlo. Diferenciado por rol (abogado 10 pasos de contenido, cliente/basic/corporate 7) con cambio automático de pestaña cuando el paso vive en otra sección. El progreso se persiste en backend (`TourProgress`): auto-inicio si nunca se completó, re-oferta vía modal brandeado a los 30 días, re-lanzamiento manual con el botón "?" (que muestra un ping azul mientras la guía esté pendiente).

**Pasos:**
1. Usuario entra a `/dynamic_document_dashboard` por primera vez (status `never`); el botón "?" muestra un ping azul
2. Tras cargar la página aparece la tarjeta de bienvenida centrada; "Comenzar recorrido" inicia (o "Ahora no" declina y registra la vista)
3. "Siguiente" recorre pestañas y botones ("Nueva Minuta", "Nuevo Documento", "Firma Electrónica", "Membrete Global") con barra de progreso "Paso X de 10/7"; el tour cambia de pestaña automáticamente cuando el elemento vive en otra tab
4. El último paso resalta el botón "?" del header; "Entendido" cierra con confetti y registra la completación (`POST /api/tour-progress/complete/`)
5. Omitir ("Omitir guía"/✕/"Ahora no") también registra la completación, sin confetti; el ping del "?" desaparece
6. En visitas posteriores (<30 días, status `recent`) el tour no se auto-inicia; el botón "?" lo relanza a demanda desde la bienvenida
7. Pasados 30 días (status `stale`) aparece el modal brandeado "¿Quieres ver la guía del módulo de Archivos Jurídicos?" ("Ver la guía" / "Ahora no"); rechazar también resetea el reloj de 30 días

**Ramificaciones:**
- ├── **Abogado/Admin:** 10 pasos de contenido (incluye Minutas, Dcs. Clientes, Nueva Minuta) + bienvenida y cierre
- ├── **Cliente/Basic/Corporate:** 7 pasos de contenido (Carpetas, Mis Documentos, Por Firmar, Formalizados) + bienvenida y cierre
- ├── **Móvil (<md):** pasos de pestañas individuales se omiten (viven en dropdown colapsado) — 3 pasos de contenido + bienvenida y cierre
- ├── **Con firmas pendientes:** paso de contenido extra resaltando "Dcs. Por Firmar" antes del cierre
- ├── **prefers-reduced-motion:** sin animaciones (pop-in, barra, ping, confetti)
- └── **Deep link (?tab=/?lawyerTab=):** el auto-inicio se suprime (el usuario llegó con un propósito)

---

### sign-pending-documents: Documentos pendientes de firma
- **Módulo:** signatures | **Prioridad:** P2 | **Ruta:** `/dynamic_document_dashboard` (tab Por Firmar) | **E2E:** ✅
- **Descripción:** Lista de documentos esperando firma del usuario

---

### sign-signed-documents: Documentos firmados
- **Módulo:** signatures | **Prioridad:** P2 | **Ruta:** `/dynamic_document_dashboard` (tab Firmados) | **E2E:** ✅
- **Descripción:** Lista de documentos completamente firmados

---

### sign-archived-documents: Documentos archivados (firma)
- **Módulo:** signatures | **Prioridad:** P3 | **Ruta:** `/dynamic_document_dashboard` (tab Archivados) | **E2E:** ✅
- **Descripción:** Documentos rechazados y expirados. La acción "Previsualizar" renderiza las variables con sus valores (los estados Rejected/Expired procesan variables igual que Completed/PendingSignatures/FullySigned)

---

### sign-status-modal: Modal de estado de firmantes
- **Módulo:** signatures | **Prioridad:** P2 | **Ruta:** N/A (modal) | **E2E:** ✅
- **Descripción:** Modal con estado de cada firmante (Pendiente, Firmado, Rechazado)

---

### legal-files-menu-pulse: Pulso visual en menú "Archivos Jurídicos" con firmas pendientes
- **Módulo:** signatures | **Prioridad:** P1 | **Ruta:** SlideBar (cualquier ruta autenticada) | **E2E:** ✅ (Req #6 — `legal-files-menu-pulse.spec.js` vía `flow-tags.js`)
- **Descripción:** Tras login, el SlideBar consulta `GET /api/dynamic-documents/pending-signatures-count/` y, si hay firmas pendientes, muestra un indicador pulsante (badge con conteo + dot animado) sobre el ítem "Archivos Jurídicos". Al visitar el módulo, el flag `pendingSignaturesAlerted` se persiste en `sessionStorage` y el pulso desaparece para el resto de la sesión. Al cerrar sesión (`auth.logout()`) el flag se limpia para que el siguiente login reactive el alerta.
- **Componentes:** `SlideBar.vue`, `composables/usePendingSignatures.js` (constante exportada `PENDING_SIGNATURES_ALERTED_KEY`), `stores/auth/auth.js`.
- **Roles:** lawyer, client, corporate_client, basic.

---

### legal-files-auto-redirect: Auto-selección de tab "Documentos Por Firmar" en primer ingreso
- **Módulo:** signatures | **Prioridad:** P2 | **Ruta:** `/dynamic_document_dashboard` | **E2E:** ✅ (Req #6 — `legal-files-auto-redirect.spec.js` vía `flow-tags.js`)
- **Descripción:** En la primera visita post-login al Dashboard de documentos, si `usePendingSignatures.shouldAlert` es `true` (hay pendientes y no se ha marcado la sesión), se selecciona automáticamente la pestaña "Dcs. Por Firmar" y se llama `markAlerted()`. Si la URL incluye `?tab=` o `?lawyerTab=` explícitos, esos parámetros tienen prioridad sobre la auto-redirección. Visitas posteriores en la misma sesión respetan la navegación normal.
- **Componentes:** `views/dynamic_document/Dashboard.vue` (lógica en `onMounted` + watch sobre `route.query`).
- **Roles:** lawyer, client, corporate_client, basic.

---

### legal-files-table-pulse: Pulso de ~8s en filas pendientes de la tabla de firmas
- **Módulo:** signatures | **Prioridad:** P2 | **Ruta:** `/dynamic_document_dashboard` (tab Por Firmar) | **E2E:** ✅ (Req #6 — `legal-files-table-pulse.spec.js` vía `flow-tags.js`)
- **Descripción:** Al montar `SignaturesListTable` con `state="PendingSignatures"`, las filas donde el usuario actual figura como firmante con firma pendiente reciben la clase `animate-pulse bg-blue-50` durante `PULSE_DURATION_MS = 8000` (8 segundos). El `setTimeout` se cancela en `onBeforeUnmount` para evitar fugas. Pasado el timeout, el pulso se detiene y `shouldPulsate(document)` retorna `false`.
- **Componentes:** `components/dynamic_document/common/SignaturesListTable.vue` (`isPulseActive` ref + `shouldPulsate`).
- **Roles:** lawyer, client, corporate_client, basic.

---

### legal-management-lawyer: Gestión de solicitudes (Lawyer)
- **Módulo:** legal-requests | **Prioridad:** P1 | **Ruta:** `/legal_requests` | **E2E:** ✅
- **Descripción:** Ver y gestionar todas las solicitudes

**Acciones:**
- Filtrar por estado (Pendiente, En Revisión, Respondida, Cerrada) y rango de fechas
- Cambiar estado de solicitud
- Responder con mensajes (thread)
- Eliminar solicitudes
- Descargar archivos adjuntos

---

### legal-response-thread: Thread de conversación
- **Módulo:** legal-requests | **Prioridad:** P1 | **Ruta:** `/legal_request_detail/:id` | **E2E:** ✅
- **Descripción:** Mensajería bidireccional cliente-abogado

---

### legal-add-files: Agregar archivos a solicitud
- **Módulo:** legal-requests | **Prioridad:** P2 | **Ruta:** N/A (modal) | **E2E:** ✅
- **Descripción:** Modal para subir archivos adicionales a una solicitud existente

---

### legal-status-update: Actualizar estado de solicitud
- **Módulo:** legal-requests | **Prioridad:** P2 | **Ruta:** `/legal_request_detail/:id` | **E2E:** ✅
- **Descripción:** Cambiar estado y eliminar solicitudes (Lawyer)

---

### legal-lawyer-modals: Modales de gestión de solicitudes
- **Módulo:** legal-requests | **Prioridad:** P3 | **Ruta:** N/A (modales) | **E2E:** ✅
- **Descripción:** StatusUpdateModal y DeleteConfirmModal para gestión de solicitudes

---

### secop-list-browse: Browse SECOP processes
- **Módulo:** secop | **Prioridad:** P2 | **Ruta:** `/secop` | **E2E:** ✅
- **Descripción:** Browse, search, filter, and sort SECOP public procurement opportunities

**Pasos:**
1. Navigate to `/secop` via sidebar "Contratación Estatal"
2. View paginated table of SECOP processes
3. Use filters (department, procurement method, status)
4. Use search bar for keyword search
5. Change sort order (date, budget, entity)
6. Paginate through results

---

### secop-process-detail: View SECOP process detail
- **Módulo:** secop | **Prioridad:** P2 | **Ruta:** `/secop/:id` | **E2E:** ✅
- **Descripción:** View full detail of a SECOP procurement process

**Pasos:**
1. Click on a process row in the list
2. View entity info, process details, dates, budget
3. View team classifications
4. Click "Ver en SECOP" to open external portal link

---

### secop-classify-process: Classify a SECOP process
- **Módulo:** secop | **Prioridad:** P2 | **Ruta:** `/secop` or `/secop/:id` | **E2E:** ✅
- **Descripción:** Mark a process with a classification status and add internal notes

**Pasos:**
1. Click tag icon on a process row OR click "Clasificar" in detail view
2. Select status (Interesting / Under Review / Applied / Discarded)
3. Optionally add internal notes
4. Save classification

**Ramificaciones:**
- ├── **Edit:** Change status or notes of existing classification
- └── **Delete:** Remove classification entirely

---

### secop-create-alert: Create SECOP alert
- **Módulo:** secop | **Prioridad:** P2 | **Ruta:** `/secop` (Alerts tab) | **E2E:** ✅
- **Descripción:** Configure an alert to receive notifications for matching processes

**Pasos:**
1. Navigate to Alerts tab
2. Click "Nueva Alerta"
3. Fill in criteria: name, keywords, departments, entities, budget range, procurement methods
4. Select notification frequency (Immediate / Daily / Weekly)
5. Save alert

---

### secop-manage-alerts: Manage SECOP alerts
- **Módulo:** secop | **Prioridad:** P3 | **Ruta:** `/secop` (Alerts tab) | **E2E:** ✅
- **Descripción:** Edit, toggle, or delete existing alerts

**Ramificaciones:**
- ├── **Toggle:** Pause/resume an alert
- ├── **Edit:** Modify criteria or frequency
- └── **Delete:** Remove alert permanently

---

### secop-export-excel: Export SECOP processes to Excel
- **Módulo:** secop | **Prioridad:** P3 | **Ruta:** `/secop` | **E2E:** ✅
- **Descripción:** Export filtered process list to .xlsx file

**Pasos:**
1. Apply desired filters
2. Click "Exportar" button
3. Download .xlsx file with current filter results

---

### secop-add-notes: Add internal notes to a SECOP process
- **Módulo:** secop | **Prioridad:** P3 | **Ruta:** `/secop` or `/secop/:id` | **E2E:** ✅
- **Descripción:** Add internal notes to a classified process for team collaboration

**Pasos:**
1. Open classification modal (tag icon or "Clasificar" button)
2. Select classification status
3. Write notes in the text area
4. Save classification with notes

---

### secop-save-view: Save filter combination as named view
- **Módulo:** secop | **Prioridad:** P3 | **Ruta:** `/secop` (Vistas Guardadas tab) | **E2E:** ✅
- **Descripción:** Save current filter combination as a named view for quick future access

**Pasos:**
1. Apply desired filters (department, procurement method, status, search)
2. Navigate to "Vistas Guardadas" tab
3. Click "Guardar Vista Actual"
4. Enter a descriptive name
5. Click "Guardar"

---

### secop-apply-saved-view: Apply a saved filter view
- **Módulo:** secop | **Prioridad:** P3 | **Ruta:** `/secop` (Vistas Guardadas tab) | **E2E:** ✅
- **Descripción:** Apply a previously saved filter combination to the process list

**Pasos:**
1. Navigate to "Vistas Guardadas" tab
2. Click "Aplicar" on a saved view
3. Redirected to "Todas las Oportunidades" tab with filters applied

---

### secop-view-in-portal: Open deep-link to SECOP portal
- **Módulo:** secop | **Prioridad:** P3 | **Ruta:** `/secop/:id` | **E2E:** ✅
- **Descripción:** Open the official SECOP portal page for a process in a new tab

**Pasos:**
1. Navigate to process detail page
2. Click "Ver en SECOP" button
3. New tab opens with the official SECOP process page

---

### secop-sync-status: View sync status and history
- **Módulo:** secop | **Prioridad:** P3 | **Ruta:** `/secop` | **E2E:** ✅
- **Descripción:** View the last synchronization time and status indicator

**Pasos:**
1. Navigate to `/secop`
2. View sync status indicator in the header bar
3. The indicator shows the authoritative latest attempt: in progress, success freshness, or failure
4. **Failure:** a failed attempt shows a safe message and the relative time of the last success without exposing diagnostics

---

### secop-trigger-sync: Lawyer-like user triggers manual sync
- **Módulo:** secop | **Prioridad:** P4 | **Ruta:** `/secop` | **E2E:** ✅
- **Descripción:** Lawyer/admin/staff/superuser triggers a manual synchronization with SECOP API via the sync button in the header; other roles still see status but not the trigger

**Pasos:**
1. Navigate to `/secop`
2. Click "Sincronizar" button in the sync status bar
3. Button disables and shows spinner while syncing
4. The page polls the server-side sync history while Huey runs asynchronously
5. A successful newer SyncLog refreshes the opportunity count and re-enables the button

---

### secop-filter-classifications: Filter classified processes by status
- **Módulo:** secop | **Prioridad:** P3 | **Ruta:** `/secop` | **E2E:** ✅
- **Descripción:** Filter the Mis Clasificaciones tab by classification status

**Pasos:**
1. Navigate to `/secop`
2. Click "Mis Clasificaciones" tab
3. Select a status from the classification filter dropdown (Interesante, En Revisión, Aplicado, Descartado)
4. List updates to show only processes with that classification status

---

### secop-saved-view-favorites: Toggle saved view as favorite
- **Módulo:** secop | **Prioridad:** P3 | **Ruta:** `/secop` (Vistas Guardadas tab) | **E2E:** ✅
- **Descripción:** Mark/unmark a saved view as favorite (default filter). Favorites show a star icon and load automatically.

**Pasos:**
1. Navigate to "Vistas Guardadas" tab
2. Click the star icon on a saved view card
3. View toggles between favorite/non-favorite state
4. Favorite views appear first in the list and load automatically

**Ramificaciones:**
- ├── **Set favorite:** Star icon fills, view becomes default filter
- └── **Remove favorite:** Star icon empties, view no longer auto-loads

---

### secop-keyword-tags: Keyword tags in saved views and filters
- **Módulo:** secop | **Prioridad:** P3 | **Ruta:** `/secop` (Vistas Guardadas tab) | **E2E:** ✅
- **Descripción:** Add pipe-delimited keyword tag phrases to saved views for granular SECOP search

**Pasos:**
1. Create or edit a saved view
2. Add keyword tag phrases (pipe-delimited for multi-word phrases)
3. Keywords display as filter badges on saved view cards
4. When applied, keywords filter SECOP processes by matching terms

---

### secop-edit-saved-view: Edit an existing saved view
- **Módulo:** secop | **Prioridad:** P3 | **Ruta:** `/secop` (Vistas Guardadas tab) | **E2E:** ✅
- **Descripción:** Click the edit icon on a saved view card to open SavedViewModal in edit mode, update name and/or filters, save via PATCH

**Pasos:**
1. Navigate to "Vistas Guardadas" tab
2. Click the edit (pencil) icon on a saved view card
3. SavedViewModal opens pre-filled with existing name and filters
4. Modify name and/or filter values (including multi-select UNSPSC)
5. Click "Guardar" to update via `PATCH secop/saved-views/:id/`

**Ramificaciones:**
- ├── **Éxito:** View updates in list with new name/filters
- ├── **Sin cambios:** Modal closes, view unchanged
- └── **Error de red:** Toast de error, modal permanece abierto

---

## Flujos — Client

> El Client hereda los flujos compartidos y tiene acceso a los siguientes flujos específicos.

### dashboard (Client): Panel principal
- **Módulo:** dashboard | **Prioridad:** P2 | **Ruta:** `/dashboard` | **E2E:** ✅

**Diferencias con Lawyer:**
- Botones de acción rápida: Mis Procesos, Agendar Cita, Nueva Solicitud
- Sin botón "Radicar Proceso" ni "Radicar Informe"

---

### process-list-view (Client): Ver procesos
- **Módulo:** processes | **Prioridad:** P1 | **Ruta:** `/process_list` | **E2E:** ✅

**Tabs para Client:**
- ├── **Mis Procesos:** Solo procesos propios
- └── **Procesos Archivados:** Casos finalizados propios

**No tiene** tab "Todos los Procesos".

---

### process-detail (Client): Detalle con solicitar información
- **Módulo:** processes | **Prioridad:** P1 | **Ruta:** `/process_detail/:process_id` | **E2E:** ✅
- **Descripción:** Misma vista que Lawyer + botón "Solicitar Información"

**Ramificación exclusiva Client:**
- └── **Solicitar Información:** Botón en detalle → formulario pre-llenado → envía al abogado responsable

---

### docs-dashboard-client: Dashboard de documentos (Client)
- **Módulo:** documents | **Prioridad:** P1 | **Ruta:** `/dynamic_document_dashboard` | **E2E:** ✅

**Tabs para Client:**
1. **Minutas** — Plantillas disponibles para usar
2. **Mis Documentos** — Documentos asignados y completados
3. **Carpetas** — Documentos organizados por carpetas
4. **Dcs. Por Firmar** — Pendientes de firma
5. **Dcs. Firmados** — Archivo final

---

### docs-use-template (Client): Completar documento
- **Módulo:** documents | **Prioridad:** P1 | **Ruta:** `/dynamic_document_dashboard/document/use/:mode/:id/:title` | **E2E:** ✅
- **Descripción:** Seleccionar plantilla publicada y llenar campos variables

**Pasos:**
1. En tab "Minutas", click "Usar" en plantilla publicada
2. Formulario con campos variables (6 tipos de campo — ver docs-variables-config)
3. **Guardar progreso** (queda como borrador) o **Generar** (completa el documento)

**Ramificaciones — Acción final:**
- ├── **Guardar progreso:** Estado Progress, puede continuar después
- └── **Generar/Completar:** Estado Completed, abogado puede revisar

---

### sign-client-flow: Firmar documento (Client)
- **Módulo:** signatures | **Prioridad:** P1 | **Ruta:** N/A | **E2E:** ✅
- **Descripción:** Cliente firma o rechaza documento pendiente

**Ramificaciones:**
- ├── **Firmar:** Aplica firma electrónica (dibujar o imagen guardada)
- └── **Rechazar:** Modal con motivo → documento pasa a Rejected

---

### legal-create-request: Crear solicitud legal
- **Módulo:** legal-requests | **Prioridad:** P1 | **Ruta:** `/legal_request_create` | **E2E:** ✅
- **Descripción:** Enviar nueva consulta legal

**Pasos:**
1. Navega a "Solicitudes" → "Nueva Solicitud"
2. **Tipo de solicitud** (Combobox): Consulta, Asesoría, Revisión, Representación, etc.
3. **Disciplina legal** (Combobox): Civil, Penal, Laboral, Familia, Administrativo, etc.
4. Descripción detallada (mínimo 50 caracteres)
5. Anexos opcionales (upload múltiple: PDF, DOCX, JPG, PNG — max 30MB)
6. Click "Enviar" → número auto-generado SOL-YYYY-NNN

**Ramificaciones — Tipo de solicitud:**
- ├── **Consulta:** Consulta general
- ├── **Asesoría:** Asesoría especializada
- ├── **Revisión:** Revisión de documentos
- └── **Representación:** Representación legal

**Ramificaciones — Disciplina legal:**
- ├── **Civil**
- ├── **Penal**
- ├── **Laboral**
- ├── **Familia**
- └── **Administrativo** (y otros)

**Ramificaciones — Anexos:**
- ├── **Sin anexos:** Formulario se envía solo con descripción
- ├── **Con archivos:** Drag & drop o selección manual, múltiples archivos
- └── **Agregar más archivos:** Botón "Agregar más" después de subir primeros

---

### legal-list-client: Ver mis solicitudes
- **Módulo:** legal-requests | **Prioridad:** P1 | **Ruta:** `/legal_requests` | **E2E:** ✅

---

### legal-detail-client: Detalle de solicitud
- **Módulo:** legal-requests | **Prioridad:** P1 | **Ruta:** `/legal_request_detail/:id` | **E2E:** ✅
- **Descripción:** Info + thread de conversación + agregar archivos

---

### org-client-view: Ver organizaciones (Client)
- **Módulo:** organizations | **Prioridad:** P2 | **Ruta:** `/organizations_dashboard` | **E2E:** ✅
- **Descripción:** Ver organizaciones donde es miembro (lectura)

**Contenido:**
- Lista de organizaciones
- Posts de la organización
- Otros miembros
- Solicitudes corporativas

---

### org-client-invitations: Gestionar invitaciones
- **Módulo:** organizations | **Prioridad:** P1 | **Ruta:** `/organizations_dashboard` | **E2E:** ✅
- **Descripción:** Aceptar, rechazar o ver invitaciones expiradas

**Ramificaciones:**
- ├── **Aceptar:** Se une a la organización → gana acceso a posts, miembros, solicitudes
- ├── **Rechazar:** No se une → invitación desaparece
- └── **Expirada:** No puede actuar → mensaje informativo

---

### org-client-requests: Solicitudes dentro de organización
- **Módulo:** organizations | **Prioridad:** P2 | **Ruta:** `/organizations_dashboard` | **E2E:** ✅
- **Descripción:** Crear solicitud corporativa y ver respuestas

---

### org-client-leave: Salir de organización
- **Módulo:** organizations | **Prioridad:** P3 | **Ruta:** `/organizations_dashboard` | **E2E:** ✅
- **Descripción:** Confirmación + pierde acceso a la organización

---

### schedule-appointment: Agendar cita
- **Módulo:** schedule | **Prioridad:** P2 | **Ruta:** `/schedule_appointment` | **E2E:** ✅
- **Descripción:** Agendar cita con abogado vía Calendly

**Ramificaciones — Tipo de cita:**
- ├── **Consulta inicial**
- ├── **Asesoría**
- ├── **Seguimiento**
- └── **Revisión**

---

## Flujos — Corporate Client

> Hereda **todos** los flujos de Client, más los siguientes exclusivos.

### org-create: Crear organización
- **Módulo:** organizations | **Prioridad:** P1 | **Ruta:** `/organizations_dashboard` | **E2E:** ✅
- **Descripción:** Crear nueva organización empresarial

**Pasos:**
1. Click "Nueva Organización"
2. Formulario: nombre + descripción
3. Subir imagen de perfil + imagen de portada
4. Click "Crear"

---

### org-edit: Editar organización
- **Módulo:** organizations | **Prioridad:** P2 | **Ruta:** `/organizations_dashboard` | **E2E:** ✅
- **Descripción:** Actualizar información y portada

---

### org-invite-members: Invitar miembros
- **Módulo:** organizations | **Prioridad:** P1 | **Ruta:** `/organizations_dashboard` | **E2E:** ✅
- **Descripción:** Enviar invitaciones por email

**Ramificaciones:**
- ├── **Email válido (usuario existe):** Invitación enviada → estado Pendiente
- ├── **Email válido (usuario no existe):** Invitación enviada → puede registrarse
- ├── **Email ya es miembro:** Mensaje de error
- └── **Email inválido:** Validación de formulario falla

**Estados de invitación:**
- ├── **Pendiente:** Esperando respuesta
- ├── **Aceptada:** Usuario se unió
- ├── **Rechazada:** Usuario declinó
- └── **Expirada:** Tiempo límite excedido

---

### org-members-list: Ver y gestionar miembros
- **Módulo:** organizations | **Prioridad:** P2 | **Ruta:** `/organizations_dashboard` | **E2E:** ✅
- **Descripción:** Lista de miembros con acción de remover

---

### org-posts-management: Gestionar publicaciones
- **Módulo:** organizations | **Prioridad:** P2 | **Ruta:** `/organizations_dashboard` | **E2E:** ✅
- **Descripción:** CRUD completo de publicaciones internas

**Ramificaciones — Crear publicación:**
- ├── **Visible para clientes:** Sí → clientes miembros la ven
- └── **Visible para clientes:** No → solo corporate ve la publicación

**Ramificaciones — Acciones sobre publicación:**
- ├── **Fijar (pin):** Sube al tope de la lista
- ├── **Desfijar (unpin):** Vuelve a orden cronológico
- ├── **Editar:** Modificar título, contenido, visibilidad
- ├── **Cambiar estado:** Activar/desactivar publicación
- └── **Eliminar:** Confirmación + eliminación

---

### org-posts-visibility: Visibilidad de publicaciones
- **Módulo:** organizations | **Prioridad:** P2 | **Ruta:** `/organizations_dashboard` | **E2E:** ✅
- **Descripción:** Control de qué ven los clientes miembros

---

### org-corporate-requests: Solicitudes recibidas
- **Módulo:** organizations | **Prioridad:** P2 | **Ruta:** `/organizations_dashboard` | **E2E:** ✅
- **Descripción:** Ver y responder solicitudes de miembros

**Ramificaciones:**
- ├── **Responder:** Mensaje en thread visible para el solicitante
- ├── **Nota interna:** Mensaje visible solo para corporate (oculto al cliente)
- └── **Cambiar estado:** Pendiente → En Revisión → Respondida → Cerrada

---

### org-request-detail: Detalle de solicitud corporativa
- **Módulo:** organizations | **Prioridad:** P3 | **Ruta:** `/organizations_dashboard` | **E2E:** ✅
- **Descripción:** Vista detallada de una solicitud corporativa con thread y archivos

---

### org-cross-invite-flow: Flujo cross-role de invitación
- **Módulo:** organizations | **Prioridad:** P1 | **Ruta:** N/A | **E2E:** ✅
- **Descripción:** Corporate invita → Client acepta/rechaza → stats se actualizan

---

### org-cross-request-flow: Flujo cross-role de solicitudes
- **Módulo:** organizations | **Prioridad:** P2 | **Ruta:** N/A | **E2E:** ✅
- **Descripción:** Client crea solicitud → Corporate responde → Client ve respuesta

---

### org-cross-member-management: Gestión cross-role de miembros
- **Módulo:** organizations | **Prioridad:** P2 | **Ruta:** N/A | **E2E:** ✅
- **Descripción:** Remover miembro, desactivar org → client pierde acceso

---

### org-store-actions: Organization store actions
- **Módulo:** organizations | **Prioridad:** P3 | **Ruta:** `/organizations_dashboard` | **E2E:** ✅
- **Descripción:** Corporate client loads organizations dashboard and triggers store actions (load, invite)

---

## Flujos — Basic

> Hereda flujos compartidos con **restricciones específicas**.

### basic-restrictions: Restricciones de usuario básico
- **Módulo:** auth | **Prioridad:** P3 | **Ruta:** N/A | **E2E:** ✅
- **Descripción:** Funcionalidades limitadas con botones deshabilitados y overlays de bloqueo

**Restricciones (cubierto por E2E):**
- ✅ **Rutas de abogado:** Redirect a `/dashboard` (directorio, editor, variables-config)
- ✅ **Membrete global:** Botón deshabilitado en `/dynamic_document_dashboard`
- ✅ **Filtros SECOP:** Overlay de bloqueo sobre el panel de filtros en `/secop`
- ✅ **Crear solicitudes:** Acceso a `/legal_request_create`
- ✅ **Agendar cita:** Acceso a `/schedule_appointment`
- ✅ **Usar documentos:** Puede completar formularios (sin firma electrónica)
- ✅ **Organizaciones:** Vista lectura igual que Client

---

## Flujos — Lawyer G&M (is_gym_lawyer)

> Hereda **todos** los flujos de Lawyer, más los siguientes exclusivos.

### intranet-main: Intranet G&M — página principal
- **Módulo:** intranet | **Prioridad:** P2 | **Ruta:** `/intranet_g_y_m` | **E2E:** ✅
- **Descripción:** Portal interno exclusivo para abogados G&M

**Secciones:**
- Perfil de la firma (banner, logo, stats)
- Botón "Radicar Informe"
- Procedimientos G&M (búsqueda)
- Organigrama (modal con imagen)

---

### intranet-facturation-form: Facturation form field interactions
- **Módulo:** intranet | **Prioridad:** P2 | **Ruta:** `/intranet_g_y_m` (modal) | **E2E:** ✅
- **Descripción:** Save button validation, file upload (input + drag-and-drop), successful submission, close modal

---

### intranet-interactions: Interacciones en Intranet
- **Módulo:** intranet | **Prioridad:** P3 | **Ruta:** `/intranet_g_y_m` | **E2E:** ✅

#### Radicar informe
**Pasos:**
1. Click "Radicar Informe"
2. Formulario:
   - No. Contrato
   - Fecha inicial del período
   - Fecha final del período
   - Concepto de pago
   - Valor a cobrar

**Ramificaciones — Anexos (3 tipos):**
- ├── **Informe de Actividades:** PDF obligatorio
- ├── **Cuenta de Cobro/Factura:** PDF obligatorio
- └── **Anexos adicionales:** Múltiples archivos opcionales

3. Observaciones (texto libre)
4. Click "Enviar"

#### Buscar procedimientos
- Búsqueda en tiempo real con highlight amarillo de coincidencias
- Click en documento → descarga directa (blob, sin pantalla en blanco)

#### Ver organigrama
- Modal con imagen de jerarquía de la firma

---

## Flujos — SECOP (Contratación Estatal)

> El módulo es completo para usuarios lawyer-like. Los usuarios Basic pueden
> consultar el listado y el estado de sincronización, pero ven bloqueados los
> filtros/alertas premium y no reciben el control de sincronización manual.

> **Nota de reconciliación (2026-07-24):** las definiciones detalladas de los 17 flujos SECOP
> (con **Pasos** y **Ramificaciones**) viven de forma canónica en la sección **Flujos — Lawyer**,
> dado que SECOP es un módulo exclusivo de ese rol (`secop-list-error-retry` se documenta además en
> la sección de auditoría 2026-07-22). Este bloque duplicaba 15 de esos flujos con descripciones
> abreviadas; se consolidó para evitar definiciones divergentes. La tabla resume el inventario y su
> estado según `scripts/flow_coverage_audit.py`.

| Flow id | Prioridad | Estado (audit 2026-08-21) |
|---------|-----------|---------------------------|
| `secop-list-browse` | P2 | ✅ covered |
| `secop-process-detail` | P2 | ✅ covered |
| `secop-classify-process` | P2 | ✅ covered |
| `secop-create-alert` | P2 | ✅ covered |
| `secop-manage-alerts` | P3 | ✅ covered |
| `secop-export-excel` | P3 | ✅ covered |
| `secop-add-notes` | P3 | ✅ covered |
| `secop-save-view` | P3 | ✅ covered |
| `secop-apply-saved-view` | P3 | ✅ covered |
| `secop-view-in-portal` | P3 | ✅ covered |
| `secop-sync-status` | P3 | ✅ covered (display + failure) |
| `secop-trigger-sync` | P4 | ✅ covered |
| `secop-filter-classifications` | P3 | ✅ covered |
| `secop-saved-view-favorites` | P3 | ✅ covered |
| `secop-keyword-tags` | P3 | ✅ covered |
| `secop-edit-saved-view` | P3 | ✅ covered |
| `secop-list-error-retry` | P4 | ⚠️ partial (failure ✅ · display ❌) |

> El audit 2026-08-21 confirma 16 flujos SECOP cubiertos y 1 parcial. La única brecha
> del módulo es el outcome `display` de `secop-list-error-retry`; su recuperación por
> interacción sí está cubierta.

---

### Form-Level Test Coverage (Unit + E2E)

The following forms and modals have dedicated unit and/or E2E tests covering field rendering, validation, submission, file uploads, and edge cases.

#### Intranet Module

| Component | Unit Tests | E2E Tests | Scenarios Covered |
|-----------|-----------|-----------|-------------------|
| `FacturationForm.vue` | 14 | 4 | Field rendering, save button validation, submit success/error/exception, file upload (input + drag-and-drop), unsupported file type, file size limit, file removal, close modal |

#### Dynamic Documents Module

| Component | Unit Tests | E2E Tests | Scenarios Covered |
|-----------|-----------|-----------|-------------------|
| `DocumentForm.vue` | 13 | 4 | 6 field types (input, textarea, number, date, email, select), currency prefix, tooltip, validation errors, generate button state, save progress, cancel navigation, loading state, editor mode |
| `DocumentVariablesConfig.vue` | 16 | 2 | Variable sections, name_es input, field type selector, summary classification, currency selector (conditional), select options input, draft/publish buttons, validation (empty name, missing options), draft skips validation, auto-adjust field type, duplicate classification reset |
| `EditDocumentModal.vue` | 14 | — | Name input, save button validation, close/overlay dismiss, edit vs create mode, update name (success/error), submit navigation (lawyer/client), showEditorButton toggle |
| `SendDocumentModal.vue` | 13 | — | Email input, send button validation (empty/invalid/valid), close/overlay dismiss, file upload (input + drag-and-drop), unsupported file type, file size limit, submit with sendEmail, file removal |
| `UseDocumentByClient.vue` | 13 | — | Name input, continue button validation, close dismiss, creator/editor route navigation, update name (success/error), edit mode UI, error when no document |
| `SendDocument.vue` (layout) | 9 | — | Email input, send button states, close emits closeEmailModal, file upload, unsupported type, submit with sendEmail, drag-and-drop |
| `CreateEditFolderModal.vue` | 15 | 2 | Folder name input, color selection, create/edit mode titles, submit button state, cancel/overlay close, create/update store calls, pre-fill in edit mode, form reset on visibility change |
| `SearchBarAndFilterBy.vue` | 8 | — | Search input rendering, icon, emit on input, empty initial state, default/auxiliary slots, multiple inputs, clear emits empty |

---

## Flujos — Servicios y Tramites

### service-browse-catalog: Explorar catalogo de servicios
- **Modulo:** services | **Prioridad:** P1 | **Ruta:** `/services` | **E2E:** ✅
- **Descripcion:** Usuario autenticado ve la lista completa de servicios activos

**Pasos:**
1. Navega al sidebar "Servicios"
2. Ve la grilla de servicios con nombre, descripcion e icono
3. Click en un servicio para ver su detalle

**Ramificaciones:**
- ├── **Con servicios:** Muestra grilla de servicios
- └── **Sin servicios:** Muestra mensaje vacio

---

### service-browse-featured: Ver servicios destacados en Dashboard
- **Modulo:** services | **Prioridad:** P1 | **Ruta:** `/dashboard` | **E2E:** ✅
- **Descripcion:** El Dashboard muestra hasta 6 servicios destacados como tarjetas cuadradas

**Pasos:**
1. Navega a `/dashboard`
2. Ve seccion "Servicios Destacados" con tarjetas
3. Click en una tarjeta navega a `/services/:id`

---

### service-fill-form: Diligenciar formulario multi-etapa
- **Modulo:** services | **Prioridad:** P1 | **Ruta:** `/services/:id` | **E2E:** ✅
- **Descripcion:** Usuario completa el formulario del servicio paso a paso

**Pasos:**
1. Navega a `/services/:id`
2. Completa campos de la etapa actual
3. Click "Siguiente" para avanzar
4. Repite hasta la ultima etapa

**Ramificaciones:**
- ├── **Validacion exitosa:** Avanza a la siguiente etapa
- └── **Campo requerido vacio:** Muestra error de validacion

---

### service-save-draft: Guardar borrador del formulario
- **Modulo:** services | **Prioridad:** P2 | **Ruta:** `/services/:id` | **E2E:** ✅
- **Descripcion:** Usuario guarda progreso parcial sin enviar

**Pasos:**
1. Completa campos parcialmente
2. Click "Guardar borrador"
3. El sistema guarda sin validar campos obligatorios
4. Al volver al servicio, se carga el borrador existente

---

### service-submit-request: Enviar solicitud de servicio
- **Modulo:** services | **Prioridad:** P1 | **Ruta:** `/services/:id` | **E2E:** ✅
- **Descripcion:** Usuario envia la solicitud y recibe numero de radicado

**Pasos:**
1. Completa todas las etapas del formulario
2. Adjunta archivos requeridos
3. Click "Enviar solicitud"
4. Recibe numero de radicado (formato YYYY-NNNNN)
5. Puede descargar PDF de confirmacion
6. Recibe correo de confirmacion

**Ramificaciones:**
- ├── **Exito:** Estado cambia a OPEN, se genera PDF y radicado
- ├── **Campos obligatorios faltantes:** Error 400, muestra campos faltantes
- └── **Archivo con extension invalida:** Error de validacion

---

### service-view-my-requests: Ver mis solicitudes
- **Modulo:** services | **Prioridad:** P1 | **Ruta:** `/services?tab=my-requests` (redirect desde `/service_requests/my`) | **E2E:** ✅
- **Descripcion:** Cliente ve su historial de solicitudes con filtros. Desde Sprint Abril 2026 esta integrado en el tab "Mis Solicitudes" dentro de ServicesHub.

**Pasos:**
1. Navega al sidebar "Servicios" (o accede directamente a `/service_requests/my`, que redirige)
2. Hace click en el tab "Mis Solicitudes"
3. Ve lista de solicitudes con estado, radicado, servicio
4. Filtra por estado, servicio o radicado
5. Click en solicitud para ver detalle

---

### service-view-request-detail: Ver detalle de solicitud
- **Modulo:** services | **Prioridad:** P1 | **Ruta:** `/service_requests/:id` | **E2E:** ✅
- **Descripcion:** Usuario ve detalle completo de su solicitud

**Pasos:**
1. Navega al detalle de la solicitud
2. Ve radicado, estado, respuestas del formulario por etapa
3. Descarga PDF si esta disponible
4. Ve respuestas del abogado si existen

---

### service-inbox-view: Bandeja de solicitudes (Abogado)
- **Modulo:** services | **Prioridad:** P1 | **Ruta:** `/service_requests/inbox` | **E2E:** ✅
- **Descripcion:** Abogado ve todas las solicitudes recibidas

**Pasos:**
1. Navega a "Bandeja de Solicitudes" en el sidebar
2. Ve tabla con radicado, servicio, solicitante, estado
3. Filtra por estado, servicio, busqueda, rango de fechas
4. Click para ver detalle

---

### service-manage-request: Gestionar solicitud (Abogado)
- **Modulo:** services | **Prioridad:** P1 | **Ruta:** `/service_requests/:id` | **E2E:** ✅
- **Descripcion:** Abogado cambia estado, envia respuesta o adjunta archivo

**Pasos:**
1. Abre detalle de solicitud desde la bandeja
2. Cambia estado (OPEN → IN_STUDY → IN_PROGRESS → ANSWERED → FINALIZED)
3. Escribe mensaje y/o adjunta archivo
4. Click "Guardar actualizacion"
5. Se envia notificacion por correo al solicitante

**Ramificaciones:**
- ├── **Transicion valida:** Estado actualizado, respuesta creada
- ├── **Transicion invalida:** Error 400 (ej: FINALIZED no permite cambios)
- └── **Sin mensaje ni cambio:** Error 400

---

### service-admin-create: Crear servicio (Admin)
- **Modulo:** services | **Prioridad:** P1 | **Ruta:** `/services_admin` | **E2E:** ✅
- **Descripcion:** Administrador crea un nuevo servicio con etapas y campos

**Pasos:**
1. Navega a "Administrar Servicios"
2. Click "Crear servicio"
3. Define nombre, descripcion, icono
4. Agrega etapas con campos (texto, email, numero, fecha, select, archivo)
5. Guarda el servicio

---

### service-admin-edit: Editar servicio (Admin)
- **Modulo:** services | **Prioridad:** P2 | **Ruta:** `/services_admin` | **E2E:** ⚠️
- **Descripcion:** Administrador edita un servicio existente

**Pasos:**
1. Navega a "Administrar Servicios"
2. Click en servicio existente
3. Modifica nombre, etapas o campos
4. Guarda los cambios

---

### service-admin-toggle: Activar/desactivar servicio (Admin)
- **Modulo:** services | **Prioridad:** P2 | **Ruta:** `/services_admin` | **E2E:** ✅
- **Descripcion:** Administrador activa o desactiva un servicio sin eliminarlo

**Pasos:**
1. Navega a "Administrar Servicios"
2. Toggle "Activo" para ocultar/mostrar servicio
3. Toggle "Destacado" para incluir/excluir del Dashboard

---

### service-hub-tab-navigation: Navegar entre tabs en ServicesHub
- **Modulo:** services | **Prioridad:** P2 | **Ruta:** `/services` | **E2E:** ✅
- **Descripcion:** Usuario cambia entre el tab "Servicios" y "Mis Solicitudes" en la vista unificada. Incluye activacion por query param `?tab=my-requests` (redirect desde legacy paths).

**Pasos:**
1. Navega a `/services` (tab "Servicios" activo por defecto)
2. Ve el catalogo de servicios renderizado en el tab
3. Click en tab "Mis Solicitudes"
4. La URL cambia a `/services?tab=my-requests`
5. Ve la lista de solicitudes propias
6. Click en tab "Servicios" para volver al catalogo

**Ramificaciones:**
- ├── **Desktop:** tabs horizontales
- └── **Mobile:** dropdown `<select>`

---

### service-upload-multiple-files: Subir multiples archivos en formulario de servicio
- **Modulo:** services | **Prioridad:** P2 | **Ruta:** `/services/:id` | **E2E:** ✅
- **Descripcion:** Usuario sube hasta 10 archivos a un campo tipo file en el formulario multi-etapa. Puede eliminar archivos individuales con el boton x.

**Pasos:**
1. Navega a un servicio con campo tipo archivo
2. Click en el input de archivo para seleccionar el primer archivo
3. Selecciona un segundo archivo (se agrega al listado)
4. Ve las tarjetas con nombre, tamano y boton eliminar
5. Click en "x" de un archivo para eliminarlo de la lista
6. Intenta agregar un 11mo archivo — el input esta deshabilitado

**Ramificaciones:**
- ├── **< 10 archivos:** Input habilitado, contador X/10 actualizado
- ├── **= 10 archivos:** Input deshabilitado, mensaje de limite alcanzado
- └── **Eliminar archivo:** Tarjeta desaparece, contador decrementado

---

### service-admin-form-validation: Validacion de formulario admin de servicio
- **Modulo:** services | **Prioridad:** P3 | **Ruta:** `/services_admin` | **E2E:** ✅
- **Descripcion:** Admin intenta guardar un servicio con datos incompletos y ve mensajes de error de validateEditor().

**Pasos:**
1. Navega a "Administrar Servicios"
2. Hace click en "Crear servicio" sin llenar el nombre
3. Intenta guardar
4. Ve mensaje de error "Nombre del servicio es requerido"
5. Agrega una etapa sin nombre
6. Ve error "Cada etapa debe tener nombre"

**Ramificaciones:**
- ├── **Nombre vacio:** Error en campo nombre
- ├── **Sin etapas:** Error por falta de etapas
- └── **Opciones de select vacias:** Error en campo tipo select

---

## Resumen de Cobertura E2E

| Módulo | Flujos | ✅ Cubierto | 🟠 Junk-only | ❌ Sin cobertura |
|--------|--------|------------|-------------|------------------|
| Auth | 13 | 9 | 4 | 0 |
| Subscriptions | 6 | 6 | 0 | 0 |
| Profile | 2 | 1 | 1 | 0 |
| Dashboard | 8 | 8 | 0 | 0 |
| Directory | 2 | 2 | 0 | 0 |
| Processes | 12 | 8 | 2 | 2 |
| Documents | 34 | 32 | 0 | 2 |
| Signatures | 13 | 12 | 1 | 0 |
| Legal Requests | 8 | 8 | 0 | 0 |
| Organizations | 17 | 17 | 0 | 0 |
| Schedule | 1 | 1 | 0 | 0 |
| Intranet | 3 | 3 | 0 | 0 |
| **SECOP** | **17** | **11** | **6** | **0** |
| **Servicios y Tramites** | **16** | **11** | **5** | **0** |
| Notifications | 6 | 6 | 0 | 0 |
| Misc | 4 | 3 | 1 | 0 |
| User Guide | 1 | 1 | 0 | 0 |
| Admin | 1 | 1 | 0 | 0 |
| **Total** | **164** | **140** | **20** | **4** |

> **Tabla derivada de `e2e/flow-definitions.json`** (campo `module`) y del estado reportado por `scripts/flow_coverage_audit.py` (2026-07-24). Los flujos por rol (p. ej. `basic-restrictions`) se agrupan bajo su módulo funcional, por lo que no hay fila "Basic" separada.
>
> **Semántica de columnas (nueva):** `Cubierto` = existe un test que ejercita el flujo; `Junk-only` = existen tests etiquetados pero **ninguno califica** (descalificados por `no_user_interaction` o `flow_tag_mismatch`) — reportan verde pero no cubren, por eso son la prioridad; `Sin cobertura` = ningún test referencia el flujo.
>
> **Total reconciliado 153 → 164 (2026-07-24):** la tabla anterior no había incorporado los 11 flujos añadidos en la auditoría 2026-07-22 (v1.12.0); `flow-definitions.json` (164) es la fuente autoritativa. Ver nota de reconciliación al pie de esta sección.
>
> **Regresión detectada — `process-alert-configure` y `process-alerts`:** la nota previa los daba por cerrados el 16-07-2026, pero el audit 2026-07-24 no encuentra evidencia calificada (0 tests que los ejerciten) → hoy figuran `missing`. Junto a `minutas-columns` y `minutas-shared-visibility` (documents) forman los 4 flujos sin cobertura. Requieren re-verificar si el spec perdió su tag `@flow:<id>` o fue renombrado.
>
> **knownGap (1):** `service-admin-edit` (Servicios) es además `junk-only`: el/los test(s) etiquetados no ejercitan la edición completa de etapas + campos.

---

## Flujos añadidos — Auditoría exhaustiva 2026-07-22 (v1.12.0)

Auditoría de doble fuente (interacciones frontend + clasificación de 205 endpoints) sobre el registro v1.11.0. Se detectaron y cubrieron 11 flujos:

### notification-mark-read: Marcar notificaciones como leídas
- **Módulo:** notifications | **Prioridad:** P3 | **Ruta:** `/notifications` | **E2E:** ✅ (`notification-actions.spec.js`)
- **Descripción:** Marcar una notificación (o todas) como leída/no-leída; el badge de no-leídas se sincroniza.

### notification-snooze: Posponer notificación (snooze)
- **Módulo:** notifications | **Prioridad:** P3 | **Ruta:** `/notifications` | **E2E:** ✅ (`notification-actions.spec.js`)
- **Descripción:** Posponer una notificación con intervalos (1h/3h/1d/3d). Fix de auditoría 2026-07-22: la barra de acciones se fija con `z-20` mientras el menú de snooze está abierto (antes quedaba invisible al salir del hover de la fila).

### notification-archive-toggle: Archivar y desarchivar notificación
- **Módulo:** notifications | **Prioridad:** P3 | **Ruta:** `/notifications` | **E2E:** ✅ (`notification-actions.spec.js`)
- **Descripción:** Archivar y desarchivar una notificación, moviéndola entre pestañas.

### notification-delete: Eliminar notificación
- **Módulo:** notifications | **Prioridad:** P3 | **Ruta:** `/notifications` | **E2E:** ✅ (`notification-actions.spec.js`)
- **Descripción:** Eliminar una notificación definitivamente.

### notification-pagination: Paginación del centro de notificaciones
- **Módulo:** notifications | **Prioridad:** P4 | **Ruta:** `/notifications` | **E2E:** ✅ (`notification-actions.spec.js`)
- **Descripción:** Paginar el centro de notificaciones con Anterior/Siguiente.

### service-admin-delete: Eliminar servicio (admin)
- **Módulo:** services | **Prioridad:** P2 | **Ruta:** `/services_admin` | **E2E:** ✅ (`service-admin-flow.spec.js`)
- **Descripción:** Admin selecciona un servicio, pulsa "Eliminar servicio", confirma en SweetAlert ("Sí, eliminar") y el servicio sale del catálogo; las solicitudes ya enviadas se conservan.

### process-users-modal: Modal de participantes del proceso
- **Módulo:** processes | **Prioridad:** P3 | **Ruta:** `/process_detail/:id` | **E2E:** ✅ (`process-detail-actions.spec.js`)
- **Descripción:** "Ver usuarios" abre el modal de participantes del proceso con los clientes asociados (avatar/iniciales + nombre) y estado vacío si no hay usuarios.

### sign-download-signatures-pdf: Descargar certificado de firmas (PDF)
- **Módulo:** signatures | **Prioridad:** P3 | **Ruta:** `/dynamic_document_dashboard/signed-documents` | **E2E:** ✅ (`signed-documents-flow.spec.js`)
- **Descripción:** Sobre un documento completamente firmado, la acción "Descargar Doc. Formalizado" del menú de la tarjeta descarga el certificado de firmas (`generate-signatures-pdf`). Requiere estado FullySigned y ≥1 firma registrada.

### org-corporate-dashboard-stats: KPIs del dashboard corporativo
- **Módulo:** organizations | **Prioridad:** P2 | **Ruta:** dashboard corporativo | **E2E:** ✅ (`organizations-corporate-invite-member-stats.spec.js`)
- **Descripción:** KPIs del dashboard del cliente corporativo (organizaciones, miembros, invitaciones pendientes) servidos por `organizations/stats/`; se actualizan tras invitar un miembro.

### directory-navigate-to-process: Navegar del directorio a procesos
- **Módulo:** directory | **Prioridad:** P4 | **Ruta:** `/directory_list` | **E2E:** ✅ (`directory.spec.js`)
- **Descripción:** Desde el modal de detalle de usuario, "Ver proceso" navega al detalle y "Ver todos en Procesos" al listado filtrado por el usuario.
- **Outcomes:** success, display. Cierre y navegación tienen nombres accesibles
  y objetivos físicos de 44×44 px, incluyendo compact y portrait con zoom global.

### secop-list-error-retry: Reintentar carga del listado SECOP
- **Módulo:** secop | **Prioridad:** P4 | **Ruta:** `/secop` | **E2E:** ✅ (`secop-list-error-retry.spec.js`)
- **Descripción:** Ante un fallo de carga del listado, se muestra el estado de error con "Reintentar"; el botón recarga y renderiza la tabla.

**Clasificados como no-flujo (auditoría 2026-07-22):** endpoints huérfanos sin consumidor de componente (candidatos a dead-code o UI pendiente): CRUD de legal-updates (store sin invocador), `corporate-requests/corporate/dashboard-stats/`, `organizations/<id>/public/`, y los pares `recent-documents/processes` (se escriben desde las vistas pero ningún widget los muestra). La plantilla Word de membrete SÍ tiene UI y quedó cubierta como ramificación de `docs-letterhead` (upload real en `docs-letterhead-flow.spec.js`). 20 endpoints no-UI (permisos granulares superseded, firmas legacy, webhook Wompi).

---

## Pasada de profundidad — Auditoría anti-synthetic 2026-07-23

Reescritura de **47 specs (135 sitios sintéticos → 0)**: asserts condicionales (`if (visible)`), `.catch(() => false)` y asserts sobre `#app` reemplazados por interacciones conducidas con outcomes observables. Hallazgos estructurales corregidos: 10+ tests apuntaban a **rutas fantasma** (`/process`, `/organizations`, `/subscription`, `/privacy-policy`, `/terms-of-use` → catch-all a sign_in); labels/estados/selectores inexistentes ("InProgress", "Nueva Solicitud", `/sign-in`); fixtures con shapes inválidos. Dead-code adicional confirmado: **no existe UI de gestión de suscripción** (cancel/reactivate/update-payment sin componente) ni CRUD de legal-updates. La pestaña Carpetas no tiene buscador (test infalsificable reemplazado). Variantes añadidas: rol basic en SECOP (overlays de upgrade) y mobile en el centro de notificaciones.

---

## Auditoría "interacción real" — 2026-07-23 (ronda 6)

Segunda pasada de profundidad, con criterio distinto al anti-synthetic de R5: **¿el test ejecuta la acción del usuario, o fabrica el estado final con mocks y aserta lo que él mismo cocinó?** Medida con `scripts/audit_e2e_interactions.py` (persistido, sale con código 1 mientras queden sospechosos).

| Categoría | Antes | Después |
|---|---|---|
| Interactivos (conducen la acción) | 394 | **544** |
| Guards / empty states / restricciones (legítimos) | 86 | 75 |
| Marcados `// audit: load-only flow` | 0 | 11 |
| **Solo renderizan un mock (sospechosos)** | **159** | **0** |

Los 159 se reescribieron para ejecutar la acción y asertar la transición. Validación del criterio "puede fallar" por mutación: quitar `pageSize` del watcher de `SecopList.vue` pone rojo el test de tamaño de página; restaurarlo lo devuelve a verde. El criterio quedó escrito en `docs/TESTING_QUALITY_STANDARDS.md` § "Drive the Interaction, Assert the Transition" para specs futuros.

**Bugs y código muerto que destapó la reescritura:**
- 🐛 **Botón de sincronización SECOP inerte**: `SyncStatus.vue` no declara `defineEmits`, así que `@trigger-sync` nunca dispara y `POST secop/sync/trigger/` jamás se envía — el usuario ve un spinner de 180 s y no pasa nada. Pendiente de decisión de producto (arreglarlo lanzaría sincronizaciones reales contra Socrata).
- 🐛 **Botón de limpiar firma sin nombre accesible** (solo-icono, sin `aria-label`): su test estaba muerto porque el locator nunca hacía match. Hueco de accesibilidad real.
- **`document-key-fields.spec.js` probaba un campo inexistente** (`is_key` no aparece en `src/`): el spec entero verificaba una funcionalidad fantasma; reescrito contra `summary_field`.
- Navegación falsificada con `page.evaluate(router.push(...))` en lugar de usar la UI.
- Rutas sin punto de entrada: `/dynamic_document_dashboard/signed-documents`, `/subscriptions`, `/legal_requests` (el sidebar filtra ambos ítems), `/no_connection` (nada escucha `navigator.onLine`).
- Ramas muertas: sub-secciones de `GuideNavigation.vue` que ningún módulo define; SweetAlert "Firmantes requeridos" inalcanzable porque el botón ya se deshabilita; `deleteOrganization` en el store sin componente que lo llame.
- `hasMore` con page size hardcodeado a 20 en `LegalRequestsList.vue`.

## Reconciliación mapa ↔ flow-definitions.json — 2026-07-24 (v1.12.1)

Auditoría estática de flujos (`scripts/flow_coverage_audit.py`) sobre el registro v1.12.0.
Fuente autoritativa: **`frontend/e2e/flow-definitions.json` (164 flujos)** — es el inventario que
consume el audit y es superconjunto exacto del mapa (0 flujos huérfanos solo-en-mapa).

**Drift de conteo resuelto (168 headings brutos → 164 conformes únicos = 164 en JSON):**
- **15 duplicados eliminados.** Los 15 flujos SECOP estaban definidos dos veces: bloque detallado en
  la sección *Flujos — Lawyer* (canónico, con Pasos/Ramificaciones) + copia abreviada en la sección
  dedicada *Flujos — SECOP*. Se consolidó dejando el bloque rico como único; la sección dedicada
  quedó como puntero + tabla de estado (sin headings `###` duplicados).
- **11 headings normalizados.** Los 11 flujos añadidos el 2026-07-22 SÍ estaban en el JSON, pero en
  el mapa se documentaron con headings no contables (5 `notification-*` agrupados en un solo `###`
  separado por `/`; 6 ids sin sufijo `: <desc>`), por lo que el conteo de headings del mapa (153
  únicos) quedaba por debajo del JSON (164). Se reescribieron como `### <id>: <desc>`.
- **Resultado:** 164 headings únicos conformes ≡ 164 flujos del JSON (coincidencia de conjunto exacta).
- **JSON intacto:** no se tocó `flow-definitions.json` (ya era autoritativo y todos sus flujos están
  referenciados por tests reales). La reconciliación fue solo sobre el mapa + esta nota.

**Estado de cobertura real (audit 2026-07-24): 140 covered · 20 junk-only · 4 missing.**

- **junk-only (20)** — reportan verde pero **ningún test los ejercita** (descalificados por
  `no_user_interaction` / `flow_tag_mismatch`); reescribir su spec es la prioridad #1:
  - P1: `auth-login-google`, `auth-login-outlook`, `service-fill-form`, `service-submit-request`
  - P2: `auth-idle-logout`, `auth-router-guards`, `legal-files-auto-redirect`, `process-case-file-upload`,
    `process-edit`, `profile-complete`, `secop-create-alert`, `service-admin-edit`, `service-save-draft`
  - P3: `secop-apply-saved-view`, `secop-keyword-tags`, `secop-save-view`, `secop-saved-view-favorites`,
    `secop-sync-status`, `service-admin-form-validation`
  - P4: `misc-offline`
- **missing (4)** — cero evidencia: `minutas-columns`, `minutas-shared-visibility` (documents);
  `process-alert-configure`, `process-alerts` (processes). Los dos últimos figuraban como "cerrados
  16-07" en el resumen previo, pero el audit no encuentra tests que los ejerciten → revisar si el spec
  perdió su tag `@flow:<id>` o fue renombrado.

**Deuda de esquema (hallazgo de metodología):** los 164 flujos aún declaran el campo antiguo
`expectedSpecs`; **0 declaran `outcomes`**. El audit corre sobre el fallback `["success"]`, así que hoy
solo verifica la clase `success` de cada flujo — por eso los 18 módulos aparecen como "declara solo
success" y no hay señal de cobertura para `error` / `failure` / `display`. Migrar a `outcomes` (declarar
las clases por flujo) es el siguiente paso para endurecer el gate; no se hizo aquí para no inventar
requisitos no revisados.

---

---

## Actualización de cobertura — 2026-08-21

La auditoría actual revisó 205 specs y 650 tests contra los 164 flujos:
128 `covered`, 32 `partial`, 0 `junk-only`, 1 `missing` (`docs-summary`) y
3 `exempt`. Ya declaran outcomes 161/164 flujos. En SECOP,
`secop-sync-status` cubre `display` + `failure` y `secop-trigger-sync` cubre
`success`; ambos tests ejecutan la interacción real. La única brecha SECOP es
el outcome `display` de `secop-list-error-retry` (el outcome `failure` está
cubierto).

Los módulos `directory`, `notifications`, `schedule` y `user-guide` aún no
declaran outcomes `error`/`failure`; corresponden al backlog general y no al
flujo SECOP modificado en esta sesión.

## Validación de mapa — 2026-09-27

La optimización de `organizations/stats/`, la actualización corporativa de solicitudes
y la exportación SECOP conserva rutas, permisos, filtros, campos de respuesta y
estados visibles. No agrega ni retira flujos; se mantienen
`org-corporate-dashboard-stats` (display), `org-corporate-requests` /
`org-cross-request-flow` (success) y `secop-export-excel` (success).
La auditoría de cobertura de esta ronda vive en el reporte QA del toolkit.

## Validación de mapa — ronda 7 (2026-09-27)

El listado legal conserva filtros, roles y campos: siguen `legal-list-client` y
`legal-management-lawyer` (display). El cambio de estado conserva validación,
permisos y respuesta: sigue `legal-status-update` (success, failure).
Las publicaciones privadas y públicas conservan permisos, filtros, orden y autor:
siguen `org-posts-management` (success, failure), `org-posts-visibility` (success)
y `org-client-view` (display, error). No se agregan ni retiran flujos u outcomes.

**Documento actualizado:** September 27, 2026
**Versión:** 1.13.4
**Estado:** Registro revisado para esta ronda backend, sin cambios de flujos ni outcomes.
