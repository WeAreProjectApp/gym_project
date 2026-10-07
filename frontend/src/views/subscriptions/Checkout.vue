<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <div class="bg-white border-b border-gray-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div class="flex items-center justify-between">
          <button
            @click="goBack"
            class="flex items-center gap-2 text-gray-600 hover:text-primary transition-colors"
          >
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
            </svg>
            <span class="text-sm font-medium">Volver a planes</span>
          </button>
          <h1 class="text-xl font-bold text-primary">Finalizar Suscripción</h1>
          <div class="w-24"></div>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <!-- Plan Details - Left Side -->
        <div class="lg:col-span-2 space-y-6">
          <!-- User Info -->
          <div class="bg-white rounded-xl border border-gray-200 p-6">
            <h2 class="text-lg font-semibold text-primary mb-4">Información de contacto</h2>
            <div class="bg-terciary border border-stroke rounded-lg p-4">
              <div class="flex items-center gap-3">
                <div class="h-12 w-12 rounded-full bg-secondary flex items-center justify-center text-white font-semibold">
                  {{ userInitials }}
                </div>
                <div>
                  <p class="font-medium text-gray-900">{{ userStore.currentUser?.first_name }} {{ userStore.currentUser?.last_name }}</p>
                  <p class="text-sm text-gray-600">{{ userStore.currentUser?.email }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- Plan Selected -->
          <div class="bg-white rounded-xl border border-gray-200 p-6">
            <h2 class="text-lg font-semibold text-primary mb-4">Plan seleccionado</h2>
            <div class="border border-gray-200 rounded-lg p-6">
              <div class="flex items-start justify-between mb-4">
                <div>
                  <h3 class="text-xl font-bold" :class="planColor">{{ planDetails.name }}</h3>
                  <p class="text-sm text-gray-600 mt-1">{{ planDetails.description }}</p>
                </div>
                <div class="text-right">
                  <p class="text-2xl font-bold text-primary">{{ planDetails.price }}</p>
                  <p class="text-sm text-gray-500">{{ planDetails.billing }}</p>
                </div>
              </div>
              
              <!-- Key Features -->
              <div class="border-t border-gray-200 pt-4 mt-4">
                <p class="text-sm font-medium text-gray-700 mb-3">Características principales:</p>
                <div class="space-y-2">
                  <div v-for="(feature, index) in planDetails.keyFeatures" :key="index" class="flex items-start gap-2 text-sm text-gray-700">
                    <svg class="h-4 w-4 text-secondary flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                    </svg>
                    <span>{{ feature }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Paid plans: online payment is not available. The Wompi card form and its third-party script
               loaders were removed (hotfix 2026-10-07, see docs/hotfixes/2026-10-07-remove-unused-third-party-loaders.md). -->
          <div v-if="planDetails.amountInCents > 0" class="bg-white rounded-xl border border-gray-200 p-6" data-testid="checkout-paid-unavailable">
            <h2 class="text-lg font-semibold text-primary mb-4">Método de pago</h2>
            <div class="bg-terciary border border-stroke rounded-lg p-4">
              <p class="text-sm font-medium text-gray-900">El pago en línea no está disponible por ahora</p>
              <p class="text-xs text-gray-600 mt-1">Este plan estará disponible próximamente. Mientras tanto puedes activar el Plan Básico gratuito.</p>
            </div>
          </div>

        </div>

        <!-- Order Summary - Right Side -->
        <div class="lg:col-span-1">
          <div class="bg-white rounded-xl border border-gray-200 p-6 sticky top-8">
            <h2 class="text-lg font-semibold text-primary mb-4">Resumen del pedido</h2>
            
            <div class="space-y-3 mb-6">
              <div class="flex justify-between text-sm">
                <span class="text-gray-600">{{ planDetails.name }}</span>
                <span class="font-medium text-gray-900">{{ planDetails.price }}</span>
              </div>
              <div class="flex justify-between text-sm">
                <span class="text-gray-600">Plan de {{ planDetails.duration }}</span>
                <span class="font-medium text-gray-900">{{ planDetails.billing }}</span>
              </div>
              
              <div class="border-t border-gray-200 pt-3 mt-3">
                <div class="flex justify-between">
                  <span class="text-sm text-gray-600">Subtotal</span>
                  <span class="text-sm font-medium text-gray-900">{{ planDetails.price }}</span>
                </div>
              </div>
              
              <div class="border-t border-gray-200 pt-3">
                <div class="flex justify-between">
                  <span class="font-semibold text-gray-900">Total a pagar hoy</span>
                  <span class="text-xl font-bold text-primary">{{ planDetails.price }}</span>
                </div>
              </div>
            </div>

            <button
              @click="handleSubscribe"
              :disabled="isProcessing || planDetails.amountInCents > 0"
              :class="{
                'w-full px-6 py-3 bg-secondary rounded-lg text-base font-semibold text-white hover:bg-blue-700 transition-all duration-200 mb-4': !isProcessing && planDetails.amountInCents === 0,
                'w-full px-6 py-3 bg-gray-400 rounded-lg text-base font-semibold text-white cursor-not-allowed mb-4': isProcessing || planDetails.amountInCents > 0
              }"
            >
              <span v-if="isProcessing" class="flex items-center justify-center gap-2">
                <svg class="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Procesando...
              </span>
              <span v-else>
                {{ planDetails.amountInCents === 0 ? 'Activar Plan Gratuito' : 'Próximamente' }}
              </span>
            </button>

            <div class="text-center">
              <div class="flex items-center justify-center gap-2 text-xs text-gray-500 mb-2">
                <svg class="h-4 w-4 text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path>
                </svg>
                <span>Pago seguro y protegido</span>
              </div>
              <p class="text-xs text-gray-500">30 días de garantía de reembolso</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useUserStore } from '@/stores/auth/user';
