/**
 * Flow tag constants for consistent E2E test tagging.
 *
 * Usage:
 *   import { FlowTags } from '../helpers/flow-tags.js';
 *   test('...', { tag: [...FlowTags.AUTH_LOGIN_EMAIL, '@role:client'] }, async ({ page }) => { ... });
 */

// ── Auth ────────────────────────────────────────────────────────────────────
export const AUTH_LOGIN_EMAIL = ['@flow:auth-login-email', '@module:auth', '@priority:P1'];
export const AUTH_LOGIN_GOOGLE = ['@flow:auth-login-google', '@module:auth', '@priority:P1'];
export const AUTH_REGISTER = ['@flow:auth-register', '@module:auth', '@priority:P1'];
export const AUTH_FORGOT_PASSWORD = ['@flow:auth-forgot-password', '@module:auth', '@priority:P2'];
export const AUTH_SUBSCRIPTION_SIGNUP = ['@flow:auth-subscription-signup', '@module:auth', '@priority:P1'];
export const AUTH_SUBSCRIPTION_SIGNIN = ['@flow:auth-subscription-signin', '@module:auth', '@priority:P1'];
export const AUTH_LOGOUT = ['@flow:auth-logout', '@module:auth', '@priority:P2'];
export const AUTH_EDGE_CASES = ['@flow:auth-edge-cases', '@module:auth', '@priority:P2'];
export const AUTH_IDLE_LOGOUT = ['@flow:auth-idle-logout', '@module:auth', '@priority:P2'];
export const AUTH_LOGIN_ATTEMPTS = ['@flow:auth-login-attempts', '@module:auth', '@priority:P2'];
export const AUTH_ROUTER_GUARDS = ['@flow:auth-router-guards', '@module:auth', '@priority:P2'];

// ── Profile ─────────────────────────────────────────────────────────────────
export const PROFILE_VIEW_EDIT = ['@flow:profile-view-edit', '@module:profile', '@priority:P2'];
export const PROFILE_COMPLETE = ['@flow:profile-complete', '@module:profile', '@priority:P2'];

// ── Notifications ───────────────────────────────────────────────────────────
export const NOTIFICATION_CENTER = ['@flow:notification-center', '@module:notifications', '@priority:P2'];

// ── Process Alerts ──────────────────────────────────────────────────────────
export const PROCESS_ALERT_CONFIGURE = ['@flow:process-alert-configure', '@module:processes', '@priority:P2'];

// ── Dashboard ───────────────────────────────────────────────────────────────
export const DASHBOARD_WELCOME_CARD = ['@flow:dashboard-welcome-card', '@module:dashboard', '@priority:P2'];
export const DASHBOARD_ACTIVITY_FEED = ['@flow:dashboard-activity-feed', '@module:dashboard', '@priority:P2'];
export const DASHBOARD_QUICK_ACTIONS = ['@flow:dashboard-quick-actions', '@module:dashboard', '@priority:P3'];
export const DASHBOARD_NAVIGATION = ['@flow:dashboard-navigation', '@module:dashboard', '@priority:P2'];
export const DASHBOARD_LEGAL_UPDATES = ['@flow:dashboard-legal-updates', '@module:dashboard', '@priority:P3'];
export const DASHBOARD_REPORTS = ['@flow:dashboard-reports', '@module:dashboard', '@priority:P2'];
export const DASHBOARD_REPORTS_ADVANCED_FILTERS = ['@flow:dashboard-reports-advanced-filters', '@module:dashboard', '@priority:P2'];
export const DASHBOARD_FOLDER_COMPONENTS = ['@flow:dashboard-folder-components', '@module:dashboard', '@priority:P3'];

