<template>
  <div class="min-h-screen bg-gray-50">
    <ModuleHeader title="Gestión de Procesos">
      <template #menu-button><slot></slot></template>
    </ModuleHeader>

    <!-- Main content -->
    <div class="py-6 px-4 sm:px-6 lg:px-8">
      <!-- Tabs Navigation — uses the shared TabsCard wrapper for a unified
           visual language across modules (Procesos, SECOP, Servicios). -->
      <TabsCard>
        <div class="flex items-center justify-between px-4 sm:px-6">
          <!-- Desktop Tabs -->
          <nav class="-mb-px hidden sm:flex space-x-8">
            <button
              @click="navigateTab('my_processes')"
              :class="[
                activeTab === 'my_processes'
                  ? 'border-secondary text-secondary'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
                'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm'
              ]"
            >
              Mis Procesos
            </button>
            <button
              v-if="currentUser?.role === 'lawyer'"
              @click="navigateTab('all_processes')"
              :class="[
                activeTab === 'all_processes'
                  ? 'border-secondary text-secondary'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
                'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm'
              ]"
            >
              Todos los Procesos
            </button>
            <button
              @click="navigateTab('archived_processes')"
              :class="[
                activeTab === 'archived_processes'
                  ? 'border-secondary text-secondary'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
                'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm'
              ]"
            >
              Procesos Archivados
            </button>
          </nav>

          <!-- Mobile Dropdown -->
          <div class="sm:hidden flex-1">
            <Menu as="div" class="relative">
              <MenuButton class="w-full inline-flex items-center justify-between px-4 py-2 border border-gray-300 rounded-md bg-white text-sm font-medium text-gray-700 hover:bg-gray-50">
                <span>{{ getActiveTabLabel() }}</span>
                <ChevronDownIcon class="h-5 w-5 ml-2" />
              </MenuButton>
              <MenuItems class="absolute left-0 z-10 mt-2 w-full origin-top-left rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
                <div class="py-1">
                  <MenuItem v-slot="{ active }">
                    <button
                      @click="navigateTab('my_processes')"
                      :class="[
                        active ? 'bg-gray-100' : '',
                        'block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50'
                      ]"
                    >
                      Mis Procesos
                    </button>
                  </MenuItem>
                  <MenuItem v-if="currentUser?.role === 'lawyer'" v-slot="{ active }">
                    <button
                      @click="navigateTab('all_processes')"
                      :class="[
                        active ? 'bg-gray-100' : '',
                        'block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50'
                      ]"
                    >
                      Todos los Procesos
                    </button>
                  </MenuItem>
                  <MenuItem v-slot="{ active }">
                    <button
                      @click="navigateTab('archived_processes')"
                      :class="[
                        active ? 'bg-gray-100' : '',
                        'block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50'
                      ]"
                    >
                      Procesos Archivados
                    </button>
                  </MenuItem>
                </div>
              </MenuItems>
            </Menu>
          </div>
          
          <!-- Nueva Solicitud Button - Only for clients -->
          <button
            v-if="currentUser?.role === 'client' || currentUser?.role === 'corporate_client'"
            @click="goToNewRequest"
            class="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-secondary bg-secondary text-sm font-medium text-white hover:bg-blue-700 transition-all duration-200 ml-3 sm:ml-4"
          >
            <PlusIcon class="h-5 w-5" />
          Solicitar Información
          </button>
        </div>
      </TabsCard>

      <!-- Filters and Search Bar -->
      <div class="rounded-xl bg-white shadow-sm ring-1 ring-gray-200 p-4 sm:p-5 mb-6">
        <!-- Search Bar - Always on top -->
        <div class="mb-4">
          <div class="relative w-full">
            <MagnifyingGlassIcon class="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Buscar procesos..."
              class="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-secondary focus:border-transparent text-sm"
            />
          </div>
        </div>

        <!-- Filters Section -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
          <Menu as="div" class="relative">
            <MenuButton class="w-full inline-flex items-center justify-between gap-2 px-3 py-2 border border-gray-300 rounded-md bg-white text-sm font-medium text-gray-700 hover:bg-gray-50">
              <div class="flex items-center gap-2 min-w-0">
                <FunnelIcon class="h-4 w-4 flex-shrink-0" />
                <span class="truncate">{{ filterByType || 'Tipo' }}</span>
              </div>
              <ChevronDownIcon class="h-4 w-4 flex-shrink-0" />
            </MenuButton>
            <MenuItems class="absolute left-0 z-10 mt-2 w-56 origin-top-left rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
              <div class="py-1">
                <MenuItem v-slot="{ active }">
                  <a @click="filterByType = null" :class="[active ? 'bg-gray-100' : '', 'block px-4 py-2 text-sm text-gray-700 cursor-pointer']">
                    Todos
                  </a>
                </MenuItem>
                <MenuItem v-for="type in processTypes" :key="type" v-slot="{ active }">
                  <a @click="filterByType = type" :class="[active ? 'bg-gray-100' : '', 'block px-4 py-2 text-sm text-gray-700 cursor-pointer']">
                    {{ type }}
                  </a>
                </MenuItem>
              </div>
            </MenuItems>
          </Menu>

          <Menu as="div" class="relative">
            <MenuButton class="w-full inline-flex items-center justify-between gap-2 px-3 py-2 border border-gray-300 rounded-md bg-white text-sm font-medium text-gray-700 hover:bg-gray-50">
              <div class="flex items-center gap-2 min-w-0">
                <FunnelIcon class="h-4 w-4 flex-shrink-0" />
                <span class="truncate">{{ filterByAuthority || 'Autoridad' }}</span>
              </div>
              <ChevronDownIcon class="h-4 w-4 flex-shrink-0" />
            </MenuButton>
            <MenuItems class="absolute left-0 z-10 mt-2 w-56 origin-top-left rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none max-h-60 overflow-y-auto">
              <div class="py-1">
                <MenuItem v-slot="{ active }">
                  <a @click="filterByAuthority = null" :class="[active ? 'bg-gray-100' : '', 'block px-4 py-2 text-sm text-gray-700 cursor-pointer']">
                    Todos
                  </a>
                </MenuItem>
                <MenuItem v-for="authority in authorities" :key="authority" v-slot="{ active }">
                  <a @click="filterByAuthority = authority" :class="[active ? 'bg-gray-100' : '', 'block px-4 py-2 text-sm text-gray-700 cursor-pointer']">
                    {{ authority }}
                  </a>
                </MenuItem>
              </div>
            </MenuItems>
          </Menu>

          <Menu as="div" class="relative">
            <MenuButton class="w-full inline-flex items-center justify-between gap-2 px-3 py-2 border border-gray-300 rounded-md bg-white text-sm font-medium text-gray-700 hover:bg-gray-50">
              <div class="flex items-center gap-2 min-w-0">
                <FunnelIcon class="h-4 w-4 flex-shrink-0" />
                <span class="truncate">{{ filterByStage || 'Etapa' }}</span>
              </div>
              <ChevronDownIcon class="h-4 w-4 flex-shrink-0" />
            </MenuButton>
            <MenuItems class="absolute left-0 z-10 mt-2 w-56 origin-top-left rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none max-h-60 overflow-y-auto">
              <div class="py-1">
                <MenuItem v-slot="{ active }">
                  <a @click="filterByStage = null" :class="[active ? 'bg-gray-100' : '', 'block px-4 py-2 text-sm text-gray-700 cursor-pointer']">
                    Todos
                  </a>
                </MenuItem>
                <MenuItem v-for="stage in stages" :key="stage" v-slot="{ active }">
                  <a @click="filterByStage = stage" :class="[active ? 'bg-gray-100' : '', 'block px-4 py-2 text-sm text-gray-700 cursor-pointer']">
                    {{ stage }}
                  </a>
                </MenuItem>
              </div>
            </MenuItems>
          </Menu>

          <div class="flex items-center justify-stretch">
            <button
              v-if="filterByType || filterByAuthority || filterByStage"
              @click="clearFilters"
              class="w-full inline-flex items-center justify-center gap-2 px-3 py-2 border border-gray-300 rounded-md bg-white text-sm font-medium text-gray-700 hover:bg-gray-50"
              title="Limpiar filtros"
            >
              <XMarkIcon class="h-4 w-4 flex-shrink-0" />
              <span>Limpiar</span>
            </button>
          </div>
        </div>

        <!-- Actions Section -->
        <div class="flex flex-col sm:flex-row gap-3 items-start sm:items-center justify-between pt-4 border-t border-gray-200">
          <!-- Left side: Results count and Action buttons -->
          <div class="flex items-center gap-3">
            <div class="text-sm text-gray-500">
              <span class="font-medium">{{ filteredAndSortedProcesses.length }}</span> resultados
            </div>

            <!-- New Process Button (lawyers and administrators) -->
            <router-link
              v-if="userStore.isLawyerLike"
              data-testid="process-create-link"
              aria-label="Nuevo proceso"
              :to="{ name: 'process_form', params: { action: 'create' } }"
              class="inline-flex items-center gap-2 px-3 py-2 bg-secondary text-white rounded-md hover:bg-blue-700 transition-colors text-sm font-medium whitespace-nowrap"
            >
              <PlusIcon class="h-4 w-4" />
              <span class="hidden sm:inline">Nuevo</span>
            </router-link>

            <!-- Export Button -->
            <button
              @click="exportProcesses"
              class="inline-flex items-center gap-2 px-3 py-2 border border-gray-300 rounded-md bg-white text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              <ArrowDownTrayIcon class="h-4 w-4" />
              <span class="hidden sm:inline">Exportar</span>
            </button>

            <!-- More options -->
            <Menu as="div" class="relative">
              <MenuButton class="inline-flex items-center justify-center w-10 h-10 rounded-md hover:bg-gray-100">
                <EllipsisVerticalIcon class="h-5 w-5 text-gray-500" />
              </MenuButton>
              <MenuItems class="absolute left-0 z-10 mt-2 w-48 origin-top-left rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
                <div class="py-1">
                  <MenuItem v-slot="{ active }">
                    <a @click="selectAll" :class="[active ? 'bg-gray-100' : '', 'block px-4 py-2 text-sm text-gray-700 cursor-pointer']">
                      Seleccionar todo
                    </a>
                  </MenuItem>
                  <MenuItem v-slot="{ active }">
                    <a @click="deselectAll" :class="[active ? 'bg-gray-100' : '', 'block px-4 py-2 text-sm text-gray-700 cursor-pointer']">
                      Deseleccionar todo
                    </a>
                  </MenuItem>
                </div>
              </MenuItems>
            </Menu>
          </div>

          <!-- Right side: Sort -->
          <Menu as="div" class="relative">
            <MenuButton class="inline-flex items-center gap-2 px-3 py-2 border border-gray-300 rounded-md bg-white text-sm font-medium text-gray-700 hover:bg-gray-50">
              <ArrowsUpDownIcon class="h-4 w-4" />
              <span class="hidden sm:inline">{{ sortLabel }}</span>
              <ChevronDownIcon class="h-4 w-4" />
            </MenuButton>
            <MenuItems class="absolute right-0 z-10 mt-2 w-48 origin-top-right rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
              <div class="py-1">
                <MenuItem v-slot="{ active }">
                  <a @click="sortBy = 'recent'" :class="[active ? 'bg-gray-100' : '', 'block px-4 py-2 text-sm text-gray-700 cursor-pointer']">
                    Más recientes
                  </a>
                </MenuItem>
                <MenuItem v-slot="{ active }">
                  <a @click="sortBy = 'name'" :class="[active ? 'bg-gray-100' : '', 'block px-4 py-2 text-sm text-gray-700 cursor-pointer']">
                    Nombre (A-Z)
                  </a>
                </MenuItem>
              </div>
            </MenuItems>
          </Menu>
        </div>
      </div>

      <!-- Table — unified card style (matches SecopList / ServicesHub). -->
      <div v-if="filteredAndSortedProcesses.length" class="rounded-xl bg-white shadow-sm ring-1 ring-gray-200">
        <div class="overflow-x-auto" :style="{ minHeight: isAnyMenuOpen ? '200px' : 'auto' }">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th scope="col" class="w-12 px-6 py-3">
                  <input
                    type="checkbox"
                    :checked="allSelected"
                    @change="toggleSelectAll"
                    class="h-4 w-4 text-secondary focus:ring-secondary border-gray-300 rounded"
                  />
                </th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Nombre
                </th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Tipo Proceso
                </th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Dte./Accionante
                </th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Ddo./Accionado
                </th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Etapa
                </th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Avance
                </th>
                <th scope="col" class="w-16 px-6 py-3"></th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr
                v-for="(process, index) in paginatedProcesses"
                :key="process.id"
                class="hover:bg-gray-50 transition-colors cursor-pointer"
                @click="goToProcessDetail(process.id)"
              >
                <td class="px-6 py-4 whitespace-nowrap" @click.stop>
                  <input
                    type="checkbox"
                    :checked="selectedProcesses.includes(process.id)"
                    @change="toggleSelectProcess(process.id)"
                    class="h-4 w-4 text-secondary focus:ring-secondary border-gray-300 rounded"
                  />
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center">
                    <div class="h-10 w-10 flex-shrink-0">
                      <img
                        v-if="getPrimaryClient(process)?.photo_profile"
                        class="h-10 w-10 rounded-full object-cover"
                        :src="getPrimaryClient(process)?.photo_profile"
                        :alt="getPrimaryClient(process)?.first_name"
                      />
                      <div
                        v-else
                        class="h-10 w-10 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center text-white font-semibold text-sm shadow-sm"
                      >
                        {{ getInitials(getPrimaryClient(process)?.first_name, getPrimaryClient(process)?.last_name) }}
                      </div>
                    </div>
                    <div class="ml-4">
                      <div class="text-sm font-medium text-gray-900">
                        {{ getPrimaryClient(process)?.first_name }} {{ getPrimaryClient(process)?.last_name }}
                      </div>
                      <button
                        v-if="process.clients && process.clients.length"
                        type="button"
                        class="mt-1 text-xs text-blue-600 hover:text-blue-800 hover:underline"
                        @click.stop="openUsersModal(process)"
                      >
                        Ver usuarios
                      </button>
                    </div>
                  </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                    {{ process.case.type }}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {{ process.plaintiff || '-' }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {{ process.defendant || '-' }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                    {{ process.stages[process.stages.length - 1]?.status || 'Sin estado' }}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {{ typeof process.progress === 'number' ? process.progress + '%' : '-' }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium" @click.stop>
                  <Menu as="div" class="relative inline-block text-left" v-slot="{ open }">
                    <MenuButton 
                      :ref="el => setMenuButtonRef(el, index)"
                      @click="handleMenuOpen(index, open)"
                      class="inline-flex items-center justify-center w-8 h-8 rounded-md hover:bg-gray-100"
                    >
                      <EllipsisVerticalIcon class="h-5 w-5 text-gray-500" />
                    </MenuButton>
                  <MenuItems
                    :ref="el => setMenuItemsRef(el, index)"
                    :class="[
                      index > 0 && index >= paginatedProcesses.length - 3
                        ? 'absolute right-0 z-50 bottom-full mb-2 w-48 origin-bottom-right rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none'
                        : 'absolute right-0 z-50 mt-2 w-48 origin-top-right rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none'
                    ]"
                  >
                      <div class="py-1">
                        <MenuItem v-slot="{ active }">
                          <router-link
                            :to="{ name: 'process_detail', params: { process_id: process.id } }"
                            :class="[active ? 'bg-gray-100' : '', 'block px-4 py-2 text-sm text-gray-700']"
                          >
                            Ver detalles
                          </router-link>
                        </MenuItem>
                        <!-- Edit option — visible to lawyer / admin / staff /
                             superuser (mirrors ProcessDetail.vue and the
                             ``isLawyerLike`` getter in the user store).
                             Admin users were missing this entry in the first
                             R3 pass (R3 follow-up). -->
                        <MenuItem v-if="userStore.isLawyerLike" v-slot="{ active }">
                          <router-link
                            :to="{ name: 'process_form', params: { action: 'edit', process_id: process.id } }"
                            :class="[active ? 'bg-gray-100' : '', 'block px-4 py-2 text-sm text-gray-700']"
                          >
                            Editar
                          </router-link>
                        </MenuItem>
                      </div>
                    </MenuItems>
                  </Menu>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Pagination -->
        <div v-if="totalPages > 1" class="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6">
          <div class="flex flex-1 justify-between sm:hidden">
            <button
              @click="previousPage"
              :disabled="currentPage === 1"
              :class="[
                'relative inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50',
                currentPage === 1 ? 'opacity-50 cursor-not-allowed' : ''
              ]"
            >
              Anterior
            </button>
            <button
              @click="nextPage"
              :disabled="currentPage === totalPages"
              :class="[
                'relative ml-3 inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50',
                currentPage === totalPages ? 'opacity-50 cursor-not-allowed' : ''
              ]"
            >
              Siguiente
            </button>
          </div>
          <div class="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
            <div>
              <p class="text-sm text-gray-700">
                Mostrando
                <span class="font-medium">{{ paginationInfo.start }}</span>
                a
                <span class="font-medium">{{ paginationInfo.end }}</span>
                de
                <span class="font-medium">{{ paginationInfo.total }}</span>
                resultados
              </p>
            </div>
            <div>
              <nav class="isolate inline-flex -space-x-px rounded-md shadow-sm" aria-label="Pagination">
                <button
                  @click="previousPage"
                  :disabled="currentPage === 1"
                  :class="[
                    'relative inline-flex items-center rounded-l-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0',
                    currentPage === 1 ? 'opacity-50 cursor-not-allowed' : ''
                  ]"
                >
                  <span class="sr-only">Anterior</span>
                  <ChevronLeftIcon class="h-5 w-5" aria-hidden="true" />
                </button>
                <template v-for="page in visiblePages" :key="page">
                  <button
                    v-if="page !== '...'"
                    @click="goToPage(page)"
                    :class="[
                      'relative inline-flex items-center px-4 py-2 text-sm font-semibold focus:z-20 focus:outline-offset-0',
                      currentPage === page
                        ? 'z-10 bg-secondary text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-secondary'
                        : 'text-gray-900 ring-1 ring-inset ring-gray-300 hover:bg-gray-50'
                    ]"
                  >
                    {{ page }}
                  </button>
                  <span
                    v-else
                    class="relative inline-flex items-center px-4 py-2 text-sm font-semibold text-gray-700"
                  >
                    ...
                  </span>
                </template>
                <button
                  @click="nextPage"
                  :disabled="currentPage === totalPages"
                  :class="[
                    'relative inline-flex items-center rounded-r-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0',
                    currentPage === totalPages ? 'opacity-50 cursor-not-allowed' : ''
                  ]"
                >
                  <span class="sr-only">Siguiente</span>
                  <ChevronRightIcon class="h-5 w-5" aria-hidden="true" />
                </button>
              </nav>
            </div>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div
        v-else
        class="rounded-xl bg-white shadow-sm ring-1 ring-gray-200 p-12 text-center"
      >
        <CubeTransparentIcon class="mx-auto h-24 w-24 text-gray-400" />
        <h3 class="mt-4 text-lg font-medium text-gray-900">No hay procesos disponibles</h3>
        <p class="mt-2 text-sm text-gray-500">
          {{ activeTab === 'archived_processes' ? 'No hay procesos archivados para mostrar.' : 'Contacta a tu abogado para gestionar tus procesos.' }}
        </p>
      </div>
      <!-- Users Modal -->
      <ProcessUsersModal
        :is-open="showUsersModal"
        :users="usersForModal"
        @close="closeUsersModal"
      />
    </div>
  </div>
