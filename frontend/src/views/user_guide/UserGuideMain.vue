<template>
  <ModuleHeader title="Manual de Usuario">
    <template #menu-button><slot></slot></template>
  </ModuleHeader>

  <!-- Main content -->
  <div class="user-guide flex min-h-0 flex-col lg:flex-row h-[calc(100vh/var(--app-zoom,1)-4rem)]">
    <!-- Sidebar Navigation -->
    <aside class="hidden lg:block shrink-0 border-r border-gray-200 bg-gray-50 overflow-y-auto" :class="isExplorer ? 'w-64' : 'w-80'">
      <GuideNavigation
        :current-role="currentUserRole"
        :selected-module="selectedModule"
        :selected-section="selectedSection"
        :explorer-selected="isExplorer"
        @explorer-selected="openExplorer"
        @module-selected="handleModuleSelected"
        @section-selected="handleSectionSelected"
      />
    </aside>

    <!-- Mobile Navigation -->
    <div class="lg:hidden w-full">
      <div class="p-4 border-b border-gray-200 bg-white">
        <button
          type="button"
          data-testid="guide-mobile-navigation-toggle"
          :aria-expanded="showMobileNav"
          aria-controls="guide-mobile-navigation"
          @click="showMobileNav = !showMobileNav"
          class="w-full flex items-center justify-between px-4 py-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
        >
          <span class="font-medium text-gray-900">
            {{ isExplorer ? 'Explorador de la plataforma' : selectedModule ? getModuleName(selectedModule) : 'Selecciona un módulo' }}
          </span>
          <ChevronDownIcon 
            :class="['h-5 w-5 text-gray-500 transition-transform', showMobileNav ? 'rotate-180' : '']"
          />
        </button>
      </div>
      
      <div v-if="showMobileNav" id="guide-mobile-navigation" data-testid="guide-mobile-navigation" class="border-b border-gray-200 bg-gray-50">
        <GuideNavigation
          :current-role="currentUserRole"
          :selected-module="selectedModule"
          :selected-section="selectedSection"
          :explorer-selected="isExplorer"
          @explorer-selected="openExplorer"
          @module-selected="handleModuleSelected"
          @section-selected="handleSectionSelected"
          @close="showMobileNav = false"
        />
      </div>
    </div>

    <!-- Content Area -->
    <main class="min-w-0 flex-1 overflow-y-auto bg-white">
      <div class="mx-auto px-4 sm:px-6 lg:px-8 py-8" :class="isExplorer ? 'max-w-none' : 'max-w-4xl'">
        <GuideExplorer v-if="isExplorer" @guide="handleExplorerGuide" />
        <!-- Search Bar -->
        <div v-if="!isExplorer" class="mb-6">
          <SearchGuide
            v-model="searchQuery"
            @search="handleSearch"
            @result-selected="handleSearchResult"
          />
        </div>

        <!-- Welcome Screen -->
        <div v-if="!isExplorer && !selectedModule" class="text-center py-12">
          <BookOpenIcon class="mx-auto h-16 w-16 text-indigo-500 mb-4" />
          <h2 class="text-2xl font-bold text-gray-900 mb-2">
            Bienvenido al Manual de Usuario
          </h2>
          <p class="text-gray-600 mb-6">
            Selecciona un módulo del menú lateral para comenzar
          </p>
          <button type="button" class="rounded-xl border border-indigo-200 bg-indigo-50 px-6 py-4 font-semibold text-indigo-800 hover:bg-indigo-100 focus-visible:ring-2 focus-visible:ring-indigo-500"
            data-testid="open-guide-explorer" @click="openExplorer">
            Explorar la plataforma
            <span class="mt-1 block text-sm font-normal">Descubre todos los módulos y cómo se conectan</span>
          </button>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl mx-auto mt-8">
            <RoleInfoCard :role="currentUserRole" />
            <QuickLinksCard :role="currentUserRole" @navigate="handleQuickLink" />
          </div>
        </div>

        <!-- Module Content -->
        <div v-else-if="!isExplorer">
          <ModuleGuide
            :module="selectedModule"
            :section="selectedSection"
            :role="currentUserRole"
            :search-query="searchQuery"
            @section-selected="handleSectionSelected"
          />
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, defineAsyncComponent, onMounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import { BookOpenIcon, ChevronDownIcon } from '@heroicons/vue/24/outline';
import ModuleHeader from '@/components/layouts/ModuleHeader.vue';
import { useUserStore } from '@/stores/auth/user';
import { useAuthStore } from '@/stores/auth/auth';
import { useUserGuideStore } from '@/stores/user_guide';
import GuideNavigation from './components/GuideNavigation.vue';
import ModuleGuide from './components/ModuleGuide.vue';
import SearchGuide from './components/SearchGuide.vue';
import RoleInfoCard from './components/RoleInfoCard.vue';
import QuickLinksCard from './components/QuickLinksCard.vue';