// ── Subscriptions ───────────────────────────────────────────────────────────
export const SUBSCRIPTIONS_VIEW_PLANS = ['@flow:subscriptions-view-plans', '@module:subscriptions', '@priority:P2'];
export const SUBSCRIPTIONS_CHECKOUT_FREE = ['@flow:subscriptions-checkout-free', '@module:subscriptions', '@priority:P1'];
export const SUBSCRIPTIONS_CHECKOUT_PAID = ['@flow:subscriptions-checkout-paid', '@module:subscriptions', '@priority:P1'];
export const SUBSCRIPTIONS_MANAGEMENT = ['@flow:subscriptions-management', '@module:subscriptions', '@priority:P2'];
export const SUBSCRIPTIONS_CANCEL = ['@flow:subscriptions-cancel', '@module:subscriptions', '@priority:P2'];
export const SUBSCRIPTIONS_UPDATE_PAYMENT = ['@flow:subscriptions-update-payment', '@module:subscriptions', '@priority:P2'];

// ── Processes ───────────────────────────────────────────────────────────────
export const PROCESS_LIST_VIEW = ['@flow:process-list-view', '@module:processes', '@priority:P1'];
export const PROCESS_CREATE = ['@flow:process-create', '@module:processes', '@priority:P1'];
export const PROCESS_EDIT = ['@flow:process-edit', '@module:processes', '@priority:P2'];
export const PROCESS_DETAIL = ['@flow:process-detail', '@module:processes', '@priority:P1'];
export const PROCESS_HISTORY = ['@flow:process-history', '@module:processes', '@priority:P2'];
export const PROCESS_FORM_VALIDATION = ['@flow:process-form-validation', '@module:processes', '@priority:P2'];
export const PROCESS_SEARCH = ['@flow:process-search', '@module:processes', '@priority:P3'];
export const PROCESS_REQUEST_INFO = ['@flow:process-request-info', '@module:processes', '@priority:P2'];
export const PROCESS_CASE_FILE_UPLOAD = ['@flow:process-case-file-upload', '@module:processes', '@priority:P2'];

// ── Documents ───────────────────────────────────────────────────────────────
export const DOCS_CREATE_TEMPLATE = ['@flow:docs-create-template', '@module:documents', '@priority:P1'];
export const DOCS_EDITOR = ['@flow:docs-editor', '@module:documents', '@priority:P1'];
export const DOCS_VARIABLES_CONFIG = ['@flow:docs-variables-config', '@module:documents', '@priority:P1'];
export const DOCS_USE_TEMPLATE = ['@flow:docs-use-template', '@module:documents', '@priority:P1'];
export const DOCS_FORM_INTERACTIONS = ['@flow:docs-form-interactions', '@module:documents', '@priority:P2'];
export const DOCS_DASHBOARD_LAWYER = ['@flow:docs-dashboard-lawyer', '@module:documents', '@priority:P1'];
export const DOCS_DASHBOARD_CLIENT = ['@flow:docs-dashboard-client', '@module:documents', '@priority:P1'];
export const DOCS_PERMISSIONS = ['@flow:docs-permissions', '@module:documents', '@priority:P1'];
export const DOCS_CARD_ACTIONS = ['@flow:docs-card-actions', '@module:documents', '@priority:P2'];
export const DOCS_FILTERS = ['@flow:docs-filters', '@module:documents', '@priority:P2'];
export const DOCS_TAGS = ['@flow:docs-tags', '@module:documents', '@priority:P2'];
export const DOCS_FOLDERS = ['@flow:docs-folders', '@module:documents', '@priority:P2'];
export const DOCS_DOWNLOAD = ['@flow:docs-download', '@module:documents', '@priority:P2'];
export const DOCS_SEND_EMAIL = ['@flow:docs-send-email', '@module:documents', '@priority:P2'];
export const DOCS_DUPLICATE = ['@flow:docs-duplicate', '@module:documents', '@priority:P3'];
export const DOCS_DELETE = ['@flow:docs-delete', '@module:documents', '@priority:P3'];
export const DOCS_STATE_TRANSITIONS = ['@flow:docs-state-transitions', '@module:documents', '@priority:P2'];
export const DOCS_RELATIONSHIPS = ['@flow:docs-relationships', '@module:documents', '@priority:P3'];
export const DOCS_KEY_FIELDS = ['@flow:docs-key-fields', '@module:documents', '@priority:P3'];
export const DOCS_LETTERHEAD = ['@flow:docs-letterhead', '@module:documents', '@priority:P2'];
export const DOCS_PREVIEW = ['@flow:docs-preview', '@module:documents', '@priority:P3'];
export const DOCS_SUMMARY = ['@flow:docs-summary', '@module:documents', '@priority:P3'];
export const DOCS_LIST_TABLE = ['@flow:docs-list-table', '@module:documents', '@priority:P3'];
export const DOCS_EMPTY_STATES = ['@flow:docs-empty-states', '@module:documents', '@priority:P4'];
export const DOCS_MULTIPLE = ['@flow:docs-multiple', '@module:documents', '@priority:P4'];
export const DOCS_PROFILE_NAVIGATION = ['@flow:docs-profile-navigation', '@module:documents', '@priority:P4'];
export const DOCS_MINUTAS_COLUMNS = ['@flow:minutas-columns', '@module:documents', '@priority:P2'];
export const DOCS_GUIDED_TOUR = ['@flow:docs-guided-tour', '@module:documents', '@priority:P2'];
export const DOCS_CONTRACT_EXECUTION = ['@flow:docs-contract-execution', '@module:documents', '@priority:P1'];

