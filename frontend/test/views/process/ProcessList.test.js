import { shallowMount, RouterLinkStub } from "@vue/test-utils";
import { setActivePinia, createPinia } from "pinia";
import { reactive } from "vue";

import ProcessList from "@/views/process/ProcessList.vue";
import { useProcessStore } from "@/stores/process";
import { useUserStore } from "@/stores/auth/user";

const mockRouterPush = jest.fn();
let mockRoute;

jest.mock("vue-router", () => ({
  __esModule: true,
  useRoute: () => mockRoute,
  useRouter: () => ({ push: mockRouterPush }),
  RouterLink: { name: "RouterLink", template: "<a><slot /></a>" },
}));

jest.mock("@heroicons/vue/24/outline", () => {
  const createIcon = (name) => ({ name, template: "<span />" });
  return {
    __esModule: true,
    MagnifyingGlassIcon: createIcon("MagnifyingGlassIcon"),
    FunnelIcon: createIcon("FunnelIcon"),
    ChevronDownIcon: createIcon("ChevronDownIcon"),
    PlusIcon: createIcon("PlusIcon"),
    ArrowDownTrayIcon: createIcon("ArrowDownTrayIcon"),
    EllipsisVerticalIcon: createIcon("EllipsisVerticalIcon"),
    CubeTransparentIcon: createIcon("CubeTransparentIcon"),
    XMarkIcon: createIcon("XMarkIcon"),
    ArrowsUpDownIcon: createIcon("ArrowsUpDownIcon"),
    ChevronLeftIcon: createIcon("ChevronLeftIcon"),
    ChevronRightIcon: createIcon("ChevronRightIcon"),
  };
});

const MenuStub = {
  name: "Menu",
  setup(_, { slots }) {
    return () => (slots.default ? slots.default({ open: false }) : null);
  },
};

const MenuItemStub = {
  name: "MenuItem",
  setup(_, { slots }) {
    return () => (slots.default ? slots.default({ active: false }) : null);
  },
};

const flushPromises = () => new Promise((resolve) => setTimeout(resolve, 0));

const buildProcess = (overrides = {}) => ({
  id: 1,
  case: { type: "Civil" },
  subcase: "Subcase",
  ref: "REF-1",
  plaintiff: "Alice",
  defendant: "Bob",
  authority: "Court",
  stages: [{ status: "Admisión" }],
  clients: [
    {
      id: 1,
      first_name: "Ana",
      last_name: "Lopez",
      email: "ana@test.com",
      photo_profile: "",
    },
  ],
  lawyer: { id: 2 },
  progress: 25,
  created_at: "2024-01-01T10:00:00Z",
  ...overrides,
});

const mountView = async ({
  processes = [],
  currentUser = { id: 1, role: "client" },
  routeParams = {},
  routeQuery = {},
} = {}) => {
  const pinia = createPinia();
  setActivePinia(pinia);

  const processStore = useProcessStore();
  const userStore = useUserStore();

  processStore.$patch({ processes });
  userStore.$patch({ currentUser });

  jest.spyOn(processStore, "init").mockResolvedValue();
  jest.spyOn(userStore, "init").mockResolvedValue();

  mockRoute.params = routeParams;
  mockRoute.query = routeQuery;

  const wrapper = shallowMount(ProcessList, {
    global: {
      plugins: [pinia],
      stubs: {
        RouterLink: RouterLinkStub,
        TabsCard: { template: "<section><slot /></section>" },
        Menu: MenuStub,
        MenuButton: { template: "<button><slot /></button>" },
        MenuItems: { template: "<div><slot /></div>" },
        MenuItem: MenuItemStub,
        ProcessUsersModal: { template: "<div />", props: ["isOpen", "users"] },
      },
    },
  });

  await flushPromises();

  return { wrapper };
};