</template>

<script setup>
import { Menu, MenuButton, MenuItem, MenuItems } from "@headlessui/vue";
import {
  MagnifyingGlassIcon,
  FunnelIcon,
  ChevronDownIcon,
  PlusIcon,
  ArrowDownTrayIcon,
  EllipsisVerticalIcon,
  CubeTransparentIcon,
  XMarkIcon,
  ArrowsUpDownIcon,
  ChevronLeftIcon,
  ChevronRightIcon
} from "@heroicons/vue/24/outline";
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useUserStore } from "@/stores/auth/user";
import { useProcessStore } from "@/stores/process";
import ModuleHeader from "@/components/layouts/ModuleHeader.vue";
import TabsCard from "@/components/layouts/TabsCard.vue";
import ProcessUsersModal from "@/components/process/ProcessUsersModal.vue";

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();
const processStore = useProcessStore();

// Current user
const currentUser = computed(() => userStore.getCurrentUser);

// Active tab state
const activeTab = ref('my_processes');

// Search and filter states
const searchQuery = ref("");
const filterByType = ref(null);
const filterByAuthority = ref(null);
const filterByStage = ref(null);
const sortBy = ref('recent');

// Selection state
const selectedProcesses = ref([]);

// Pagination state
const currentPage = ref(1);
const itemsPerPage = ref(10);

