<template>
  <ModuleHeader title="Directorio">
    <template #menu-button><slot></slot></template>
  </ModuleHeader>

  <!-- Replacing the old search bar with the new component -->
  <SearchBarAndFilterBy @update:searchQuery="searchQuery = $event">
  </SearchBarAndFilterBy>

  <div class="flex-1">
    <!-- Directory by cards -->
    <div>
      <ul role="list" class="min-w-0 divide-y divide-gray-100 grid xl:grid-cols-2">
        <li
          v-for="user in filteredUsers"
          :key="user.id"
          class="relative min-w-0 flex justify-between gap-x-6 px-4 py-5 hover:bg-gray-50 sm:px-6 lg:px-8 cursor-pointer"
          @click="openUserModal(user)"
        >
          <div
            class="flex min-w-0 flex-1 gap-x-4"
          >
            <img
              class="h-12 w-12 flex-none rounded-full bg-gray-50 object-cover object-center"
              v-if="user.photo_profile"
              :src="user.photo_profile"
              alt="Photo Profile"
            />
            <div
              v-else
              class="h-12 w-12 flex-none rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center text-white font-semibold text-lg shadow-sm"
            >
              {{ getInitials(user.first_name, user.last_name) }}
            </div>
            <div class="min-w-0 flex-auto">
              <p class="text-sm font-semibold leading-6 text-gray-900 [overflow-wrap:anywhere]">
                <a>
                  <span class="absolute inset-x-0 -top-px bottom-0" />
                  {{ user.first_name }} {{ user.last_name }}
                  <span class="text-gray-400">
                    ({{ user.role == "client" ? "Cliente" : user.role == "basic" ? "Básico" : user.role == "corporate_client" ? "Corporativo" : "Abogado" }})
                  </span>
                </a>
              </p>
              <p class="mt-1 flex text-xs leading-5 text-gray-500">
                <a
                  :href="`mailto:${user.email}`"
                  class="relative truncate hover:underline"
                  >{{ user.email }}</a
                >
              </p>
            </div>
          </div>
          <div class="flex shrink-0 items-center gap-x-4">
            <ChevronRightIcon
              class="h-5 w-5 flex-none text-gray-400"
              aria-hidden="true"
            />
          </div>
        </li>
      </ul>
    </div>
  </div>

  <!-- User details modal -->
  <teleport to="body">
    <DirectoryUserDetailsModal
      v-if="showUserModal && selectedUser"
      :is-visible="showUserModal"
      :user="selectedUser"
      @close="closeUserModal"
    />
  </teleport>
</template>

<script setup>
import ModuleHeader from "@/components/layouts/ModuleHeader.vue";
import SearchBarAndFilterBy from "@/components/layouts/SearchBarAndFilterBy.vue";
import { computed, onMounted, ref } from "vue";
import { useUserStore } from "@/stores/auth/user";
import { ChevronRightIcon } from "@heroicons/vue/20/solid";
import DirectoryUserDetailsModal from "@/components/directory/DirectoryUserDetailsModal.vue";

const userStore = useUserStore();
const searchQuery = ref("");
const showUserModal = ref(false);
const selectedUser = ref(null);

// Filter users based on search query
const filteredUsers = computed(() =>
  userStore.filteredUsers(searchQuery.value)
);

// Fetch users data on mount
onMounted(async () => {
  await userStore.init();
});

const openUserModal = (user) => {
  selectedUser.value = user;
  showUserModal.value = true;
};

const closeUserModal = () => {
  showUserModal.value = false;
  selectedUser.value = null;
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
</script>
