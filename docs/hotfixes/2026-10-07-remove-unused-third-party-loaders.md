# Hotfix 2026-10-07 — se retiran los cargadores de Wompi y Calendly que no se usan

**Rama:** `fix/07102026-gym-remove-unused-third-party-loaders` (base `master` en `7953db7ce4a7`)
**Decisión:** del operador, el 2026-10-07: «hoy en día la aplicación está funcionando y no usa Wompi» y
tampoco usa Calendly. Para los planes pagos eligió mostrar «Próximamente».

## Por qué

El 2026-10-07 el deploy de `7953db7ce4a7` a producción completó su fase de COMMIT: el código, las
dependencias y el build nuevos quedaron sirviendo, con health 200. Lo que falló fue el cierre: el
motor de integridad del VPS escanea los archivos nuevos antes de aceptar un deploy, y su regla YARA
`JSB_External_Loader` encontró 4 coincidencias.

| Archivo del bundle (en `static/frontend` y en `staticfiles`) | Qué carga |
|---|---|
| `Checkout-<hash>.js` | el SDK de Wompi (`wompijs.wompi.com`) |
| `ScheduleAppointment-<hash>.js` | el widget de Calendly (`assets.calendly.com`) |

La regla marca el código que crea un `<script>` con `document.createElement("script")` y le pone un
`src` absoluto a un host externo, porque es la forma típica de inyectar un script ajeno. Esos hosts
no están en la lista de hosts permitidos del motor, así que el cierre rechazó el deploy. El código ya
existía antes; lo que cambió fue el nombre de los archivos del bundle, y por eso entraron al escaneo
de lo nuevo.

Ninguna de las dos funciones se usa hoy. Este hotfix las retira para que el bundle no tenga
cargadores externos y el próximo deploy pueda cerrar.

## Qué se quita

**Calendly («Agendar Cita»):**
- la ruta `/schedule_appointment` y la vista `src/views/schedule_appointment/ScheduleAppointment.vue`;
- el ítem «Agendar Cita» del menú lateral (`SlideBar.vue`) y su filtro para administradores;
- la acción rápida «Agendar Cita» del dashboard de clientes (`QuickActionButtons.vue`);
- el módulo «Agendar Cita» del Manual de Usuario (`stores/user_guide/`, `views/user_guide/explorer/`).

**Wompi, dentro de `src/views/subscriptions/Checkout.vue`:**
- los cargadores `loadWompiScript` (`checkout.wompi.co/widget.js`) y `loadWompiJs` (`wompijs.wompi.com`);
- `tokenizeCard`, `clearSavedCard` y `openWompiWidget`;
- el formulario de tarjeta;
- la carga de la llave pública y del script al montar la vista.

`handleSubscribe` conserva el plan gratuito sin cambios. Para un plan pago, sólo muestra «Próximamente»
y nunca crea una suscripción.

**Tests y registro de flujos:**
- se borran los tests unitarios y E2E del agendamiento y del formulario de tarjeta;
- se ajustan los que navegaban por esas pantallas;
- se borran `e2e/helpers/wompiStubs.js` y `e2e/helpers/scheduleAppointmentMocks.js`;
- en `flow-definitions.json` (v1.13.7), `schedule-appointment` sale y `subscriptions-checkout-paid`
  pasa a un único outcome `display`;
- se actualizan `flow-tags.js`, `docs/USER_FLOW_MAP.md` y `docs/FUNCTIONAL_GUIDE_BY_ROLE.md`.

## Qué ven los usuarios

- **En `/subscriptions`:** el Plan Básico sigue con «Elegir plan». Cliente y Corporativo muestran el
  botón «Próximamente», deshabilitado.
- **En el checkout de un plan pago:** quien llega por un enlace viejo ve el resumen del plan y, en
  lugar del formulario de tarjeta, «El pago en línea no está disponible por ahora». El botón dice
  «Próximamente» y está deshabilitado.
- **El plan gratuito** se activa igual que antes.
- **En el menú, el dashboard y el Manual de Usuario** ya no aparece «Agendar Cita». Quien entre a
  `/schedule_appointment` cae en la ruta comodín, como cualquier ruta inexistente.

## Qué no cambia

- **El backend:** los endpoints de suscripciones, `wompi-config`, `generate-signature`, el webhook y
  las tareas siguen como están.
- **El store `src/stores/subscriptions/index.js`.**
- **`package.json` y el lockfile.**
- **El texto del Manual de Usuario sobre suscripciones** sigue describiendo el pago con tarjeta: vuelve
  a ser cierto al reactivar.

## Cómo reactivar

1. **Primero el motor de integridad.** Los hosts de los cargadores tienen que estar en la lista de
   hosts permitidos del motor de cada VPS (`/etc/vps-integrity/allowed-hosts.json`). Esa lista se
   versiona en `vps-ops-toolkit` y la instala la generación del motor. El cambio ya existe en el
   toolkit, commit `32a9547b` («fix(integrity): allowlist the Wompi JS SDK and Calendly widget
   hosts», que suma `wompijs.wompi.com` y `assets.calendly.com`). Hay que instalar esa generación
   **antes** de desplegar la reactivación; si no, el cierre del deploy vuelve a rechazarla.
2. **Después el código.** Revertir el commit de este hotfix (`git revert <sha>`) en una rama de sesión,
   con su PR y CI verde, y desplegarlo con el flujo normal.
3. **Al desplegar,** verificar que el cierre del deploy firma: que no quede ninguna coincidencia
   `JSB_External_Loader` sin permitir.
