import {
  InboxArrowDownIcon,
  BuildingOfficeIcon,
  ScaleIcon,
  UserCircleIcon,
  CreditCardIcon,
} from '@heroicons/vue/24/outline';

export const requestsContent = {
  name: 'Solicitudes Legales',
  icon: InboxArrowDownIcon,
  description: 'Gestión de solicitudes y consultas legales',
  overview: `
    <p>El módulo de Solicitudes permite a los clientes solicitar servicios legales y a los abogados gestionar estas solicitudes.</p>
    <p class="mt-2">Los clientes pueden crear solicitudes que son gestionadas por abogados con un sistema de thread de conversación.</p>
  `,
  sections: [
    {
      id: 'create-request',
      name: 'Crear Solicitud (Clientes)',
      description: 'Enviar una nueva consulta legal',
      roles: ['client', 'corporate_client', 'basic'],
      content: `
        <p>Los clientes pueden crear solicitudes legales para consultas, asesorías o servicios.</p>
      `,
      features: [
        'Formulario completo con tipo y disciplina',
        'Descripción detallada de la solicitud',
        'Adjuntar múltiples archivos (PDF, DOC, DOCX, JPG, PNG)',
        'Número de solicitud automático (SOL-YYYY-NNN)',
        'Notificación automática al abogado',
        'Estados: Pendiente, En Revisión, Respondida, Cerrada'
      ],
      steps: [
        {
          title: 'Accede a Solicitudes',
          description: 'Click en "Solicitudes" en el menú lateral'
        },
        {
          title: 'Click en "Nueva Solicitud"',
          description: 'Botón en la parte superior de la lista'
        },
        {
          title: 'Selecciona Tipo',
          description: 'Elige el tipo de solicitud (Consulta, Asesoría, Revisión, Representación)'
        },
        {
          title: 'Selecciona Disciplina',
          description: 'Elige la disciplina legal (Civil, Penal, Laboral, Familia, etc.)'
        },
        {
          title: 'Describe tu solicitud',
          description: 'Explica detalladamente qué necesitas (mínimo 50 caracteres)'
        },
        {
          title: 'Adjunta archivos',
          description: 'Sube documentos relacionados si los tienes'
        },
        {
          title: 'Envía la solicitud',
          description: 'Recibirás un número de solicitud para seguimiento'
        }
      ],
      tips: [
        'Sé específico en la descripción para recibir mejor ayuda',
        'Adjunta todos los documentos relevantes desde el inicio',
        'Guarda el número de solicitud para futuras consultas'
      ]
    },
    {
      id: 'manage-requests',
      name: 'Gestionar Solicitudes (Abogados)',
      description: 'Administrar solicitudes recibidas',
      roles: ['lawyer'],
      content: `
        <p>Los abogados pueden ver, responder y gestionar todas las solicitudes recibidas de clientes.</p>
      `,
      features: [
        'Ver todas las solicitudes del sistema',
        'Filtrar por estado (Pendiente, En Revisión, Respondida, Cerrada)',
        'Filtrar por rango de fechas',
        'Cambiar estado de solicitud',
        'Thread de conversación completo',
        'Responder con mensajes',
        'Eliminar solicitudes',
        'Descargar archivos adjuntos',
        'Ver información completa del cliente'
      ],
      steps: [
        {
          title: 'Accede a Gestión de Solicitudes',
          description: 'Click en "Gestión de Solicitudes" en el menú'
        },
        {
          title: 'Revisa solicitudes pendientes',
          description: 'Filtra por estado "Pendiente" para ver nuevas solicitudes'
        },
        {
          title: 'Abre el detalle',
          description: 'Click en una solicitud para ver información completa'
        },
        {
          title: 'Cambia el estado',
          description: 'Marca como "En Revisión" cuando empieces a trabajar'
        },
        {
          title: 'Responde al cliente',
          description: 'Usa el formulario de respuesta para comunicarte'
        },
        {
          title: 'Marca como Respondida',
          description: 'Cambia el estado cuando hayas dado respuesta'
        },
        {
          title: 'Cierra la solicitud',
          description: 'Marca como "Cerrada" cuando el caso esté resuelto'
        }
      ],
      tips: [
        'Responde rápidamente para mejor servicio al cliente',
        'Usa el thread de conversación para mantener historial',
        'Descarga los archivos adjuntos antes de responder'
      ]
    },
    {
      id: 'request-thread',
      name: 'Thread de Conversación',
      description: 'Sistema de mensajería bidireccional',
      roles: ['lawyer', 'client', 'corporate_client', 'basic'],
      content: `
        <p>El thread permite mantener una conversación organizada entre cliente y abogado sobre la solicitud.</p>
      `,
      features: [
        'Mensajes ordenados cronológicamente',
        'Indicador de quién escribió (Cliente/Abogado)',
        'Fecha y hora de cada mensaje',
        'Agregar archivos adicionales',
        'Historial completo de la conversación'
      ]
    }
  ]
};

