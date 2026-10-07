<template>
  <TransitionRoot as="template" :show="slidebarOpen">
    <Dialog class="relative z-50 lg:hidden" @close="slidebarOpen = false">
      <TransitionChild
        as="template"
        enter="transition-opacity ease-linear duration-300"
        enter-from="opacity-0"
        enter-to="opacity-100"
        leave="transition-opacity ease-linear duration-300"
        leave-from="opacity-100"
        leave-to="opacity-0"
      >
        <div class="fixed inset-0 bg-gray-900/80" />
      </TransitionChild>

      <div class="fixed inset-0 flex">
        <TransitionChild
          as="template"
          enter="transition ease-in-out duration-300 transform"
          enter-from="-translate-x-full"
          enter-to="translate-x-0"
          leave="transition ease-in-out duration-300 transform"
          leave-from="translate-x-0"
          leave-to="-translate-x-full"
        >
          <DialogPanel class="relative mr-16 flex w-full max-w-xs flex-1">
            <TransitionChild
              as="template"
              enter="ease-in-out duration-300"
              enter-from="opacity-0"
              enter-to="opacity-100"
              leave="ease-in-out duration-300"
              leave-from="opacity-100"
              leave-to="opacity-0"
            >
              <div
                class="absolute left-full top-0 flex w-16 justify-center pt-5"
              >
                <button
                  type="button"
                  class="-m-2.5 p-2.5"
                  @click="slidebarOpen = false"
                >
                  <span class="sr-only">Cerrar slidebar</span>
                  <XMarkIcon class="h-6 w-6 text-white" aria-hidden="true" />
                </button>
              </div>
            </TransitionChild>
            <!-- Sidebar component, swap this element with another sidebar if you like -->
            <div
              class="flex grow flex-col gap-y-5 overflow-y-auto bg-white px-6 pb-4"
            >
              <div class="flex h-18 shrink-0 items-center justify-center">
                <img
                  class="h-16 w-auto"
                  src="@/assets/images/logo/logo1.png"
                  alt="G&M Consultores Juridicos"
                />
              </div>
              <nav class="relative flex flex-1 flex-col">
                <ul role="list" class="flex flex-1 flex-col gap-y-5">
                  <li>
                    <!-- Profile dropdown -->
                    <Menu as="div" class="relative">
                      <MenuButton class="-m-1.5 flex items-center p-1.5">
                        <span class="sr-only">Abrir menú de usuario</span>
                        <img
                          class="h-8 w-8 rounded-full bg-gray-50 object-cover object-center"
                          :src="currentUser.photo_profile || userAvatar"
                          alt="Phone Profile"
                        />
                        <span class="flex items-center">
                          <span
                            class="ml-4 text-sm font-semibold leading-6 text-gray-900 truncate max-w-44"
                            aria-hidden="true"
                          >
                            {{ currentUser.first_name }}
                            {{ currentUser.last_name }}
                          </span>
                          <ChevronDownIcon
                            class="ml-2 h-5 w-5 text-gray-400"
                            aria-hidden="true"
                          />
                        </span>
                      </MenuButton>
                      <transition
                        enter-active-class="transition ease-out duration-100"
                        enter-from-class="transform opacity-0 scale-95"
                        enter-to-class="transform opacity-100 scale-100"
                        leave-active-class="transition ease-in duration-75"
                        leave-from-class="transform opacity-100 scale-100"
                        leave-to-class="transform opacity-0 scale-95"
                      >
                        <MenuItems
                          class="absolute right-0 z-10 mt-2.5 w-32 origin-top-right rounded-md bg-white py-2 shadow-lg ring-1 ring-gray-900/5 focus:outline-none"
                        >
                          <MenuItem
                            v-for="item in userNavigation"
                            :key="item.name"
                            v-slot="{ active }"
                          >
                            <a
                              @click="item.action"
                              class="cursor-pointer"
                              :class="[
                                active ? 'bg-gray-50' : '',
                                'block px-3 py-1 text-sm leading-6 text-gray-900',
                              ]"
                            >
                              {{ item.name }}
                            </a>
                          </MenuItem>
                        </MenuItems>
                      </transition>
                    </Menu>
                  </li>
                  <li>
                    <ul role="list" class="-mx-2 space-y-1">
                      <li v-for="item in navigation" :key="item.name">
                        <a
                          :href="item.href || 'javascript:void(0)'"
                          :target="item.target || null"
                          @click="!item.href && item.action(item)"
                          class="cursor-pointer"
                          :class="[
                            item.current
                              ? 'bg-gray-50 text-secondary'
                              : 'text-primary hover:bg-gray-50 hover:text-secondary',
                            'group flex gap-x-3 rounded-md p-2 text-sm font-semibold leading-6',
                          ]"
                        >
                          <div class="relative">
                            <component
                              :is="item.icon"
                              :class="[
                                item.current
                                  ? 'text-secondary'
                                  : 'text-primary group-hover:text-secondary',
                                'h-6 w-6 shrink-0',
                              ]"
                              aria-hidden="true"
                            />
                            <span
                              v-if="item.name === 'Archivos Juridicos' && hasPending"
                              data-testid="pending-signatures-indicator-mobile"
                              class="absolute -top-1 -right-1 flex items-center justify-center w-3 h-3 bg-red-500 rounded-full animate-pulse"
                            >
                              <span class="sr-only">Documentos pendientes de firma</span>
                            </span>
                            <span
                              v-if="item.name === 'Procesos' && hasProcessPending"
                              data-testid="pending-process-indicator-mobile"
                              class="absolute -top-1 -right-1 flex items-center justify-center w-3 h-3 bg-red-500 rounded-full animate-pulse"
                            >
                              <span class="sr-only">Alertas de procesos pendientes</span>
                            </span>
                          </div>
                          <span class="flex items-center gap-2">
                            {{ item.name }}
                            <span
                              v-if="item.name === 'Archivos Juridicos' && hasPending"
                              data-testid="pending-signatures-count-mobile"
                              class="inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-bold text-white bg-red-500 rounded-full"
                            >
                              {{ pendingCount > 99 ? '99+' : pendingCount }}
                            </span>
                            <span
                              v-if="item.name === 'Procesos' && hasProcessPending"
                              data-testid="pending-process-count-mobile"
                              class="inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-bold text-white bg-red-500 rounded-full"
                            >
                              {{ processPendingCount > 99 ? '99+' : processPendingCount }}
                            </span>
                          </span>
                        </a>
                      </li>
                    </ul>
                  </li>
                  <li class="mt-auto pb-10">
                    <ul role="list" class="-mx-2 space-y-1">
                      <li v-for="item in bottomNavigation" :key="item.name">
                        <a
                          :href="item.href || 'javascript:void(0)'"
                          :target="item.target || null"
                          @click="!item.href && item.action(item)"
                          class="cursor-pointer"
                          :class="[
                            item.current
                              ? 'bg-gray-50 text-secondary'
                              : 'text-primary hover:bg-gray-50 hover:text-secondary',
                            'group flex gap-x-3 rounded-md p-2 text-sm font-semibold leading-6',
                          ]"
                        >
                          <div class="relative">
                            <component
                              :is="item.icon"
                              :class="[
                                item.current
                                  ? 'text-secondary'
                                  : 'text-primary group-hover:text-secondary',
                                'h-6 w-6 shrink-0',
                              ]"
                              aria-hidden="true"
                            />
                            <span
                              v-if="item.name === 'Notificaciones' && hasNotificationsUnread"
                              data-testid="pending-notifications-indicator-mobile"
                              class="absolute -top-1 -right-1 flex items-center justify-center w-3 h-3 bg-red-500 rounded-full animate-pulse"
                            >
                              <span class="sr-only">Notificaciones sin leer</span>
                            </span>
                          </div>
                          <span class="flex items-center gap-2">
                            {{ item.name }}
                            <span
                              v-if="item.name === 'Notificaciones' && hasNotificationsUnread"
                              data-testid="pending-notifications-count-mobile"
                              class="inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-bold text-white bg-red-500 rounded-full"
                            >
                              {{ notificationsUnreadCount > 99 ? '99+' : notificationsUnreadCount }}
                            </span>
                          </span>
                        </a>
                      </li>
                      <PWAInstallButton></PWAInstallButton>
                    </ul>
                  </li>
                </ul>
                <!-- Social Networks Buttons -->
                <div class="absolute bottom-0 w-full flex gap-0.5 items-center">
                  <a
                    href="https://api.whatsapp.com/message/XR7PDKOQS3R6A1?autoload=1&app_absent=0"
                    target="_blank"
                    class="cursor-pointer"
                  >
                    <img :src="WhatsappIcon" />
                  </a>
                  <a
                    href="https://www.instagram.com/gymconsultoresjuridicos/"
                    target="_blank"
                    class="cursor-pointer"
                  >
                    <img :src="InstagramIcon" />
                  </a>
                  <a
                    href="https://www.facebook.com/profile.php?id=100089865602579&mibextid=ZbWKwL"
                    target="_blank"
                    class="-mt-2 cursor-pointer"
                  >
                    <img :src="FacebookIcon" />
                  </a>
                </div>
              </nav>
            </div>
          </DialogPanel>
        </TransitionChild>
      </div>
    </Dialog>
  </TransitionRoot>

  <!-- Static sidebar for desktop -->
  <div class="hidden lg:fixed lg:inset-y-0 lg:z-50 lg:flex lg:w-72 lg:flex-col">
    <!-- Sidebar component, swap this element with another sidebar if you like -->
    <div
      class="flex grow flex-col gap-y-5 overflow-y-auto border-r border-gray-200 bg-white px-6 pb-4"
    >
      <div class="flex h-24 shrink-0 items-center justify-center">
        <img
          class="h-22 w-auto"
          src="@/assets/images/logo/logo1.png"
          alt="G&M Consultores Juridicos"
        />
      </div>
      <nav data-testid="sidebar-nav" class="relative flex flex-1 flex-col">
        <ul role="list" class="flex flex-1 flex-col gap-y-5">
          <li>
            <!-- Profile dropdown -->
            <Menu as="div" class="relative">
              <MenuButton class="-m-1.5 flex items-center p-1.5">
                <span class="sr-only">Open user menu</span>
                <img
                  class="h-8 w-8 rounded-full bg-gray-50 object-cover object-center"
                  :src="currentUser.photo_profile || userAvatar"
                  alt="Phone Profile"
                />
                <span class="hidden lg:flex lg:items-center">
                  <span
                    class="ml-4 text-sm font-semibold leading-6 text-gray-900 truncate max-w-44"
                    aria-hidden="true"
                    >{{ currentUser.first_name }}
                    {{ currentUser.last_name }}</span
                  >
                  <ChevronDownIcon
                    class="ml-2 h-5 w-5 text-gray-400"
                    aria-hidden="true"
                  />
                </span>
              </MenuButton>
              <transition
                enter-active-class="transition ease-out duration-100"
                enter-from-class="transform opacity-0 scale-95"
                enter-to-class="transform opacity-100 scale-100"
                leave-active-class="transition ease-in duration-75"
                leave-from-class="transform opacity-100 scale-100"
                leave-to-class="transform opacity-0 scale-95"
              >
                <MenuItems
                  class="absolute right-0 z-10 mt-2.5 w-32 origin-top-right rounded-md bg-white py-2 shadow-lg ring-1 ring-gray-900/5 focus:outline-none"
                >
                  <MenuItem
                    v-for="item in userNavigation"
                    :key="item.name"
                    v-slot="{ active }"
                  >
                    <a
                      @click="item.action"
                      class="cursor-pointer"
                      :class="[
                        active ? 'bg-gray-50' : '',
                        'block px-3 py-1 text-sm leading-6 text-gray-900',
                      ]"
                      >{{ item.name }}
                    </a>
                  </MenuItem>
                </MenuItems>
              </transition>
            </Menu>
          </li>
          <li>
            <ul role="list" class="-mx-2 space-y-1">
              <li v-for="item in navigation" :key="item.name">
                <a
                  :href="item.href || 'javascript:void(0)'"
                  :target="item.target || null"
                  @click="!item.href && item.action(item)"
                  class="cursor-pointer"
                  :class="[
                    item.current
                      ? 'bg-selected-background text-secondary'
                      : 'text-primary hover:bg-gray-50 hover:text-secondary',
                    'group flex gap-x-3 rounded-md p-2 text-sm font-semibold leading-6',
                  ]"
                >
                  <div class="relative">
                    <component
                      :is="item.icon"
                      :class="[
                        item.current
                          ? 'text-secondary'
                          : 'text-primary group-hover:text-secondary',
                        'h-6 w-6 shrink-0',
                      ]"
                      aria-hidden="true"
                    />
                    <span
                      v-if="item.name === 'Archivos Juridicos' && hasPending"
                      class="absolute -top-1 -right-1 flex items-center justify-center w-3 h-3 bg-red-500 rounded-full animate-pulse"
                      data-testid="pending-signatures-indicator"
                    >
                      <span class="sr-only">Documentos pendientes de firma</span>
                    </span>
                    <span
                      v-if="item.name === 'Procesos' && hasProcessPending"
                      class="absolute -top-1 -right-1 flex items-center justify-center w-3 h-3 bg-red-500 rounded-full animate-pulse"
                      data-testid="pending-process-indicator"
                    >
                      <span class="sr-only">Alertas de procesos pendientes</span>
                    </span>
                  </div>
                  <span class="flex items-center gap-2">
                    {{ item.name }}
                    <span
                      v-if="item.name === 'Archivos Juridicos' && hasPending"
                      class="inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-bold text-white bg-red-500 rounded-full"
                      data-testid="pending-signatures-count"
                    >
                      {{ pendingCount > 99 ? '99+' : pendingCount }}
                    </span>
                    <span
                      v-if="item.name === 'Procesos' && hasProcessPending"
                      class="inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-bold text-white bg-red-500 rounded-full"
                      data-testid="pending-process-count"
                    >
                      {{ processPendingCount > 99 ? '99+' : processPendingCount }}
                    </span>
                  </span>
                </a>
              </li>
            </ul>
          </li>
          <li class="mt-auto pb-10">
            <ul role="list" class="-mx-2 space-y-1">
              <li v-for="item in bottomNavigation" :key="item.name">
                <a
                  :href="item.href || 'javascript:void(0)'"
                  :target="item.target || null"
                  @click="!item.href && item.action(item)"
                  class="cursor-pointer"
                  :class="[
                    item.current
                      ? 'bg-selected-background text-secondary'
                      : 'text-primary hover:bg-gray-50 hover:text-secondary',
                    'group flex gap-x-3 rounded-md p-2 text-sm font-semibold leading-6',
                  ]"
                >
                  <div class="relative">
                    <component
                      :is="item.icon"
                      :class="[
                        item.current
                          ? 'text-secondary'
                          : 'text-primary group-hover:text-secondary',
                        'h-6 w-6 shrink-0',
                      ]"
                      aria-hidden="true"
                    />
                    <span
                      v-if="item.name === 'Notificaciones' && hasNotificationsUnread"
                      data-testid="pending-notifications-indicator"
                      class="absolute -top-1 -right-1 flex items-center justify-center w-3 h-3 bg-red-500 rounded-full animate-pulse"
                    >
                      <span class="sr-only">Notificaciones sin leer</span>
                    </span>
                  </div>
                  <span class="flex items-center gap-2">
                    {{ item.name }}
                    <span
                      v-if="item.name === 'Notificaciones' && hasNotificationsUnread"
                      data-testid="pending-notifications-count"
                      class="inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-bold text-white bg-red-500 rounded-full"
                    >
                      {{ notificationsUnreadCount > 99 ? '99+' : notificationsUnreadCount }}
                    </span>
                  </span>
                </a>
              </li>
              <PWAInstallButton></PWAInstallButton>
            </ul>
          </li>
        </ul>
        <!-- Social Networks Buttons -->
        <div class="absolute bottom-0 w-full flex gap-0.5 items-center">
          <a
            href="https://api.whatsapp.com/message/XR7PDKOQS3R6A1?autoload=1&app_absent=0"
            target="_blank"
            class="cursor-pointer"
          >
            <img :src="WhatsappIcon" />
          </a>
          <a
            href="https://www.instagram.com/gymconsultoresjuridicos/"
            target="_blank"
            class="cursor-pointer"
          >
            <img :src="InstagramIcon" />
          </a>
          <a
            href="https://www.facebook.com/profile.php?id=100089865602579&mibextid=ZbWKwL"
            target="_blank"
            class="-mt-2 cursor-pointer"
          >
            <img :src="FacebookIcon" />
          </a>
        </div>
      </nav>
    </div>
  </div>

  <div class="lg:pl-72 w-full h-screen flex-1 flex flex-col">
    <NotificationBell />
    <main class="h-full">
      <!-- Content -->
      <router-view v-slot="{ Component }">
        <component :is="Component">
          <template #default>
            <button
              type="button"
              class="-m-2.5 p-2.5 text-gray-700 lg:hidden"
              @click="slidebarOpen = true"
            >
              <span class="sr-only">Open sidebar</span>
              <Bars3Icon class="h-6 w-6" aria-hidden="true" />
            </button>
          </template>
        </component>
      </router-view>
    </main>
  </div>
  <!-- Profile modal information -->
  <Profile
    :currentUser="currentUser"
    :visible="showProfile"
    @update:visible="showProfile = $event"
  >
  </Profile>
