import { useAuthStore } from "@/stores/auth/auth";
import { createRouter, createWebHistory } from "vue-router";
import SlideBar from "@/components/layouts/SlideBar.vue";

// Import useRecentViews lazily to avoid premature initialization
let recentViewsModule = null;
const getRecentViews = async () => {
  if (!recentViewsModule) {
    recentViewsModule = await import("@/composables/useRecentViews");
  }
  return recentViewsModule.useRecentViews();
};

// Create the router without circular dependencies
const router = createRouter({
  history: createWebHistory(),
  routes: [
    // Root path — guard redirects to dashboard (auth) or sign_in (no auth)
    {
      path: "/",
      name: "root",
      component: { render: () => null },
      meta: { requiresAuth: false },
    },
    {
      path: "/sign_in",
      name: "sign_in",
      component: () => import(/* webpackChunkName: "auth" */ "@/views/auth/SignIn.vue"),
      meta: { requiresAuth: false, title: "Iniciar Sesión" },
    },
    // Special route for Google OAuth callback
    {
      path: "/auth/google/callback",
      name: "google_oauth_callback",
      component: () => import(/* webpackChunkName: "auth" */ "@/views/auth/SignIn.vue"),
      meta: { requiresAuth: false, title: "Autenticación con Google", isCallback: true },
    },
    // No route for /auth/outlook/callback on purpose: the MSAL popup redirect
    // URI is served as a minimal static page by the backend, so the SPA never
    // boots inside the popup and MSAL can read the response and close it.
    {
      path: "/home",
      name: "home",
      component: () => import(/* webpackChunkName: "policies" */ "@/views/policies/Home.vue"),
      meta: { requiresAuth: false, title: "Políticas de Privacidad" },
    },
    {
      path: "/sign_on",
      name: "sign_on",
      component: () => import(/* webpackChunkName: "auth" */ "@/views/auth/SignOn.vue"),
      meta: { requiresAuth: false, title: "Registrarse" },
    },
    {
      path: "/forget_password",
      name: "forget_password",
      component: () => import(/* webpackChunkName: "auth" */ "@/views/auth/ForgetPassword.vue"),
      meta: { requiresAuth: false, title: "Recuperar Contraseña" },
    },
    {
      path: "/policies/privacy_policy",
      name: "privacy_policy",
      component: () => import(/* webpackChunkName: "policies" */ "@/views/policies/PrivacyPolicy.vue"),
      meta: { requiresAuth: false, title: "Política de Privacidad" },
    },
    {
      path: "/policies/terms_of_use",
      name: "terms_of_use",
      component: () => import(/* webpackChunkName: "policies" */ "@/views/policies/TermsOfUse.vue"),
      meta: { requiresAuth: false, title: "Términos de Uso" },
    },
    {
      path: "/no_connection",
      name: "no_connection",
      component: () => import(/* webpackChunkName: "offline" */ "@/views/offline/NoConnection.vue"),
      meta: { requiresAuth: false, title: "Sin Conexión" },
    },
    {
      path: "/subscriptions",
      name: "subscriptions",
      component: () => import(/* webpackChunkName: "subscriptions" */ "@/views/subscriptions/Subscriptions.vue"),
      meta: { requiresAuth: false, title: "Planes de Suscripción" },
    },
    {
      path: "/checkout/:plan",
      name: "checkout",
      component: () => import(/* webpackChunkName: "subscriptions" */ "@/views/subscriptions/Checkout.vue"),
      meta: { requiresAuth: true, title: "Finalizar Suscripción" },
    },
    {
      path: "/subscription/sign_in",
      name: "subscription_sign_in",
      component: () => import(/* webpackChunkName: "auth" */ "@/views/auth/SubscriptionSignIn.vue"),
      meta: { requiresAuth: false, title: "Iniciar Sesión - Suscripción" },
    },
    {
      path: "/subscription/sign_up",
      name: "subscription_sign_up",
      component: () => import(/* webpackChunkName: "auth" */ "@/views/auth/SubscriptionSignUp.vue"),
      meta: { requiresAuth: false, title: "Registrarse - Suscripción" },
    },
    {
      path: "/dashboard",
      component: SlideBar,
      children: [
        {
          path: "",
          name: "dashboard",
          component: () => import(/* webpackChunkName: "dashboard" */ "@/views/dashboard/dashboard.vue"),
          meta: { 
            requiresAuth: true, 
            title: "Panel Principal",
            prefetch: true
          },
        },
      ],
    },
    {
      path: "/notifications",
      component: SlideBar,
      children: [
        {
          path: "",
          name: "notifications",
          component: () => import(/* webpackChunkName: "notifications" */ "@/views/notifications/NotificationsList.vue"),
          meta: { requiresAuth: true, title: "Notificaciones" },
        },
      ],
    },
    {
      path: "/process_list/:user_id?/:display?",
      component: SlideBar,
      children: [
        {
          path: "",
          name: "process_list",
          component: () => import(/* webpackChunkName: "process-list" */ "@/views/process/ProcessList.vue"),
          meta: { requiresAuth: true, title: "Lista de Procesos" },
        },
      ],
    },
    {
      path: "/process_detail/:process_id/:display?",
      component: SlideBar,
      children: [
        {
          path: "",
          name: "process_detail",
          component: () => import(/* webpackChunkName: "process-detail" */ "@/views/process/ProcessDetail.vue"),
          meta: { requiresAuth: true, title: "Detalle de Proceso" },
        },
      ],
    },
    {
      path: "/process_form/:action/:process_id?",
      component: SlideBar,
      children: [
        {
          path: "",
          name: "process_form",
          component: () => import(/* webpackChunkName: "process-form" */ "@/views/process/ProcessForm.vue"),
          meta: { 
            requiresAuth: true, 
            title: "Formulario de Proceso",
            requiresLawyer: true
          },
        },
      ],
    },
    {
      path: "/directory_list",
      component: SlideBar,
      children: [
        {
          path: "",
          name: "directory_list",
          component: () => import(/* webpackChunkName: "directory" */ "@/views/directory/DirectoryList.vue"),
          meta: { 
            requiresAuth: true, 
            title: "Directorio",
            requiresLawyer: true
          },
        },
      ],
    },
    {
      path: "/legal_request",
      component: SlideBar,
      children: [
        {
          path: "",
          name: "legal_request",
          component: () => import(/* webpackChunkName: "legal-request" */ "@/views/legal_request/LegalRequest.vue"),
          meta: { requiresAuth: true, title: "Solicitud Legal" },
        },
      ],
    },
    {
      path: "/legal_requests",
      component: SlideBar,
      children: [
        {
          path: "",
          name: "legal_requests_list",
          component: () => import(/* webpackChunkName: "legal-requests-list" */ "@/views/legal_request/LegalRequestsList.vue"),
          meta: { requiresAuth: true, title: "Lista de Solicitudes" },
        },
      ],
    },
    {
      path: "/legal_request_create",
      component: SlideBar,
      children: [
        {
          path: "",
          name: "legal_request_create",
          component: () => import(/* webpackChunkName: "legal-request-create" */ "@/views/legal_request/LegalRequest.vue"),
          meta: { requiresAuth: true, title: "Nueva Solicitud" },
        },
      ],
    },
    {
      path: "/legal_request_detail/:id",
      component: SlideBar,
      children: [
        {
          path: "",
          name: "legal_request_detail",
          component: () => import(/* webpackChunkName: "legal-request-detail" */ "@/views/legal_request/LegalRequestDetail.vue"),
          meta: { requiresAuth: true, title: "Detalle de Solicitud" },
        },
      ],
    },
    {
      path: "/services",
      component: SlideBar,
      children: [
        {
          path: "",
          name: "services_hub",
          component: () => import(/* webpackChunkName: "services-hub" */ "@/views/services/ServicesHub.vue"),
          meta: { requiresAuth: true, title: "Servicios" },
        },
      ],
    },
    {
      path: "/services/:id",
      component: SlideBar,
      children: [
        {
          path: "",
          name: "service_detail",
          component: () => import(/* webpackChunkName: "service-detail" */ "@/views/services/ServiceDetail.vue"),
          meta: { requiresAuth: true, title: "Detalle de Servicio" },
        },
      ],
    },
    // Redirect legacy routes to unified hub
    {
      path: "/service_requests/my",
      redirect: { name: "services_hub", query: { tab: "my-requests" } },
    },
    // Keep these route names for backwards compatibility
    {
      path: "/services_list",
      redirect: { name: "services_hub" },
    },
    {
      path: "/my_requests",
      redirect: { name: "services_hub", query: { tab: "my-requests" } },
    },
    {
      path: "/service_requests/inbox",
      component: SlideBar,
      children: [
        {
          path: "",
          name: "service_requests_inbox",
          component: () => import(/* webpackChunkName: "service-requests-inbox" */ "@/views/services/ServiceRequestsInbox.vue"),
          meta: { requiresAuth: true, title: "Bandeja de Solicitudes", requiresLawyer: true },
        },
      ],
    },
    {
      path: "/service_requests/:id",
      component: SlideBar,
      children: [
        {
          path: "",
          name: "service_request_detail",
          component: () => import(/* webpackChunkName: "service-request-detail" */ "@/views/services/ServiceRequestDetail.vue"),
          meta: { requiresAuth: true, title: "Detalle de Solicitud" },
        },
      ],
    },
    {
      path: "/services_admin",
      component: SlideBar,
      children: [
        {
          path: "",
          name: "services_admin",
          component: () => import(/* webpackChunkName: "services-admin" */ "@/views/services/ServicesAdmin.vue"),
          meta: { requiresAuth: true, title: "Administrar Servicios", requiresAdmin: true },
        },
      ],
    },
    {
      path: "/data_reassignment",
      component: SlideBar,
      children: [
        {
          path: "",
          name: "data_reassignment",
          component: () => import(/* webpackChunkName: "data-reassignment" */ "@/views/admin/DataReassignment.vue"),
          meta: { requiresAuth: true, title: "Reasignación de Datos", requiresAdmin: true },
        },
      ],
    },
    {
      path: "/intranet_g_y_m",
      component: SlideBar,
      children: [
        {
          path: "",
          name: "intranet_g_y_m",
          component: () => import(/* webpackChunkName: "intranet" */ "@/views/intranet_g_y_m/IntranetGyM.vue"),
          meta: { 
            requiresAuth: true, 
            title: "Intranet G y M",
            requiresLawyer: true
          },
        },
      ],
    },
    {
      path: "/organizations_dashboard",
      component: SlideBar,
      children: [
        {
          path: "",
          name: "organizations_dashboard",
          component: () => import(/* webpackChunkName: "organizations" */ "@/views/organizations/Dashboard.vue"),
          meta: { requiresAuth: true, title: "Organizaciones" },
        },
      ],
    },
    {
      path: "/dynamic_document_dashboard",
      component: SlideBar,
      children: [
        {
          path: "",
          name: "dynamic_document_dashboard",
          component: () => import(/* webpackChunkName: "dynamic-document" */ "@/views/dynamic_document/Dashboard.vue"),
          meta: { requiresAuth: true, title: "Documentos Dinámicos" },
        },
        {
          path: "signed-documents",
          name: "signed-documents",
          component: () => import(/* webpackChunkName: "dynamic-document" */ "@/components/dynamic_document/common/SignaturesList.vue"),
          props: {
            state: 'FullySigned'
          },
          meta: { requiresAuth: true, title: "Documentos Firmados" },
        },
        {
          path: "lawyer/editor/create/:title",
          component: () => import(/* webpackChunkName: "dynamic-document-editor" */ "@/views/dynamic_document/DocumentEditor.vue"),
          props: true,
          meta: { 
            requiresAuth: true, 
            title: "Crear Documento",
            requiresLawyer: true
          },
        },
        {
          path: "lawyer/editor/edit/:id",
          component: () => import(/* webpackChunkName: "dynamic-document-editor" */ "@/views/dynamic_document/DocumentEditor.vue"),
          props: true,
          meta: { 
            requiresAuth: true, 
            title: "Editar Documento", 
            requiresLawyer: true 
          },
        },
        {
          path: "client/editor/edit/:id",
          component: () => import(/* webpackChunkName: "dynamic-document-editor" */ "@/views/dynamic_document/DocumentEditor.vue"),
          props: true,
          meta: { 
            requiresAuth: true, 
            title: "Editar Documento"
          },
        },
        {
          path: "document/use/:mode/:id/:title",
          component: () => import(/* webpackChunkName: "dynamic-document-form" */ "@/views/dynamic_document/DocumentForm.vue"),
          // DocumentForm usa useRoute() para leer mode, id y title, por lo que no es necesario pasar props
          meta: { requiresAuth: true, title: "Completar Documento" },
        },
        {
          path: "lawyer/variables-config",
          component: () => import(/* webpackChunkName: "dynamic-document-config" */ "@/views/dynamic_document/DocumentVariablesConfig.vue"),
          meta: { 
            requiresAuth: true, 
            title: "Configurar Variables",
            requiresLawyer: true
          },
        },
      ],
    },
    {
      path: "/secop",
      component: SlideBar,
      children: [
        {
          path: "",
          name: "secop_list",
          component: () => import(/* webpackChunkName: "secop" */ "@/views/secop/SecopList.vue"),
          meta: { 
            requiresAuth: true, 
            title: "Contratación Estatal"
          },
        },
        {
          path: ":id",
          name: "secop_detail",
          component: () => import(/* webpackChunkName: "secop-detail" */ "@/views/secop/SecopDetail.vue"),
          meta: { 
            requiresAuth: true, 
            title: "Detalle SECOP"
          },
        },
      ],
    },
    {
      path: "/user_guide",
      component: SlideBar,
      children: [
        {
          path: "",
          name: "user_guide",
          component: () => import(/* webpackChunkName: "user-guide" */ "@/views/user_guide/UserGuideMain.vue"),
          meta: { 
            requiresAuth: true, 
            title: "Manual de Usuario"
          },
        },
      ],
    },
    // Catch-all route to handle not found routes
    { 
      path: '/:pathMatch(.*)*', 
      redirect: to => {
        // This redirect will be handled in the global guard
        return { name: 'sign_in' };
      }
    }
  ],
  scrollBehavior() {
    return { top: 0 };
  },
});