export const organizationsContent = {
  name: 'Organizaciones',
  icon: BuildingOfficeIcon,
  description: 'Gestión de organizaciones empresariales',
  overview: `
    <p>Módulo para clientes corporativos para gestionar sus organizaciones, miembros y solicitudes corporativas.</p>
  `,
  sections: [
    {
      id: 'corporate-dashboard',
      name: 'Dashboard Corporativo',
      description: 'Vista principal para clientes corporativos',
      roles: ['corporate_client'],
      content: `
        <p>Los clientes corporativos pueden crear y gestionar organizaciones completas con múltiples miembros.</p>
      `,
      features: [
        'Crear organización con nombre y descripción',
        'Subir <strong>logo</strong> (avatar circular en cards) y <strong>portada</strong> (banner del header) — formatos JPG/PNG',
        'Gestionar miembros del equipo',
        'Enviar invitaciones por email',
        'Ver invitaciones pendientes',
        'Crear solicitudes corporativas',
        'Publicar anuncios internos',
        'Ver estadísticas de la organización (organizaciones, miembros, invitaciones, solicitudes)'
      ],
      steps: [
        {
          title: 'Crear Organización',
          description: 'Click en "Nueva Organización" y completa el formulario'
        },
        {
          title: 'Personaliza',
          description: 'Sube logo y portada, agrega descripción'
        },
        {
          title: 'Invita Miembros',
          description: 'Envía invitaciones por email a tu equipo'
        },
        {
          title: 'Gestiona Solicitudes',
          description: 'Crea solicitudes en nombre de la organización'
        },
        {
          title: 'Publica Anuncios',
          description: 'Comparte información con todos los miembros'
        }
      ]
    },
    {
      id: 'org-corporate-stats',
      name: 'Estadísticas del Dashboard',
      description: 'Indicadores clave en el header del dashboard corporativo',
      roles: ['corporate_client'],
      content: `
        <p>El header del dashboard muestra cuatro tarjetas con el estado actual del ecosistema corporativo. Sirven como termómetro semanal para detectar invitaciones sin responder o solicitudes acumuladas.</p>
      `,
      features: [
        '<strong>Organizaciones</strong>: total de organizaciones que administras',
        '<strong>Miembros</strong>: agregado de miembros entre todas tus organizaciones',
        '<strong>Invitaciones pendientes</strong>: invitaciones enviadas que aún no han sido aceptadas o rechazadas',
        '<strong>Solicitudes recibidas</strong>: solicitudes corporativas creadas por miembros'
      ],
      tips: [
        'Si "Invitaciones pendientes" crece sin parar, revisa si los emails están llegando o si necesitas reenviarlas',
        'Un alto número de "Solicitudes recibidas" sin abrir indica que conviene priorizar la bandeja corporativa'
      ]
    },
    {
      id: 'org-edit-organization',
      name: 'Editar y Desactivar Organización',
      description: 'Actualizar datos o pausar temporalmente una organización',
      roles: ['corporate_client'],
      content: `
        <p>Una vez creada, la organización se puede editar en cualquier momento: cambiar título, descripción, logo y portada, o desactivarla temporalmente sin perder los datos.</p>
      `,
      features: [
        'Editar título y descripción',
        'Reemplazar logo o imagen de portada',
        'Toggle <strong>activa / inactiva</strong> — al desactivarla, deja de mostrarse a los miembros y no acepta nuevas solicitudes',
        'Confirmación explícita antes de desactivar',
        'Los datos (miembros, publicaciones, solicitudes) se conservan al desactivar'
      ],
      steps: [
        { title: 'Abre la organización', description: 'Click en la tarjeta dentro del dashboard corporativo' },
        { title: 'Click en "Editar"', description: 'Botón en la cabecera de la organización' },
        { title: 'Actualiza los campos', description: 'Modifica los datos o cambia las imágenes' },
        { title: 'Guarda los cambios', description: 'Click en "Guardar" — los miembros verán los cambios al recargar' },
        { title: 'Desactivar (opcional)', description: 'Para pausar la organización, usa el toggle "Activa" y confirma' }
      ],
      tips: [
        'Si la organización va a estar inactiva mucho tiempo, avisa a los miembros con una publicación antes de desactivarla',
        'Reactivar es inmediato — solo vuelve a mover el toggle'
      ]
    },
    {
      id: 'org-all-members',
      name: 'Vista Global de Miembros',
      description: 'Ver miembros de todas tus organizaciones en una sola vista',
      roles: ['corporate_client'],
      content: `
        <p>Cuando administras varias organizaciones, la vista <strong>"Todos los miembros"</strong> agrupa los miembros de todas tus organizaciones en un único modal, útil para encontrar a alguien rápido sin recordar a cuál pertenece.</p>
      `,
      features: [
        'Listado agregado de miembros de todas las organizaciones',
        'Agrupación visible por organización con el conteo total al inicio',
        'Detalle por miembro: nombre, email y organización a la que pertenece',
        'Acceso rápido al modal de detalle de cada miembro'
      ],
      steps: [
        { title: 'Abre el dashboard corporativo', description: 'Sección "Organizaciones" en el menú' },
        { title: 'Click en "Ver todos los miembros"', description: 'Botón en la cabecera del dashboard' },
        { title: 'Explora', description: 'Modal con todos los miembros agrupados por organización' }
      ],
      tips: [
        'Útil cuando recibes una solicitud y no recuerdas en qué organización está esa persona'
      ]
    },
    {
      id: 'client-view',
      name: 'Vista de Cliente',
      description: 'Organizaciones donde eres miembro',
      roles: ['client', 'basic'],
      content: `
        <p>Los clientes ven la dashboard organizada en pestañas para separar sus organizaciones, las invitaciones pendientes y las solicitudes que han creado.</p>
      `,
      features: [
        'Pestaña <strong>Mis Organizaciones</strong>: organizaciones donde eres miembro activo',
        'Pestaña <strong>Invitaciones</strong>: invitaciones pendientes de respuesta',
        'Pestaña <strong>Mis Solicitudes</strong>: solicitudes corporativas que has creado',
        'Aceptar o rechazar invitaciones',
        'Ver publicaciones de la organización',
        'Ver otros miembros',
        'Salir de una organización'
      ],
      steps: [
        {
          title: 'Revisa Invitaciones',
          description: 'Pestaña "Invitaciones" muestra las pendientes'
        },
        {
          title: 'Acepta Invitación',
          description: 'Click en "Aceptar" para unirte a la organización'
        },
        {
          title: 'Explora la Organización',
          description: 'Cambia a "Mis Organizaciones" para ver publicaciones, miembros y crear solicitudes'
        }
      ],
      restrictions: [
        'El rol <strong>basic</strong> ve la dashboard de organizaciones pero algunas acciones (crear solicitud corporativa, descargar adjuntos pesados) están limitadas con un overlay que invita a mejorar el plan'
      ]
    },
    {
      id: 'invite-members',
      name: 'Invitar Miembros',
      description: 'Enviar invitaciones por email a tu equipo',
      roles: ['corporate_client'],
      content: `
        <p>Los clientes corporativos pueden invitar nuevos miembros a su organización enviando invitaciones por correo electrónico.</p>
        <p class="mt-2">Las invitaciones tienen estados: <strong>Pendiente</strong>, <strong>Aceptada</strong>, <strong>Rechazada</strong> o <strong>Expirada</strong>.</p>
      `,
      features: [
        'Enviar invitación por email',
        'Invitar usuarios registrados y no registrados',
        'Ver lista de invitaciones pendientes',
        'Estados de invitación: Pendiente, Aceptada, Rechazada, Expirada',
        'Reenviar invitaciones expiradas',
        'Cancelar invitaciones pendientes'
      ],
      steps: [
        {
          title: 'Accede a tu Organización',
          description: 'Navega a la sección de Organizaciones y selecciona tu organización'
        },
        {
          title: 'Click en "Invitar Miembro"',
          description: 'Botón en la sección de miembros de la organización'
        },
        {
          title: 'Ingresa el email',
          description: 'Escribe el correo electrónico de la persona que deseas invitar'
        },
        {
          title: 'Envía la invitación',
          description: 'Click en "Enviar" para enviar la invitación por email'
        },
        {
          title: 'Seguimiento',
          description: 'Revisa el estado de la invitación en la lista de invitaciones pendientes'
        }
      ],
      restrictions: [
        'Solo los clientes corporativos pueden invitar miembros',
        'No se puede invitar a alguien que ya es miembro',
        'Las invitaciones tienen un tiempo de expiración'
      ],
      tips: [
        'Verifica que el email sea correcto antes de enviar',
        'Si la invitación expira, puedes reenviarla',
        'Los usuarios no registrados recibirán un enlace para crear cuenta'
      ]
    },
    {
      id: 'member-management',
      name: 'Gestión de Miembros',
      description: 'Administrar los miembros de tu organización',
      roles: ['corporate_client'],
      content: `
        <p>Gestiona los miembros de tu organización: visualiza la lista completa y remueve miembros cuando sea necesario.</p>
      `,
      features: [
        'Ver lista completa de miembros',
        'Ver rol y fecha de ingreso de cada miembro',
        'Remover miembros de la organización',
        'Ver estadísticas de miembros activos'
      ],
      steps: [
        {
          title: 'Accede a Miembros',
          description: 'En tu organización, navega a la sección de miembros'
        },
        {
          title: 'Revisa la lista',
          description: 'Ve todos los miembros con su información'
        },
        {
          title: 'Remover Miembro (si necesario)',
          description: 'Click en "Remover" junto al miembro que deseas eliminar'
        },
        {
          title: 'Confirma la acción',
          description: 'Confirma que deseas remover al miembro de la organización'
        }
      ],
      restrictions: [
        'Solo los clientes corporativos pueden remover miembros',
        'No puedes removerte a ti mismo como propietario'
      ],
      tips: [
        'Al remover un miembro, pierde acceso inmediato a la organización',
        'Puedes re-invitar a un miembro removido posteriormente'
      ]
    },
    {
      id: 'posts-management',
      name: 'Gestionar Publicaciones',
      description: 'Crear, editar y administrar publicaciones internas',
      roles: ['corporate_client'],
      content: `
        <p>Publica anuncios y comunicaciones internas para los miembros de tu organización. Controla la <strong>visibilidad</strong> de cada publicación y destaca las más importantes con la opción de <strong>fijar</strong>.</p>
      `,
      features: [
        'Crear publicaciones con título y contenido',
        'Controlar visibilidad: visible para clientes miembros (sí/no)',
        'Fijar publicaciones importantes (pin/unpin)',
        'Editar publicaciones existentes',
        'Cambiar estado de publicación (activa/inactiva)',
        'Eliminar publicaciones con confirmación'
      ],
      steps: [
        {
          title: 'Accede a Publicaciones',
          description: 'En tu organización, navega a la sección de publicaciones'
        },
        {
          title: 'Crear Nueva Publicación',
          description: 'Click en "Nueva Publicación" y completa título y contenido'
        },
        {
          title: 'Configura Visibilidad',
          description: 'Elige si la publicación será visible para los clientes miembros'
        },
        {
          title: 'Publica',
          description: 'Click en "Publicar" para que sea visible según la configuración'
        },
        {
          title: 'Gestiona (opcional)',
          description: 'Fija, edita, desactiva o elimina publicaciones según necesites'
        }
      ],
      tips: [
        'Las publicaciones fijadas aparecen siempre al inicio de la lista',
        'Usa la opción de visibilidad para comunicaciones solo para administradores',
        'Desactiva publicaciones temporalmente en lugar de eliminarlas'
      ]
    },
    {
      id: 'client-invitations',
      name: 'Gestionar Invitaciones (Cliente)',
      description: 'Aceptar o rechazar invitaciones a organizaciones',
      roles: ['client', 'basic'],
      content: `
        <p>Cuando recibes una invitación para unirte a una organización, puedes <strong>aceptarla</strong> para ganar acceso o <strong>rechazarla</strong>. Las invitaciones también pueden <strong>expirar</strong> si no se responden a tiempo.</p>
      `,
      features: [
        'Ver invitaciones pendientes',
        'Aceptar invitación para unirse a la organización',
        'Rechazar invitación',
        'Ver invitaciones expiradas',
        'Notificación de nueva invitación'
      ],
      steps: [
        {
          title: 'Revisa Invitaciones',
          description: 'En la sección de Organizaciones, ve las invitaciones pendientes'
        },
        {
          title: 'Lee los Detalles',
          description: 'Revisa qué organización te invita y quién envió la invitación'
        },
        {
          title: 'Acepta o Rechaza',
          description: 'Click en "Aceptar" para unirte o "Rechazar" para declinar'
        },
        {
          title: 'Accede a la Organización',
          description: 'Si aceptaste, ya puedes ver publicaciones, miembros y solicitudes'
        }
      ],
      restrictions: [
        'Las invitaciones expiradas no pueden ser aceptadas',
        'Debes esperar una nueva invitación si la anterior expiró'
      ],
      tips: [
        'Responde las invitaciones a tiempo para evitar que expiren',
        'Al aceptar, ganarás acceso inmediato a los recursos de la organización'
      ]
    },
    {
      id: 'client-requests',
      name: 'Solicitudes dentro de Organización (Cliente)',
      description: 'Crear solicitudes corporativas como miembro',
      roles: ['client', 'basic'],
      content: `
        <p>Como miembro de una organización, puedes crear solicitudes corporativas que serán gestionadas por el administrador de la organización.</p>
      `,
      features: [
        'Crear solicitud dentro del contexto de la organización',
        'Describir la solicitud con detalle',
        'Ver estado de solicitudes enviadas',
        'Recibir respuestas del administrador',
        'Thread de conversación sobre la solicitud'
      ],
      steps: [
        {
          title: 'Accede a la Organización',
          description: 'Selecciona la organización donde deseas crear la solicitud'
        },
        {
          title: 'Click en "Nueva Solicitud"',
          description: 'Botón en la sección de solicitudes de la organización'
        },
        {
          title: 'Describe tu Solicitud',
          description: 'Escribe el detalle de lo que necesitas'
        },
        {
          title: 'Envía',
          description: 'El administrador recibirá tu solicitud y podrá responderte'
        },
        {
          title: 'Sigue el Estado',
          description: 'Revisa el estado y las respuestas en el thread de la solicitud'
        }
      ],
      tips: [
        'Sé específico en tu solicitud para facilitar la gestión',
        'Revisa las respuestas periódicamente para mantener la comunicación activa'
      ]
    },
    {
      id: 'client-leave',
      name: 'Salir de Organización',
      description: 'Abandonar una organización de la que eres miembro',
      roles: ['client', 'basic'],
      content: `
        <p>Puedes salir de una organización en cualquier momento. Al hacerlo, perderás acceso a publicaciones, miembros y solicitudes de esa organización.</p>
      `,
      features: [
        'Opción para abandonar la organización',
        'Confirmación antes de salir',
        'Pérdida inmediata de acceso tras confirmación'
      ],
      steps: [
        {
          title: 'Accede a la Organización',
          description: 'Selecciona la organización de la que deseas salir'
        },
        {
          title: 'Click en "Salir de Organización"',
          description: 'Opción disponible en la configuración de la organización'
        },
        {
          title: 'Confirma',
          description: 'Lee la advertencia y confirma que deseas salir'
        }
      ],
      restrictions: [
        'Al salir pierdes acceso inmediatamente',
        'Para volver necesitarás una nueva invitación'
      ],
      tips: [
        'Antes de salir, descarga cualquier información que necesites conservar',
        'Si sales por error, solicita al administrador una nueva invitación'
      ]
    },
    {
      id: 'corporate-requests',
      name: 'Gestionar Solicitudes Corporativas',
      description: 'Administrar solicitudes recibidas de miembros',
      roles: ['corporate_client'],
      content: `
        <p>Los administradores de organizaciones pueden ver, responder y gestionar las solicitudes enviadas por los miembros. El sistema incluye un thread de conversación y la opción de agregar <strong>notas internas</strong> que solo el administrador puede ver.</p>
      `,
      features: [
        'Ver todas las solicitudes recibidas',
        'Filtrar por estado (Pendiente, En Revisión, Respondida, Cerrada)',
        'Responder con mensajes visibles para el solicitante',
        'Agregar notas internas (ocultas al cliente)',
        'Cambiar estado de solicitudes',
        'Ver detalle completo de cada solicitud'
      ],
      steps: [
        {
          title: 'Accede a Solicitudes',
          description: 'En tu organización, navega a la sección de solicitudes'
        },
        {
          title: 'Revisa Solicitudes Pendientes',
          description: 'Filtra por estado "Pendiente" para ver las nuevas'
        },
        {
          title: 'Abre el Detalle',
          description: 'Click en la solicitud para ver la información completa'
        },
        {
          title: 'Responde',
          description: 'Escribe tu respuesta en el thread (visible para el solicitante)'
        },
        {
          title: 'Nota Interna (opcional)',
          description: 'Agrega notas internas visibles solo para ti como administrador'
        },
        {
          title: 'Cambia el Estado',
          description: 'Actualiza el estado según el progreso: En Revisión → Respondida → Cerrada'
        }
      ],
      tips: [
        'Usa notas internas para registrar decisiones o comentarios privados',
        'Responde rápidamente para mantener la confianza del equipo',
        'Cierra las solicitudes resueltas para mantener la lista organizada'
      ]
    }
  ]
};

