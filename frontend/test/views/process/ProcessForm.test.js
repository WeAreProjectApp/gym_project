import { shallowMount } from "@vue/test-utils";
import { setActivePinia, createPinia } from "pinia";
import { reactive, nextTick } from "vue";

import ProcessForm from "@/views/process/ProcessForm.vue";
import { useCaseTypeStore } from "@/stores/legal/case_type";
import { useUserStore } from "@/stores/auth/user";
import { useAuthStore } from "@/stores/auth/auth";
import { useProcessStore } from "@/stores/process";

const mockRouterPush = jest.fn();
const mockRouterBack = jest.fn();
const mockSubmitHandler = jest.fn();
const mockSwalFire = jest.fn();
const mockShowNotification = jest.fn();

let mockRoute;

jest.mock("@/router", () => ({
  __esModule: true,
  default: {
    push: (...args) => mockRouterPush(...args),
    back: () => mockRouterBack(),
  },
}));

jest.mock("vue-router", () => ({
  __esModule: true,
  useRoute: () => mockRoute,
}));

jest.mock("@/shared/submit_handler", () => ({
  __esModule: true,
  submitHandler: (...args) => mockSubmitHandler(...args),
}));

jest.mock("@/shared/notification_message.js", () => ({
  __esModule: true,
  showNotification: (...args) => mockShowNotification(...args),
}));

jest.mock("sweetalert2", () => ({
  __esModule: true,
  default: {
    fire: (...args) => mockSwalFire(...args),
  },
}));

jest.mock("@headlessui/vue", () => ({
  __esModule: true,
  Combobox: { name: "Combobox", template: "<div><slot /></div>" },
  ComboboxButton: { name: "ComboboxButton", template: "<button><slot /></button>" },
  ComboboxInput: { name: "ComboboxInput", template: "<input />" },
  ComboboxLabel: { name: "ComboboxLabel", template: "<label><slot /></label>" },
  ComboboxOptions: { name: "ComboboxOptions", template: "<div><slot /></div>" },
  ComboboxOption: {
    name: "ComboboxOption",
    setup(_, { slots }) {
      return () => (slots.default ? slots.default({ active: false, selected: false }) : null);
    },
  },
}));

jest.mock("@heroicons/vue/20/solid", () => ({
  __esModule: true,
  CheckIcon: { template: "<span />" },
  ChevronDownIcon: { template: "<span />" },
  PlusIcon: { template: "<span />" },
}));

jest.mock("@heroicons/vue/24/outline", () => ({
  __esModule: true,
  TrashIcon: { template: "<span />" },
  EyeIcon: { template: "<span />" },
}));

const flushPromises = () => new Promise((resolve) => setTimeout(resolve, 0));

const buildProcess = (overrides = {}) => ({
  id: 101,
  plaintiff: "Alice",
  defendant: "Bob",
  case: { id: 10, type: "Civil" },
  subcase: "Subcase",
  ref: "REF-1",
  authority: "Court",
  authority_email: "court@test.com",
  clients: [{ id: 1, first_name: "Ana", last_name: "Lopez", role: "client" }],
  lawyer: { id: 99 },
  progress: 20,
  stages: [{ status: "Admisión", date: "2099-12-31" }],
  case_files: [{ id: 5, file: "http://files.test/file.pdf" }],
  ...overrides,
});

const createFile = (name, type, size = 1000) => {
  const file = new File([new ArrayBuffer(8)], name, { type });
  Object.defineProperty(file, "size", { value: size });
  return file;
};

const getSetupState = (wrapper) => wrapper.vm.$.setupState;
const getFormData = (wrapper) => getSetupState(wrapper).formData;

const mountView = async ({
  routeParams = { action: "add", process_id: "" },
  processes = [],
  caseTypes = [],
  users = [],
  currentUser = { id: 99, role: "lawyer" },
  authUser = { id: 99 },
} = {}) => {
  const pinia = createPinia();
  setActivePinia(pinia);

  const processStore = useProcessStore();
  const caseTypeStore = useCaseTypeStore();
  const userStore = useUserStore();
  const authStore = useAuthStore();

  processStore.$patch({ processes });
  caseTypeStore.$patch({ caseTypes });
  userStore.$patch({ users, currentUser });
  authStore.$patch({ userAuth: authUser });

  const processInitSpy = jest.spyOn(processStore, "init").mockResolvedValue();
  const caseTypeInitSpy = jest.spyOn(caseTypeStore, "init").mockResolvedValue();
  const userInitSpy = jest.spyOn(userStore, "init").mockResolvedValue();

  mockRoute.params = routeParams;

  const wrapper = shallowMount(ProcessForm, {
    global: {
      plugins: [pinia],
    },
  });

  await flushPromises();

  return {
    wrapper,
    processInitSpy,
    caseTypeInitSpy,
    userInitSpy,
    processStore,
    caseTypeStore,
    userStore,
    authStore,
  };
};

