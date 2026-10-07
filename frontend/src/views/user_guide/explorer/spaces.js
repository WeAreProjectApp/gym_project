const audience = {
  all: 'Todos los usuarios', lawyer: 'Abogados y administración', admin: 'Administración',
  intranet: 'Abogados internos de G&M y administración', organization: 'Clientes, corporativos y básicos',
  corporate: 'Clientes corporativos', paid: 'Cuenta con plan habilitado', appointment: 'Usuarios sin rol administrativo',
};

function feature(id, label, summary, options = {}) {
  return { id, kind: 'feature', label, summary, value: summary, icon: 'feature',
    ...options, audience: audience[options.access || 'all'] };
}

function moduleNode(id, label, summary, value, icon, routeName, guide, children, options = {}) {
  const defaults = { access: 'all', ...options };
  const destination = routeName ? { name: routeName } : null;
  return { id, kind: 'module', label, summary, value, icon, destination, guide, ...defaults,
    audience: audience[defaults.access],
    children: children.map(([key, title, text, settings = {}]) => feature(`${id}-${key}`, title, text, {
      ...defaults, destination, guide: guide ? [guide[0], key] : null, ...settings,
    })),
  };
}

const space = (id, label, summary, value, icon, children, relations = []) => ({
  id, kind: 'space', label, summary, value, icon, audience: audience.all, children, relations,
});

export const legalSpace = space('legal', 'Trabajo jurídico',
  'Procesos, documentos y contratación pública en un mismo ecosistema.',
  'Organiza la información jurídica desde la consulta hasta la formalización.', 'legal', [
    moduleNode('processes', 'Procesos', 'Consulta y gestión de procesos judiciales.',
      'Mantén el expediente y sus etapas a mano.', 'processes', 'process_list', ['processes'], [
        ['filters-search', 'Consulta y búsqueda', 'Encuentra procesos por sus datos y consulta los asignados a tu cuenta.'],
        ['create-process', 'Radicación y edición', 'Registra un proceso o selecciona uno existente para actualizar sus datos.', { access: 'lawyer' }],
        ['process-stages-management', 'Etapas y alertas', 'Registra etapas, fechas y destinatarios de alertas desde el formulario del proceso.', { access: 'lawyer' }],
        ['case-file-upload', 'Expediente digital', 'Consulta los archivos del proceso; los abogados gestionan sus adjuntos.'],
        ['process-historical', 'Histórico y detalle', 'Selecciona un proceso para consultar sus partes, evolución e información judicial.'],
      ]),
    moduleNode('documents', 'Archivos Jurídicos', 'Minutas, contratos, documentos y firma electrónica.',
      'Transforma una minuta en un documento organizado, formalizado y trazable.', 'documents', 'dynamic_document_dashboard', ['documents'], [
        ['lawyer-tabs', 'Minutas y editor', 'Crea y publica minutas compartidas entre abogados; configura variables y permisos.', { access: 'lawyer' }],
        ['client-use-document', 'Diligenciar documentos', 'Selecciona una minuta disponible y completa sus campos para crear tu documento.'],
        ['electronic-signature', 'Formalización y firmas', 'Solicita firmas, revisa pendientes y consulta documentos formalizados o archivados.'],
        ['folders', 'Carpetas y etiquetas', 'Organiza archivos y encuentra documentos por carpeta o etiqueta.'],
        ['document-relationships', 'Documentos relacionados', 'Vincula documentos y consulta sus asociaciones desde las acciones de cada archivo.', { access: 'paid' }],
        ['contract-execution', 'Ejecución del contrato', 'Consulta cuentas de cobro y registra el seguimiento de la ejecución desde el documento.'],
        ['download-export', 'Descargas y correo', 'Descarga documentos en PDF o Word y utiliza la opción de envío por correo.'],
        ['letterhead', 'Membretes', 'Configura un membrete global o selecciona uno para un documento desde sus acciones.', { access: 'paid' }],
        ['guided-tour', 'Guía interactiva', 'Abre la guía del módulo para conocer sus pestañas y controles.'],
      ]),
    moduleNode('secop', 'Contratación Estatal', 'Explora oportunidades de contratación pública en SECOP.',
      'Encuentra procesos de interés y organiza su seguimiento.', 'secop', 'secop_list', ['secop'], [
        ['secop-process-detail', 'Consulta de procesos públicos', 'Abre un proceso para ver entidad, presupuesto, fechas y enlace a SECOP.'],
        ['secop-search-filters', 'Búsqueda y filtros', 'Combina palabras clave, ubicación, presupuesto y códigos UNSPSC.', { access: 'paid' }],
        ['secop-classifications', 'Clasificaciones', 'Marca procesos de interés y conserva tus notas de seguimiento.'],
        ['secop-alerts', 'Alertas personalizadas', 'Define criterios y frecuencia para recibir avisos de nuevas oportunidades.', { access: 'paid' }],
        ['secop-saved-views', 'Vistas guardadas', 'Guarda y reutiliza combinaciones de filtros.', { access: 'paid' }],
        ['secop-export-sync', 'Exportación', 'Exporta los resultados de contratación pública a Excel.'],
        ['sync', 'Sincronización', 'Actualiza manualmente los procesos desde la fuente pública de SECOP.', { access: 'lawyer', guide: ['secop', 'secop-export-sync'] }],
      ]),
  ]);

