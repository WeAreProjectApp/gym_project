import { mockApi } from "./api.js";

export function buildMockUser({
  id,
  role,
  firstName = "E2E",
  lastName = role === "lawyer" ? "Lawyer" : "Client",
  email = "e2e@example.com",
  isProfileCompleted = true,
  isGymLawyer = role === "lawyer",
  hasSignature = false,
} = {}) {
  return {
    id,
    first_name: firstName,
    last_name: lastName,
    email,
    role,
    contact: "",
    birthday: "",
    identification: "",
    document_type: "",
    photo_profile: "",
    created_at: new Date().toISOString(),
    is_profile_completed: isProfileCompleted,
    is_gym_lawyer: isGymLawyer,
    has_signature: hasSignature,
  };
}

export function buildMockProcess({
  id,
  lawyerId,
  client,
  caseType,
  subcase,
  ref,
  authority,
  authorityEmail,
  plaintiff,
  defendant,
  stages,
  progress = 0,
  caseFiles = [],
} = {}) {
  return {
    id,
    clients: [client].filter(Boolean),
    lawyer: { id: lawyerId },
    case: { type: caseType },
    subcase,
    ref,
    authority,
    authority_email: authorityEmail,
    plaintiff,
    defendant,
    stages,
    progress,
    case_files: caseFiles,
  };
}

export async function installProcessFormApiMocks(
  page,
  {
    lawyer,
    client,
    currentUser = lawyer,
    caseTypes = [{ id: 1, type: "Civil" }],
    createdProcess,
  }
) {
  let processes = [];

  const nowIso = new Date().toISOString();
  const initialCreatedProcess =
    createdProcess ||
    buildMockProcess({
      id: 9002,
      lawyerId: lawyer.id,
      client,
      caseType: caseTypes[0]?.type || "Civil",
      subcase: "Subcaso",
      ref: "RAD-9002",
      authority: "Juzgado 1",
      authorityEmail: "juzgado1@example.com",
      plaintiff: "Demandante",
      defendant: "Demandado",
      stages: [{ status: "Inicio", date: nowIso.slice(0, 10) }],
      progress: 0,
      caseFiles: [],
    });

  await mockApi(page, async ({ route, apiPath }) => {
    if (apiPath === "validate_token/") {
      return { status: 200, contentType: "application/json", body: "{}" };
    }

    if (apiPath === "users/") {
      return {
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([...new Map([lawyer, client, currentUser].map(user => [user.id, user])).values()]),
      };
    }

    if (apiPath === `users/${currentUser.id}/`) {
      return {
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(currentUser),
      };
    }

    if (apiPath === `users/${currentUser.id}/signature/`) {
      return {
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ has_signature: false }),
      };
    }

    if (apiPath === "case_types/") {
      return {
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(caseTypes),
      };
    }

    if (apiPath === "processes/") {
      return {
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(processes),
      };
    }

    if (apiPath === "create_process/") {
      if (route.request().method() === "POST") {
        processes = [initialCreatedProcess];
        return {
          status: 201,
          contentType: "application/json",
          body: JSON.stringify({ id: initialCreatedProcess.id }),
        };
      }
    }

    if (apiPath === "update_case_file/") {
      if (route.request().method() === "POST") {
        return { status: 201, contentType: "application/json", body: "{}" };
      }
    }

    if (apiPath === "create-activity/") {
      return {
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({ id: 1, action_type: "create", description: "", created_at: nowIso }),
      };
    }

    if (apiPath === "user-activities/") {
      return { status: 200, contentType: "application/json", body: "[]" };
    }

    if (apiPath === "google-captcha/site-key/") {
      return { status: 200, contentType: "application/json", body: JSON.stringify({ site_key: "e2e-key" }) };
    }

    if (apiPath === "recent-processes/") {
      return { status: 200, contentType: "application/json", body: "[]" };
    }

    if (apiPath === "dynamic-documents/recent/") {
      return { status: 200, contentType: "application/json", body: "[]" };
    }

    if (apiPath === "legal-updates/active/") {
      return { status: 200, contentType: "application/json", body: "[]" };
    }

    return null;
  });
}