// Menu refs for scroll handling
const menuButtonRefs = ref({});
const menuItemsRefs = ref({});
const isAnyMenuOpen = ref(false);

// Users modal state
const showUsersModal = ref(false);
const selectedProcessForUsers = ref(null);

// Initialize
onMounted(async () => {
  try {
    await Promise.all([
      processStore.init(),
      userStore.init(),
    ]);
  } catch (error) {
    console.error('Error initializing process list:', error);
  }
  
  // Set initial tab based on route params
  if (route.params.display === 'history') {
    activeTab.value = 'archived_processes';
  } else if (route.query.group === 'general') {
    activeTab.value = 'all_processes';
  } else {
    activeTab.value = 'my_processes';
  }
});

// Watch for route changes - use a single watcher to avoid race conditions
watch(
  () => ({ display: route.params.display, group: route.query.group }),
  (newRoute) => {
    // Priority: display param takes precedence over query param
    if (newRoute.display === 'history') {
      activeTab.value = 'archived_processes';
    } else if (newRoute.group === 'general') {
      activeTab.value = 'all_processes';
    } else if (newRoute.group === 'default') {
      activeTab.value = 'my_processes';
    } else {
      // Default to my_processes if no specific route params
      activeTab.value = 'my_processes';
    }
  },
  { deep: true }
);