// ── Admin ─────────────────────────────────────────────────────────────────────
export const ADMIN_DATA_REASSIGNMENT = ['@flow:admin-data-reassignment', '@module:admin', '@priority:P1'];

// ── Signatures ──────────────────────────────────────────────────────────────
export const SIGN_ELECTRONIC_SIGNATURE = ['@flow:sign-electronic-signature', '@module:signatures', '@priority:P1'];
export const SIGN_DOCUMENT_FLOW = ['@flow:sign-document-flow', '@module:signatures', '@priority:P1'];
export const SIGN_CLIENT_FLOW = ['@flow:sign-client-flow', '@module:signatures', '@priority:P1'];
export const SIGN_REJECT = ['@flow:sign-reject', '@module:signatures', '@priority:P1'];
export const SIGN_REOPEN = ['@flow:sign-reopen', '@module:signatures', '@priority:P1'];
export const SIGN_SIGNED_DOCUMENTS = ['@flow:sign-signed-documents', '@module:signatures', '@priority:P2'];
export const SIGN_PENDING_DOCUMENTS = ['@flow:sign-pending-documents', '@module:signatures', '@priority:P2'];
export const SIGN_ARCHIVED_DOCUMENTS = ['@flow:sign-archived-documents', '@module:signatures', '@priority:P3'];
export const SIGN_STATUS_MODAL = ['@flow:sign-status-modal', '@module:signatures', '@priority:P2'];
export const LEGAL_FILES_MENU_PULSE = ['@flow:legal-files-menu-pulse', '@module:signatures', '@priority:P1'];
export const LEGAL_FILES_AUTO_REDIRECT = ['@flow:legal-files-auto-redirect', '@module:signatures', '@priority:P2'];
export const LEGAL_FILES_TABLE_PULSE = ['@flow:legal-files-table-pulse', '@module:signatures', '@priority:P2'];

// ── Legal Requests ──────────────────────────────────────────────────────────
export const LEGAL_CREATE_REQUEST = ['@flow:legal-create-request', '@module:legal-requests', '@priority:P1'];
export const LEGAL_LIST_CLIENT = ['@flow:legal-list-client', '@module:legal-requests', '@priority:P1'];
export const LEGAL_DETAIL_CLIENT = ['@flow:legal-detail-client', '@module:legal-requests', '@priority:P1'];
export const LEGAL_ADD_FILES = ['@flow:legal-add-files', '@module:legal-requests', '@priority:P2'];
export const LEGAL_MANAGEMENT_LAWYER = ['@flow:legal-management-lawyer', '@module:legal-requests', '@priority:P1'];
export const LEGAL_RESPONSE_THREAD = ['@flow:legal-response-thread', '@module:legal-requests', '@priority:P1'];
export const LEGAL_STATUS_UPDATE = ['@flow:legal-status-update', '@module:legal-requests', '@priority:P2'];
export const LEGAL_LAWYER_MODALS = ['@flow:legal-lawyer-modals', '@module:legal-requests', '@priority:P3'];