export const intranetContent = {
  name: 'Intranet G&M',
  icon: ScaleIcon,
  description: 'Portal interno exclusivo para abogados de G&M',
  overview: `
    <p>Intranet exclusiva para abogados que pertenecen a la firma G&M (is_gym_lawyer = true).</p>
  `,
  sections: [
    {
      id: 'profile',
      name: 'Perfil de la Firma',
      description: 'Información corporativa de G&M',
      roles: ['lawyer'],
      content: `
        <p>Información institucional de la firma G&M Abogados.</p>
      `,
      features: [
        'Banner con atributos: Seguridad, Confianza, Tranquilidad',
        'Imagen de portada corporativa',
        'Logo de la firma',
        'Número total de miembros',
        'Invitaciones pendientes',
        'Fecha de creación de la firma',
        'Botón para ver organigrama'
      ]
    },
    {
      id: 'submit-report',
      name: 'Radicar Informe',
      description: 'Enviar informes de actividad y facturación',
      roles: ['lawyer'],
      content: `
        <p>Los abogados G&M pueden enviar informes mensuales de actividades y facturación.</p>
      `,
      features: [
        'Formulario completo de facturación',
        'Campo: No. Contrato',
        'Campo: Fecha Inicial del período',
        'Campo: Fecha Final del período',
        'Campo: Concepto de Pago',
        'Campo: Valor a Cobrar',
        'Adjuntar: Informe de Actividades (PDF)',
        'Adjuntar: Cuenta de Cobro/Factura (PDF)',
        'Adjuntar: Anexos adicionales',
        'Campo: Observaciones',
        'Validación de campos obligatorios',
        'Validación de fechas (final > inicial)'
      ],
      steps: [
        {
          title: 'Click en "Radicar Informe"',
          description: 'Botón en la sección de Intranet'
        },
        {
          title: 'Completa información del contrato',
          description: 'No. Contrato y período (fechas inicial y final)'
        },
        {
          title: 'Detalla el concepto',
          description: 'Concepto de pago y valor a cobrar'
        },
        {
          title: 'Adjunta documentos',
          description: 'Informe de actividades y cuenta de cobro en PDF'
        },
        {
          title: 'Agrega anexos',
          description: 'Documentos adicionales si son necesarios'
        },
        {
          title: 'Envía el informe',
          description: 'Revisa y envía para aprobación'
        }
      ],
      tips: [
        'Prepara todos los documentos antes de empezar',
        'Verifica que las fechas sean correctas',
        'Incluye todos los anexos necesarios'
      ]
    },
    {
      id: 'procedures',
      name: 'Procedimientos G&M',
      description: 'Biblioteca de documentos internos',
      roles: ['lawyer'],
      content: `
        <p>Acceso a procedimientos administrativos, operativos, de mercadeo y comerciales de la firma.</p>
      `,
      features: [
        'Búsqueda en tiempo real de procedimientos',
        'Resaltado de coincidencias en amarillo',
        'Links a documentos externos',
        'Scroll vertical (máx 500px)',
        'Categorías: Administrativos, Operativos, Mercadeo, Comerciales',
        'Apertura en nueva pestaña'
      ],
      steps: [
        {
          title: 'Accede a Procedimientos',
          description: 'Sección en la parte inferior de Intranet'
        },
        {
          title: 'Busca procedimiento',
          description: 'Usa la barra de búsqueda para encontrar documentos'
        },
        {
          title: 'Click en el documento',
          description: 'Se abrirá en una nueva pestaña'
        }
      ]
    },
    {
      id: 'organigram',
      name: 'Organigrama G&M',
      description: 'Estructura organizacional de la firma',
      roles: ['lawyer'],
      content: `
        <p>Visualización de la estructura jerárquica y organizacional de G&M Abogados.</p>
      `,
      features: [
        'Imagen del organigrama completo',
        'Modal para visualización ampliada',
        'Jerarquía de la firma',
        'Roles y responsabilidades',
        'Zoom y scroll en la imagen'
      ]
    },
    {
      id: 'document-download-fix',
      name: 'Descarga de Documentos Optimizada',
      description: 'Descarga sin pantalla en blanco en PWA',
      roles: ['lawyer'],
      content: `
        <p>La descarga de documentos de procedimientos G&M ha sido <strong>optimizada</strong> para evitar que la pantalla quede en blanco, especialmente en la aplicación móvil (PWA).</p>
        <p class="mt-2">Ahora los documentos se descargan usando el mismo patrón que los documentos jurídicos, garantizando una experiencia fluida.</p>
      `,
      features: [
        'Descarga mediante blob para evitar navegación',
        'No deja la pantalla en blanco en PWA',
        'Notificación de éxito al completar descarga',
        'Notificación de error si falla la descarga',
        'Soporta múltiples formatos: Word, PDF, etc.',
        'Funciona igual en móvil, tablet y escritorio',
        'Experiencia consistente con documentos jurídicos'
      ],
      steps: [
        {
          title: 'Accede a Intranet G&M',
          description: 'Click en "Intranet G&M" en el menú lateral'
        },
        {
          title: 'Sección Procedimientos',
          description: 'Scroll hacia abajo hasta "Procedimientos G&M"'
        },
        {
          title: 'Buscar Documento',
          description: 'Usa la barra de búsqueda para encontrar el procedimiento'
        },
        {
          title: 'Click en Documento',
          description: 'Click en el nombre del documento para descargarlo'
        },
        {
          title: 'Descarga Automática',
          description: 'El archivo se descarga sin abrir nueva pestaña'
        },
        {
          title: 'Notificación',
          description: 'Recibes confirmación de descarga exitosa'
        }
      ],
      tips: [
        'La descarga es instantánea, no esperes que se abra nueva pestaña',
        'Busca el archivo en tu carpeta de descargas',
        'Funciona perfectamente en la app móvil sin problemas',
        'Si falla, recibirás un mensaje de error claro'
      ]
    }
  ]
};