// Get unique values for filters
const processTypes = computed(() => {
  const types = new Set();
  processStore.processes.forEach(process => {
    if (process.case?.type) {
      types.add(process.case.type);
    }
  });
  return Array.from(types).sort();
});

const authorities = computed(() => {
  const authoritiesList = new Set();
  processStore.processes.forEach(process => {
    if (process.authority) {
      authoritiesList.add(process.authority);
    }
  });
  return Array.from(authoritiesList).sort();
});

const stages = computed(() => {
  const stagesList = new Set();
  processStore.processes.forEach(process => {
    if (process.stages && process.stages.length > 0) {
      process.stages.forEach(stage => {
        if (stage.status) {
          stagesList.add(stage.status);
        }
      });
    }
  });
  return Array.from(stagesList).sort();
});

// Navigation between tabs: keep URL in sync and ensure `/history` only appears for archived_processes
const navigateTab = (tab) => {
  const currentUserId = currentUser.value?.id || '';
  const userIdFromRoute = route.params.user_id;

  // Prefer the user_id that ya esté en la URL; si no hay, usamos el del usuario actual
  const userId = userIdFromRoute || currentUserId;

  let path = '/process_list';
  if (userId) {
    path += `/${userId}`;
  }

  // Solo agregamos `/history` cuando vamos a Procesos Archivados
  if (tab === 'archived_processes') {
    path += '/history';
  }

  const query = { ...route.query };

  if (tab === 'all_processes') {
    query.group = 'general';
  } else if (tab === 'my_processes') {
    query.group = 'default';
  } else {
    // Para procesos archivados no necesitamos grupo
    delete query.group;
  }

  router.push({ path, query });
};

