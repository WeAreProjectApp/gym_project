import { defineStore } from 'pinia';
import { guideGetters } from './getters.js';
import { dashboardContent, directoryContent } from './content/dashboard_directory.js';
import { processesContent } from './content/processes.js';
import { documentsContent } from './content/documents.js';
import { secopContent } from './content/secop.js';
import { servicesTramitesContent } from './content/services_tramites.js';
import { adminStaffContent } from './content/admin_staff.js';
import {
  requestsContent,
  organizationsContent,
  intranetContent,
  authenticationContent,
  subscriptionsContent,
} from './content/services.js';

/**
 * User Guide Store
 *
 * Modular store for the interactive user guide, split by content domain:
 * - Dashboard & Directory
 * - Processes
 * - Documents (largest section)
 * - Services (requests, organizations, intranet, auth, subscriptions)
 */
export const useUserGuideStore = defineStore('userGuide', {
  state: () => ({
    guideContent: {},
    initialized: false
  }),

  getters: {
    ...guideGetters,
  },

  actions: {
    /**
     * Initialize guide content from sub-modules
     */
    initializeGuideContent() {
      if (this.initialized) return;

      this.guideContent = {
        dashboard: dashboardContent,
        directory: directoryContent,
        processes: processesContent,
        documents: documentsContent,
        secop: secopContent,
        services: servicesTramitesContent,
        requests: requestsContent,
        organizations: organizationsContent,
        intranet: intranetContent,
        authentication: authenticationContent,
        subscriptions: subscriptionsContent,
        admin_staff: adminStaffContent,
      };

      this.initialized = true;
    }
  }
});
