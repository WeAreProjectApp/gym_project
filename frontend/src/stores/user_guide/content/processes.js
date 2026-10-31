import { FolderIcon } from '@heroicons/vue/24/outline';

export const processesContent = {
  name: 'Procesos',
  icon: FolderIcon,
  description: 'Gestión y consulta de procesos judiciales',
  overview: `
    <p>El módulo de Procesos te permite gestionar y consultar todos los casos judiciales de manera organizada y eficiente.</p>
    <p class="mt-2">Los procesos están organizados en <strong>3 pestañas principales</strong>:</p>
    <ul class="list-disc list-inside mt-2 space-y-1">
      <li><strong>Mis Procesos:</strong> Casos donde eres parte o responsable</li>
      <li><strong>Todos los Procesos:</strong> Vista completa del sistema (solo abogados)</li>
      <li><strong>Procesos Archivados:</strong> Casos finalizados</li>
    </ul>
  `,
  sections: [
    {
      id: 'process-tabs',
      name: 'Pestañas de Procesos',
      description: 'Organización de procesos por categorías',
      roles: ['lawyer', 'client', 'corporate_client', 'basic'],
      content: `
        <p>Los procesos están organizados en pestañas para facilitar su consulta y gestión.</p>
      `,
      features: [
        'Mis Procesos: Casos donde eres parte o responsable',
        'Todos los Procesos: Vista completa del sistema (SOLO ABOGADOS)',
        'Procesos Archivados: Casos finalizados e históricos'
      ],
      restrictions: [
        'Los clientes solo ven "Mis Procesos" y "Procesos Archivados"',
        'Solo los abogados pueden ver "Todos los Procesos"',
        'Los usuarios básicos no pueden solicitar información'
      ],
      example: {
        title: 'Ejemplo: Navegando por las Pestañas de Procesos',
        description: 'Aprende a usar las diferentes pestañas para organizar y consultar tus procesos judiciales.',
        steps: [
          {
            title: 'Accede al módulo de Procesos',
            description: 'Click en "Procesos" en el menú lateral izquierdo',
            note: 'Verás las pestañas disponibles según tu rol'
          },
          {
            title: 'Pestaña "Mis Procesos"',
            description: 'Muestra solo los procesos donde eres parte. Para abogados: casos asignados. Para clientes: casos propios.',
            note: 'Esta es la vista predeterminada al entrar'
          },
          {
            title: 'Pestaña "Todos los Procesos" (Solo Abogados)',
            description: 'Vista completa de todos los procesos en el sistema para supervisión general',
            note: 'Útil para coordinadores y supervisores'
          },
          {
            title: 'Pestaña "Procesos Archivados"',
            description: 'Histórico de casos finalizados. Útil para consultas y referencias',
            note: 'Los procesos archivados son de solo lectura'
          }
        ],
        tips: [
          'Usa "Mis Procesos" para tu trabajo diario',
          'Los abogados pueden usar "Todos los Procesos" para supervisión',
          'Archiva procesos finalizados para mantener limpia tu vista principal'
        ]
      }
    },
    {
      id: 'filters-search',
      name: 'Filtros y Búsqueda',
      description: 'Encuentra procesos específicos rápidamente',
      roles: ['lawyer', 'client', 'corporate_client', 'basic'],
      content: `
        <p>El sistema de filtros te permite encontrar procesos específicos de manera eficiente usando múltiples criterios.</p>
      `,
      features: [
        'Búsqueda por referencia, demandante, demandado, autoridad o cliente',
        'Filtro por Tipo de Caso (Civil, Penal, Laboral, etc.)',
        'Filtro por Autoridad (Juzgados, Tribunales, Cortes)',
        'Filtro por Etapa Procesal (Admisión, Pruebas, Alegatos, Sentencia)',
        'Botón "Limpiar" para resetear todos los filtros',
        'Ordenamiento por fecha (más recientes) o nombre (A-Z)',
        'Contador de resultados encontrados',
        'En la columna "Nombre" puedes usar el enlace "Ver usuarios" para consultar todos los clientes asociados a un proceso'
      ],
      steps: [
        {
          title: 'Usa la barra de búsqueda',
          description: 'Escribe cualquier término: referencia, nombre de parte, autoridad, etc.'
        },
        {
          title: 'Aplica filtros específicos',
          description: 'Selecciona tipo, autoridad o etapa desde los dropdowns'
        },
        {
          title: 'Combina filtros',
          description: 'Puedes usar búsqueda + filtros simultáneamente para mayor precisión'
        },
        {
          title: 'Limpia filtros',
          description: 'Click en "Limpiar" para resetear y volver a la vista completa'
        }
      ],
      tips: [
        'La búsqueda funciona en tiempo real, no necesitas presionar Enter',
        'Combina múltiples filtros para búsquedas muy específicas',
        'El contador te muestra cuántos procesos coinciden con tu búsqueda'
      ]
    },
    {
      id: 'create-process',
      name: 'Radicar Proceso (Abogados y Administradores)',
      description: 'Crear un nuevo proceso judicial',
      roles: ['lawyer', 'admin'],
      content: `
        <p>Los abogados y administradores pueden crear nuevos procesos judiciales. El administrador debe seleccionar un abogado responsable; al abogado se le asigna inicialmente su propia cuenta.</p>
      `,
      features: [
        'Formulario completo con validación de campos',
        'Combobox con búsqueda para Tipo de Proceso',
        'Selección de uno o varios Clientes desde base de datos (multi-selección)',
        'Asignación de Abogado responsable',
        'Subida de múltiples archivos adjuntos',
        'Campos: Demandante, Demandado, Autoridad, Referencia, Subclase',
        'Definición de etapa procesal inicial',
        'Tabla con el listado de clientes seleccionados para revisar fácilmente las asociaciones del proceso'
      ],
      steps: [
        {
          title: 'Click en "Nuevo"',
          description: 'Botón con el símbolo + junto al contador de resultados de la lista de procesos'
        },
        {
          title: 'Completa información básica',
          description: 'Llena Demandante, Demandado, Autoridad y Referencia/Radicado'
        },
        {
          title: 'Selecciona Tipo de Proceso',
          description: 'Usa el combobox con búsqueda para encontrar el tipo correcto'
        },
        {
          title: 'Asigna Cliente y Abogado',
          description: 'Selecciona uno o varios clientes asociados y el abogado responsable del proceso'
        },
        {
          title: 'Define Subclase y Etapa',
          description: 'Especifica la subclase del proceso y la etapa procesal actual'
        },
        {
          title: 'Adjunta archivos',
          description: 'Sube documentos relacionados (demanda, poder, etc.)'
        },
        {
          title: 'Guarda el proceso',
          description: 'Click en "Guardar" para crear el proceso en el sistema'
        }
      ],
      restrictions: [
        'Solo los abogados y administradores pueden crear procesos',
        'El administrador debe seleccionar un abogado responsable antes de guardar',
        'Todos los campos marcados con * son obligatorios',
        'Los clientes NO tienen acceso a esta funcionalidad'
      ],
      tips: [
        'Usa el combobox de búsqueda para encontrar rápidamente el tipo de proceso',
        'Puedes subir múltiples archivos a la vez',
        'Asegúrate de asignar el cliente correcto para que pueda ver el proceso'
      ],
      example: {
        title: 'Ejemplo: Radicar un Proceso de Tutela',
        description: 'Paso a paso para crear un nuevo proceso de tutela en el sistema.',
        steps: [
          {
            title: 'Accede a Radicar Proceso',
            description: 'Desde la lista de procesos, click en el botón "Nuevo" junto al contador de resultados'
          },
          {
            title: 'Información de las Partes',
            description: 'Demandante: "Juan Pérez García", Demandado: "EPS Salud Total"'
          },
          {
            title: 'Tipo y Autoridad',
            description: 'Tipo: "Tutela", Autoridad: "Juzgado 10 Civil Municipal de Bogotá"'
          },
          {
            title: 'Referencia',
            description: 'Radicado: "2024-00123", Subclase: "Derecho a la Salud"'
          },
          {
            title: 'Asignaciones',
            description: 'Clientes: Selecciona uno o varios clientes (por ejemplo, "Juan Pérez") de la lista. Abogado: Asigna el responsable del caso.'
          },
          {
            title: 'Etapa y Archivos',
            description: 'Etapa: "Admisión", Adjunta: demanda.pdf, poder.pdf, documentos_identidad.pdf'
          },
          {
            title: 'Guardar',
            description: 'Revisa toda la información y click en "Guardar"'
          }
        ],
        tips: [
          'Para tutelas, la etapa inicial suele ser "Admisión"',
          'Adjunta siempre el poder y la demanda en el momento de radicar',
          'El cliente recibirá notificación del nuevo proceso'
        ],
        commonErrors: [
          'Olvidar adjuntar el poder - es un documento obligatorio',
          'No asignar el cliente correcto - el cliente no podrá ver el proceso',
          'Dejar campos obligatorios vacíos - el sistema no permitirá guardar'
        ]
      }
    },
    {
      id: 'process-detail',
      name: 'Detalle de Proceso',
      description: 'Información completa de un proceso',
      roles: ['lawyer', 'client', 'corporate_client', 'basic'],
      content: `
        <p>El detalle del proceso muestra toda la información relevante y el historial completo del caso.</p>
      `,
      features: [
        'Información completa del caso',
        'Timeline visual de etapas con burbujas',
        'Expediente digital con tabla de archivos',
        'Búsqueda de documentos en el expediente',
        'Descarga individual de archivos',
        'Paginación de archivos (10 por página)',
        'Botón "Ver usuarios" para abrir un modal con todos los clientes asociados al proceso (foto o iniciales y nombre completo)',
        'Barra de progreso que refleja de forma continua el porcentaje de avance del proceso'
      ],
      tips: [
        'Usa la búsqueda del expediente para encontrar documentos específicos',
        'El timeline muestra visualmente el progreso del caso',
        'Si un proceso tiene varios clientes, utiliza "Ver usuarios" para confirmar todas las personas asociadas'
      ]
    },
    {
      id: 'request-info',
      name: 'Solicitar Información',
      description: 'Clientes pueden solicitar información sobre procesos',
      roles: ['client', 'corporate_client'],
      content: `
        <p>Los clientes pueden solicitar información adicional sobre sus procesos directamente desde el detalle.</p>
      `,
      features: [
        'Botón "Solicitar Información" en el detalle del proceso',
        'Formulario pre-llenado con información del proceso',
        'Envío directo al abogado responsable'
      ],
      steps: [
        {
          title: 'Abre el detalle del proceso',
          description: 'Click en el proceso que te interesa'
        },
        {
          title: 'Click en "Solicitar Información"',
          description: 'Botón visible en la parte superior'
        },
        {
          title: 'Completa tu consulta',
          description: 'Describe qué información necesitas'
        },
        {
          title: 'Envía la solicitud',
          description: 'El abogado recibirá tu consulta'
        }
      ]
    },
    {
      id: 'process-stages-management',
      name: 'Gestión de Etapas con Fechas',
      description: 'Control de fechas por etapa procesal',
      roles: ['lawyer', 'client', 'corporate_client', 'basic'],
      content: `
        <p>Cada etapa del proceso cuenta ahora con una <strong>fecha explícita</strong> que puede ser definida por el abogado o usar la fecha actual por defecto.</p>
        <p class="mt-2">Esto permite mantener una línea de tiempo precisa del caso y facilita el seguimiento de actuaciones judiciales.</p>
      `,
      features: [
        'Fecha personalizable por cada etapa procesal',
        'Fecha automática (actual) si no se especifica',
        'Edición de fechas en cualquier momento',
        'Histórico ordenado cronológicamente',
        'Visualización clara de la línea de tiempo del caso',
        'Control preciso de vencimientos y plazos'
      ],
      steps: [
        {
          title: 'Accede a Editar Proceso',
          description: 'Desde la lista de procesos, click en el botón de editar del proceso'
        },
        {
          title: 'Tabla de Etapas',
          description: 'Verás una tabla con columnas: Descripción de Etapa y Fecha'
        },
        {
          title: 'Define la Fecha',
          description: 'Click en el campo de fecha y selecciona del calendario la fecha real de la etapa'
        },
        {
          title: 'Fecha Automática',
          description: 'Si no defines fecha, el sistema usará automáticamente la fecha actual'
        },
        {
          title: 'Agregar Etapas',
          description: 'Puedes agregar nuevas etapas con sus respectivas fechas'
        },
        {
          title: 'Guardar Cambios',
          description: 'Click en "Guardar" para actualizar el proceso con las fechas definidas'
        }
      ],
      tips: [
        'Define fechas reales de audiencias y actuaciones para mejor trazabilidad',
        'Puedes corregir fechas pasadas si fueron registradas incorrectamente',
        'El histórico procesal mostrará las etapas ordenadas por estas fechas',
        'Útil para calcular tiempos entre etapas y generar reportes'
      ],
      restrictions: [
        'Solo los abogados pueden editar fechas de etapas',
        'Los clientes solo pueden visualizar las fechas en el histórico'
      ],
      example: {
        title: 'Ejemplo: Ajustando Fechas de un Proceso de Tutela',
        description: 'Cómo registrar las fechas reales de cada etapa procesal.',
        steps: [
          {
            title: 'Proceso Creado',
            description: 'Tienes un proceso de tutela con etapas: Admisión, Traslado, Fallo',
            note: 'Inicialmente todas tienen la fecha de creación'
          },
          {
            title: 'Editar Proceso',
            description: 'Click en editar para acceder a la tabla de etapas'
          },
          {
            title: 'Admisión - 12/10/2024',
            description: 'Seleccionas la fecha real cuando se admitió la tutela'
          },
          {
            title: 'Traslado - 15/10/2024',
            description: 'Fecha cuando se corrió traslado a la entidad accionada'
          },
          {
            title: 'Fallo - 30/10/2024',
            description: 'Fecha de la sentencia del juez'
          },
          {
            title: 'Guardar',
            description: 'El histórico ahora muestra la cronología real del caso'
          }
        ],
        tips: [
          'Registra fechas apenas ocurran las actuaciones',
          'Mantén un calendario de audiencias para no olvidar fechas',
          'El cliente verá estas fechas en el histórico procesal'
        ]
      }
    },
    {
      id: 'process-detail-visual',
      name: 'Vista Optimizada del Detalle',
      description: 'Interfaz moderna con avatar y tarjetas',
      roles: ['lawyer', 'client', 'corporate_client', 'basic'],
      content: `
        <p>El detalle del proceso ha sido completamente rediseñado con una <strong>interfaz visual moderna</strong> que facilita la consulta de información.</p>
        <p class="mt-2">Ahora incluye avatar del cliente, tarjetas organizadas y una barra de progreso visual tipo chevron.</p>
      `,
      features: [
        'Avatar circular con iniciales del cliente',
        'Encabezado con nombre completo y etiqueta de rol',
        'Dos tarjetas principales: Información del Proceso y Expediente',
        'Barra de progreso tipo chevron (Inicio → Etapa Actual → Fin)',
        'Porcentaje de avance del proceso',
        'Botón integrado "Histórico Procesal"',
        'Secciones organizadas: Oficina/Autoridad y Partes del Proceso',
        'Diseño responsive para móvil y escritorio'
      ],
      steps: [
        {
          title: 'Abre el Detalle',
          description: 'Click en cualquier proceso de la lista'
        },
        {
          title: 'Encabezado Modernizado',
          description: 'Verás el avatar del cliente a la izquierda con su nombre y rol'
        },
        {
          title: 'Tarjeta de Información',
          description: 'Primera tarjeta muestra tipo de proceso, autoridad, radicado y partes'
        },
        {
          title: 'Barra de Progreso',
          description: 'Visualiza el avance con flechas: Inicio → Etapa Actual → Fin'
        },
        {
          title: 'Histórico Procesal',
          description: 'Click en el botón para ver todas las etapas con sus fechas'
        },
        {
          title: 'Tarjeta de Expediente',
          description: 'Segunda tarjeta lista todos los documentos del caso'
        }
      ],
      tips: [
        'El avatar muestra las iniciales si no hay foto de perfil',
        'La barra de progreso da una idea visual rápida del avance',
        'El histórico procesal ahora muestra fechas reales de cada etapa'
      ]
    },
    {
      id: 'process-historical',
      name: 'Histórico Procesal Mejorado',
      description: 'Timeline con fechas reales por etapa',
      roles: ['lawyer', 'client', 'corporate_client', 'basic'],
      content: `
        <p>El <strong>Histórico Procesal</strong> ahora muestra una línea de tiempo clara con las fechas reales de cada etapa del proceso.</p>
        <p class="mt-2">Las etapas se ordenan cronológicamente según las fechas definidas, no solo por orden de creación.</p>
      `,
      features: [
        'Modal amplio y legible',
        'Lista numerada de todas las etapas',
        'Fecha asociada a cada etapa (definida por usuario o automática)',
        'Etapas ordenadas por fecha (más recientes primero)',
        'Nombre descriptivo de cada etapa',
        'Sin elementos decorativos innecesarios',
        'Diseño centrado en la información'
      ],
      steps: [
        {
          title: 'Abre el Detalle del Proceso',
          description: 'Click en el proceso que quieres consultar'
        },
        {
          title: 'Click en "Histórico Procesal"',
          description: 'Botón integrado con la barra de progreso'
        },
        {
          title: 'Visualiza la Línea de Tiempo',
          description: 'Verás todas las etapas ordenadas cronológicamente'
        },
        {
          title: 'Revisa Fechas',
          description: 'Cada etapa muestra su fecha real de ocurrencia'
        },
        {
          title: 'Cierra el Modal',
          description: 'Click en X, botón Cerrar o fuera del modal'
        }
      ],
      tips: [
        'Útil para entender la duración real del proceso',
        'Permite identificar etapas que tomaron más tiempo',
        'Los clientes pueden ver cuándo ocurrió cada actuación'
      ],
      example: {
        title: 'Ejemplo: Consultando Histórico de Tutela',
        description: 'Cómo revisar la cronología completa de un caso.',
        steps: [
          {
            title: 'Abrir Proceso',
            description: 'Cliente abre el detalle de su tutela'
          },
          {
            title: 'Click en Histórico',
            description: 'Botón visible en la barra de progreso'
          },
          {
            title: 'Ver Etapas',
            description: '1. Investigación - 12 oct 2024\n2. Alegatos - 15 ene 2025\n3. Pliego de Cargos - 06 jun 2025\n4. Fallo - 05 sept 2025'
          },
          {
            title: 'Comprender Duración',
            description: 'El cliente ve que el proceso duró casi un año'
          }
        ]
      }
    },
    {
      id: 'edit-process',
      name: 'Editar Proceso',
      description: 'Modificar un proceso judicial existente',
      roles: ['lawyer'],
      content: `
        <p>Los abogados pueden editar procesos existentes para actualizar información, agregar etapas, modificar partes involucradas o actualizar archivos del expediente.</p>
      `,
      features: [
        'Precarga de todos los datos del proceso',
        'Modificar tipo de caso y subcaso',
        'Actualizar partes (demandante, demandado)',
        'Agregar o quitar clientes asociados',
        'Agregar nuevas etapas procesales con fecha',
        'Actualizar archivos del expediente',
        'Cambiar abogado responsable'
      ],
      steps: [
        {
          title: 'Accede al Proceso',
          description: 'Navega al detalle del proceso que deseas editar'
        },
        {
          title: 'Click en "Editar"',
          description: 'Botón disponible en la vista de detalle del proceso'
        },
        {
          title: 'Modifica los Campos',
          description: 'Actualiza la información necesaria (los datos existentes están precargados)'
        },
        {
          title: 'Guarda los Cambios',
          description: 'Click en "Guardar" para confirmar las modificaciones'
        }
      ],
      restrictions: [
        'Solo los abogados pueden editar procesos',
        'Los procesos archivados no pueden ser editados'
      ],
      tips: [
        'Revisa todos los campos antes de guardar para asegurarte de que la información es correcta',
        'Al agregar nuevas etapas, define la fecha real de ocurrencia',
        'Los cambios se reflejan inmediatamente en el detalle del proceso'
      ]
    },
    {
      id: 'case-file-upload',
      name: 'Expediente Digital',
      description: 'Subir y gestionar archivos del expediente',
      roles: ['lawyer'],
      content: `
        <p>El expediente digital permite subir y organizar todos los documentos relevantes de un proceso judicial. Los archivos se pueden buscar, descargar y paginar.</p>
      `,
      features: [
        'Upload múltiple de archivos',
        'Drag & drop para subir archivos',
        'Tabla de archivos con búsqueda',
        'Descarga individual de archivos',
        'Paginación (10 archivos por página)',
        'Tipos soportados: PDF, DOC, DOCX, JPG, PNG y más'
      ],
      steps: [
        {
          title: 'Accede al Detalle del Proceso',
          description: 'Navega al proceso donde quieres subir archivos'
        },
        {
          title: 'Sección Expediente Digital',
          description: 'Scroll hacia la tarjeta de expediente digital'
        },
        {
          title: 'Sube Archivos',
          description: 'Arrastra archivos al área de upload o click para seleccionar'
        },
        {
          title: 'Busca Archivos',
          description: 'Usa la barra de búsqueda para encontrar archivos específicos'
        },
        {
          title: 'Descarga',
          description: 'Click en el botón de descarga junto a cada archivo'
        }
      ],
      tips: [
        'Sube todos los documentos relevantes para tener un expediente completo',
        'Usa nombres descriptivos en los archivos para facilitar la búsqueda',
        'Los clientes pueden ver los archivos del expediente en el detalle del proceso'
      ]
    }
  ]
};