// Users for modal (clients of the selected process)
const usersForModal = computed(() => {
  const p = selectedProcessForUsers.value
  if (!p || !Array.isArray(p.clients)) return []
  return p.clients
})

// Helper: get the primary client (first in clients array) for display/search
const getPrimaryClient = (process) => {
  if (!process || !Array.isArray(process.clients)) return null;
  return process.clients.length ? process.clients[0] : null;
};

// Base filtered processes based on active tab
const baseFilteredProcesses = computed(() => {
  let processes = [];
  const isClient = currentUser.value?.role === 'client' || currentUser.value?.role === 'basic' || currentUser.value?.role === 'corporate_client';
  const userId = currentUser.value?.id;

  if (activeTab.value === 'archived_processes') {
    // Archived processes
    processes = processStore.processesWithClosedStatus;
    // Filter archived processes by user
    if (isClient) {
      processes = processes.filter(p => {
        return Array.isArray(p.clients) && p.clients.some(c => c.id === userId);
      });
    } else if (currentUser.value?.role === 'lawyer') {
      processes = processes.filter(p => p.lawyer?.id === userId);
    }
  } else {
    // Active processes
    processes = processStore.processesWithoutClosedStatus;
    
    // Filter by tab
    if (activeTab.value === 'my_processes') {
      // My processes only
      if (isClient) {
        processes = processes.filter(p => {
          return Array.isArray(p.clients) && p.clients.some(c => c.id === userId);
        });
      } else if (currentUser.value?.role === 'lawyer') {
        processes = processes.filter(p => p.lawyer?.id === userId);
      }
    }
    // 'all_processes' shows all (no additional filtering)
  }

  return processes;
});