</template>

<script setup>
import { onMounted, computed, ref, watch } from "vue";
import Profile from "@/components/user/Profile.vue";
import PWAInstallButton from "@/components/pwa/PWAInstallButton.vue";
import {
  Dialog,
  DialogPanel,
  Menu,
  MenuButton,
  MenuItem,
  MenuItems,
  TransitionChild,
  TransitionRoot,
} from "@headlessui/vue";
import {
  ScaleIcon,
  HomeIcon,
  XMarkIcon,
  Bars3Icon,
  InboxArrowDownIcon,
  UsersIcon,
  DocumentTextIcon,
  RectangleStackIcon,
  EnvelopeIcon,
  BuildingOfficeIcon,
  BuildingLibraryIcon,
  BookOpenIcon,
  BellAlertIcon,
  ArrowsRightLeftIcon,
} from "@heroicons/vue/24/outline";
import { ChevronDownIcon } from "@heroicons/vue/20/solid";
import { useRouter, useRoute } from "vue-router";
import { useAuthStore } from "@/stores/auth/auth";
import { useUserStore } from "@/stores/auth/user";
import { usePendingSignatures } from "@/composables/usePendingSignatures";
import { usePendingProcessAlerts } from "@/composables/usePendingProcessAlerts";
import { useNotificationStore } from "@/stores/notification";
import { googleLogout } from "vue3-google-login";
import userAvatar from "@/assets/images/user_avatar.jpg";
import RegisteredIcon from "@/components/icons/RegisteredIcon.vue";
import NotificationBell from "@/components/notifications/NotificationBell.vue";
import WhatsappIcon from "@/assets/icons/social_network/whatsapp.svg";
import FacebookIcon from "@/assets/icons/social_network/facebook.svg";
import InstagramIcon from "@/assets/icons/social_network/instagram.svg";

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore(); // Get the authentication store instance
const userStore = useUserStore();

