import { shallowMount } from "@vue/test-utils";
import { setActivePinia, createPinia } from "pinia";

import Checkout from "@/views/subscriptions/Checkout.vue";
import { useUserStore } from "@/stores/auth/user";
import { useSubscriptionStore } from "@/stores/subscriptions";

const mockRouterPush = jest.fn();

let mockRoute;

jest.mock("vue-router", () => ({
  __esModule: true,
  useRouter: () => ({ push: mockRouterPush }),
  useRoute: () => mockRoute,
}));

jest.mock("sweetalert2", () => ({
  __esModule: true,
  default: {
    fire: jest.fn(),
  },
}));

const flushPromises = () => new Promise((resolve) => setTimeout(resolve, 0));

const mountView = async ({
  plan = "basico",
  subscriptionOverrides = {},
  user = { first_name: "Ana", last_name: "Lopez", email: "ana@test.com" },
} = {}) => {
  const pinia = createPinia();
  setActivePinia(pinia);

  const userStore = useUserStore();
  const subscriptionStore = useSubscriptionStore();

  userStore.$patch({ currentUser: user });
  jest.spyOn(userStore, "init").mockResolvedValue();

  jest.spyOn(subscriptionStore, "fetchWompiPublicKey").mockResolvedValue("pk_test");
  jest.spyOn(subscriptionStore, "createSubscription").mockResolvedValue();
  Object.assign(subscriptionStore, subscriptionOverrides);

  mockRoute = { params: { plan }, query: {} };

  const wrapper = shallowMount(Checkout, {
    global: {
      plugins: [pinia],
    },
  });

  await flushPromises();

  return { wrapper, subscriptionStore };
};

const getSetupState = (wrapper) => wrapper.vm.$.setupState;

const runGoBack = (wrapper) => getSetupState(wrapper).goBack();
const runHandleSubscribe = (wrapper) => getSetupState(wrapper).handleSubscribe();

describe("Checkout view", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("goBack routes to subscriptions", async () => {
    const { wrapper } = await mountView();

    runGoBack(wrapper);

    expect(mockRouterPush).toHaveBeenCalledWith({ name: "subscriptions" });
    expect(mockRouterPush.mock.calls.length).toBe(1);
  });

  test("creates free plan subscription and navigates", async () => {
    const { wrapper, subscriptionStore } = await mountView({ plan: "basico" });

    await runHandleSubscribe(wrapper);

    expect(subscriptionStore.createSubscription).toHaveBeenCalledWith({ plan_type: "basico" });
    expect(mockRouterPush).toHaveBeenCalledWith({ name: "dashboard" });
    expect(mockRouterPush.mock.calls.length).toBe(1);
  });

  test("shows error when free plan activation fails", async () => {
    const { wrapper, subscriptionStore } = await mountView({
      plan: "basico",
      subscriptionOverrides: {
        createSubscription: jest.fn().mockRejectedValue(new Error("fail")),
      },
    });

    await runHandleSubscribe(wrapper);

    expect(subscriptionStore.createSubscription).toHaveBeenCalled();
    expect(mockRouterPush.mock.calls.length).toBe(0);
  });

  test("free plan keeps an enabled activation button", async () => {
    const { wrapper } = await mountView({ plan: "basico" });

    const activate = wrapper.findAll("button").find((b) => b.text().includes("Activar Plan Gratuito"));

    expect(activate.attributes("disabled")).toBeUndefined();
    expect(wrapper.find("[data-testid='checkout-paid-unavailable']").exists()).toBe(false);
  });

  // Hotfix 2026-10-07: online payment is not available. A paid plan shows the notice and a disabled
  // «Próximamente» button instead of the Wompi card form.
  test("paid plan shows the unavailable notice and a disabled Próximamente button", async () => {
    const { wrapper } = await mountView({ plan: "cliente" });

    const notice = wrapper.get("[data-testid='checkout-paid-unavailable']");
    const soon = wrapper.findAll("button").find((b) => b.text().includes("Próximamente"));

    expect(notice.text()).toContain("El pago en línea no está disponible por ahora");
    expect(soon.attributes("disabled")).toBe("");
    expect(wrapper.find("input").exists()).toBe(false);
  });

  test("paid plan never creates a subscription without payment", async () => {
    const { wrapper, subscriptionStore } = await mountView({ plan: "corporativo" });

    await runHandleSubscribe(wrapper);

    const Swal = await import("sweetalert2");
    expect(subscriptionStore.createSubscription).not.toHaveBeenCalled();
    expect(Swal.default.fire).toHaveBeenCalledWith(expect.objectContaining({ title: "Próximamente" }));
    expect(mockRouterPush.mock.calls.length).toBe(0);
  });

  test("paid plan loads no third-party payment script and asks no payment key", async () => {
    const { subscriptionStore } = await mountView({ plan: "cliente" });

    expect(document.head.querySelectorAll("script[src*='wompi']")).toHaveLength(0);
    expect(subscriptionStore.fetchWompiPublicKey).not.toHaveBeenCalled();
  });
});