// Apply search and filters
const filteredAndSortedProcesses = computed(() => {
  let processes = [...baseFilteredProcesses.value];

  // Apply search
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase();
    processes = processes.filter(process => {
      const primaryClient = getPrimaryClient(process) || {};
      return (
        primaryClient.first_name?.toLowerCase().includes(query) ||
        primaryClient.last_name?.toLowerCase().includes(query) ||
        primaryClient.email?.toLowerCase().includes(query) ||
        process.case?.type?.toLowerCase().includes(query) ||
        process.subcase?.toLowerCase().includes(query) ||
        process.ref?.toLowerCase().includes(query) ||
        process.plaintiff?.toLowerCase().includes(query) ||
        process.defendant?.toLowerCase().includes(query) ||
        process.authority?.toLowerCase().includes(query) ||
        process.stages?.some(stage => stage.status?.toLowerCase().includes(query))
      );
    });
  }

  // Apply type filter
  if (filterByType.value) {
    processes = processes.filter(p => p.case?.type === filterByType.value);
  }

  // Apply authority filter
  if (filterByAuthority.value) {
    processes = processes.filter(p => p.authority === filterByAuthority.value);
  }

  // Apply stage filter
  if (filterByStage.value) {
    processes = processes.filter(p => {
      const lastStage = p.stages?.[p.stages.length - 1];
      return lastStage?.status === filterByStage.value;
    });
  }

  // Apply sorting
  if (sortBy.value === 'name') {
    processes.sort((a, b) => {
      const aClient = getPrimaryClient(a) || {};
      const bClient = getPrimaryClient(b) || {};
      const nameA = `${aClient.first_name || ''} ${aClient.last_name || ''}`.toLowerCase();
      const nameB = `${bClient.first_name || ''} ${bClient.last_name || ''}`.toLowerCase();
      return nameA.localeCompare(nameB);
    });
  } else if (sortBy.value === 'recent') {
    // Most recent first - sort by created_at date
    processes.sort((a, b) => {
      const dateA = a.created_at ? new Date(a.created_at).getTime() : 0;
      const dateB = b.created_at ? new Date(b.created_at).getTime() : 0;
      return dateB - dateA; // Descending order (newest first)
    });
  }

  return processes;
});