export const authenticationContent = {
  name: 'Autenticación y Cuenta',
  icon: UserCircleIcon,
  description: 'Gestiona tu acceso a la plataforma y configuración de cuenta',
  overview: `
    <p>Este módulo cubre todas las funciones relacionadas con tu acceso a la plataforma: inicio de sesión, registro, recuperación de contraseña, perfil y seguridad.</p>
  `,
  sections: [
    {
      id: 'login-email',
      name: 'Iniciar sesión con email',
      description: 'Accede a tu cuenta usando tu correo electrónico y contraseña',
      roles: ['lawyer', 'client', 'corporate_client', 'basic'],
      content: `
        <p>Ingresa con tu correo electrónico registrado y tu contraseña para acceder a todas las funcionalidades de la plataforma.</p>
      `,
      features: [
        'Ingreso con correo y contraseña',
        'Verificación reCAPTCHA de seguridad',
        'Redirección automática al Dashboard tras inicio exitoso',
        'Enlace a recuperación de contraseña'
      ],
      steps: [
        { title: 'Accede a la página de inicio', description: 'Navega a la URL de la plataforma' },
        { title: 'Ingresa tu correo', description: 'Escribe tu correo electrónico registrado' },
        { title: 'Ingresa tu contraseña', description: 'Escribe tu contraseña' },
        { title: 'Verifica el captcha', description: 'Completa la verificación de seguridad' },
        { title: 'Haz clic en "Iniciar Sesión"', description: 'Serás redirigido al Dashboard' }
      ]
    },
    {
      id: 'login-google',
      name: 'Iniciar sesión con Google',
      description: 'Accede rápidamente usando tu cuenta de Google',
      roles: ['lawyer', 'client', 'corporate_client', 'basic'],
      content: `
        <p>Usa tu cuenta de Google para acceder sin necesidad de recordar otra contraseña.</p>
      `,
      features: [
        'Acceso con un solo clic usando Google',
        'No requiere contraseña adicional',
        'Registro automático si es tu primera vez'
      ],
      steps: [
        { title: 'Ve a la página de inicio', description: 'Navega a la URL de la plataforma' },
        { title: 'Haz clic en "Continuar con Google"', description: 'Debajo del formulario de inicio de sesión' },
        { title: 'Selecciona tu cuenta', description: 'Elige tu cuenta de Google en la ventana emergente' },
        { title: 'Autoriza el acceso', description: 'Confirma los permisos solicitados' },
        { title: 'Acceso completado', description: 'Serás redirigido al Dashboard automáticamente' }
      ]
    },
    {
      id: 'login-microsoft',
      name: 'Iniciar sesión con Microsoft',
      description: 'Accede rápidamente usando tu cuenta de Microsoft (Outlook, Hotmail, Live o Microsoft 365)',
      roles: ['lawyer', 'client', 'corporate_client', 'basic'],
      content: `
        <p>Usa tu cuenta de Microsoft para acceder sin necesidad de recordar otra contraseña. Es compatible con cuentas personales (Outlook.com, Hotmail, Live) y cuentas corporativas (Microsoft 365 / Azure AD).</p>
      `,
      features: [
        'Acceso con un solo clic usando Microsoft',
        'Compatible con cuentas personales y corporativas (Microsoft 365)',
        'No requiere contraseña adicional',
        'Registro automático si es tu primera vez'
      ],
      steps: [
        { title: 'Ve a la página de inicio', description: 'Navega a la URL de la plataforma' },
        { title: 'Haz clic en "Continuar con Microsoft"', description: 'Debajo del botón de Google' },
        { title: 'Inicia sesión en la ventana de Microsoft', description: 'Ingresa tus credenciales de Microsoft en la ventana emergente' },
        { title: 'Autoriza el acceso', description: 'Confirma los permisos solicitados' },
        { title: 'Acceso completado', description: 'Serás redirigido al Dashboard automáticamente' }
      ]
    },
    {
      id: 'register',
      name: 'Registrar nueva cuenta',
      description: 'Crea una cuenta nueva en la plataforma',
      roles: ['lawyer', 'client', 'corporate_client', 'basic'],
      content: `
        <p>Crea tu cuenta proporcionando tus datos personales y verificando tu correo electrónico con un código de seguridad.</p>
      `,
      features: [
        'Formulario de registro con datos personales',
        'Verificación de correo electrónico por código',
        'Aceptación de políticas de privacidad',
        'Opción de registro con Google o Microsoft'
      ],
      steps: [
        { title: 'Haz clic en "Crear cuenta"', description: 'En la página de inicio de sesión' },
        { title: 'Completa el formulario', description: 'Ingresa nombre, apellido, email y contraseña' },
        { title: 'Acepta las políticas', description: 'Marca la casilla de políticas de privacidad' },
        { title: 'Completa el captcha', description: 'Verifica que no eres un robot' },
        { title: 'Recibe el código', description: 'Se enviará un código a tu correo electrónico' },
        { title: 'Ingresa el código', description: 'Escribe el código recibido para verificar tu cuenta' },
        { title: 'Cuenta activada', description: 'Tu cuenta estará lista para usar' }
      ]
    },
    {
      id: 'forgot-password',
      name: 'Recuperar contraseña',
      description: 'Restablece tu contraseña si la olvidaste',
      roles: ['lawyer', 'client', 'corporate_client', 'basic'],
      content: `
        <p>Si olvidaste tu contraseña, puedes restablecerla usando tu correo electrónico registrado y un código de verificación.</p>
      `,
      features: [
        'Envío de código de verificación al correo',
        'Creación de nueva contraseña segura',
        'Confirmación de contraseña',
        'Redirección automática a inicio de sesión'
      ],
      steps: [
        { title: 'Haz clic en "¿Olvidaste tu contraseña?"', description: 'En la página de inicio de sesión' },
        { title: 'Ingresa tu correo', description: 'Escribe el correo electrónico asociado a tu cuenta' },
        { title: 'Haz clic en "Enviar código"', description: 'Recibirás un código en tu correo' },
        { title: 'Ingresa el código', description: 'Escribe el código recibido' },
        { title: 'Crea tu nueva contraseña', description: 'Ingresa y confirma tu nueva contraseña' },
        { title: 'Contraseña actualizada', description: 'Ahora puedes iniciar sesión con tu nueva contraseña' }
      ]
    },
    {
      id: 'profile',
      name: 'Editar perfil',
      description: 'Actualiza tu información personal y foto de perfil',
      roles: ['lawyer', 'client', 'corporate_client', 'basic'],
      content: `
        <p>Mantén tu información personal actualizada para que tus colegas y clientes puedan contactarte correctamente.</p>
      `,
      features: [
        'Edición de nombre, apellido y datos de contacto',
        'Cambio de foto de perfil',
        'Actualización de número de identificación',
        'Tipo de documento y fecha de nacimiento'
      ],
      steps: [
        { title: 'Abre el menú de usuario', description: 'Haz clic en tu nombre en la barra lateral' },
        { title: 'Selecciona "Perfil"', description: 'Se abrirá el modal de información de perfil' },
        { title: 'Haz clic en "Editar"', description: 'Para modificar tus datos personales' },
        { title: 'Actualiza los campos', description: 'Modifica la información que necesites' },
        { title: 'Guarda los cambios', description: 'Haz clic en "Guardar" para confirmar' }
      ]
    },
    {
      id: 'logout',
      name: 'Cerrar sesión',
      description: 'Cierra tu sesión de forma segura',
      roles: ['lawyer', 'client', 'corporate_client', 'basic'],
      content: `
        <p>Cierra tu sesión cuando termines de usar la plataforma para proteger tu cuenta.</p>
      `,
      features: [
        'Cierre de sesión con un clic',
        'Limpieza de datos de sesión local',
        'Redirección a página de inicio de sesión'
      ],
      steps: [
        { title: 'Abre el menú de usuario', description: 'Haz clic en tu nombre en la barra lateral' },
        { title: 'Selecciona "Cerrar Sesión"', description: 'Tu sesión se cerrará inmediatamente' },
        { title: 'Redirección', description: 'Serás llevado a la página de inicio de sesión' }
      ]
    },
    {
      id: 'subscription-signin',
      name: 'Iniciar sesión para suscripción',
      description: 'Login desde el flujo de suscripción con redirección al checkout',
      roles: ['lawyer', 'client', 'corporate_client', 'basic'],
      content: `
        <p>Si seleccionas un plan de suscripción sin estar autenticado, serás redirigido a una página de inicio de sesión especial que preserva tu plan seleccionado.</p>
      `,
      features: [
        'Login con email y contraseña',
        'Preservación del plan seleccionado en la URL',
        'Redirección automática al checkout tras login exitoso',
        'Enlace a registro de suscripción si no tienes cuenta'
      ],
      steps: [
        { title: 'Selecciona un plan', description: 'En la página de suscripciones, elige un plan' },
        { title: 'Redirección', description: 'Si no estás autenticado, llegarás al login de suscripción' },
        { title: 'Inicia sesión', description: 'Ingresa tu email, contraseña y completa el captcha' },
        { title: 'Checkout', description: 'Tras el login, serás redirigido al checkout con tu plan seleccionado' }
      ]
    },
    {
      id: 'subscription-signup',
      name: 'Registrarse para suscripción',
      description: 'Registro desde el flujo de suscripción con redirección al checkout',
      roles: ['lawyer', 'client', 'corporate_client', 'basic'],
      content: `
        <p>Si no tienes cuenta, puedes registrarte directamente desde el flujo de suscripción. Tras verificar tu email, serás redirigido al checkout con el plan seleccionado.</p>
      `,
      features: [
        'Formulario de registro completo',
        'Verificación de email con código',
        'Preservación del plan seleccionado',
        'Redirección automática al checkout tras registro'
      ],
      steps: [
        { title: 'Desde el login de suscripción', description: 'Click en "Crear cuenta" en la página de login de suscripción' },
        { title: 'Completa el formulario', description: 'Ingresa nombre, apellido, email, contraseña y acepta políticas' },
        { title: 'Verifica tu email', description: 'Ingresa el código de verificación enviado a tu correo' },
        { title: 'Checkout', description: 'Tras la verificación, serás redirigido al checkout con tu plan' }
      ]
    },
    {
      id: 'idle-logout',
      name: 'Cierre automático por inactividad',
      description: 'La sesión se cierra automáticamente después de un período sin actividad',
      roles: ['lawyer', 'client', 'corporate_client', 'basic'],
      content: `
        <p>Por seguridad, si no detectamos actividad en tu sesión durante 15 minutos, el sistema cerrará tu sesión automáticamente.</p>
      `,
      features: [
        'Detección de inactividad (mouse, teclado, scroll, touch)',
        'Cierre automático después de 15 minutos sin actividad',
        'Redirección a página de inicio de sesión',
        'Cualquier actividad reinicia el temporizador'
      ]
    },
    {
      id: 'login-attempts',
      name: 'Protección contra accesos no autorizados',
      description: 'El sistema limita intentos de acceso fallidos para proteger tu cuenta',
      roles: ['lawyer', 'client', 'corporate_client', 'basic'],
      content: `
        <p>Después de varios intentos fallidos de inicio de sesión, el sistema bloqueará temporalmente el acceso para proteger tu cuenta.</p>
      `,
      features: [
        'Bloqueo temporal después de 3 intentos fallidos',
        'Tiempo de espera progresivo (60s, 120s, 240s...)',
        'Contador visible de segundos restantes',
        'Opción de recuperar contraseña durante bloqueo'
      ]
    },
    {
      id: 'user-signature',
      name: 'Firma Digital del Perfil',
      description: 'Registrar la firma que se usará en documentos electrónicos',
      roles: ['lawyer', 'client', 'corporate_client', 'basic'],
      content: `
        <p>Desde el perfil puedes registrar tu <strong>firma digital</strong>, que luego se aplicará automáticamente a los documentos que firmes desde el módulo de Archivos Jurídicos.</p>
        <p class="mt-2">Puedes dibujarla con el mouse/touch o cargar una imagen (PNG con fondo transparente recomendado).</p>
      `,
      features: [
        'Dibujar la firma directamente en el navegador',
        'Cargar imagen de firma (PNG/JPG)',
        'Vista previa antes de guardar',
        'Reemplazar firma existente en cualquier momento',
        'La firma se usa en el flujo de firma electrónica de documentos'
      ],
      steps: [
        {
          title: 'Accede a tu perfil',
          description: 'Click en tu avatar en el menú lateral y selecciona "Mi Perfil"'
        },
        {
          title: 'Abre la sección Firma',
          description: 'Scroll hasta "Firma Digital"'
        },
        {
          title: 'Dibuja o carga',
          description: 'Elige entre dibujar con el mouse/touch o subir una imagen de tu firma'
        },
        {
          title: 'Guarda',
          description: 'Click en "Guardar Firma". Se almacena asociada a tu usuario'
        }
      ],
      tips: [
        'Para mejor calidad, usa PNG con fondo transparente',
        'Si dibujas la firma, hazlo con el trackpad o una pantalla táctil para más control',
        'Puedes actualizar tu firma cuando quieras; los documentos ya firmados conservan la firma original'
      ]
    }
  ]
};

