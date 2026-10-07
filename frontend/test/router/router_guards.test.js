let mockRouterInstance;
let mockBeforeEachGuard;
let mockAfterEachGuard;
let mockRouterOptions;

jest.mock("@/stores/auth/auth", () => ({
  __esModule: true,
  useAuthStore: jest.fn(),
}));

jest.mock("@/components/layouts/SlideBar.vue", () => ({
  __esModule: true,
  default: {},
}));

jest.mock("@/views/auth/SignIn.vue", () => ({ __esModule: true, default: {} }));
jest.mock("@/views/policies/Home.vue", () => ({ __esModule: true, default: {} }));
jest.mock("@/views/auth/SignOn.vue", () => ({ __esModule: true, default: {} }));
jest.mock("@/views/auth/ForgetPassword.vue", () => ({ __esModule: true, default: {} }));
jest.mock("@/views/policies/PrivacyPolicy.vue", () => ({ __esModule: true, default: {} }));
jest.mock("@/views/policies/TermsOfUse.vue", () => ({ __esModule: true, default: {} }));
jest.mock("@/views/offline/NoConnection.vue", () => ({ __esModule: true, default: {} }));
jest.mock("@/views/subscriptions/Subscriptions.vue", () => ({ __esModule: true, default: {} }));
jest.mock("@/views/subscriptions/Checkout.vue", () => ({ __esModule: true, default: {} }));
jest.mock("@/views/auth/SubscriptionSignIn.vue", () => ({ __esModule: true, default: {} }));
jest.mock("@/views/auth/SubscriptionSignUp.vue", () => ({ __esModule: true, default: {} }));
jest.mock("@/views/dashboard/dashboard.vue", () => ({ __esModule: true, default: {} }));
jest.mock("@/views/process/ProcessList.vue", () => ({ __esModule: true, default: {} }));
jest.mock("@/views/process/ProcessDetail.vue", () => ({ __esModule: true, default: {} }));
jest.mock("@/views/process/ProcessForm.vue", () => ({ __esModule: true, default: {} }));
jest.mock("@/views/directory/DirectoryList.vue", () => ({ __esModule: true, default: {} }));
jest.mock("@/views/legal_request/LegalRequest.vue", () => ({ __esModule: true, default: {} }));
jest.mock("@/views/legal_request/LegalRequestsList.vue", () => ({ __esModule: true, default: {} }));
jest.mock("@/views/legal_request/LegalRequestDetail.vue", () => ({ __esModule: true, default: {} }));
jest.mock("@/views/intranet_g_y_m/IntranetGyM.vue", () => ({ __esModule: true, default: {} }));
jest.mock("@/views/organizations/Dashboard.vue", () => ({ __esModule: true, default: {} }));
jest.mock("@/views/dynamic_document/Dashboard.vue", () => ({ __esModule: true, default: {} }));
jest.mock("@/components/dynamic_document/common/SignaturesList.vue", () => ({ __esModule: true, default: {} }));
jest.mock("@/views/dynamic_document/DocumentEditor.vue", () => ({ __esModule: true, default: {} }));
jest.mock("@/views/dynamic_document/DocumentForm.vue", () => ({ __esModule: true, default: {} }));
jest.mock("@/views/dynamic_document/DocumentVariablesConfig.vue", () => ({ __esModule: true, default: {} }));
jest.mock("@/views/user_guide/UserGuideMain.vue", () => ({ __esModule: true, default: {} }));

const mockRegisterView = jest.fn();

let mockUseRecentViewsImpl = () => ({
  registerView: mockRegisterView,
});

jest.mock("@/composables/useRecentViews", () => ({
  __esModule: true,
  useRecentViews: (...args) => mockUseRecentViewsImpl(...args),
}));

const mockUserStore = {
  init: jest.fn(),
  currentUser: { role: "lawyer" },
  get isLawyerLike() {
    const role = this.currentUser?.role;
    return role === "lawyer" || role === "admin";
  },
};

jest.mock("@/stores/auth/user", () => ({
  __esModule: true,
  useUserStore: () => mockUserStore,
}));

jest.mock("vue-router", () => {
  const createWebHistory = jest.fn(() => ({}));
  const createRouter = jest.fn((options) => {
    mockRouterOptions = options;
    mockRouterInstance = {
      beforeEach: jest.fn((cb) => {
        mockBeforeEachGuard = cb;
      }),
      afterEach: jest.fn((cb) => {
        mockAfterEachGuard = cb;
      }),
      options,
    };
    return mockRouterInstance;
  });

  return {
    __esModule: true,
    createRouter,
    createWebHistory,
  };
});

async function loadRouterModuleFresh() {
  mockBeforeEachGuard = undefined;
  mockAfterEachGuard = undefined;
  mockRouterInstance = undefined;
  mockRouterOptions = undefined;
  mockUserStore.init.mockClear();
  mockRegisterView.mockClear();
  mockUseRecentViewsImpl = () => ({
    registerView: mockRegisterView,
  });

  jest.resetModules();
  return await import("@/router/index.js");
}