export const attentionSpace = space('attention', 'Atención y organizaciones',
  'Servicios, consultas, citas y colaboración con organizaciones.',
  'Lleva cada necesidad desde su solicitud hasta la atención y el seguimiento.', 'attention', [
    moduleNode('services', 'Servicios y Solicitudes', 'Catálogo de servicios y seguimiento de tus trámites.',
      'Presenta solicitudes con información y adjuntos organizados.', 'services', 'services_hub', ['services'], [
        ['services-catalog', 'Catálogo', 'Selecciona un servicio para conocer sus requisitos e iniciar el formulario.'],
        ['services-dynamic-form', 'Formularios por etapas', 'Completa los campos y adjuntos requeridos de cada etapa del servicio.'],
        ['services-drafts', 'Borradores', 'Guarda el avance y retoma la solicitud desde Mis Solicitudes.'],
        ['services-submission', 'Envío y radicado', 'Envía la solicitud completa para obtener su número de radicado.'],
        ['services-my-requests', 'Mis Solicitudes', 'Consulta estados, respuestas, adjuntos y PDF de tus solicitudes.', { destination: { name: 'services_hub', query: { tab: 'my-requests' } } }],
      ]),
    moduleNode('inbox', 'Bandeja de Solicitudes', 'Atención de solicitudes recibidas por el equipo jurídico.',
      'Centraliza las respuestas y el estado de cada trámite.', 'inbox', 'service_requests_inbox', ['services', 'services-inbox'], [
        ['review', 'Revisión y filtros', 'Encuentra solicitudes y abre su detalle para revisar lo radicado.', { guide: ['services', 'services-inbox'] }],
        ['reply', 'Respuestas y estados', 'Responde con adjuntos y actualiza el estado desde el detalle de una solicitud.', { guide: ['services', 'services-status-lifecycle'] }],
      ], { access: 'lawyer' }),
    moduleNode('requests', 'Solicitudes Legales', 'Consultas jurídicas con conversación y documentos adjuntos.',
      'Conserva la consulta y sus respuestas en un solo hilo.', 'requests', 'legal_requests_list', ['requests'], [
        ['create-request', 'Crear una consulta', 'Describe tu necesidad y adjunta los documentos para el equipo jurídico.'],
        ['request-thread', 'Conversación y seguimiento', 'Selecciona una solicitud para consultar respuestas y continuar la conversación.'],
        ['manage-requests', 'Gestión jurídica', 'Revisa consultas recibidas, responde y actualiza sus estados.', { access: 'lawyer' }],
      ]),
    moduleNode('organizations', 'Organizaciones', 'Miembros, publicaciones y solicitudes de organizaciones.',
      'Reúne la comunicación entre clientes y su organización.', 'organizations', 'organizations_dashboard', ['organizations'], [
        ['corporate-dashboard', 'Administrar organizaciones', 'Crea organizaciones, edita su perfil y consulta estadísticas.', { access: 'corporate' }],
        ['invite-members', 'Invitaciones y miembros', 'Invita personas y administra la membresía desde tu organización.', { access: 'corporate' }],
        ['client-invitations', 'Mis organizaciones', 'Responde invitaciones y consulta las organizaciones a las que perteneces.'],
        ['posts-management', 'Publicaciones', 'Publica novedades y enlaces para los miembros de tu organización.', { access: 'corporate' }],
        ['client-requests', 'Solicitudes corporativas', 'Envía solicitudes dentro de una organización y consulta sus respuestas.'],
        ['corporate-requests', 'Atención corporativa', 'Revisa solicitudes recibidas, responde y actualiza el seguimiento.', { access: 'corporate' }],
      ], { access: 'organization' }),
  ], [{ from: 'services', to: 'inbox', label: 'Las solicitudes radicadas llegan a la bandeja' }]);