export const subscriptionsContent = {
  name: 'Suscripciones y Pagos',
  icon: CreditCardIcon,
  description: 'Gestiona tu plan de suscripción y métodos de pago',
  overview: `
    <p>La plataforma ofrece diferentes planes de suscripción para adaptarse a tus necesidades. Puedes ver los planes disponibles, suscribirte, actualizar o cancelar tu plan.</p>
  `,
  sections: [
    {
      id: 'view-plans',
      name: 'Ver planes disponibles',
      description: 'Conoce los diferentes planes de suscripción',
      roles: ['lawyer', 'client', 'corporate_client', 'basic'],
      content: `
        <p>Compara los planes disponibles con sus características y precios para elegir el que mejor se adapte a tus necesidades.</p>
      `,
      features: [
        'Visualización de planes con características detalladas',
        'Comparación de precios y beneficios',
        'Indicador de plan actual (si ya tienes suscripción)',
        'Botones de selección para cada plan'
      ],
      steps: [
        { title: 'Navega a Suscripciones', description: 'Accede a la sección de planes' },
        { title: 'Revisa los planes', description: 'Compara características y precios' },
        { title: 'Selecciona un plan', description: 'Haz clic en el plan que desees' }
      ]
    },
    {
      id: 'checkout',
      name: 'Realizar pago de suscripción',
      description: 'Completa el pago de tu plan seleccionado',
      roles: ['lawyer', 'client', 'corporate_client', 'basic'],
      content: `
        <p>Completa el proceso de pago de forma segura usando tu tarjeta de crédito o débito a través de nuestro procesador de pagos Wompi.</p>
      `,
      features: [
        'Resumen del plan seleccionado',
        'Datos del usuario para facturación',
        'Pago seguro con tarjeta (Wompi)',
        'Activación gratuita para plan básico',
        'Confirmación por email',
        'Garantía de reembolso de 30 días',
        'Formulario de tarjeta: titular, número, mes/año expiración, CVC',
        'Tokenización segura de tarjeta vía Wompi',
        'Botón "Cambiar" para modificar método de pago guardado'
      ],
      steps: [
        { title: 'Selecciona un plan', description: 'Desde la página de suscripciones' },
        { title: 'Revisa el resumen', description: 'Verifica el plan y precio seleccionado' },
        { title: 'Plan gratuito', description: 'Si es plan básico (gratuito), no se muestra formulario de tarjeta. Click en "Confirmar Suscripción" directamente' },
        { title: 'Plan pago — datos de tarjeta', description: 'Si es plan pago, completa: nombre del titular, número de tarjeta, mes/año de expiración, CVC' },
        { title: 'Plan pago — guardar método', description: 'Click en "Guardar método de pago" para tokenizar la tarjeta de forma segura' },
        { title: 'Confirma el pago', description: 'Verás un badge verde "Método de pago guardado". Click en "Confirmar Suscripción"' },
        { title: 'Plan activado', description: 'Tu plan se activa inmediatamente' }
      ],
      restrictions: [
        'Los planes pagos requieren tarjeta de crédito o débito válida',
        'Si la tokenización falla, puedes reintentar con otra tarjeta',
        'El plan básico no requiere datos de pago'
      ],
      tips: [
        'El plan básico se activa inmediatamente sin necesidad de tarjeta',
        'Para planes pagos, puedes cambiar tu método de pago haciendo click en "Cambiar"',
        'Si la tarjeta es rechazada, verifica los datos e intenta de nuevo'
      ]
    },
    {
      id: 'cancel-subscription',
      name: 'Cancelar suscripción',
      description: 'Cancela tu suscripción actual',
      roles: ['lawyer', 'client', 'corporate_client'],
      content: `
        <p>Puedes cancelar tu suscripción en cualquier momento. Tu plan permanecerá activo hasta el final del período pagado.</p>
      `,
      features: [
        'Cancelación sin penalización',
        'Plan activo hasta final del período',
        'Opción de reactivar en cualquier momento',
        'Transición automática a plan gratuito'
      ],
      steps: [
        { title: 'Ve a tu suscripción', description: 'Accede a la sección de suscripciones' },
        { title: 'Selecciona "Cancelar"', description: 'Haz clic en la opción de cancelar suscripción' },
        { title: 'Confirma la cancelación', description: 'Lee las condiciones y confirma' },
        { title: 'Plan vigente', description: 'Tu plan sigue activo hasta el final del período' }
      ]
    },
    {
      id: 'upgrade-plan',
      name: 'Mejorar plan (Upgrade)',
      description: 'Cambia a un plan con más beneficios',
      roles: ['basic', 'client'],
      content: `
        <p>Mejora tu plan para acceder a funcionalidades avanzadas como firma electrónica, membrete personalizado y más.</p>
      `,
      features: [
        'Comparación con plan actual',
        'Cálculo proporcional del costo',
        'Activación inmediata de nuevos beneficios',
        'Acceso a firma electrónica y membrete'
      ],
      steps: [
        { title: 'Ve a Suscripciones', description: 'Accede a la sección de planes' },
        { title: 'Selecciona plan superior', description: 'Elige un plan con más beneficios' },
        { title: 'Completa el pago', description: 'Ingresa datos de pago si es plan pago' },
        { title: 'Beneficios activados', description: 'Los nuevos beneficios se activan inmediatamente' }
      ]
    },
    {
      id: 'payment-method-update',
      name: 'Actualizar método de pago',
      description: 'Cambiar la tarjeta asociada a tu suscripción',
      roles: ['lawyer', 'client', 'corporate_client', 'basic'],
      content: `
        <p>Puedes actualizar la tarjeta que cobra tu suscripción recurrente sin interrumpir el servicio.</p>
        <p class="mt-2">La tarjeta se re-tokeniza de forma segura a través de Wompi; G&M no almacena el número completo de tarjeta.</p>
      `,
      features: [
        'Cambio de tarjeta sin cancelar la suscripción',
        'Tokenización segura vía Wompi (PCI-DSS)',
        'Vigente desde el siguiente ciclo de facturación',
        'Valida la tarjeta con un cobro mínimo de prueba antes de aceptar el cambio'
      ],
      steps: [
        { title: 'Abre tu suscripción', description: 'Menú → Suscripciones → plan activo' },
        { title: 'Click en "Actualizar método de pago"', description: 'Se abre el formulario seguro de Wompi' },
        { title: 'Ingresa los datos de la nueva tarjeta', description: 'Número, vencimiento, CVV y titular' },
        { title: 'Confirma', description: 'Si la validación es exitosa, la tarjeta queda activa para el próximo cobro' }
      ],
      tips: [
        'Actualiza la tarjeta antes de que venza para evitar fallos de cobro y suspensiones',
        'Si el cobro falla, recibirás un email con instrucciones para reintentar'
      ]
    },
    {
      id: 'payment-history',
      name: 'Historial de pagos',
      description: 'Consultar los cobros realizados en tu suscripción',
      roles: ['lawyer', 'client', 'corporate_client', 'basic'],
      content: `
        <p>Consulta el <strong>historial de pagos</strong> de tu suscripción: fechas, montos, estado de cada transacción y reintentos automáticos.</p>
      `,
      features: [
        'Listado cronológico de todas las transacciones',
        'Estado por pago: Aprobado, Pendiente, Rechazado',
        'Monto, fecha y método utilizado',
        'Reintentos automáticos cuando un cobro falla',
        'Referencia de transacción para soporte'
      ],
      steps: [
        { title: 'Abre tu suscripción', description: 'Menú → Suscripciones' },
        { title: 'Click en "Historial de Pagos"', description: 'Se despliega la tabla de transacciones' },
        { title: 'Filtra si es necesario', description: 'Por estado o por rango de fechas' }
      ],
      tips: [
        'Guarda la referencia de transacción si necesitas contactar soporte por un cobro',
        'Los pagos rechazados se reintentan automáticamente antes de suspender el servicio'
      ]
    }
  ]
};