// Use computed to make currentUser reactive to store changes
const currentUser = computed(() => {
  return userStore.userById(authStore.userAuth?.id) || {};
});

// Initialize pending signatures composable
const { pendingCount, hasPending, fetchPendingCount } = usePendingSignatures();

// Pending process alerts (badge on the "Procesos" item).
const {
  pendingCount: processPendingCount,
  hasPending: hasProcessPending,
  fetchPendingCount: fetchProcessPendingCount,
} = usePendingProcessAlerts();

// Notification Center unread count (badge on the bottom-nav "Notificaciones"
// entry). Reuses the existing store so the count stays in sync with the
// bell icon and the dashboard widget — no extra API calls beyond what the
// rest of the app already issues. Requested in R3 — "los badge no aparecen
// en el módulo de notificaciones".
const notificationStore = useNotificationStore();
const notificationsUnreadCount = computed(() => notificationStore.unreadCount || 0);
const hasNotificationsUnread = computed(() => notificationsUnreadCount.value > 0);

const showProfile = ref(false); // Show modal with profile information
const slidebarOpen = ref(false); // Show modal with navigation

onMounted(async () => {
  await userStore.init();
  showProfile.value = !!!currentUser.value.is_profile_completed;

  // Hide legacy legal-request menu entries now replaced by Services module navigation.
  navigation.value = navigation.value.filter(
    (navItem) =>
      navItem.name !== "Solicitudes" && navItem.name !== "Gestión de Solicitudes"
  );

  const role = currentUser.value.role;
  const isAdmin = role === "admin" || currentUser.value.is_staff || currentUser.value.is_superuser;

  if (role === "client" || role === "corporate_client" || role === "basic") {
    // The "Organizaciones" module is intentionally EXCLUSIVE to these three
    // roles — confirmed by the product owner (R3 follow-up, May 2026): it is
    // a feature designed for clients/corporate/basic users only, so it stays
    // hidden for `lawyer` (filtered below) and admin/staff (filtered further
    // down). Keeping the access list narrow here also avoids surfacing the
    // module to roles that don't need it.
    navigation.value = navigation.value.filter(
      (navItem) =>
        navItem.name !== "Directorio" &&
        navItem.name !== "Intranet G&M" &&
        navItem.name !== "Bandeja de Solicitudes" &&
        navItem.name !== "Administrar Servicios" &&
        navItem.name !== "Reasignación de Datos"
    );
  }

  if (role === "lawyer") {
    navigation.value = navigation.value.filter(
      (navItem) =>
        navItem.name !== "Organizaciones" &&
        navItem.name !== "Administrar Servicios" &&
        navItem.name !== "Reasignación de Datos"
    );

    if (!currentUser.value.is_gym_lawyer) {
      navigation.value = navigation.value.filter(
        (navItem) => navItem.name !== "Intranet G&M"
      );
    }
  }

  if (isAdmin) {
    navigation.value = navigation.value.filter(
      (navItem) =>
        navItem.name !== "Organizaciones"
    );
  } else {
    navigation.value = navigation.value.filter(
      (navItem) =>
        navItem.name !== "Administrar Servicios" &&
        navItem.name !== "Reasignación de Datos"
    );
  }

  updateActiveNavItem();

  // Best-effort badge fetches — run AFTER navigation filtering so a failing
  // request can never block the role-based nav filtering above. allSettled
  // keeps a single failed fetch from rejecting the whole hook.
  await Promise.allSettled([
    fetchPendingCount(),
    fetchProcessPendingCount(),
    notificationStore.fetchUnreadCount(),
  ]);
});

