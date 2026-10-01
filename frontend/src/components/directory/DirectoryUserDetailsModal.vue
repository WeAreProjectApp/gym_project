<template>
  <ModalTransition v-show="isVisible">
    <div class="relative bg-white rounded-xl shadow-xl max-w-3xl w-full max-h-[90vh] flex flex-col overflow-hidden">
      <!-- Header -->
      <div class="bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-5 flex items-center justify-between">
        <div class="min-w-0 flex-1 flex items-center gap-3 mr-3">
          <div class="relative shrink-0">
            <img
              v-if="user?.photo_profile"
              :src="user.photo_profile"
              :alt="userFullName"
              class="h-12 w-12 rounded-full object-cover border-2 border-white/40 shadow-sm"
            />
            <div
              v-else
              class="h-12 w-12 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center text-white font-semibold text-lg shadow-sm"
            >
              {{ userInitials }}
            </div>
          </div>
          <div class="min-w-0">
            <h2 class="text-lg font-semibold text-white [overflow-wrap:anywhere]">
              {{ userFullName }}
            </h2>
            <p class="text-blue-100 text-xs mt-0.5 [overflow-wrap:anywhere]">
              {{ roleLabel }} · {{ user?.email }}
            </p>
          </div>
        </div>
        <button
          type="button"
          aria-label="Cerrar detalle de usuario"
          @click="handleClose"
          class="directory-action shrink-0 flex items-center justify-center p-2.5 rounded-full text-white hover:text-blue-100 hover:bg-white/10 transition-colors"
        >
          <XMarkIcon class="h-5 w-5" />
        </button>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-6 bg-gray-50">
        <!-- User info section -->
        <section class="bg-white rounded-lg border border-gray-200 shadow-sm p-4 sm:p-5">
          <h3 class="text-sm font-semibold text-gray-900 mb-3">Información del usuario</h3>
          <dl class="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3 text-sm [&>div]:min-w-0 [&_dd]:[overflow-wrap:anywhere]">
            <div>
              <dt class="text-gray-500">Nombre completo</dt>
              <dd class="mt-0.5 text-gray-900">{{ userFullName || 'Sin información' }}</dd>
            </div>
            <div>
              <dt class="text-gray-500">Correo electrónico</dt>
              <dd class="mt-0.5 text-gray-900">{{ user?.email || 'Sin información' }}</dd>
            </div>
            <div>
              <dt class="text-gray-500">Identificación</dt>
              <dd class="mt-0.5 text-gray-900">{{ user?.identification || 'Sin información' }}</dd>
            </div>
            <div>
              <dt class="text-gray-500">Contacto</dt>
              <dd class="mt-0.5 text-gray-900">{{ user?.contact || 'Sin información' }}</dd>
            </div>
            <div>
              <dt class="text-gray-500">Rol</dt>
              <dd class="mt-0.5 text-gray-900">{{ roleLabel }}</dd>
            </div>
            <div>
              <dt class="text-gray-500">Fecha de nacimiento</dt>
              <dd class="mt-0.5 text-gray-900">{{ user?.birthday || 'Sin información' }}</dd>
            </div>
          </dl>
        </section>

        <!-- Processes section -->
        <section class="bg-white rounded-lg border border-gray-200 shadow-sm p-4 sm:p-5">
          <div class="flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between mb-3">
            <div class="min-w-0">
              <h3 class="text-sm font-semibold text-gray-900">Procesos del usuario</h3>
              <p class="text-xs text-gray-500 mt-0.5">
                {{ processes.length > 0 ? `Se encontraron ${processes.length} proceso(s) asociados` : 'Este usuario no tiene procesos registrados.' }}
              </p>
            </div>
            <button
              v-if="processes.length > 0"
              type="button"
              @click="goToProcessList"
              class="directory-action shrink-0 inline-flex items-center justify-center px-3 py-1.5 rounded-md border border-gray-200 text-xs font-medium text-gray-700 bg-gray-50 hover:bg-gray-100"
            >
              Ver todos en Procesos
            </button>
          </div>

          <div v-if="isLoading" class="flex items-center justify-center py-8">
            <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
            <span class="ml-3 text-sm text-gray-500">Cargando procesos...</span>
          </div>

          <div v-else-if="processes.length === 0" class="flex flex-col items-center justify-center py-8 text-center">
            <CubeTransparentIcon class="h-10 w-10 text-gray-300" />
            <p class="mt-2 text-sm text-gray-600">No se encontraron procesos para este usuario.</p>
          </div>

          <div v-else class="space-y-3 max-h-[40vh] overflow-y-auto pr-1">
            <article
              v-for="process in processes"
              :key="process.id"
              class="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 flex flex-col sm:flex-row items-start justify-between gap-3 hover:border-blue-200 hover:bg-blue-50/40 transition-colors"
            >
              <div class="min-w-0 flex-1">
                <h4 class="text-sm font-semibold text-blue-700 [overflow-wrap:anywhere]">
                  {{ process.case?.type || 'Proceso sin tipo' }}
                </h4>
                <p class="mt-0.5 text-xs text-gray-600 [overflow-wrap:anywhere]">
                  {{ process.subcase || 'Sin descripción' }}
                </p>
                <p class="mt-1 text-[11px] text-gray-500 [overflow-wrap:anywhere]">
                  Radicado: <span class="font-medium">{{ process.ref || 'N/A' }}</span>
                  · Autoridad: <span class="font-medium">{{ process.authority || 'N/A' }}</span>
                </p>
                <p class="mt-1 text-[11px] text-gray-500">
                  Última etapa:
                  <span class="font-medium">
                    {{ (process.stages && process.stages.length > 0) ? process.stages[process.stages.length - 1].status : 'Sin etapas' }}
                  </span>
                </p>
              </div>
              <div class="flex flex-col items-end gap-2 flex-shrink-0">
                <span class="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium bg-blue-50 text-blue-700 border border-blue-100">
                  {{ process.case?.type ? 'Expediente' : 'Proceso' }} #{{ process.id }}
                </span>
                <button
                  type="button"
                  @click="goToProcessDetail(process.id)"
                  class="directory-action inline-flex items-center justify-center px-3 py-1.5 rounded-md text-xs font-medium text-blue-700 bg-white border border-blue-200 hover:bg-blue-50"
                >
                  Ver proceso
                </button>
              </div>
            </article>
          </div>
        </section>
      </div>
    </div>
  </ModalTransition>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useProcessStore } from '@/stores/process';
