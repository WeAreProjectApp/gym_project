<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header Section -->
    <div class="bg-white">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
        <div class="text-center">
          <h1 class="text-3xl sm:text-5xl font-bold text-gray-900 mb-4">
            Servicios Legales
          </h1>
          <div class="flex flex-wrap items-center justify-center gap-6 text-sm text-gray-600 mt-6">
            <div class="flex items-center gap-2">
              <svg class="h-5 w-5 text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
              </svg>
              <span>30 días de garantía de reembolso</span>
            </div>
            <div class="flex items-center gap-2">
              <svg class="h-5 w-5 text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
              </svg>
              <span>Ayuda las 24 horas</span>
            </div>
            <div class="flex items-center gap-2">
              <svg class="h-5 w-5 text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
              </svg>
              <span>Cancela en cualquier momento</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
      <!-- Plans Grid -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-12">
        <!-- Plan Básico -->
        <div class="bg-white rounded-xl border border-gray-200 hover:border-gray-300 transition-all duration-200 relative overflow-hidden">
          <div class="p-6">
            <div class="mb-4">
              <h3 class="text-2xl font-bold text-primary mb-2">Plan Básico</h3>
              <p class="text-sm text-gray-600">Personas con necesidades legales básicas</p>
            </div>
            <div class="mb-6">
              <div class="flex items-baseline gap-1">
                <span class="text-4xl font-bold text-primary">Gratuito</span>
              </div>
            </div>
            <button @click="selectPlan('basico')" class="w-full px-6 py-3 bg-white border-2 border-gray-300 rounded-lg text-base font-semibold text-gray-700 hover:bg-gray-50 transition-all duration-200 mb-6">
              Elegir plan
            </button>
            <div class="space-y-3 text-sm">
              <div class="flex items-start gap-2 text-gray-700">
                <svg class="h-4 w-4 text-secondary flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
                <span>Consulta Procesos Judiciales</span>
              </div>
              <div class="flex items-start gap-2 text-gray-700">
                <svg class="h-4 w-4 text-secondary flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
                <div>
                  <div>Documentos Jurídicos</div>
                  <div class="text-xs text-gray-500">+100 Docs.</div>
                </div>
              </div>
              <div class="flex items-start gap-2 text-gray-500">
                <svg class="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
                <span>Membrete Personalizado</span>
              </div>
              <div class="flex items-start gap-2 text-gray-700">
                <svg class="h-4 w-4 text-yellow-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
                </svg>
                <div>
                  <div>Firma Electrónica</div>
                  <div class="text-xs text-gray-500">Solo recibe Docs. para firma</div>
                </div>
              </div>
              <div class="flex items-start gap-2 text-gray-500">
                <svg class="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
                <span>Envío de Documentos para Firma Electrónica</span>
              </div>
              <div class="flex items-start gap-2 text-gray-500">
                <svg class="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
                <span>Usuarios Vinculados</span>
              </div>
              <div class="flex items-start gap-2 text-gray-500">
                <svg class="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
                <span>Módulo de Organizaciones</span>
              </div>
              <div class="flex items-start gap-2 text-gray-500">
                <svg class="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
                <span>Documentos personalizados a la medida por Expertos</span>
              </div>
              <div class="flex items-start gap-2 text-gray-500">
                <svg class="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
                <span>Revisión por Abogados Expertos</span>
              </div>
              <div class="flex items-start gap-2 text-gray-500">
                <svg class="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
                <span>Consultoría Profesional</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Plan Cliente -->
        <div class="bg-white rounded-xl border-2 border-secondary hover:border-secondary transition-all duration-200 relative overflow-hidden shadow-lg">
          <div class="absolute top-4 right-4">
            <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-selected-background text-secondary">
              MÁS VENDIDO
            </span>
          </div>
          <div class="p-6">
            <div class="mb-4">
              <h3 class="text-2xl font-bold text-secondary mb-2">Plan Cliente</h3>
              <p class="text-sm text-gray-600">Clientes individuales o emprendedores</p>
            </div>
            <div class="mb-6">
              <div class="flex items-baseline gap-1">
                <span class="text-sm text-gray-500">COP</span>
                <span class="text-4xl font-bold text-secondary">$22,900</span>
                <span class="text-sm text-gray-500">/mes</span>
              </div>
            </div>
            <!-- Paid plan: online payment is not available yet (hotfix 2026-10-07). -->
            <button type="button" disabled data-testid="plan-cliente-coming-soon" class="w-full px-6 py-3 bg-secondary rounded-lg text-base font-semibold text-white opacity-60 cursor-not-allowed mb-6">
              Próximamente
            </button>
            <div class="space-y-3 text-sm">
              <div class="flex items-start gap-2 text-gray-700">
                <svg class="h-4 w-4 text-secondary flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
                <span>Consulta Procesos Judiciales</span>
              </div>
              <div class="flex items-start gap-2 text-gray-700">
                <svg class="h-4 w-4 text-secondary flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
                <div>
                  <div>Documentos Jurídicos</div>
                  <div class="text-xs text-gray-500">+500 Docs Premium</div>
                </div>
              </div>
              <div class="flex items-start gap-2 text-gray-700">
                <svg class="h-4 w-4 text-secondary flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
                <span>Membrete Personalizado</span>
              </div>
              <div class="flex items-start gap-2 text-gray-700">
                <svg class="h-4 w-4 text-secondary flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
                <div>
                  <div>Firma Electrónica</div>
                  <div class="text-xs text-gray-500">Crear y enviar Docs. para firma</div>
                </div>
              </div>
              <div class="flex items-start gap-2 text-gray-700">
                <svg class="h-4 w-4 text-secondary flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
                <div>
                  <div>Envío de Documentos para Firma Electrónica</div>
                  <div class="text-xs text-gray-500">Ilimitado</div>
                </div>
              </div>
              <div class="flex items-start gap-2 text-gray-500">
                <svg class="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
                <span>Usuarios Vinculados</span>
              </div>
              <div class="flex items-start gap-2 text-gray-500">
                <svg class="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
                <span>Módulo de Organizaciones</span>
              </div>
              <div class="flex items-start gap-2 text-gray-700">
                <svg class="h-4 w-4 text-secondary flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
                <div>
                  <div>Documentos personalizados a la medida por Expertos</div>
                  <div class="text-xs text-gray-500">3 docs. personalizados de mediana y baja complejidad incluidos por única vez y -50% descuento por documentos personalizados extra</div>
                </div>
              </div>
              <div class="flex items-start gap-2 text-gray-700">
                <svg class="h-4 w-4 text-secondary flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
                <div>
                  <div>Revisión por Abogados Expertos</div>
                  <div class="text-xs text-gray-500">Revisiones de un experto de 3 docs. mensuales y -50% descuento en documentos personalizados extra</div>
                </div>
              </div>
              <div class="flex items-start gap-2 text-gray-700">
                <svg class="h-4 w-4 text-secondary flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
                <div>
                  <div>Consultoría Profesional</div>
                  <div class="text-xs text-gray-500">2h de consultoría especializada mensual incluida y 30% descuento en horas consultorías extra</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Plan Corporativo -->
        <div class="bg-white rounded-xl border border-gray-200 hover:border-primary transition-all duration-200 relative overflow-hidden">
          <div class="p-6">
            <div class="mb-4">
              <h3 class="text-2xl font-bold text-primary mb-2">Plan Corporativo</h3>
              <p class="text-sm text-gray-600">Empresas, pymes y organizaciones</p>
            </div>
            <div class="mb-6">
              <div class="flex items-baseline gap-1">
                <span class="text-sm text-gray-500">COP</span>
                <span class="text-4xl font-bold text-primary">$550,000</span>
                <span class="text-sm text-gray-500">/mes</span>
              </div>
            </div>
            <!-- Paid plan: online payment is not available yet (hotfix 2026-10-07). -->
            <button type="button" disabled data-testid="plan-corporativo-coming-soon" class="w-full px-6 py-3 bg-primary rounded-lg text-base font-semibold text-white opacity-60 cursor-not-allowed mb-6">
              Próximamente
            </button>
            <div class="space-y-3 text-sm">
              <div class="flex items-start gap-2 text-gray-700">
                <svg class="h-4 w-4 text-secondary flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
                <span>Consulta de procesos</span>
              </div>
              <div class="flex items-start gap-2 text-gray-700">
                <svg class="h-4 w-4 text-secondary flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
                <div>
                  <div>Documentos Jurídicos</div>
                  <div class="text-xs text-gray-500">+1000 Docs Premium y Corporativos</div>
                </div>
              </div>
              <div class="flex items-start gap-2 text-gray-700">
                <svg class="h-4 w-4 text-secondary flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
                <span>Membrete Personalizado</span>
              </div>
              <div class="flex items-start gap-2 text-gray-700">
                <svg class="h-4 w-4 text-secondary flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
                <div>
                  <div>Firma Electrónica</div>
                  <div class="text-xs text-gray-500">Crear y enviar Docs. para firma</div>
                </div>
              </div>
              <div class="flex items-start gap-2 text-gray-700">
                <svg class="h-4 w-4 text-secondary flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
                <div>
                  <div>Envío de Documentos para Firma Electrónica</div>
                  <div class="text-xs text-gray-500">Ilimitado con gestión avanzada</div>
                </div>
              </div>
              <div class="flex items-start gap-2 text-gray-700">
                <svg class="h-4 w-4 text-secondary flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
                <div>
                  <div>Usuarios Vinculados</div>
                  <div class="text-xs text-gray-500">Usuarios vinculados a la Organización adquieren automáticamente beneficios del Plan Cliente</div>
                </div>
              </div>
              <div class="flex items-start gap-2 text-gray-700">
                <svg class="h-4 w-4 text-secondary flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
                <div>
                  <div>Módulo de Organizaciones</div>
                  <div class="text-xs text-gray-500">Gestión de miembros, solicitudes y documentos personalizados</div>
                </div>
              </div>
              <div class="flex items-start gap-2 text-gray-700">
                <svg class="h-4 w-4 text-secondary flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
                <div>
                  <div>Documentos personalizados a la medida por Expertos</div>
                  <div class="text-xs text-gray-500">5 docs personalizados por un experto de alta complejidad y 50% descuento en documentos personalizados extra</div>
                </div>
              </div>
              <div class="flex items-start gap-2 text-gray-700">
                <svg class="h-4 w-4 text-secondary flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
                <div>
                  <div>Revisión por Abogados Expertos</div>
                  <div class="text-xs text-gray-500">Revisión de un experto de hasta 10 docs. mensuales de alta complejidad y -50% descuento en documentos personalizados extra</div>
                </div>
              </div>
              <div class="flex items-start gap-2 text-gray-700">
                <svg class="h-4 w-4 text-secondary flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
                <div>
                  <div>Consultoría Profesional</div>
                  <div class="text-xs text-gray-500">10h de consultoría especializada mensual incluida y 30% descuento en horas consultorías extra</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Info Section -->
      <div class="bg-terciary border border-stroke rounded-lg p-6 sm:p-8 text-center">
        <h3 class="text-xl font-semibold text-primary mb-3">
          ¿Necesitas más información?
        </h3>
        <p class="text-gray-600 mb-4">
          Contáctanos para conocer más detalles sobre nuestros planes y servicios.
        </p>
        <a 
          href="mailto:info@gymabogados.com" 
          class="inline-flex items-center text-secondary hover:text-blue-700 font-medium transition-colors duration-200"
        >
          <svg class="h-5 w-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path>
          </svg>
          info@gymabogados.com
        </a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth/auth';

const router = useRouter();
const authStore = useAuthStore();

const selectPlan = async (planType) => {
  // Check if user is authenticated
  const isAuthenticated = await authStore.isAuthenticated();
  
  if (isAuthenticated) {
    // If authenticated, go directly to checkout
    router.push({ name: 'checkout', params: { plan: planType } });
  } else {
    // If not authenticated, go to subscription sign in with plan as query param
    router.push({ name: 'subscription_sign_in', query: { plan: planType } });
  }
};

onMounted(() => {
  console.log('Subscriptions view loaded');
});
</script>