/**
 * Logs out the user by clearing the auth store and logging out from Google.
 */
const logOut = () => {
  authStore.logout(); // Log out from the auth store
  googleLogout(); // Log out from Google
  router.push({ name: "sign_in" });
};

/**
 * Shows to profile modal.
 */
const goProfile = () => {
  slidebarOpen.value = false;
  showProfile.value = true;
};

/**
 * Navigation items for the sidebar menu.
 *
 * This array contains objects representing different navigation items in the sidebar menu.
 * Each object has the following properties:
 * - `name` {string}: The display name of the navigation item.
 * - `action` {function|null}: The function to execute when the item is clicked. If `null`, no action is taken.
 * - `icon` {Component}: The icon component to display next to the navigation item name.
 * - `current` {boolean}: Indicates if the navigation item is currently active (true) or not (false).
 * - `routes` {Array<string>}: Array of route paths that should trigger this navigation item to be highlighted.
 *
 * @constant {Array<Object>}
 */
const navigation = ref([
  {
    name: "Inicio",
    action: (item) => {
      setCurrent(item);
      router.push({ name: "dashboard" });
    },
    icon: HomeIcon,
    current: false,
    routes: ['/dashboard']
  },
  {
    name: "Directorio",
    action: (item) => {
      setCurrent(item);
      router.push({ name: "directory_list" });
    },
    icon: UsersIcon,
    current: false,
    routes: ['/directory_list']
  },
  {
    name: "Procesos",
    action: (item) => {
      setCurrent(item);
      router.push({
        name: "process_list",
        params: { user_id: "", display: "" },
      });
    },
    icon: RectangleStackIcon,
    current: false,
    routes: ['/process_list', '/process_detail', '/process_form']
  },
  {
    name: "Organizaciones",
    action: (item) => {
      setCurrent(item);
      router.push({
        name: "organizations_dashboard",
      });
    },
    icon: BuildingOfficeIcon,
    current: false,
    routes: ['/organizations_dashboard']
  },
  {
    name: "Archivos Juridicos",
    action: (item) => {
      setCurrent(item);
      router.push({
        name: "dynamic_document_dashboard",
      });
    },
    icon: DocumentTextIcon,
    current: false,
    routes: ['/dynamic_document_dashboard']
  },
  {
    name: "Servicios y Solicitudes",
    action: (item) => {
      setCurrent(item);
      router.push({ name: "services_hub" });
    },
    icon: RegisteredIcon,
    current: false,
    routes: ['/services']
  },
  {
    name: "Bandeja de Solicitudes",
    action: (item) => {
      setCurrent(item);
      router.push({ name: "service_requests_inbox" });
    },
    icon: EnvelopeIcon,
    current: false,
    routes: ['/service_requests/inbox']
  },
  {
    name: "Administrar Servicios",
    action: (item) => {
      setCurrent(item);
      router.push({ name: "services_admin" });
    },
    icon: BookOpenIcon,
    current: false,
    routes: ['/services_admin']
  },
  {
    name: "Reasignación de Datos",
    action: (item) => {
      setCurrent(item);
      router.push({ name: "data_reassignment" });
    },
    icon: ArrowsRightLeftIcon,
    current: false,
    routes: ['/data_reassignment']
  },
  {
    name: "Solicitudes",
    action: (item) => {
      setCurrent(item);
      router.push({ name: "legal_requests_list" });
    },
    icon: InboxArrowDownIcon,
    current: false,
    routes: ['/legal_requests', '/legal_request']
  },
  {
    name: "Gestión de Solicitudes",
    action: (item) => {
      setCurrent(item);
      router.push({ name: "legal_requests_list" });
    },
    icon: EnvelopeIcon,
    current: false,
    routes: ['/legal_requests', '/legal_request']
  },
  {
    name: "Intranet G&M",
    action: (item) => {
      setCurrent(item);
      router.push({ name: "intranet_g_y_m" });
    },
    icon: ScaleIcon,
    current: false,
    routes: ['/intranet_g_y_m']
  },
  {
    name: "Contratación Estatal",
    action: (item) => {
      setCurrent(item);
      router.push({ name: "secop_list" });
    },
    icon: BuildingLibraryIcon,
    current: false,
    routes: ['/secop']
  },
]);