const GuideExplorer = defineAsyncComponent(() => import('./explorer/GuideExplorer.vue'));

const router = useRouter();
const userStore = useUserStore();
const authStore = useAuthStore();
const guideStore = useUserGuideStore();

// State
const selectedModule = ref(null);
const selectedSection = ref(null);
const searchQuery = ref('');
const showMobileNav = ref(false);
const isExplorer = computed(() => router.currentRoute.value.query?.view === 'explorer');

const openExplorer = () => {
  selectedModule.value = null;
  selectedSection.value = null;
  showMobileNav.value = false;
  return router.push({ query: { view: 'explorer' } });
};

const closeExplorer = () => {
  if (!isExplorer.value) return;
  const query = { ...router.currentRoute.value.query };
  ['view', 'node', 'tour', 'relations'].forEach(key => delete query[key]);
  router.push({ query });
};

const handleExplorerGuide = (target) => {
  handleModuleSelected(target.moduleId);
  selectedSection.value = target.sectionId;
};

// Computed
const currentUserRole = computed(() => {
  const user = userStore.userById(authStore.userAuth?.id);
  // is_staff/is_superuser users (with any persisted role) browse the manual
  // as "admin" — same content set the router treats as lawyer-like.
  if (user?.role === 'admin' || user?.is_staff || user?.is_superuser) return 'admin';
  return user?.role || 'client';
});

// Methods
const handleModuleSelected = (module) => {
  closeExplorer();
  selectedModule.value = module;
  selectedSection.value = null;
  showMobileNav.value = false;
  searchQuery.value = '';
};

const handleSectionSelected = (section) => {
  selectedSection.value = section;
  showMobileNav.value = false;
};

const handleSearch = (query) => {
  // Search functionality will filter content in ModuleGuide
  console.log('Searching for:', query);
};

const handleSearchResult = (result) => {
  closeExplorer();
  // Navigate to the module and section from search result
  selectedModule.value = result.moduleId;
  selectedSection.value = result.sectionId;
  searchQuery.value = '';
  showMobileNav.value = false;
};

const handleQuickLink = (module) => {
  closeExplorer();
  selectedModule.value = module;
  selectedSection.value = null;
};

const getModuleName = (moduleId) => {
  const modules = guideStore.getModulesForRole(currentUserRole.value);
  const module = modules.find(m => m.id === moduleId);
  return module?.name || moduleId;
};

// Lifecycle
onMounted(async () => {
  await userStore.init();
  guideStore.initializeGuideContent();
});

// Watch for route changes to reset view when clicking menu again
watch(() => router.currentRoute.value.params.refresh, () => {
  selectedModule.value = null;
  selectedSection.value = null;
  searchQuery.value = '';
});
</script>

<style>
/* Keep the hit area at 44 physical pixels despite the application's zoom. */
.user-guide :is(button, a, input, select),
.guide-example :is(button, a, input, select) {
  min-width: calc(44px / var(--app-zoom, 1));
  min-height: calc(44px / var(--app-zoom, 1));
}

.user-guide input,
.guide-example input {
  font-size: calc(16px / var(--app-zoom, 1));
}
</style>