// ── Organizations ───────────────────────────────────────────────────────────
export const ORG_CREATE = ['@flow:org-create', '@module:organizations', '@priority:P1'];
export const ORG_EDIT = ['@flow:org-edit', '@module:organizations', '@priority:P2'];
export const ORG_INVITE_MEMBERS = ['@flow:org-invite-members', '@module:organizations', '@priority:P1'];
export const ORG_MEMBERS_LIST = ['@flow:org-members-list', '@module:organizations', '@priority:P2'];
export const ORG_POSTS_MANAGEMENT = ['@flow:org-posts-management', '@module:organizations', '@priority:P2'];
export const ORG_POSTS_VISIBILITY = ['@flow:org-posts-visibility', '@module:organizations', '@priority:P2'];
export const ORG_CORPORATE_REQUESTS = ['@flow:org-corporate-requests', '@module:organizations', '@priority:P2'];
export const ORG_CLIENT_VIEW = ['@flow:org-client-view', '@module:organizations', '@priority:P2'];
export const ORG_CLIENT_INVITATIONS = ['@flow:org-client-invitations', '@module:organizations', '@priority:P1'];
export const ORG_CLIENT_REQUESTS = ['@flow:org-client-requests', '@module:organizations', '@priority:P2'];
export const ORG_CLIENT_LEAVE = ['@flow:org-client-leave', '@module:organizations', '@priority:P3'];
export const ORG_CROSS_INVITE_FLOW = ['@flow:org-cross-invite-flow', '@module:organizations', '@priority:P1'];
export const ORG_CROSS_REQUEST_FLOW = ['@flow:org-cross-request-flow', '@module:organizations', '@priority:P2'];
export const ORG_CROSS_MEMBER_MANAGEMENT = ['@flow:org-cross-member-management', '@module:organizations', '@priority:P2'];
export const ORG_REQUEST_DETAIL = ['@flow:org-request-detail', '@module:organizations', '@priority:P3'];

// ── Directory ───────────────────────────────────────────────────────────────
export const DIRECTORY_SEARCH = ['@flow:directory-search', '@module:directory', '@priority:P2'];


// ── Intranet ────────────────────────────────────────────────────────────────
export const INTRANET_MAIN = ['@flow:intranet-main', '@module:intranet', '@priority:P2'];
export const INTRANET_INTERACTIONS = ['@flow:intranet-interactions', '@module:intranet', '@priority:P3'];

// ── User Guide ──────────────────────────────────────────────────────────────
export const USER_GUIDE_NAVIGATION = ['@flow:user-guide-navigation', '@module:user-guide', '@priority:P3'];
export const USER_GUIDE_EXPLORER_NAVIGATION = ['@flow:user-guide-explorer-navigation', '@module:user-guide', '@priority:P2'];
export const USER_GUIDE_EXPLORER_SEARCH = ['@flow:user-guide-explorer-search', '@module:user-guide', '@priority:P2'];
export const USER_GUIDE_EXPLORER_ACCESS = ['@flow:user-guide-explorer-access', '@module:user-guide', '@priority:P2'];
export const USER_GUIDE_EXPLORER_TOUR = ['@flow:user-guide-explorer-tour', '@module:user-guide', '@priority:P3'];
export const USER_GUIDE_EXPLORER_RELATIONS = ['@flow:user-guide-explorer-relations', '@module:user-guide', '@priority:P3'];
export const USER_GUIDE_EXPLORER_RESPONSIVE = ['@flow:user-guide-explorer-responsive', '@module:user-guide', '@priority:P2'];
export const USER_GUIDE_EXPLORER_ORBIT = ['@flow:user-guide-explorer-orbit', '@module:user-guide', '@priority:P3'];