import ModalTransition from '@/components/layouts/animations/ModalTransition.vue';
import { XMarkIcon, CubeTransparentIcon } from '@heroicons/vue/24/outline';

const props = defineProps({
  isVisible: {
    type: Boolean,
    default: false,
  },
  user: {
    type: Object,
    required: true,
  },
});

const emit = defineEmits(['close']);

const router = useRouter();
const processStore = useProcessStore();
const isLoading = ref(false);

const userFullName = computed(() => {
  if (!props.user) return '';
  const first = props.user.first_name || '';
  const last = props.user.last_name || '';
  const full = `${first} ${last}`.trim();
  return full || props.user.email || 'Usuario';
});

const userInitials = computed(() => {
  if (!props.user) return '';
  const first = (props.user.first_name || '').charAt(0);
  const last = (props.user.last_name || '').charAt(0);
  const initials = `${first}${last}`.trim();
  return initials || (props.user.email ? props.user.email.charAt(0).toUpperCase() : '?');
});

const roleLabel = computed(() => {
  const role = props.user?.role;
  if (role === 'client') return 'Cliente';
  if (role === 'basic') return 'Básico';
  if (role === 'corporate_client') return 'Corporativo';
  if (role === 'lawyer') return 'Abogado';
  return 'Usuario';
});

const processes = computed(() => {
  if (!props.user || !processStore.processes || processStore.processes.length === 0) return [];
  const role = props.user.role;
  const userId = props.user.id;

  return processStore.processes.filter((p) => {
    if (!p) return false;
    if (role === 'client' || role === 'basic' || role === 'corporate_client') {
      return p.client && p.client.id === userId;
    }
    if (role === 'lawyer') {
      return p.lawyer && p.lawyer.id === userId;
    }
    return false;
  });
});

const loadProcesses = async () => {
  if (processStore.dataLoaded) return;
  isLoading.value = true;
  try {
    await processStore.fetchProcessesData();
  } finally {
    isLoading.value = false;
  }
};

const handleClose = () => {
  emit('close');
};

const goToProcessDetail = (processId) => {
  emit('close');
  router.push({ name: 'process_detail', params: { process_id: processId } });
};

const goToProcessList = () => {
  if (!props.user) return;
  emit('close');
  router.push({ name: 'process_list', params: { user_id: props.user.id, display: '' } });
};

watch(
  () => props.isVisible,
  (visible) => {
    if (visible) {
      loadProcesses();
    }
  }
);

onMounted(() => {
  if (props.isVisible) {
    loadProcesses();
  }
});
</script>

<style scoped>
.directory-action {
  min-width: calc(44px / var(--app-zoom, 1));
  min-height: calc(44px / var(--app-zoom, 1));
}
</style>
