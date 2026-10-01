<template>
  <TransitionRoot as="template" :show="open">
    <Dialog as="div" class="relative z-50" @close="$emit('close')">
      <TransitionChild
        as="template"
        enter="ease-out duration-300"
        enter-from="opacity-0"
        enter-to="opacity-100"
        leave="ease-in duration-200"
        leave-from="opacity-100"
        leave-to="opacity-0"
      >
        <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
      </TransitionChild>

      <div class="fixed inset-0 z-10 overflow-y-auto">
        <div class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
          <TransitionChild
            as="template"
            enter="ease-out duration-300"
            enter-from="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            enter-to="opacity-100 translate-y-0 sm:scale-100"
            leave="ease-in duration-200"
            leave-from="opacity-100 translate-y-0 sm:scale-100"
            leave-to="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
          >
            <DialogPanel data-testid="guide-example-dialog" class="guide-example relative w-full transform rounded-lg bg-white px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:max-w-3xl sm:p-6">
              <!-- Close button -->
              <div class="absolute right-0 top-0 pr-4 pt-4">
                <button
                  type="button"
                  data-testid="guide-example-close"
                  class="flex items-center justify-center rounded-md bg-white text-gray-400 hover:text-gray-500 focus:outline-none"
                  @click="$emit('close')"
                >
                  <span class="sr-only">Cerrar</span>
                  <XMarkIcon class="h-6 w-6" aria-hidden="true" />
                </button>
              </div>

              <!-- Content -->
              <div class="sm:flex sm:items-start">
                <div class="mt-3 text-center sm:mt-0 sm:text-left w-full">
                  <!-- Header -->
                  <DialogTitle as="h3" class="pr-[calc(60px/var(--app-zoom,1))] break-words text-2xl font-bold leading-6 text-gray-900 mb-4">
                    {{ example.title }}
                  </DialogTitle>

                  <!-- Description -->
                  <div class="mt-2 mb-6">
                    <p class="text-sm text-gray-600">
                      {{ example.description }}
                    </p>
                  </div>

                  <!-- Steps -->
                  <div class="space-y-4 mb-6">
                    <h4 class="text-lg font-semibold text-gray-900">Paso a Paso:</h4>
                    <ol class="space-y-4">
                      <li
                        v-for="(step, index) in example.steps"
                        :key="index"
                        class="flex items-start space-x-4"
                      >
                        <div class="flex-shrink-0 w-8 h-8 bg-indigo-600 text-white rounded-full flex items-center justify-center font-bold text-sm">
                          {{ index + 1 }}
                        </div>
                        <div class="flex-1">
                          <p class="text-gray-900 font-medium">{{ step.title }}</p>
                          <p class="text-gray-600 text-sm mt-1">{{ step.description }}</p>
                          <div v-if="step.note" class="mt-2 p-2 bg-blue-50 border-l-4 border-blue-400 text-sm text-blue-700">
                            <strong>Nota:</strong> {{ step.note }}
                          </div>
                        </div>
                      </li>
                    </ol>
                  </div>

                  <!-- Tips -->
                  <div v-if="example.tips && example.tips.length > 0" class="mb-6">
                    <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
                      <div class="flex items-start space-x-3">
                        <LightBulbIcon class="h-6 w-6 text-blue-600 flex-shrink-0" />
                        <div>
                          <h4 class="font-semibold text-blue-900 mb-2">Consejos Útiles:</h4>
                          <ul class="space-y-2">
                            <li
                              v-for="(tip, index) in example.tips"
                              :key="index"
                              class="text-sm text-blue-800"
                            >
                              • {{ tip }}
                            </li>
                          </ul>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Common Errors -->
                  <div v-if="example.commonErrors && example.commonErrors.length > 0">
                    <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                      <div class="flex items-start space-x-3">
                        <ExclamationTriangleIcon class="h-6 w-6 text-yellow-600 flex-shrink-0" />
                        <div>
                          <h4 class="font-semibold text-yellow-900 mb-2">Errores Comunes a Evitar:</h4>
                          <ul class="space-y-2">
                            <li
                              v-for="(error, index) in example.commonErrors"
                              :key="index"
                              class="text-sm text-yellow-800"
                            >
                              • {{ error }}
                            </li>
                          </ul>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Actions -->
              <div class="mt-6 flex justify-end">
                <button
                  type="button"
                  class="inline-flex justify-center rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
                  @click="$emit('close')"
                >
                  Entendido
                </button>
              </div>
            </DialogPanel>
          </TransitionChild>
        </div>
      </div>
    </Dialog>
  </TransitionRoot>
</template>

<script setup>
import { Dialog, DialogPanel, DialogTitle, TransitionChild, TransitionRoot } from '@headlessui/vue';
import { XMarkIcon, LightBulbIcon, ExclamationTriangleIcon } from '@heroicons/vue/24/outline';

defineProps({
  open: {
    type: Boolean,
    required: true
  },
  example: {
    type: Object,
    required: true
  }
});

defineEmits(['close']);
</script>