import { useSubscriptionStore } from '@/stores/subscriptions';
import Swal from 'sweetalert2';

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();
const subscriptionStore = useSubscriptionStore();

const planType = ref(route.params.plan);
const isProcessing = ref(false);

const planDetails = computed(() => {
  const plans = {
    basico: {
      name: 'Plan Básico',
      description: 'Personas con necesidades legales básicas',
      price: 'Gratuito',
      billing: '/mes',
      duration: '48 meses',
      color: 'text-primary',
      amountInCents: 0,
      keyFeatures: [
        'Consulta Procesos Judiciales',
        '+100 Documentos Jurídicos',
        'Firma Electrónica (solo recibe)',
      ]
    },
    cliente: {
      name: 'Plan Cliente',
      description: 'Clientes individuales o emprendedores',
      price: '$22,900 COP',
      billing: '/mes',
      duration: '48 meses',
      color: 'text-secondary',
      amountInCents: 2290000, // $22,900 COP in cents
      keyFeatures: [
        '+500 Documentos Premium',
        'Membrete Personalizado',
        'Firma Electrónica completa',
        'Envío ilimitado de documentos',
        '3 docs personalizados incluidos',
        '2h consultoría mensual',
      ]
    },
    corporativo: {
      name: 'Plan Corporativo',
      description: 'Empresas, pymes y organizaciones',
      price: '$550,000 COP',
      billing: '/mes',
      duration: '48 meses',
      color: 'text-primary',
      amountInCents: 55000000, // $550,000 COP in cents
      keyFeatures: [
        '+1000 Docs Premium y Corporativos',
        'Usuarios Vinculados',
        'Módulo de Organizaciones',
        '5 docs de alta complejidad',
        '10 revisiones mensuales',
        '10h consultoría mensual',
      ]
    }
  };

  return plans[planType.value] || plans.basico;
});

const planColor = computed(() => planDetails.value.color);

const userInitials = computed(() => {
  const firstName = userStore.currentUser?.first_name || '';
  const lastName = userStore.currentUser?.last_name || '';
  return `${firstName.charAt(0)}${lastName.charAt(0)}`.toUpperCase();
});

const goBack = () => {
  router.push({ name: 'subscriptions' });
};

const handleSubscribe = async () => {
  if (isProcessing.value) return;

  // Free plan - no payment needed
  if (planDetails.value.amountInCents === 0) {
    isProcessing.value = true;
    try {
      await subscriptionStore.createSubscription({
        plan_type: planType.value,
      });

      await Swal.fire({
        title: '¡Suscripción Activada!',
        text: 'Tu plan gratuito ha sido activado exitosamente.',
        icon: 'success',
        confirmButtonColor: '#3348FF',
      });

      router.push({ name: 'dashboard' });
    } catch (error) {
      await Swal.fire({
        title: 'Error',
        text: error.response?.data?.error || 'No se pudo activar tu suscripción. Por favor, intenta nuevamente.',
        icon: 'error',
        confirmButtonColor: '#3348FF',
      });
    } finally {
      isProcessing.value = false;
    }
    return;
  }

  // Paid plans: online payment is not available (hotfix 2026-10-07). The button is disabled;
  // this guard keeps a programmatic call from creating a subscription without payment.
  await Swal.fire({
    title: 'Próximamente',
    text: 'El pago en línea no está disponible por ahora. Mientras tanto puedes activar el Plan Básico gratuito.',
    icon: 'info',
    confirmButtonColor: '#3348FF',
  });
};

onMounted(async () => {
  // Ensure user store is initialized
  if (!userStore.currentUser) {
    await userStore.init();
  }
});
</script>