describe("ProcessList.vue", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockRoute = reactive({ params: {}, query: {} });
  });

  test.each([
    { role: "lawyer" },
    { role: "admin" },
    { role: "basic", is_staff: true },
    { role: "basic", is_superuser: true },
  ])("offers process creation for $role $is_staff $is_superuser", async (permissions) => {
    const { wrapper } = await mountView({ currentUser: { id: 9, ...permissions } });

    const link = wrapper.find('[data-testid="process-create-link"]');

    expect(link.exists()).toBe(true);
    expect(wrapper.findComponent(RouterLinkStub).props("to")).toEqual({
      name: "process_form", params: { action: "create" },
    });
  });

  test.each(["client", "basic", "corporate_client"])("hides process creation for %s", async (role) => {
    const { wrapper } = await mountView({ currentUser: { id: 9, role } });

    const link = wrapper.find('[data-testid="process-create-link"]');

    expect(link.exists()).toBe(false);
  });

  test("filters archived processes for client and toggles modal", async () => {
    const processes = [
      buildProcess({ id: 1, stages: [{ status: "Fallo" }] }),
      buildProcess({ id: 2, stages: [{ status: "Admisión" }] }),
      buildProcess({
        id: 3,
        stages: [{ status: "Fallo" }],
        clients: [{ id: 2, first_name: "Otro", last_name: "Cliente" }],
      }),
    ];

    const { wrapper } = await mountView({
      processes,
      currentUser: { id: 1, role: "client" },
      routeParams: { display: "history" },
    });

    // quality: allow-implementation-coupling (Vue component internals needed for this assertion)
    expect(wrapper.vm.$.setupState.activeTab).toBe("archived_processes");
    expect(wrapper.vm.$.setupState.filteredAndSortedProcesses.map((p) => p.id)).toEqual([1]);

    wrapper.vm.$.setupState.openUsersModal(processes[0]);
    expect(wrapper.vm.$.setupState.showUsersModal).toBe(true);
    wrapper.vm.$.setupState.closeUsersModal();
    expect(wrapper.vm.$.setupState.showUsersModal).toBe(false);
    expect(wrapper.vm.$.setupState.getActiveTabLabel()).toBe("Procesos Archivados");
  });

  test("searches, sorts, and navigates tabs", async () => {
    const processes = [
      buildProcess({
        id: 4,
        clients: [{ id: 1, first_name: "Beto", last_name: "Zuluaga", email: "b@test.com" }],
      }),
      buildProcess({
        id: 5,
        clients: [{ id: 1, first_name: "Ana", last_name: "Alonso", email: "a@test.com" }],
      }),
    ];

    const { wrapper } = await mountView({
      processes,
      currentUser: { id: 2, role: "lawyer" },
      routeParams: { user_id: "2" },
      routeQuery: { group: "general" },
    });

    // quality: allow-implementation-coupling (Vue component internals needed for this assertion)
    wrapper.vm.$.setupState.searchQuery = "ana";
    await flushPromises();
    expect(wrapper.vm.$.setupState.filteredAndSortedProcesses.map((p) => p.id)).toEqual([5]);

    wrapper.vm.$.setupState.searchQuery = "";
    wrapper.vm.$.setupState.sortBy = "name";
    expect(wrapper.vm.$.setupState.filteredAndSortedProcesses.map((p) => p.id)).toEqual([5, 4]);

    wrapper.vm.$.setupState.navigateTab("archived_processes");
    expect(mockRouterPush).toHaveBeenLastCalledWith({
      path: "/process_list/2/history",
      query: {},
    });
  });

  test("selects and deselects processes", async () => {
    const processes = [buildProcess({ id: 10 }), buildProcess({ id: 11 })];
    const { wrapper } = await mountView({ processes });

    // quality: allow-implementation-coupling (Vue component internals needed for this assertion)
    wrapper.vm.$.setupState.toggleSelectAll();
    expect(wrapper.vm.$.setupState.selectedProcesses).toEqual([10, 11]);
    expect(wrapper.vm.$.setupState.allSelected).toBe(true);

    wrapper.vm.$.setupState.toggleSelectProcess(10);
    expect(wrapper.vm.$.setupState.selectedProcesses).toEqual([11]);
  });
});