// ── Misc ────────────────────────────────────────────────────────────────────
export const MISC_POLICIES = ['@flow:misc-policies', '@module:misc', '@priority:P4'];
export const MISC_PWA_INSTALL = ['@flow:misc-pwa-install', '@module:misc', '@priority:P4'];
export const MISC_ERROR_HANDLING = ['@flow:misc-error-handling', '@module:misc', '@priority:P3'];
export const MISC_OFFLINE = ['@flow:misc-offline', '@module:misc', '@priority:P4'];

// ── Basic User ──────────────────────────────────────────────────────────────
export const BASIC_RESTRICTIONS = ['@flow:basic-restrictions', '@module:auth', '@priority:P3'];

// ── Documents (additional) ──────────────────────────────────────────────────
export const DOCS_FORM_FIELD_TYPES = ['@flow:docs-form-field-types', '@module:documents', '@priority:P2'];
export const DOCS_FOLDER_CRUD = ['@flow:docs-folder-crud', '@module:documents', '@priority:P2'];

// ── Organizations (additional) ──────────────────────────────────────────────
export const ORG_STORE_ACTIONS = ['@flow:org-store-actions', '@module:organizations', '@priority:P3'];

// ── Intranet (additional) ───────────────────────────────────────────────────
export const INTRANET_FACTURATION_FORM = ['@flow:intranet-facturation-form', '@module:intranet', '@priority:P2'];

// ── SECOP ───────────────────────────────────────────────────────────────────
export const SECOP_LIST_BROWSE = ['@flow:secop-list-browse', '@module:secop', '@priority:P2'];
export const SECOP_PROCESS_DETAIL = ['@flow:secop-process-detail', '@module:secop', '@priority:P2'];
export const SECOP_CLASSIFY_PROCESS = ['@flow:secop-classify-process', '@module:secop', '@priority:P2'];
export const SECOP_CREATE_ALERT = ['@flow:secop-create-alert', '@module:secop', '@priority:P2'];
export const SECOP_MANAGE_ALERTS = ['@flow:secop-manage-alerts', '@module:secop', '@priority:P3'];
export const SECOP_EXPORT_EXCEL = ['@flow:secop-export-excel', '@module:secop', '@priority:P3'];
export const SECOP_ADD_NOTES = ['@flow:secop-add-notes', '@module:secop', '@priority:P3'];
export const SECOP_SAVE_VIEW = ['@flow:secop-save-view', '@module:secop', '@priority:P3'];
export const SECOP_APPLY_SAVED_VIEW = ['@flow:secop-apply-saved-view', '@module:secop', '@priority:P3'];
export const SECOP_VIEW_IN_PORTAL = ['@flow:secop-view-in-portal', '@module:secop', '@priority:P3'];
export const SECOP_SYNC_STATUS = ['@flow:secop-sync-status', '@module:secop', '@priority:P3'];
export const SECOP_TRIGGER_SYNC = ['@flow:secop-trigger-sync', '@module:secop', '@priority:P4'];
export const SECOP_FILTER_CLASSIFICATIONS = ['@flow:secop-filter-classifications', '@module:secop', '@priority:P3'];
export const SECOP_SAVED_VIEW_FAVORITES = ['@flow:secop-saved-view-favorites', '@module:secop', '@priority:P3'];
export const SECOP_KEYWORD_TAGS = ['@flow:secop-keyword-tags', '@module:secop', '@priority:P3'];
export const SECOP_EDIT_SAVED_VIEW = ['@flow:secop-edit-saved-view', '@module:secop', '@priority:P3'];
