import { mount } from "@vue/test-utils";

import QuickActionButtons from "@/components/dashboard/QuickActionButtons.vue";

const findClickableCardByText = (wrapper, text) => {
  const card = wrapper.findAll("div").find((node) => {
    const className = node.attributes("class") || "";
    return className.includes("cursor-pointer") && (node.text() || "").includes(text);
  });
  if (!card) {
    throw new Error(`Card not found: ${text}`);
  }
  return card;
};

const mountView = (user) =>
  mount(QuickActionButtons, {
    props: { user },
    global: {
      stubs: {
        RouterLink: { template: "<a><slot /></a>" },
        ModalTransition: {
          template: "<div data-test='facturation-modal' v-bind='$attrs'><slot /></div>",
        },
        FacturationForm: { template: "<div data-test='facturation-form' />" },
        FolderOpenIcon: { template: "<span />" },
        DocumentArrowDownIcon: { template: "<span />" },
        DocumentTextIcon: { template: "<span />" },
        DocumentChartBarIcon: { template: "<span />" },
        CalendarDaysIcon: { template: "<span />" },
        FolderIcon: { template: "<span />" },
        PlusCircleIcon: { template: "<span />" },
        ChevronRightIcon: { template: "<span />" },
        ArrowsRightLeftIcon: { template: "<span />" },
      },
    },
  });

describe("QuickActionButtons.vue", () => {
  test("renders lawyer actions and opens facturation modal", async () => {
    const wrapper = mountView({ role: "lawyer" });

    expect(wrapper.text()).toContain("Todos los Procesos");
    expect(wrapper.text()).toContain("Radicar Proceso");
    expect(wrapper.text()).toContain("Nueva Minuta");
    expect(wrapper.text()).toContain("Radicar Informe");
    expect(wrapper.text()).not.toContain("Mis Procesos");

    expect(wrapper.find("[data-test='facturation-modal']").isVisible()).toBe(false);

    await findClickableCardByText(wrapper, "Radicar Informe").trigger("click");

    expect(wrapper.find("[data-test='facturation-modal']").isVisible()).toBe(true);
  });

  test("renders client actions for non-lawyers", () => {
    const wrapper = mountView({ role: "client" });

    expect(wrapper.text()).toContain("Mis Procesos");
    // Calendly scheduling was removed (hotfix 2026-10-07): the card must not come back.
    expect(wrapper.text()).not.toContain("Agendar Cita");
    expect(wrapper.text()).toContain("Radicar Solicitud");
    expect(wrapper.text()).not.toContain("Radicar Informe");
  });

  test("renders lawyer navigation links", () => {
    const wrapper = mountView({ role: "lawyer" });
    const links = wrapper.findAll("a");

    expect(links.some((link) => link.text().includes("Nueva Minuta"))).toBe(true);
    expect(links.length).toBeGreaterThanOrEqual(3);
  });

  test("admins see the reassignment quick action (not lawyer/client cards)", () => {
    const wrapper = mountView({ role: "admin", is_staff: true });

    expect(wrapper.text()).toContain("Reasignar Datos");
    expect(wrapper.find("[data-testid='quick-action-reassign']").exists()).toBe(true);
    expect(wrapper.text()).not.toContain("Radicar Informe"); // lawyer-only
    expect(wrapper.text()).not.toContain("Radicar Solicitud"); // client-only
  });

  test("lawyers and clients do not see the reassignment quick action", () => {
    expect(mountView({ role: "lawyer" }).text()).not.toContain("Reasignar Datos");
    expect(mountView({ role: "client" }).text()).not.toContain("Reasignar Datos");
  });
});