const bottomNavigation = ref([
  {
    name: "Notificaciones",
    action: (item) => {
      setCurrentBottom(item);
      router.push({ name: "notifications" });
    },
    icon: BellAlertIcon,
    current: false,
    routes: ['/notifications']
  },
  {
    name: "Manual de Usuario",
    action: (item) => {
      setCurrentBottom(item);
      if (route.path === '/user_guide') {
        router.push({ name: "user_guide", params: { refresh: Date.now() } });
      } else {
        router.push({ name: "user_guide" });
      }
    },
    icon: BookOpenIcon,
    current: false,
    routes: ['/user_guide']
  },
]);

/**
 * User navigation items for the user menu.
 *
 * This array contains objects representing different actions available to the user in the user menu.
 * Each object has the following properties:
 * - `name` {string}: The display name of the user menu item.
 * - `action` {function|null}: The function to execute when the item is clicked. If `null`, no action is taken.
 *
 * @constant {Array<Object>}
 */
const userNavigation = [
  {
    name: "Perfil",
    action: goProfile,
  },
  {
    name: "Cerrar sesión",
    action: logOut,
  },
];

/**
 * Updates the active navigation item based on the current route path.
 * 
 * @function updateActiveNavItem
 * @returns {void}
 */
const updateActiveNavItem = () => {
  let foundMatch = false;
  const currentPath = route.path;
  
  navigation.value.forEach((navItem) => {
    // Special case for Procesos (includes archived view now)
    if (navItem.name === "Procesos" && 
            (currentPath.startsWith('/process_list') ||
             currentPath.startsWith('/process_detail') || 
             currentPath.startsWith('/process_form'))) {
      navItem.current = true;
      foundMatch = true;
    }
    // For other navigation items
    else if (navItem.routes && navItem.routes.some(routePath => currentPath.startsWith(routePath))) {
      navItem.current = true;
      foundMatch = true;
    }
    else {
      navItem.current = false;
    }
  });

  bottomNavigation.value.forEach((navItem) => {
    if (navItem.routes && navItem.routes.some(routePath => currentPath.startsWith(routePath))) {
      navItem.current = true;
      foundMatch = true;
    } else {
      navItem.current = false;
    }
  });
  
  // If no match is found, no button should be highlighted
  if (!foundMatch) {
    navigation.value.forEach(navItem => {
      navItem.current = false;
    });
    bottomNavigation.value.forEach(navItem => {
      navItem.current = false;
    });
  }
};

// Call updateActiveNavItem on component mount and route change
onMounted(() => {
  updateActiveNavItem();
});

// Watch for route changes
watch(
  () => route.fullPath,
  () => {
    updateActiveNavItem();
  }
);

/**
 * Sets the current navigation item as active.
 *
 * This function iterates through the `navigation` items, setting the `current` property of each item to `false`.
 * Then, it sets the `current` property of the provided `item` to `true`, marking it as the active navigation item.
 *
 * @function setCurrent
 * @param {Object} item - The navigation item object to set as active.
 * @returns {void}
 */
const setCurrent = (item) => {
  navigation.value.forEach((navItem) => {
    navItem.current = false;
  });
  bottomNavigation.value.forEach((navItem) => {
    navItem.current = false;
  });

  item.current = true;
  slidebarOpen.value = false;
};

const setCurrentBottom = (item) => {
  navigation.value.forEach((navItem) => {
    navItem.current = false;
  });
  bottomNavigation.value.forEach((navItem) => {
    navItem.current = false;
  });

  item.current = true;
  slidebarOpen.value = false;
};
</script>
