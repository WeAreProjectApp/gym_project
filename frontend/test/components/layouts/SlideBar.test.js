import { mount } from "@vue/test-utils";
import { setActivePinia, createPinia } from "pinia";
import { defineComponent, nextTick } from "vue";

import { useAuthStore } from "@/stores/auth/auth";
import { useUserStore } from "@/stores/auth/user";

import SlideBar from "@/components/layouts/SlideBar.vue";

const mockRouterPush = jest.fn();
const mockGoogleLogout = jest.fn();
var mockRoute;

jest.mock("vue-router", () => {
  const { reactive } = require("vue");
// quality: allow-test-too-long (component tests with complex mount setup and validation)

  if (!mockRoute) {
    mockRoute = reactive({
      path: "/dashboard",
      fullPath: "/dashboard",
    });
  }

  return {
    __esModule: true,
    useRouter: () => ({
      push: mockRouterPush,
    }),
    useRoute: () => mockRoute,
  };
});

jest.mock("vue3-google-login", () => ({
  __esModule: true,
  googleLogout: () => mockGoogleLogout(),
}));

jest.mock("@/composables/usePendingSignatures", () => {
  const { ref } = require("vue");
  return {
    __esModule: true,
    PENDING_SIGNATURES_ALERTED_KEY: "pendingSignaturesAlerted",
    usePendingSignatures: () => ({
      pendingCount: ref(0),
      hasPending: ref(false),
      shouldAlert: ref(false),
      isLoading: ref(false),
      error: ref(null),
      hasAlertedThisSession: ref(false),
      fetchPendingCount: jest.fn().mockResolvedValue(),
      markAlerted: jest.fn(),
      resetAlertFlag: jest.fn(),
    }),
  };
});

jest.mock("@/composables/usePendingProcessAlerts", () => {
  const { ref } = require("vue");
  return {
    __esModule: true,
    usePendingProcessAlerts: () => ({
      pendingCount: ref(0),
      hasPending: ref(false),
      fetchPendingCount: jest.fn().mockResolvedValue(),
    }),
  };
});

jest.mock("@headlessui/vue", () => ({
  __esModule: true,
  Dialog: { name: "Dialog", template: "<div><slot /></div>" },
  DialogPanel: { name: "DialogPanel", template: "<div><slot /></div>" },
  TransitionRoot: {
    name: "TransitionRoot",
    props: ["show"],
    template: "<div v-show='show' data-test='transition-root'><slot /></div>",
  },
  TransitionChild: { name: "TransitionChild", template: "<div><slot /></div>" },
  Menu: { name: "Menu", template: "<div><slot /></div>" },
  MenuButton: { name: "MenuButton", template: "<button><slot /></button>" },
  MenuItems: { name: "MenuItems", template: "<div><slot /></div>" },
  MenuItem: {
    name: "MenuItem",
    setup(_, { slots }) {
      return () => (slots.default ? slots.default({ active: false }) : null);
    },
  },
}));

const flushPromises = () => new Promise((resolve) => setTimeout(resolve, 0));

const MenuItemStub = {
  name: "MenuItem",
  setup(_, { slots }) {
    return () => (slots.default ? slots.default({ active: false }) : null);
  },
};

const RouterViewStub = defineComponent({
  name: "RouterView",
  setup(_, { slots }) {
    const Component = defineComponent({
      name: "RouterViewInner",
      template: "<div><slot /></div>",
    });
    return () => (slots.default ? slots.default({ Component }) : null);
  },
});

const TransitionRootStub = {
  name: "TransitionRoot",
  props: ["show"],
  template: "<div v-show='show' data-test='transition-root'><slot /></div>",
};

