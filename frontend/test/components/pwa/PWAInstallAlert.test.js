import { mount } from "@vue/test-utils";
import { ref } from "vue";

import PWAInstallAlert from "@/components/pwa/PWAInstallAlert.vue";

const mockPromptInstall = jest.fn();
const mockIsAppInstalled = ref(false);

jest.mock("@/composables/usePWAInstall", () => {
  return {
    __esModule: true,
    usePWAInstall: () => ({
      isAppInstalled: mockIsAppInstalled,
      promptInstall: mockPromptInstall,
    }),
  };
});

jest.mock("@heroicons/vue/20/solid", () => ({
  __esModule: true,
  InformationCircleIcon: { template: "<span />" },
}));

jest.mock("gsap", () => ({
  __esModule: true,
  default: {
    to: jest.fn(() => ({ kill: jest.fn() })),
  },
}));

describe("PWAInstallAlert.vue", () => {
  let wrapper;

  beforeEach(() => {
    mockPromptInstall.mockClear();
    mockIsAppInstalled.value = false;
  });

  afterEach(() => {
    wrapper.unmount();
  });

  // Catches an install CTA that stops invoking the installation flow.
  test("clicking install triggers promptInstall", async () => {
    wrapper = mount(PWAInstallAlert);

    const button = wrapper.get('[data-testid="pwa-install-alert-button"]');

    expect(button.text()).toContain("Instalar aplicación");
    await button.trigger("click");

    expect(mockPromptInstall).toHaveBeenCalledTimes(1);
  });

  // Catches an overlay being rendered after installation or omitted on the web.
  test.each([
    { state: "installed", installed: true, expectedCount: 0 },
    { state: "web", installed: false, expectedCount: 1 },
  ])("$state application renders $expectedCount install alerts", ({ installed, expectedCount }) => {
    mockIsAppInstalled.value = installed;

    wrapper = mount(PWAInstallAlert);

    expect(wrapper.findAll('[data-testid="pwa-install-alert"]')).toHaveLength(expectedCount);
  });
});