// Set a flag to control if guards are already installed
let guardsInstalled = false;

// Function to install router guards when auth store is ready
export function installRouterGuards(authStore) {
  if (guardsInstalled) return;
  guardsInstalled = true;

  router.beforeEach(async (to, from, next) => {
    try {
      // Check authentication
      const isAuthenticated = await authStore.isAuthenticated();
      
      // Check if it's the root path '/' or a not found route
      if (to.name === null || to.name === 'root' || to.path === '/') {
        if (isAuthenticated) {
          return next({ name: 'dashboard' });
        } else {
          return next({ name: 'sign_in' });
        }
      }
      
      // Check if route requires authentication
      if (to.meta.requiresAuth && !isAuthenticated) {
        console.warn("User is not authenticated. Redirecting to sign_in.");
        return next({ name: "sign_in" });
      }
      
      // If user is authenticated, check role restrictions
      if (isAuthenticated && to.meta.requiresLawyer) {
        // Load user data if not loaded
        const userStore = await import('@/stores/auth/user').then(m => m.useUserStore());
        await userStore.init();
        
        if (!userStore.isLawyerLike) {
          console.warn("Non-lawyer user attempting to access lawyer-only route. Redirecting to dashboard.");
          return next({ name: 'dashboard' });
        }
      }

      if (isAuthenticated && to.meta.requiresAdmin) {
        const userStore = await import('@/stores/auth/user').then(m => m.useUserStore());
        await userStore.init();

        const currentUser = userStore.currentUser || {};
        const isAdmin = currentUser?.role === 'admin' || currentUser?.is_staff || currentUser?.is_superuser;
        if (!isAdmin) {
          console.warn("Non-admin user attempting to access admin-only route. Redirecting to dashboard.");
          return next({ name: 'dashboard' });
        }
      }
      
      // Proceed to the requested route
      return next();
    } catch (error) {
      console.error("Error in router guard:", error);
      return next({ name: 'sign_in' });
    }
  });

  // Register views after each successful navigation
  router.afterEach(async (to) => {
    try {
      // Update page title
      if (to.meta.title) {
        document.title = `${to.meta.title} | G&M Abogados`;
      } else {
        document.title = 'G&M Abogados';
      }

      // Only try to register views if there's an ID to register
      if (to.name === 'process_detail' || 
          to.path.includes('/dynamic_document_dashboard/') ||
          (to.query && to.query.documentId)) {
        
        // Get recent views module lazily
        try {
          const { registerView } = await getRecentViews();
          
          // Register process view
          if (to.name === 'process_detail' && to.params.process_id) {
            registerView('process', to.params.process_id);
          }

          // Register document view for lawyer editor
          if (to.path.includes('/dynamic_document_dashboard/lawyer/editor/edit/') && to.params.id) {
            registerView('document', to.params.id);
          }

          // Register document view for client
          if (to.path.includes('/dynamic_document_dashboard/document/use/') && to.params.id) {
            registerView('document', to.params.id);
          }

          // Register document view for variables configuration
          if (to.path.includes('/dynamic_document_dashboard/lawyer/variables-config') && to.query.documentId) {
            registerView('document', to.query.documentId);
          }
        } catch (e) {
          console.error("Error registering view:", e);
          // We don't block navigation because of an error registering views
        }
      }
    } catch (error) {
      console.error("Error in afterEach guard:", error);
      // We don't do anything, allow navigation to continue
    }
  });
}

export default router;
export const routes = router.options.routes;