// Paginated processes
const paginatedProcesses = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage.value;
  const end = start + itemsPerPage.value;
  return filteredAndSortedProcesses.value.slice(start, end);
});

// Total pages
const totalPages = computed(() => {
  return Math.ceil(filteredAndSortedProcesses.value.length / itemsPerPage.value);
});

// Pagination info
const paginationInfo = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage.value + 1;
  const end = Math.min(currentPage.value * itemsPerPage.value, filteredAndSortedProcesses.value.length);
  return { start, end, total: filteredAndSortedProcesses.value.length };
});

// Reset to first page when filters change
watch([searchQuery, filterByType, filterByAuthority, filterByStage, activeTab], () => {
  currentPage.value = 1;
});

// Sort label
const sortLabel = computed(() => {
  switch (sortBy.value) {
    case 'name': return 'Nombre (A-Z)';
    case 'recent':
    default: return 'Más recientes';
  }
});

// Clear all filters
const clearFilters = () => {
  filterByType.value = null;
  filterByAuthority.value = null;
  filterByStage.value = null;
};

// Selection functions
const allSelected = computed(() => {
  return filteredAndSortedProcesses.value.length > 0 &&
    selectedProcesses.value.length === filteredAndSortedProcesses.value.length;
});

const toggleSelectAll = () => {
  if (allSelected.value) {
    selectedProcesses.value = [];
  } else {
    selectedProcesses.value = filteredAndSortedProcesses.value.map(p => p.id);
  }
};

const toggleSelectProcess = (id) => {
  const index = selectedProcesses.value.indexOf(id);
  if (index > -1) {
    selectedProcesses.value.splice(index, 1);
  } else {
    selectedProcesses.value.push(id);
  }
};

const selectAll = () => {
  selectedProcesses.value = filteredAndSortedProcesses.value.map(p => p.id);
};

const deselectAll = () => {
  selectedProcesses.value = [];
};

// Get active tab label for mobile dropdown
const getActiveTabLabel = () => {
  switch (activeTab.value) {
    case 'my_processes':
      return 'Mis Procesos';
    case 'all_processes':
      return 'Todos los Procesos';
    case 'archived_processes':
      return 'Procesos Archivados';
    default:
      return 'Mis Procesos';
  }
};

// Navigation
const goToProcessDetail = (processId) => {
  router.push({
    name: 'process_detail',
    params: { process_id: processId }
  });
};

/**
 * Gets initials from first and last name
 * @param {string} firstName
 * @param {string} lastName
 * @returns {string} Initials
 */
const getInitials = (firstName, lastName) => {
  const first = firstName?.charAt(0)?.toUpperCase() || '';
  const last = lastName?.charAt(0)?.toUpperCase() || '';
  return `${first}${last}` || '?';
};

// Users modal handlers
const openUsersModal = (process) => {
  selectedProcessForUsers.value = process
  showUsersModal.value = true
}

const closeUsersModal = () => {
  showUsersModal.value = false
  selectedProcessForUsers.value = null
}

