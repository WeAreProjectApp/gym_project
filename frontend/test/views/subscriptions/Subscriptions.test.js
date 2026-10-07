import { shallowMount } from "@vue/test-utils";
import { setActivePinia, createPinia } from "pinia";

import Subscriptions from "@/views/subscriptions/Subscriptions.vue";
import { useAuthStore } from "@/stores/auth/auth";

const mockRouterPush = jest.fn();

let mockRoute;

jest.mock("vue-router", () => ({
  __esModule: true,
  useRouter: () => ({ push: mockRouterPush }),
  useRoute: () => mockRoute,
}));

const flushPromises = () => new Promise((resolve) => setTimeout(resolve, 0));

let pinia;

describe("Subscriptions view", () => {
  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
    jest.clearAllMocks();
    mockRoute = { params: {}, query: {} };
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test("routes authenticated users to checkout", async () => {
    const authStore = useAuthStore();
    authStore.isAuthenticated = jest.fn().mockResolvedValue(true);

    const wrapper = shallowMount(Subscriptions, {
      global: {
        plugins: [pinia],
      },
    });

    await flushPromises();

    const planButtons = wrapper
      .findAll("button")
      .filter((button) => button.text().includes("Elegir plan"));
    await planButtons[0].trigger("click");

    expect(mockRouterPush).toHaveBeenCalledWith({
      name: "checkout",
      params: { plan: "basico" },
    });
  });

  // Hotfix 2026-10-07: online payment is not available, so the paid plans cannot be chosen.
  test("paid plans show a disabled Próximamente button that does not navigate", async () => {
    const authStore = useAuthStore();
    authStore.isAuthenticated = jest.fn().mockResolvedValue(true);

    const wrapper = shallowMount(Subscriptions, {
      global: {
        plugins: [pinia],
      },
    });

    await flushPromises();

    const choose = wrapper.findAll("button").filter((button) => button.text().includes("Elegir plan"));
    const cliente = wrapper.get("[data-testid='plan-cliente-coming-soon']");
    const corporativo = wrapper.get("[data-testid='plan-corporativo-coming-soon']");

    expect(choose).toHaveLength(1);
    expect(cliente.text()).toBe("Próximamente");
    expect(cliente.attributes("disabled")).toBe("");
    expect(corporativo.attributes("disabled")).toBe("");

    await cliente.trigger("click");
    await corporativo.trigger("click");
    await flushPromises();

    expect(mockRouterPush).not.toHaveBeenCalled();
  });

  test("routes anonymous users to subscription sign in", async () => {
    const authStore = useAuthStore();
    authStore.isAuthenticated = jest.fn().mockResolvedValue(false);

    const wrapper = shallowMount(Subscriptions, {
      global: {
        plugins: [pinia],
      },
    });

    await flushPromises();

    const planButtons = wrapper
      .findAll("button")
      .filter((button) => button.text().includes("Elegir plan"));
    await planButtons[0].trigger("click");

    expect(mockRouterPush).toHaveBeenCalledWith({
      name: "subscription_sign_in",
      query: { plan: "basico" },
    });
  });
});