export const collaborationSpace = space('collaboration', 'Seguimiento y colaboración',
  'Panorama diario, personas, novedades y avisos de la plataforma.',
  'Identifica lo que necesita atención y encuentra el contexto para actuar.', 'collaboration', [
    moduleNode('dashboard', 'Inicio', 'Resumen de tu actividad y accesos recientes.',
      'Retoma el trabajo desde los elementos y servicios relevantes.', 'dashboard', 'dashboard', ['dashboard'], [
        ['activity', 'Actividad y recientes', 'Consulta la actividad, procesos y documentos recientes desde Inicio.', { guide: ['dashboard'] }],
        ['reports', 'Reportes', 'Abre los reportes disponibles en Inicio para consultar o exportar información.', { access: 'lawyer', guide: ['dashboard'] }],
        ['lawyer-metrics', 'Métricas de abogados', 'Consulta el resumen de abogados activos y archivados desde Inicio.', { access: 'admin', guide: ['admin_staff', 'admin-data-reassignment'] }],
      ]),
    moduleNode('directory', 'Directorio', 'Consulta de clientes y usuarios del sistema.',
      'Encuentra los datos de contacto y el contexto del cliente.', 'directory', 'directory_list', ['directory'], [
        ['user-detail-modal', 'Detalle de usuario', 'Selecciona una persona para consultar su información y accesos asociados.'],
      ], { access: 'lawyer' }),
    moduleNode('notifications', 'Notificaciones', 'Avisos de firmas, procesos y solicitudes.',
      'Prioriza pendientes y abre el elemento relacionado con cada aviso.', 'notifications', 'notifications', null, [
        ['read', 'Lectura y filtros', 'Consulta notificaciones y marca avisos como leídos.'],
        ['organize', 'Posponer y archivar', 'Pospone avisos para después o archívalos cuando ya no requieran atención.'],
        ['links', 'Elementos relacionados', 'Abre el proceso, documento o solicitud desde su notificación.'],
      ]),
    moduleNode('updates', 'Actualizaciones jurídicas', 'Novedades jurídicas disponibles en Inicio.',
      'Mantente al tanto de información publicada por el equipo.', 'updates', 'dashboard', null, [
        ['read', 'Consultar novedades', 'Desde Inicio, consulta las actualizaciones y sus enlaces.'],
        ['publish', 'Administrar novedades', 'El equipo autorizado gestiona las actualizaciones desde el panel administrativo.', { access: 'admin', destination: null }],
      ]),
    moduleNode('intranet', 'Intranet G&M', 'Información y recursos internos de la firma.',
      'Consulta procedimientos y radica informes desde el portal interno.', 'intranet', 'intranet_g_y_m', ['intranet'], [
        ['profile', 'Perfil de la firma', 'Consulta la presentación y la información interna de G&M.'],
        ['procedures', 'Procedimientos y organigrama', 'Consulta los documentos internos y la estructura de la firma.'],
        ['submit-report', 'Radicar informe', 'Abre el formulario interno para presentar tu informe y sus archivos.'],
      ], { access: 'intranet' }),
  ], [{ from: 'notifications', to: 'dashboard', label: 'Inicio resume los avisos y la actividad' }]);