const mountEditView = async (processOverrides = {}) => {
  const process = buildProcess(processOverrides);
  const view = await mountView({
    routeParams: { action: "edit", process_id: String(process.id) },
    processes: [process],
  });

  return { ...view, process };
};

describe("ProcessForm.vue", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockRoute = reactive({ params: { action: "add", process_id: "" } });
  });

  test("loads process data in edit mode", async () => {
    const { wrapper, processInitSpy, caseTypeInitSpy, userInitSpy, process } = await mountEditView();
    const setupState = getSetupState(wrapper);

    expect([processInitSpy, caseTypeInitSpy, userInitSpy].every((spy) => spy.mock.calls.length)).toBe(true);
    expect([
      setupState.formData.plaintiff,
      setupState.formData.authorityEmail,
      setupState.selectedCaseType,
      setupState.selectedClients.length,
      setupState.formData.caseFiles.length,
      setupState.isFormModified,
      setupState.isSaveButtonEnabled,
    ]).toEqual(["Alice", "court@test.com", process.case, 1, 1, false, true]);
  });

  test("tracks changes and resets when route action changes", async () => {
    const { wrapper } = await mountEditView();
    const setupState = getSetupState(wrapper);

    setupState.formData.plaintiff = "Updated";
    await nextTick();
    expect(setupState.isFormModified).toBe(true);

    mockRoute.params.action = "add";
    await nextTick();
    expect(setupState.formData.plaintiff).toBe("");
  });

  test("submits a valid new process and navigates to list", async () => {
    const client = { id: 7, first_name: "Ana", last_name: "Lopez", role: "client" };
    const lawyer = { id: 55, role: "lawyer" };

    const { wrapper } = await mountView({
      routeParams: { action: "add", process_id: "" },
      caseTypes: [{ id: 10, type: "Civil" }],
      users: [client, lawyer],
      currentUser: lawyer,
      authUser: { id: 55 },
    });
    const setupState = getSetupState(wrapper);

    setupState.selectedCaseType = { id: 10, type: "Civil" };
    setupState.selectedClients = [client];

    setupState.formData.plaintiff = "Plaintiff";
    setupState.formData.defendant = "Defendant";
    setupState.formData.subcase = "Sub";
    setupState.formData.ref = "REF";
    setupState.formData.authority = "Court";
    setupState.formData.stages = [{ status: "Inicio", date: "2024-01-01" }];
    setupState.formData.caseFiles = [
      { file: createFile("file.pdf", "application/pdf") },
    ];

    mockSubmitHandler.mockResolvedValue();

    await setupState.onSubmit();

    expect(mockSubmitHandler).toHaveBeenCalledWith(
      expect.objectContaining({
        plaintiff: "Plaintiff",
        caseTypeId: 10,
        clientIds: [7],
        lawyerId: 55,
      }),
      expect.stringContaining("guardado exitosamente"),
      false
    );

    expect(mockRouterPush).toHaveBeenCalledWith({
      name: "process_list",
      params: { user_id: "", display: "" },
    });
  });

  test("blocks submit when required fields are missing", async () => {
    const { wrapper } = await mountView({
      routeParams: { action: "add", process_id: "" },
      authUser: { id: 42 },
    });
    const setupState = getSetupState(wrapper);

    setupState.selectedCaseType = { id: 10, type: "Civil" };
    setupState.selectedClients = [{ id: 1, role: "client" }];
    setupState.formData.defendant = "Defendant";
    setupState.formData.subcase = "Sub";
    setupState.formData.ref = "REF";
    setupState.formData.authority = "Court";
    setupState.formData.stages = [{ status: "Inicio", date: "2024-01-01" }];
    setupState.formData.caseFiles = [
      { file: createFile("file.pdf", "application/pdf") },
    ];

    await setupState.onSubmit();

    expect(mockSwalFire).toHaveBeenCalled();
    expect(mockSubmitHandler).not.toHaveBeenCalled();
  });

  test("archives a process when confirmed", async () => {
    const client = { id: 3, first_name: "Ana", last_name: "Lopez", role: "client" };
    const process = buildProcess({ id: 77, clients: [client] });

    const { wrapper } = await mountView({
      routeParams: { action: "edit", process_id: "77" },
      processes: [process],
      authUser: { id: 55 },
    });
    const setupState = getSetupState(wrapper);

    setupState.selectedCaseType = { id: 10, type: "Civil" };
    setupState.selectedClients = [client];
    setupState.formData.caseFiles = [
      { file: createFile("file.pdf", "application/pdf") },
    ];

    mockSwalFire.mockResolvedValueOnce({ isConfirmed: true });
    mockSubmitHandler.mockResolvedValue();

    await setupState.archiveProcess();

    expect(setupState.formData.isArchiving).toBe(true);
    expect(setupState.formData.stages.slice(-1)[0].status).toBe("Fallo");
    expect(mockSubmitHandler).toHaveBeenCalledWith(
      expect.objectContaining({ processIdParam: "77" }),
      expect.stringContaining("archivado exitosamente"),
      true
    );
    expect(mockRouterBack).toHaveBeenCalled();
  });

  test("manages client selection and removal", async () => {
    const { wrapper } = await mountView();
    const client = { id: 5, first_name: "Ana", last_name: "Lopez" };
    const setupState = getSetupState(wrapper);

    setupState.onClientSelected(client);
    setupState.onClientSelected(client);

    expect([
      setupState.selectedClients.length,
      setupState.isClientSelected(client),
    ]).toEqual([1, true]);

    setupState.removeClient(5);
    expect([
      setupState.selectedClients.length,
      setupState.formData.clientIds,
    ]).toEqual([0, []]);
  });

  test("manages stages and case files", async () => {
    const { wrapper } = await mountView();
    const setupState = getSetupState(wrapper);
    const formData = getFormData(wrapper);

    const initialStages = formData.stages.length;
    setupState.addStage();
    const stagesAfterAdd = formData.stages.length;
    setupState.deleteStage(0);
    const stagesAfterDelete = formData.stages.length;

    const initialFiles = formData.caseFiles.length;
    setupState.addCaseFile();
    const filesAfterAdd = formData.caseFiles.length;
    setupState.removeCaseFile(0);
    const filesAfterRemove = formData.caseFiles.length;

    expect([stagesAfterAdd, stagesAfterDelete, filesAfterAdd, filesAfterRemove]).toEqual([
      initialStages + 1,
      initialStages,
      initialFiles + 1,
      initialFiles,
    ]);
  });

  test("handles file uploads and openFile", async () => {
    const { wrapper } = await mountView();
    const setupState = getSetupState(wrapper);

    const largeFile = createFile("large.pdf", "application/pdf", 51 * 1024 * 1024);
    setupState.handleFileUpload({ target: { files: [largeFile] } }, 0);

    const invalidFile = createFile("virus.exe", "application/octet-stream", 1000);
    setupState.handleFileUpload({ target: { files: [invalidFile] } }, 0);

    const validFile = createFile("file.pdf", "application/pdf", 1000);
    setupState.handleFileUpload({ target: { files: [validFile] } }, 0);

    expect(mockShowNotification).toHaveBeenCalled();
    expect(setupState.formData.caseFiles[0].file).toBe(validFile);

    const openSpy = jest.spyOn(window, "open").mockImplementation(() => {});
    setupState.openFile("http://files.test/file.pdf");
    expect(openSpy).toHaveBeenCalledWith("http://files.test/file.pdf", "_blank");
    openSpy.mockRestore();
  });

  test("create mode defaults the responsible lawyer to the logged-in user", async () => {
    const lawyer = { id: 42, first_name: "Luis", last_name: "Abo", role: "lawyer" };
    const { wrapper } = await mountView({
      routeParams: { action: "add", process_id: "" },
      users: [lawyer],
      currentUser: lawyer,
      authUser: { id: 42 },
    });
    const setupState = getSetupState(wrapper);

    expect(setupState.selectedLawyer?.id).toBe(42);
    expect(setupState.formData.lawyerId).toBe(42);
  });

  test("selector value (not the logged-in user) is what gets submitted", async () => {
    const me = { id: 42, first_name: "Luis", last_name: "Abo", role: "lawyer" };
    const colleague = { id: 77, first_name: "Marta", last_name: "Colega", role: "lawyer" };
    const client = { id: 7, first_name: "Ana", last_name: "Lopez", role: "client" };
    const { wrapper } = await mountView({
      routeParams: { action: "add", process_id: "" },
      caseTypes: [{ id: 10, type: "Civil" }],
      users: [me, colleague, client],
      currentUser: me,
      authUser: { id: 42 },
    });
    const setupState = getSetupState(wrapper);

    // Admin/lawyer reassigns the process to a colleague at creation time
    setupState.selectedLawyer = colleague;
    setupState.selectedCaseType = { id: 10, type: "Civil" };
    setupState.selectedClients = [client];
    setupState.formData.plaintiff = "P";
    setupState.formData.defendant = "D";
    setupState.formData.subcase = "S";
    setupState.formData.ref = "R";
    setupState.formData.authority = "Court";
    setupState.formData.stages = [{ status: "Inicio", date: "2024-01-01" }];
    setupState.formData.caseFiles = [{ file: createFile("f.pdf", "application/pdf") }];

    mockSubmitHandler.mockResolvedValue();
    await setupState.onSubmit();

    expect(mockSubmitHandler).toHaveBeenCalledWith(
      expect.objectContaining({ lawyerId: 77 }),
      expect.any(String),
      false
    );
  });

  test("edit mode prefills the stage alert configuration", async () => {
    const { wrapper } = await mountEditView({
      stages: [
        { status: "Admisión", date: "2099-12-31", alert: { is_active: true, description: "Vence pronto", notify_clients: true } },
      ],
    });
    const setupState = getSetupState(wrapper);

    expect([
      setupState.formData.alertIsActive,
      setupState.formData.alertDescription,
      setupState.formData.alertNotifyClients,
    ]).toEqual([true, "Vence pronto", true]);
  });

  test("blocks submit when a stage status is empty", async () => {
    const { wrapper } = await mountEditView();
    const setupState = getSetupState(wrapper);
    setupState.formData.stages = [{ status: "   ", date: "2099-12-31" }];

    await setupState.onSubmit();

    expect(mockSwalFire).toHaveBeenCalledWith(
      expect.objectContaining({ title: "Estado requerido!" })
    );
    expect(mockSubmitHandler).not.toHaveBeenCalled();
  });

  test("blocks submit when a case file row has no file", async () => {
    const { wrapper } = await mountEditView();
    const setupState = getSetupState(wrapper);
    setupState.formData.caseFiles = [{ file: null }];

    await setupState.onSubmit();

    expect(mockSwalFire).toHaveBeenCalledWith(
      expect.objectContaining({ title: "¡Archivo requerido!" })
    );
    expect(mockSubmitHandler).not.toHaveBeenCalled();
  });

  test("submitting an edit updates the process and navigates back", async () => {
    const { wrapper, process } = await mountEditView();
    const setupState = getSetupState(wrapper);
    mockSubmitHandler.mockResolvedValue();

    await setupState.onSubmit();

    expect(mockSubmitHandler).toHaveBeenCalledWith(
      expect.objectContaining({ processIdParam: String(process.id) }),
      expect.stringContaining("guardado exitosamente"),
      true
    );
    expect(mockRouterBack).toHaveBeenCalled();
    expect(mockRouterPush).not.toHaveBeenCalled();
  });

  test("case type search filters options by query", async () => {
    const { wrapper } = await mountView({
      caseTypes: [{ id: 10, type: "Civil" }, { id: 11, type: "Penal" }],
    });
    const setupState = getSetupState(wrapper);

    expect(setupState.filteredCaseTypes.map((c) => c.id)).toEqual([10, 11]);

    setupState.query = "civ";
    await nextTick();

    expect(setupState.filteredCaseTypes.map((c) => c.id)).toEqual([10]);
  });

  test("client search filters options by query", async () => {
    const ana = { id: 7, first_name: "Ana", last_name: "Lopez", identification: "111", email: "ana@test.com", role: "client" };
    const juan = { id: 8, first_name: "Juan", last_name: "Perez", identification: "222", email: "juan@test.com", role: "client" };
    const { wrapper } = await mountView({ users: [ana, juan] });
    const setupState = getSetupState(wrapper);

    expect(setupState.filteredClients.map((c) => c.id)).toEqual([7, 8]);

    setupState.query = "ana";
    await nextTick();

    expect(setupState.filteredClients.map((c) => c.id)).toEqual([7]);
  });

  test("rejects case files larger than the 200 MB limit", async () => {
    const { wrapper } = await mountView();
    const setupState = getSetupState(wrapper);
    setupState.formData.caseFiles = [{ file: null }];
    const bigFile = createFile("huge.pdf", "application/pdf", 201 * 1024 * 1024);

    setupState.handleFileUpload({ target: { files: [bigFile] } }, 0);

    expect(mockShowNotification).toHaveBeenCalledWith(
      expect.stringContaining("excede el límite de 200 MB"),
      "warning"
    );
    expect(setupState.formData.caseFiles[0].file).toBeNull();
  });

  test("getInitials falls back to ? when both names are empty", async () => {
    const { wrapper } = await mountView();
    const setupState = getSetupState(wrapper);

    expect([
      setupState.getInitials("Ana", "Lopez"),
      setupState.getInitials("", ""),
    ]).toEqual(["AL", "?"]);
  });

  test("cancelAction navigates back without submitting", async () => {
    const { wrapper } = await mountView();
    const setupState = getSetupState(wrapper);

    setupState.cancelAction();

    expect(mockRouterBack).toHaveBeenCalled();
    expect(mockSubmitHandler).not.toHaveBeenCalled();
  });

  test("lawyer search filters the selector options by query", async () => {
    const me = { id: 42, first_name: "Luis", last_name: "Abo", role: "lawyer" };
    const colleague = { id: 77, first_name: "Marta", last_name: "Colega", role: "lawyer" };
    const { wrapper } = await mountView({
      users: [me, colleague],
      currentUser: me,
      authUser: { id: 42 },
    });
    const setupState = getSetupState(wrapper);

    setupState.lawyerQuery = "mar";
    await nextTick();

    expect(setupState.filteredLawyers.map((l) => l.id)).toEqual([77]);
  });

  test("edit mode keeps an archived assigned lawyer selectable at the top", async () => {
    const archived = { id: 99, first_name: "Ori", last_name: "Ginal", role: "lawyer", is_archived: true };
    const active = { id: 77, first_name: "Marta", last_name: "Colega", role: "lawyer" };
    const process = buildProcess({ lawyer: archived });

    const { wrapper } = await mountView({
      routeParams: { action: "edit", process_id: String(process.id) },
      processes: [process],
      users: [archived, active],
    });
    const setupState = getSetupState(wrapper);

    expect(setupState.filteredLawyers.map((l) => l.id)).toEqual([99, 77]);
  });

  test("logs and continues when auxiliary data fails to load", async () => {
    const consoleSpy = jest.spyOn(console, "error").mockImplementation(() => {});
    const pinia = createPinia();
    setActivePinia(pinia);

    const processStore = useProcessStore();
    const caseTypeStore = useCaseTypeStore();
    const userStore = useUserStore();
    const authStore = useAuthStore();
    authStore.$patch({ userAuth: { id: 99 } });

    jest.spyOn(processStore, "init").mockResolvedValue();
    jest.spyOn(caseTypeStore, "init").mockResolvedValue();
    jest.spyOn(userStore, "init").mockRejectedValue(new Error("network down"));

    mockRoute.params = { action: "add", process_id: "" };
    const wrapper = shallowMount(ProcessForm, {
      global: { plugins: [pinia] },
    });
    await flushPromises();

    expect(wrapper.exists()).toBe(true);
    expect(consoleSpy).toHaveBeenCalledWith(
      "Error initializing process form auxiliary data:",
      expect.any(Error)
    );
    consoleSpy.mockRestore();
  });

  test("edit mode prefills the selector from the assigned lawyer", async () => {
    const { wrapper } = await mountEditView({ lawyer: { id: 99, first_name: "Ori", last_name: "Ginal", role: "lawyer" } });
    const setupState = getSetupState(wrapper);

    expect(setupState.selectedLawyer?.id).toBe(99);
    expect(setupState.formData.lawyerId).toBe(99);
  });
});
