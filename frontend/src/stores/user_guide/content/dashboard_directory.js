import {
  HomeIcon,
  UsersIcon,
} from '@heroicons/vue/24/outline';

export const dashboardContent = {
  name: 'Inicio (Dashboard)',
  icon: HomeIcon,
  description: 'Panel principal con vista general de tu actividad en la plataforma',
  overview: `
    <p>El Dashboard es tu punto de partida en la plataforma G&M Abogados. Aquí encontrarás un resumen de toda tu actividad y accesos rápidos a las funcionalidades más importantes.</p>
  `,
  sections: [
    {
      id: 'welcome-card',
      name: 'Tarjeta de Bienvenida',
      description: 'Información personalizada y estadísticas',
      roles: ['lawyer', 'client', 'corporate_client', 'basic'],
      content: `
        <p>La tarjeta de bienvenida te saluda con tu nombre y muestra información relevante según tu rol.</p>
      `,
      features: [
        'Saludo personalizado con tu nombre',
        'Contador de procesos activos',
        'Botón de acción rápida contextual'
      ]
    },
    {
      id: 'activity-feed',
      name: 'Feed de Actividad',
      description: 'Historial de tus acciones recientes',
      roles: ['lawyer', 'client', 'corporate_client', 'basic'],
      content: `
        <p>El feed de actividad muestra un registro cronológico de todas tus acciones en la plataforma.</p>
      `,
      features: [
        'Creación y actualización de procesos',
        'Firma de documentos',
        'Creación de minutas',
        'Edición de contenido de documentos jurídicos',
        'Rechazo de documentos y correcciones reenviadas para firma',
        'Actualización de perfil',
        'Scroll infinito para ver más actividades'
      ]
    },
    {
      id: 'quick-actions',
      name: 'Botones de Acción Rápida',
      description: 'Accesos directos a funciones principales',
      roles: ['lawyer', 'client', 'corporate_client', 'basic'],
      content: `
        <p>Los botones de acción rápida cambian según tu rol y te dan acceso inmediato a las funciones que más utilizas.</p>
      `,
      features: [
        'Para Abogados: Todos los Procesos, Radicar Proceso, Nueva Minuta, Radicar Informe',
        'Para Clientes: Mis Procesos, Nueva Solicitud'
      ],
      tips: [
        'Los botones cambian según tu rol para mostrarte solo las opciones relevantes',
        'Usa estos botones para acceder rápidamente sin navegar por el menú'
      ]
    },
    {
      id: 'recent-items',
      name: 'Elementos Recientes',
      description: 'Procesos y documentos visitados recientemente',
      roles: ['lawyer', 'client', 'corporate_client', 'basic'],
      content: `
        <p>Accede rápidamente a los últimos 5 procesos y documentos que has visualizado o editado.</p>
      `,
      features: [
        'Lista de procesos recientes',
        'Lista de documentos recientes',
        'Acceso con un solo click'
      ]
    },
    {
      id: 'legal-updates',
      name: 'Actualizaciones Legales',
      description: 'Noticias y actualizaciones del sector legal',
      roles: ['lawyer', 'client', 'corporate_client', 'basic'],
      content: `
        <p>El dashboard incluye un carrusel de <strong>actualizaciones legales</strong> con noticias relevantes del sector. Los abogados pueden crear, editar y eliminar estas actualizaciones.</p>
      `,
      features: [
        'Carrusel de noticias legales en el dashboard',
        'Título, contenido y enlaces en cada actualización',
        'Crear nueva actualización (solo abogados)',
        'Editar actualización existente (solo abogados)',
        'Eliminar actualización con confirmación (solo abogados)',
        'Estado activo/inactivo para cada actualización'
      ],
      steps: [
        {
          title: 'Ver Actualizaciones',
          description: 'En el dashboard, navega al carrusel de actualizaciones legales'
        },
        {
          title: 'Crear Actualización (Abogados)',
          description: 'Click en "Nueva Actualización" y completa título, contenido y estado'
        },
        {
          title: 'Editar (Abogados)',
          description: 'Click en editar para modificar una actualización existente'
        },
        {
          title: 'Eliminar (Abogados)',
          description: 'Click en eliminar y confirma para remover la actualización'
        }
      ],
      restrictions: [
        'Solo los abogados pueden crear, editar y eliminar actualizaciones',
        'Los clientes y usuarios básicos solo pueden ver las actualizaciones activas'
      ],
      tips: [
        'Mantén las actualizaciones al día para informar a tus clientes',
        'Usa el estado inactivo para ocultar temporalmente una actualización sin eliminarla'
      ]
    },
    {
      id: 'reports',
      name: 'Generar Reportes',
      description: 'Exportar reportes de actividad en Excel',
      roles: ['lawyer'],
      content: `
        <p>Los abogados pueden generar reportes de actividad exportados en formato <strong>Excel</strong>, filtrados por rango de fechas.</p>
      `,
      features: [
        'Generar reporte de actividad en Excel',
        'Filtrar por rango de fechas (inicio y fin)',
        'Descarga automática del archivo',
        'Datos de procesos, documentos y actividad general'
      ],
      steps: [
        {
          title: 'Accede a Reportes',
          description: 'En el dashboard, click en el botón de reportes'
        },
        {
          title: 'Selecciona Rango de Fechas',
          description: 'Elige la fecha de inicio y fin del período a reportar'
        },
        {
          title: 'Genera el Reporte',
          description: 'Click en "Generar" para crear y descargar el archivo Excel'
        }
      ],
      tips: [
        'Genera reportes mensuales para llevar un control de actividad',
        'El archivo Excel incluye múltiples hojas con datos detallados',
        'Usa rangos de fecha cortos para reportes más específicos'
      ]
    },
    {
      id: 'featured-services',
      name: 'Servicios Destacados',
      description: 'Accesos directos a los trámites más usados',
      roles: ['lawyer', 'client', 'corporate_client', 'basic'],
      content: `
        <p>El Dashboard muestra una cuadrícula con los <strong>servicios destacados</strong> configurados por el administrador (ej: Registro Marcario).</p>
        <p class="mt-2">Cada tarjeta lleva directo al formulario del servicio para iniciar la solicitud.</p>
      `,
      features: [
        'Grid con íconos personalizados por servicio',
        'Nombre y descripción breve de cada servicio',
        'Click directo al formulario del trámite',
        'Solo aparecen servicios marcados como destacados por el admin',
        'Integra con el módulo Servicios y Trámites'
      ],
      tips: [
        'Si no ves servicios destacados, accede al catálogo completo desde el menú "Servicios"',
        'Los administradores controlan qué servicios aparecen destacados'
      ]
    }
  ]
};