const goToNewRequest = () => {
  router.push('/legal_request_create');
};

// Pagination methods
const previousPage = () => {
  if (currentPage.value > 1) {
    currentPage.value--;
  }
};

const nextPage = () => {
  if (currentPage.value < totalPages.value) {
    currentPage.value++;
  }
};

const goToPage = (page) => {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page;
  }
};

// Visible pages for pagination (show max 7 pages)
const visiblePages = computed(() => {
  const total = totalPages.value;
  const current = currentPage.value;
  const pages = [];
  
  if (total <= 7) {
    // Show all pages if total is 7 or less
    for (let i = 1; i <= total; i++) {
      pages.push(i);
    }
  } else {
    // Show pages with ellipsis logic
    if (current <= 4) {
      // Show first 5 pages, then ellipsis, then last page
      for (let i = 1; i <= 5; i++) {
        pages.push(i);
      }
      pages.push('...');
      pages.push(total);
    } else if (current >= total - 3) {
      // Show first page, ellipsis, then last 5 pages
      pages.push(1);
      pages.push('...');
      for (let i = total - 4; i <= total; i++) {
        pages.push(i);
      }
    } else {
      // Show first page, ellipsis, current-1, current, current+1, ellipsis, last page
      pages.push(1);
      pages.push('...');
      pages.push(current - 1);
      pages.push(current);
      pages.push(current + 1);
      pages.push('...');
      pages.push(total);
    }
  }
  
  return pages;
});

// Menu refs handlers
const setMenuButtonRef = (el, index) => {
  if (el) {
    menuButtonRefs.value[index] = el;
  }
};

const setMenuItemsRef = (el, index) => {
  if (el) {
    menuItemsRefs.value[index] = el;
  }
};

// Handle menu open and scroll into view if needed
const handleMenuOpen = (index, wasOpen) => {
  // Track if menu is being opened or closed
  isAnyMenuOpen.value = !wasOpen;
  
  // Use setTimeout to ensure the menu is rendered before checking position
  if (!wasOpen) {
    setTimeout(() => {
      const menuItems = menuItemsRefs.value[index];
      
      if (menuItems) {
        // Get the actual DOM element (Headless UI components wrap the element)
        const menuElement = menuItems.$el || menuItems;
        
        if (menuElement && menuElement.getBoundingClientRect) {
          const rect = menuElement.getBoundingClientRect();
          const viewportHeight = window.innerHeight;
          
          // Special handling for first row (index 0) - always ensure it's fully visible
          if (index === 0) {
            // Check if menu extends below viewport
            if (rect.bottom > viewportHeight - 20) {
              const scrollAmount = rect.bottom - viewportHeight + 40;
              window.scrollBy({ 
                top: scrollAmount, 
                behavior: 'smooth'
              });
            }
          } else {
            // For other rows, use standard logic
            
            // Check if menu is cut off at the bottom of viewport
            if (rect.bottom > viewportHeight - 10) {
              const scrollAmount = rect.bottom - viewportHeight + 30;
              window.scrollBy({ 
                top: scrollAmount, 
                behavior: 'smooth'
              });
            }
            // Check if menu is cut off at the top of viewport
            else if (rect.top < 80) {
              const scrollAmount = rect.top - 100;
              window.scrollBy({ 
                top: scrollAmount, 
                behavior: 'smooth'
              });
            }
          }
        }
      }
    }, 100);
  }
};

// Export function
const exportProcesses = () => {
  const processesToExport = selectedProcesses.value.length > 0
    ? filteredAndSortedProcesses.value.filter(p => selectedProcesses.value.includes(p.id))
    : filteredAndSortedProcesses.value;

  // Create CSV content
  const headers = ['Nombre', 'Tipo Proceso', 'Dte./Accionante', 'Ddo./Accionado', 'Etapa'];
  const rows = processesToExport.map(process => {
    const primaryClient = getPrimaryClient(process) || {};
    const lastStage = process.stages?.[process.stages.length - 1] || null;
    return [
      `${primaryClient.first_name || ''} ${primaryClient.last_name || ''}`,
      process.case?.type || '',
      process.plaintiff || '-',
      process.defendant || '-',
      lastStage?.status || ''
    ];
  });

  const csvContent = [
    headers.join(','),
    ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
  ].join('\n');

  // Download CSV
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  link.setAttribute('href', url);
  link.setAttribute('download', `procesos_${new Date().toISOString().split('T')[0]}.csv`);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};
</script>