describe("Router Guards (auth)", () => {
  test("installRouterGuards installs guards only once", async () => {
    const { installRouterGuards } = await loadRouterModuleFresh();

    const authStore = {
      isAuthenticated: jest.fn().mockResolvedValue(false),
    };

    installRouterGuards(authStore);
    installRouterGuards(authStore);

    expect(mockRouterInstance.beforeEach).toHaveBeenCalledTimes(1);
    expect(mockRouterInstance.afterEach).toHaveBeenCalledTimes(1);
  });

  test("routes include root and catch-all with correct metadata", async () => {
    const { routes } = await loadRouterModuleFresh();

    expect(Array.isArray(routes)).toBe(true);

    const root = routes.find((r) => r.path === "/");
    expect(root.path).toBe("/");
    expect(root.name).toBe("root");
    expect(root.meta.requiresAuth).toBe(false);

    const catchAll = routes.find((r) => r.path === "/:pathMatch(.*)*");
    expect(catchAll.path).toBe("/:pathMatch(.*)*");
    expect(catchAll.redirect({})).toEqual({ name: "sign_in" });
  });

  test("router options expose scrollBehavior that scrolls to top", async () => {
    await loadRouterModuleFresh();

    expect(typeof mockRouterOptions.scrollBehavior).toBe("function");
    expect(mockRouterOptions.scrollBehavior()).toEqual({ top: 0 });
  });

  test("route component lazy-loaders can be invoked", async () => {
    const { routes } = await loadRouterModuleFresh();

    const componentLoaders = [];
    const walk = (list) => {
      for (const r of list) {
        if (typeof r.component === "function") componentLoaders.push(r.component);
        if (Array.isArray(r.children)) walk(r.children);
      }
    };
    walk(routes);

    expect(componentLoaders.length).toBeGreaterThan(5);

    for (const loader of componentLoaders) {
      const mod = await loader();
      expect(mod).toHaveProperty("default");
    }
  });

  test("root path '/' redirects to dashboard when authenticated", async () => {
    const { installRouterGuards } = await loadRouterModuleFresh();

    const authStore = {
      isAuthenticated: jest.fn().mockResolvedValue(true),
    };

    installRouterGuards(authStore);

    const next = jest.fn();

    await mockBeforeEachGuard({ name: "sign_in", path: "/", meta: {} }, {}, next);

    expect(next).toHaveBeenCalledWith({ name: "dashboard" });
  });

  test("root path '/' redirects to sign_in when not authenticated", async () => {
    const { installRouterGuards } = await loadRouterModuleFresh();

    const authStore = {
      isAuthenticated: jest.fn().mockResolvedValue(false),
    };

    installRouterGuards(authStore);

    const next = jest.fn();

    await mockBeforeEachGuard({ name: "sign_in", path: "/", meta: {} }, {}, next);

    expect(next).toHaveBeenCalledWith({ name: "sign_in" });
  });

  test("requiresAuth redirects to sign_in when not authenticated", async () => {
    const { installRouterGuards } = await loadRouterModuleFresh();

    const authStore = {
      isAuthenticated: jest.fn().mockResolvedValue(false),
    };

    installRouterGuards(authStore);

    const consoleWarnSpy = jest.spyOn(console, "warn").mockImplementation(() => {});

    const next = jest.fn();
    await mockBeforeEachGuard(
      { name: "dashboard", path: "/dashboard", meta: { requiresAuth: true } },
      {},
      next
    );

    expect(next).toHaveBeenCalledWith({ name: "sign_in" });

    consoleWarnSpy.mockRestore();
  });

  test("allows navigation when route does not require auth", async () => {
    const { installRouterGuards } = await loadRouterModuleFresh();

    const authStore = {
      isAuthenticated: jest.fn().mockResolvedValue(false),
    };

    installRouterGuards(authStore);

    const next = jest.fn();
    await mockBeforeEachGuard({ name: "home", path: "/home", meta: { requiresAuth: false } }, {}, next);

    expect(next).toHaveBeenCalledWith();
  });

  test("not found route (name null) redirects based on auth", async () => {
    const { installRouterGuards } = await loadRouterModuleFresh();

    const authStore = {
      isAuthenticated: jest.fn().mockResolvedValue(true),
    };

    installRouterGuards(authStore);

    const next = jest.fn();
    await mockBeforeEachGuard({ name: null, path: "/does-not-exist", meta: {} }, {}, next);

    expect(next).toHaveBeenCalledWith({ name: "dashboard" });
  });

  test("requiresLawyer redirects client/basic/corporate_client to dashboard", async () => {
    const { installRouterGuards } = await loadRouterModuleFresh();

    const authStore = {
      isAuthenticated: jest.fn().mockResolvedValue(true),
    };

    mockUserStore.currentUser = { role: "client" };

    installRouterGuards(authStore);

    const consoleWarnSpy = jest.spyOn(console, "warn").mockImplementation(() => {});

    const next = jest.fn();
    await mockBeforeEachGuard(
      { name: "lawyer_only", path: "/lawyer", meta: { requiresAuth: true, requiresLawyer: true } },
      {},
      next
    );

    expect(mockUserStore.init).toHaveBeenCalled();
    expect(next).toHaveBeenCalledWith({ name: "dashboard" });

    consoleWarnSpy.mockRestore();
  });

  test("requiresLawyer allows lawyer role", async () => {
    const { installRouterGuards } = await loadRouterModuleFresh();

    const authStore = {
      isAuthenticated: jest.fn().mockResolvedValue(true),
    };

    mockUserStore.currentUser = { role: "lawyer" };

    installRouterGuards(authStore);

    const next = jest.fn();
    await mockBeforeEachGuard(
      { name: "lawyer_only", path: "/lawyer", meta: { requiresAuth: true, requiresLawyer: true } },
      {},
      next
    );

    expect(mockUserStore.init).toHaveBeenCalled();
    expect(next).toHaveBeenCalledWith();
  });

  test("guard errors redirect to sign_in", async () => {
    const { installRouterGuards } = await loadRouterModuleFresh();

    const authStore = {
      isAuthenticated: jest.fn().mockRejectedValue(new Error("boom")),
    };

    installRouterGuards(authStore);

    const consoleErrorSpy = jest.spyOn(console, "error").mockImplementation(() => {});

    const next = jest.fn();
    await mockBeforeEachGuard(
      { name: "dashboard", path: "/dashboard", meta: { requiresAuth: true } },
      {},
      next
    );

    expect(next).toHaveBeenCalledWith({ name: "sign_in" });

    consoleErrorSpy.mockRestore();
  });

  test("afterEach sets document title and registers process view when appropriate", async () => {
    const { installRouterGuards } = await loadRouterModuleFresh();

    const authStore = {
      isAuthenticated: jest.fn().mockResolvedValue(true),
    };

    installRouterGuards(authStore);

    document.title = "";

    await mockAfterEachGuard({
      name: "process_detail",
      path: "/process/1",
      params: { process_id: 1 },
      query: {},
      meta: { title: "Proceso" },
    });

    expect(document.title).toBe("Proceso | G&M Abogados");
    expect(mockRegisterView).toHaveBeenCalledWith("process", 1);
  });

  test("afterEach sets default title and registers dynamic document views", async () => {
    const { installRouterGuards } = await loadRouterModuleFresh();

    const authStore = {
      isAuthenticated: jest.fn().mockResolvedValue(true),
    };

    installRouterGuards(authStore);

    document.title = "";
    await mockAfterEachGuard({
      name: "dashboard",
      path: "/dashboard",
      params: {},
      query: {},
      meta: {},
    });
    expect(document.title).toBe("G&M Abogados");

    await mockAfterEachGuard({
      name: "doc_edit",
      path: "/dynamic_document_dashboard/lawyer/editor/edit/33",
      params: { id: 33 },
      query: {},
      meta: { title: "Editar Documento" },
    });

    await mockAfterEachGuard({
      name: "doc_use",
      path: "/dynamic_document_dashboard/document/use/edit/44/title",
      params: { id: 44 },
      query: {},
      meta: { title: "Completar Documento" },
    });

    await mockAfterEachGuard({
      name: "variables_config",
      path: "/dynamic_document_dashboard/lawyer/variables-config",
      params: {},
      query: { documentId: 55 },
      meta: { title: "Configurar Variables" },
    });

    expect(mockRegisterView).toHaveBeenCalledWith("document", 33);
    expect(mockRegisterView).toHaveBeenCalledWith("document", 44);
    expect(mockRegisterView).toHaveBeenCalledWith("document", 55);
  });

  test("afterEach logs error when recent views registration fails", async () => {
    const { installRouterGuards } = await loadRouterModuleFresh();

    const authStore = {
      isAuthenticated: jest.fn().mockResolvedValue(true),
    };

    installRouterGuards(authStore);

    mockUseRecentViewsImpl = () => {
      throw new Error("recent views fail");
    };

    const consoleErrorSpy = jest.spyOn(console, "error").mockImplementation(() => {});

    await mockAfterEachGuard({
      name: "process_detail",
      path: "/process/2",
      params: { process_id: 2 },
      query: {},
      meta: { title: "Proceso" },
    });

    expect(consoleErrorSpy).toHaveBeenCalledWith(
      "Error registering view:",
      expect.any(Error)
    );

    consoleErrorSpy.mockRestore();
  });

  test("afterEach logs error when unexpected error occurs", async () => {
    const { installRouterGuards } = await loadRouterModuleFresh();

    const authStore = {
      isAuthenticated: jest.fn().mockResolvedValue(true),
    };

    installRouterGuards(authStore);

    const consoleErrorSpy = jest.spyOn(console, "error").mockImplementation(() => {});

    await mockAfterEachGuard({
      name: "process_detail",
      path: "/process/2",
      params: { process_id: 2 },
      query: {},
      meta: null,
    });

    expect(consoleErrorSpy).toHaveBeenCalledWith(
      "Error in afterEach guard:",
      expect.any(Error)
    );

    consoleErrorSpy.mockRestore();
  });
});