export const directoryContent = {
  name: 'Directorio',
  icon: UsersIcon,
  description: 'Listado completo de clientes y usuarios del sistema',
  overview: `
    <p>El Directorio es una funcionalidad exclusiva para abogados que permite buscar y consultar información de todos los usuarios del sistema.</p>
  `,
  sections: [
    {
      id: 'search-users',
      name: 'Búsqueda de Usuarios',
      description: 'Encuentra usuarios rápidamente',
      roles: ['lawyer'],
      content: `
        <p>Utiliza la barra de búsqueda para encontrar usuarios por nombre, email, identificación o rol.</p>
      `,
      features: [
        'Búsqueda en tiempo real',
        'Filtrado por múltiples campos',
        'Resultados instantáneos'
      ],
      steps: [
        {
          title: 'Accede al Directorio',
          description: 'Click en "Directorio" en el menú lateral'
        },
        {
          title: 'Usa la barra de búsqueda',
          description: 'Escribe el nombre, email o identificación del usuario'
        },
        {
          title: 'Selecciona un usuario',
          description: 'Click en el usuario para ver sus procesos asociados'
        }
      ]
    },
    {
      id: 'user-info',
      name: 'Información de Usuarios',
      description: 'Datos visibles de cada usuario',
      roles: ['lawyer'],
      content: `
        <p>Cada usuario en el directorio muestra información básica y su rol en el sistema.</p>
      `,
      features: [
        'Foto de perfil',
        'Nombre completo',
        'Rol (con badge de color)',
        'Email de contacto',
        'Click para ver procesos del usuario'
      ]
    },
    {
      id: 'user-detail-modal',
      name: 'Modal de Detalle de Usuario',
      description: 'Información completa y procesos del usuario',
      roles: ['lawyer'],
      content: `
        <p>Al hacer click en un usuario del directorio, ahora se abre un <strong>modal detallado</strong> en lugar de redirigir directamente a procesos.</p>
        <p class="mt-2">El modal muestra información del usuario y lista sus procesos asociados de forma resumida.</p>
      `,
      features: [
        'Modal con dos secciones: Información del Usuario y Procesos',
        'Avatar con iniciales si no hay foto',
        'Información completa: nombre, email, identificación, contacto, rol, fecha de nacimiento',
        'Lista de procesos del usuario con información resumida',
        'Botón "Ver proceso" para ir al detalle de cada caso',
        'Botón "Ver todos en Procesos" para lista completa filtrada',
        'Diseño responsive para móvil y escritorio',
        'Carga automática de procesos al abrir el modal'
      ],
      steps: [
        {
          title: 'Accede al Directorio',
          description: 'Click en "Directorio" en el menú lateral'
        },
        {
          title: 'Busca Usuario',
          description: 'Usa la barra de búsqueda o scroll para encontrar al usuario'
        },
        {
          title: 'Click en Tarjeta',
          description: 'Click en cualquier parte de la tarjeta del usuario'
        },
        {
          title: 'Modal se Abre',
          description: 'Aparece modal con información del usuario en la parte superior'
        },
        {
          title: 'Sección de Información',
          description: 'Revisa datos: nombre, email, identificación, contacto, rol, cumpleaños'
        },
        {
          title: 'Sección de Procesos',
          description: 'Scroll hacia abajo para ver lista de procesos del usuario'
        },
        {
          title: 'Ver Proceso',
          description: 'Click en "Ver proceso" para ir al detalle de un caso específico'
        },
        {
          title: 'Ver Todos',
          description: 'Click en "Ver todos en Procesos" para lista completa filtrada'
        }
      ],
      tips: [
        'El modal carga procesos automáticamente, puede tardar un momento',
        'Si el usuario no tiene procesos, se muestra un mensaje claro',
        'Puedes cerrar con X, botón Cerrar o click fuera del modal',
        'Útil para consultas rápidas sin navegar a otra página'
      ]
    }
  ]
};