describe("SlideBar.vue", () => {
  beforeEach(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
    jest.clearAllMocks();
    jest.useRealTimers();

    if (mockRoute) {
      mockRoute.path = "/dashboard";
      mockRoute.fullPath = "/dashboard";
    }
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  const globalStubs = {
    Profile: {
      props: ["visible", "currentUser"],
      template: "<div v-if='visible' data-test='profile-modal'>Profile Modal</div>",
    },
    PWAInstallButton: { template: "<div />" },
    "router-view": RouterViewStub,

    Dialog: { template: "<div><slot /></div>" },
    DialogPanel: { template: "<div><slot /></div>" },
    TransitionRoot: TransitionRootStub,
    TransitionChild: { template: "<div><slot /></div>" },
    Menu: { template: "<div><slot /></div>" },
    MenuButton: { template: "<button><slot /></button>" },
    MenuItems: { template: "<div><slot /></div>" },
    MenuItem: MenuItemStub,
  };

  const mountSlideBar = async ({ user, routePath } = {}) => {
    const pinia = createPinia();
    setActivePinia(pinia);

    const authStore = useAuthStore();
    const userStore = useUserStore();

    if (user) {
      authStore.$patch({ userAuth: { id: user.id } });
      userStore.$patch({ users: [user] });
    }

    jest.spyOn(userStore, "init").mockResolvedValue();

    if (mockRoute && routePath) {
      mockRoute.path = routePath;
      mockRoute.fullPath = routePath;
    }

    const wrapper = mount(SlideBar, {
      global: {
        plugins: [pinia],
        stubs: globalStubs,
      },
    });

    await flushPromises();
    return { wrapper, pinia, authStore, userStore };
  };

  test("clicking 'Perfil' opens Profile modal", async () => {
    const { wrapper } = await mountSlideBar({
      user: {
        id: 1,
        first_name: "Test",
        last_name: "User",
        role: "client",
        is_profile_completed: true,
        is_gym_lawyer: false,
        photo_profile: "",
      },
    });

    expect(wrapper.find("[data-test='profile-modal']").exists()).toBe(false);

    const perfilLink = wrapper
      .findAll("a")
      .find((a) => (a.text() || "").trim() === "Perfil");

    expect(perfilLink.text().trim()).toBe("Perfil");

    await perfilLink.trigger("click");
    await flushPromises();

    expect(wrapper.find("[data-test='profile-modal']").exists()).toBe(true);
  });

  test("logout calls auth logout, googleLogout and redirects to sign_in", async () => {
    const { wrapper, authStore } = await mountSlideBar({
      user: {
        id: 2,
        first_name: "Test",
        last_name: "User",
        role: "client",
        is_profile_completed: true,
        is_gym_lawyer: false,
        photo_profile: "",
      },
    });

    const logoutSpy = jest.spyOn(authStore, "logout").mockImplementation(() => {});

    const logoutLink = wrapper
      .findAll("a")
      .find((a) => (a.text() || "").trim() === "Cerrar sesión");
    expect(logoutLink.text().trim()).toBe("Cerrar sesión");

    await logoutLink.trigger("click");
    await flushPromises();

    expect(logoutSpy).toHaveBeenCalled();
    expect(mockGoogleLogout).toHaveBeenCalled();
    expect(mockRouterPush).toHaveBeenCalledWith({ name: "sign_in" });
  });

  test("filters navigation for client role", async () => {
    const { wrapper } = await mountSlideBar({
      user: {
        id: 3,
        first_name: "C",
        last_name: "User",
        role: "client",
        is_profile_completed: true,
        is_gym_lawyer: false,
        photo_profile: "",
      },
    });

    const texts = wrapper
      .findAll("a")
      .map((a) => (a.text() || "").trim())
      .filter(Boolean);

    expect(texts).not.toContain("Solicitudes");
    // Calendly scheduling was removed (hotfix 2026-10-07): the item must not come back.
    expect(texts).not.toContain("Agendar Cita");
    expect(texts).not.toContain("Directorio");
    expect(texts).not.toContain("Intranet G&M");
    expect(texts).not.toContain("Gestión de Solicitudes");
    expect(texts).toContain("Organizaciones");
  });

  test("filters navigation for non-gym lawyer role", async () => {
    const { wrapper } = await mountSlideBar({
      user: {
        id: 4,
        first_name: "L",
        last_name: "User",
        role: "lawyer",
        is_profile_completed: true,
        is_gym_lawyer: false,
        photo_profile: "",
      },
    });

    const texts = wrapper
      .findAll("a")
      .map((a) => (a.text() || "").trim())
      .filter(Boolean);

    expect(texts).toContain("Directorio");
    expect(texts).not.toContain("Gestión de Solicitudes");
    expect(texts).not.toContain("Organizaciones");
    expect(texts).not.toContain("Intranet G&M");
    expect(texts).not.toContain("Solicitudes");
    expect(texts).not.toContain("Agendar Cita");
  });

  test("Manual de Usuario pushes refresh param when already on /user_guide", async () => {
    const { wrapper } = await mountSlideBar({
      user: {
        id: 5,
        first_name: "C",
        last_name: "User",
        role: "client",
        is_profile_completed: true,
        is_gym_lawyer: false,
        photo_profile: "",
      },
      routePath: "/user_guide",
    });

    const manualLink = wrapper
      .findAll("a")
      .find((a) => (a.text() || "").trim() === "Manual de Usuario");
    expect(manualLink.text().trim()).toBe("Manual de Usuario");

    await manualLink.trigger("click");
    await flushPromises();

    expect(mockRouterPush).toHaveBeenCalledWith({
      name: "user_guide",
      params: { refresh: expect.any(Number) },
    });
  });

  test("highlights active nav item based on route and updates on route changes", async () => {
    const { wrapper } = await mountSlideBar({
      user: {
        id: 6,
        first_name: "L",
        last_name: "User",
        role: "lawyer",
        is_profile_completed: true,
        is_gym_lawyer: true,
        photo_profile: "",
      },
      routePath: "/dashboard",
    });

    const linksByText = (t) =>
      wrapper.findAll("a").filter((a) => (a.text() || "").trim() === t);
    const isActiveLink = (a) =>
      a.classes().includes("bg-selected-background") || a.classes().includes("bg-gray-50");
    const expectAnyActive = (t) => {
      const links = linksByText(t);
      expect(links.length).toBeGreaterThan(0);
      expect(links.some(isActiveLink)).toBe(true);
    };
    const expectAllInactive = (t) => {
      const links = linksByText(t);
      expect(links.length).toBeGreaterThan(0);
      expect(
        links.every(
          (a) =>
            !a.classes().includes("bg-selected-background") &&
            !a.classes().includes("bg-gray-50")
        )
      ).toBe(true);
    };

    expectAnyActive("Inicio");
    expectAllInactive("Procesos");

    mockRoute.path = "/process_detail/3";
    mockRoute.fullPath = "/process_detail/3";
    await flushPromises();

    expectAnyActive("Procesos");

    mockRoute.path = "/somewhere";
    mockRoute.fullPath = "/somewhere";
    await flushPromises();

    expectAllInactive("Inicio");
    expectAllInactive("Procesos");
  });

  test("mobile slidebar opens from router-view slot button and closes when selecting a nav item", async () => {
    const { wrapper } = await mountSlideBar({
      user: {
        id: 7,
        first_name: "C",
        last_name: "User",
        role: "client",
        is_profile_completed: true,
        is_gym_lawyer: false,
        photo_profile: "",
      },
      routePath: "/dashboard",
    });

    const transitionRoot = wrapper.find("[data-test='transition-root']");
    expect(transitionRoot.exists()).toBe(true);
    expect(transitionRoot.attributes("style") || "").toContain("display: none");

    const openBtn = wrapper.find("button.text-gray-700.lg\\:hidden");
    expect(openBtn.exists()).toBe(true);
    await openBtn.trigger("click");
    await nextTick();
    await flushPromises();

    const mobileRoot = wrapper.find("[data-test='transition-root']");
    expect(mobileRoot.exists()).toBe(true);
    expect(mobileRoot.attributes("style") || "").not.toContain("display: none");

    const inicioMobile = mobileRoot
      .findAll("a")
      .find((a) => (a.text() || "").trim() === "Inicio");
    expect(inicioMobile.text().trim()).toBe("Inicio");
    await inicioMobile.trigger("click");
    await nextTick();
    await flushPromises();

    expect(wrapper.find("[data-test='transition-root']").attributes("style") || "").toContain(
      "display: none"
    );
  });

  test("mobile slidebar close button closes slidebar", async () => {
    const { wrapper } = await mountSlideBar({
      user: {
        id: 8,
        first_name: "C",
        last_name: "User",
        role: "client",
        is_profile_completed: true,
        is_gym_lawyer: false,
        photo_profile: "",
      },
      routePath: "/dashboard",
    });

    const openBtn = wrapper.find("button.text-gray-700.lg\\:hidden");
    expect(openBtn.exists()).toBe(true);
    await openBtn.trigger("click");
    await nextTick();
    await flushPromises();

    const mobileRoot = wrapper.find("[data-test='transition-root']");
    expect(mobileRoot.exists()).toBe(true);

    const closeBtn = mobileRoot
      .findAll("button")
      .find((b) => {
        const spans = b.findAll("span");
        return spans.some((s) => (s.text() || "").trim() === "Cerrar slidebar");
      });
    expect(closeBtn.text()).toContain("Cerrar slidebar");
    await closeBtn.trigger("click");
    await nextTick();
    await flushPromises();

    expect(wrapper.find("[data-test='transition-root']").attributes("style") || "").toContain(
      "display: none"
    );
  });

  test("shows profile modal automatically when profile is not completed", async () => {
    const { wrapper } = await mountSlideBar({
      user: {
        id: 9,
        first_name: "Auto",
        last_name: "Open",
        role: "client",
        is_profile_completed: false,
        is_gym_lawyer: false,
        photo_profile: "",
      },
    });

    await flushPromises();
    expect(wrapper.find("[data-test='profile-modal']").exists()).toBe(true);
  });

  test("Manual de Usuario navigates normally when not already on /user_guide", async () => {
    const { wrapper } = await mountSlideBar({
      user: {
        id: 10,
        first_name: "C",
        last_name: "User",
        role: "client",
        is_profile_completed: true,
        is_gym_lawyer: false,
        photo_profile: "",
      },
      routePath: "/dashboard",
    });

    const manualLink = wrapper
      .findAll("a")
      .find((a) => (a.text() || "").trim() === "Manual de Usuario");
    expect(manualLink.text().trim()).toBe("Manual de Usuario");

    await manualLink.trigger("click");
    await flushPromises();

    expect(mockRouterPush).toHaveBeenCalledWith({ name: "user_guide" });
  });

  test("gym lawyer navigation actions call router.push with expected routes", async () => {
    const { wrapper } = await mountSlideBar({
      user: {
        id: 11,
        first_name: "Gym",
        last_name: "Lawyer",
        role: "lawyer",
        is_profile_completed: true,
        is_gym_lawyer: true,
        photo_profile: "",
      },
      routePath: "/dashboard",
    });

    const clickNav = async (label) => {
      const link = wrapper
        .findAll("a")
        .find((a) => (a.text() || "").trim() === label);
      expect(link.text().trim()).toBe(label);
      mockRouterPush.mockClear();
      await link.trigger("click");
      await flushPromises();
      return mockRouterPush.mock.calls[0]?.[0];
    };

    expect(await clickNav("Inicio")).toEqual({ name: "dashboard" });
    expect(await clickNav("Directorio")).toEqual({ name: "directory_list" });
    expect(await clickNav("Procesos")).toEqual({
      name: "process_list",
      params: { user_id: "", display: "" },
    });
    expect(await clickNav("Archivos Juridicos")).toEqual({
      name: "dynamic_document_dashboard",
    });
    expect(await clickNav("Bandeja de Solicitudes")).toEqual({
      name: "service_requests_inbox",
    });
    expect(await clickNav("Intranet G&M")).toEqual({ name: "intranet_g_y_m" });
  });

  test("client navigation actions call router.push with expected routes", async () => {
    const { wrapper } = await mountSlideBar({
      user: {
        id: 12,
        first_name: "Client",
        last_name: "User",
        role: "client",
        is_profile_completed: true,
        is_gym_lawyer: false,
        photo_profile: "",
      },
      routePath: "/dashboard",
    });

    const clickNav = async (label) => {
      const link = wrapper
        .findAll("a")
        .find((a) => (a.text() || "").trim() === label);
      expect(link.text().trim()).toBe(label);
      mockRouterPush.mockClear();
      await link.trigger("click");
      await flushPromises();
      return mockRouterPush.mock.calls[0]?.[0];
    };

    expect(await clickNav("Servicios y Solicitudes")).toEqual({ name: "services_hub" });
    expect(await clickNav("Organizaciones")).toEqual({ name: "organizations_dashboard" });
  });

  test("admin navigation shows Reasignación de Datos and hides client-only items", async () => {
    const { wrapper } = await mountSlideBar({
      user: {
        id: 14,
        first_name: "Admin",
        last_name: "User",
        role: "admin",
        is_profile_completed: true,
        is_gym_lawyer: false,
        photo_profile: "",
      },
    });

    const texts = wrapper
      .findAll("a")
      .map((a) => (a.text() || "").trim())
      .filter(Boolean);

    expect(texts).toContain("Reasignación de Datos");
    expect(texts).not.toContain("Agendar Cita");
    expect(texts).not.toContain("Organizaciones");
  });

  test("Reasignación de Datos navigates to the data_reassignment route", async () => {
    const { wrapper } = await mountSlideBar({
      user: {
        id: 15,
        first_name: "Admin",
        last_name: "User",
        role: "admin",
        is_profile_completed: true,
        is_gym_lawyer: false,
        photo_profile: "",
      },
      routePath: "/dashboard",
    });

    const link = wrapper
      .findAll("a")
      .find((a) => (a.text() || "").trim() === "Reasignación de Datos");
    expect(link.text().trim()).toBe("Reasignación de Datos");
    mockRouterPush.mockClear();

    await link.trigger("click");
    await flushPromises();

    expect(mockRouterPush).toHaveBeenCalledWith({ name: "data_reassignment" });
  });

  test("hides Reasignación de Datos for lawyer role", async () => {
    const { wrapper } = await mountSlideBar({
      user: {
        id: 16,
        first_name: "Gym",
        last_name: "Lawyer",
        role: "lawyer",
        is_profile_completed: true,
        is_gym_lawyer: true,
        photo_profile: "",
      },
    });

    const texts = wrapper
      .findAll("a")
      .map((a) => (a.text() || "").trim())
      .filter(Boolean);

    expect(texts).not.toContain("Reasignación de Datos");
  });

  test("falls back to empty currentUser when auth user is not set", async () => {
    const { wrapper } = await mountSlideBar();
    await flushPromises();

    // With empty currentUser, is_profile_completed is undefined => showProfile becomes true
    expect(wrapper.find("[data-test='profile-modal']").exists()).toBe(true);
  });

  test("filters navigation for basic role (client-like)", async () => {
    const { wrapper } = await mountSlideBar({
      user: {
        id: 13,
        first_name: "Basic",
        last_name: "User",
        role: "basic",
        is_profile_completed: true,
        is_gym_lawyer: false,
        photo_profile: "",
      },
    });

    const texts = wrapper
      .findAll("a")
      .map((a) => (a.text() || "").trim())
      .filter(Boolean);

    expect(texts).not.toContain("Solicitudes");
    expect(texts).not.toContain("Gestión de Solicitudes");
    expect(texts).not.toContain("Intranet G&M");
    expect(texts).toContain("Organizaciones");
  });
});
