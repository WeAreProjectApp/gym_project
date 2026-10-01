<template>
  <div class="relative">
    <div class="relative">
      <MagnifyingGlassIcon class="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
      <input
        v-model="searchValue"
        type="text"
        placeholder="Buscar en el manual..."
        data-testid="guide-search-input"
        aria-label="Buscar en el manual"
        class="w-full pl-10 pr-[calc(64px/var(--app-zoom,1))] py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
        @input="handleInput"
        @keyup.enter="handleSearch"
      />
      <button
        v-if="searchValue"
        type="button"
        data-testid="guide-search-clear"
        aria-label="Limpiar búsqueda"
        @click="clearSearch"
        class="absolute right-0 top-1/2 flex items-center justify-center transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
      >
        <XMarkIcon class="h-5 w-5" />
      </button>
    </div>

    <!-- Search Results Dropdown -->
    <div
      v-if="showResults && searchResults.length > 0"
      class="absolute z-10 w-full mt-2 bg-white border border-gray-200 rounded-lg shadow-lg max-h-96 overflow-y-auto"
    >
      <div class="p-2">
        <p class="text-xs text-gray-500 px-3 py-2">
          {{ searchResults.length }} resultado(s) encontrado(s)
        </p>
        <button
          v-for="(result, index) in searchResults"
          :key="index"
          @click="selectResult(result)"
          class="w-full text-left px-3 py-2 hover:bg-gray-50 rounded-lg transition-colors"
        >
          <div class="flex items-start space-x-3">
            <component
              :is="result.icon"
              class="h-5 w-5 text-indigo-600 flex-shrink-0 mt-0.5"
            />
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-gray-900 truncate">
                {{ result.title }}
              </p>
              <p class="text-xs text-gray-500 truncate">
                {{ result.module }} › {{ result.section }}
              </p>
              <p class="text-xs text-gray-600 mt-1 line-clamp-2">
                {{ result.snippet }}
              </p>
            </div>
          </div>
        </button>
      </div>
    </div>

    <!-- No Results -->
    <div
      v-if="showResults && searchValue && searchResults.length === 0"
      class="absolute z-10 w-full mt-2 bg-white border border-gray-200 rounded-lg shadow-lg p-4"
    >
      <p class="text-sm text-gray-600 text-center">
        No se encontraron resultados para "{{ searchValue }}"
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';
import { MagnifyingGlassIcon, XMarkIcon } from '@heroicons/vue/24/outline';
import { useUserGuideStore } from '@/stores/user_guide';

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  }
});

const emit = defineEmits(['update:modelValue', 'search', 'result-selected']);

const guideStore = useUserGuideStore();

const searchValue = ref(props.modelValue);
const showResults = ref(false);
const searchResults = ref([]);

watch(() => props.modelValue, (newValue) => {
  searchValue.value = newValue;
});

const handleInput = () => {
  emit('update:modelValue', searchValue.value);
  
  if (searchValue.value.length >= 3) {
    performSearch();
  } else {
    searchResults.value = [];
    showResults.value = false;
  }
};

const handleSearch = () => {
  if (searchValue.value.length >= 3) {
    performSearch();
    emit('search', searchValue.value);
  }
};

const performSearch = () => {
  searchResults.value = guideStore.searchGuideContent(searchValue.value);
  showResults.value = true;
};

const selectResult = (result) => {
  emit('result-selected', result);
  showResults.value = false;
};

const clearSearch = () => {
  searchValue.value = '';
  searchResults.value = [];
  showResults.value = false;
  emit('update:modelValue', '');
};
</script>