export const accountSpace = space('account', 'Cuenta y administración',
  'Acceso, perfil, suscripción, administración y ayuda.',
  'Configura tu cuenta y conoce las herramientas que sostienen la operación.', 'account', [
    moduleNode('authentication', 'Autenticación y Cuenta', 'Ingreso, registro y recuperación de acceso.',
      'Accede con tu cuenta y mantén tus datos actualizados.', 'authentication', null, ['authentication'], [
        ['login-email', 'Ingreso a la plataforma', 'Inicia sesión con email, Google o Microsoft desde la pantalla de acceso.'],
        ['register', 'Registro y recuperación', 'Crea tu cuenta o utiliza Recuperar contraseña desde la pantalla de acceso.'],
        ['profile', 'Perfil', 'Abre tu avatar en el menú principal y selecciona Perfil para editar tus datos.'],
        ['user-signature', 'Firma personal', 'En Perfil, selecciona Firma electrónica para dibujar o cargar tu firma.'],
        ['idle-logout', 'Seguridad de sesión', 'Cierra sesión desde tu menú; el sistema también la cierra por inactividad.'],
      ]),
    moduleNode('subscriptions', 'Suscripciones y Pagos', 'Planes de acceso y contratación mediante Wompi.',
      'Compara las opciones de acceso y completa el pago de tu plan.', 'subscriptions', 'subscriptions', ['subscriptions'], [
        ['view-plans', 'Planes y contratación', 'Compara planes y selecciona uno para continuar al pago.'],
        ['checkout', 'Pago y activación', 'Selecciona un plan y continúa al formulario de pago para activar la suscripción.'],
      ]),
    moduleNode('administration', 'Administración del Sistema', 'Herramientas reservadas a administración.',
      'Mantén el catálogo y las asignaciones del equipo organizados.', 'administration', null, ['admin_staff'], [
        ['admin-services-catalog', 'Administrar Servicios', 'Crea servicios y configura sus etapas, campos y requisitos.', { destination: { name: 'services_admin' } }],
        ['admin-data-reassignment', 'Reasignación de Datos', 'Revisa y reasigna procesos y documentos de un abogado desde la herramienta administrativa.', { destination: { name: 'data_reassignment' } }],
        ['admin-django-panel', 'Administración avanzada', 'La administración autorizada dispone del panel administrativo para la gestión interna.'],
      ], { access: 'admin' }),
    moduleNode('help', 'Ayuda y políticas', 'Manual, soporte y condiciones de uso.',
      'Encuentra instrucciones y conoce las condiciones de la plataforma.', 'help', null, null, [
        ['manual', 'Manual de Usuario', 'Usa la navegación del manual para consultar instrucciones según tu rol.', { guide: ['dashboard'] }],
        ['support', 'Soporte', 'Utiliza Contactar por WhatsApp en el menú del manual para solicitar ayuda.'],
        ['privacy', 'Privacidad', 'Consulta la política de privacidad de la plataforma.', { destination: { name: 'privacy_policy' } }],
        ['terms', 'Términos de uso', 'Consulta las condiciones de uso de la plataforma.', { destination: { name: 'terms_of_use' } }],
        ['offline', 'Instalación y conexión', 'Puedes instalar la aplicación como PWA; sin conexión, la pantalla de aviso te permite reintentar.'],
      ]),
  ]);
