# Complete Feature Manual - G&M Abogados

## Table of Contents

1. [Introduction](#introduction)
2. [System Roles](#system-roles)
3. [Modules by Role](#modules-by-role)
4. [Detailed Features](#detailed-features)
5. [Permissions Comparison Table](#permissions-comparison-table)
6. [Technical Implementation](#technical-implementation)

---

## Introduction

This document consolidates all information about features, roles, and permissions in the G&M Abogados platform. It includes a technical mapping, features by role, and an implementation guide.

**Date**: November 21, 2025  
**Version**: 1.0.0  
**Status**: Production

---

## System Roles

### 4 Main Roles

1. **Lawyer**
   - Full management of processes, clients, and documents
   - Access to all modules except Organizations
   - Can file processes and manage requests

2. **Client**
   - View their own processes
   - Request legal services
   - Use assigned documents
   - Schedule appointments

3. **Corporate Client**
   - All Client capabilities
   - Full Organizations management
   - Create corporate requests

4. **Basic**
   - Limited access to essential features
   - No electronic signature or letterhead
   - Read-only in most modules

### Special Flag

- **is_gym_lawyer**: Lawyers from the G&M firm with access to the Intranet

---

## Modules by Role

### LAWYER

#### Available Modules (8)
1. ✅ **Dashboard** - Main panel
2. ✅ **Directory** - Users list (EXCLUSIVE)
3. ✅ **Processes** - Full management
4. ✅ **Legal Files** - Create and manage documents
5. ✅ **Requests Management** - Manage requests (EXCLUSIVE)
6. ✅ **G&M Intranet** - Internal portal (is_gym_lawyer only)
7. ❌ **Schedule Appointment** - Not available
8. ❌ **Organizations** - Not available

### CLIENT

#### Available Modules (6)
1. ✅ **Dashboard** - Main panel
2. ✅ **Processes** - Read-only access to own processes
3. ✅ **Legal Files** - Use assigned documents
4. ✅ **Requests** - Create requests (EXCLUSIVE)
5. ✅ **Schedule Appointment** - Book appointments
6. ✅ **Organizations** - View organizations (read-only)

### CORPORATE CLIENT

#### Available Modules (6)
1. ✅ **Dashboard** - Main panel
2. ✅ **Processes** - Read-only access to own processes
3. ✅ **Legal Files** - Use assigned documents
4. ✅ **Requests** - Create requests
5. ✅ **Schedule Appointment** - Book appointments
6. ✅ **Organizations** - Full management (EXCLUSIVE)

### BASIC

#### Available Modules (5)
1. ✅ **Dashboard** - Simplified dashboard
2. ✅ **Processes** - Read-only (cannot request process info)
3. ✅ **Legal Files** - Use documents (no signature)
4. ✅ **Requests** - Create and view requests
5. ✅ **Schedule Appointment** - Book appointments

---

## Detailed Features

### 1. DASHBOARD (Home)

**Available for**: All roles

#### Components:
- **Welcome Card**
  - Personalized greeting
  - Active processes counter
  - Contextual quick action button

- **Activity Feed**
  - Chronological history of actions
  - Infinite scroll
  - Types: process creation/updates, document signing, minutes creation

- **Quick Action Buttons**
  - Lawyer: All Processes, File Process, New Minutes, File Report
  - Client: My Processes, Schedule Appointment, New Request

- **Legal Updates**
  - Legal sector news
  - Legislative changes

- **Recent Items**
  - Last 5 viewed processes
  - Last 5 edited documents

---

### 2. DIRECTORY

**Available for**: Lawyers only

#### Features:
- **Advanced Search**
  - By first name, last name, email, identification, role
  - Real-time search

- **Visible Information**
  - Profile picture
  - Full name
  - Role (color badge)
  - Contact email
  - Click to view the user's processes

---

### 3. PROCESSES

**Available for**: All roles (with different permissions)

#### Tabs:

**For Lawyers:**
1. **My Processes** - Assigned cases
2. **All Processes** - Full system view (EXCLUSIVE)
3. **Archived Processes** - Closed cases

**For Clients:**
1. **My Processes** - Own cases only
2. **Archived Processes** - Closed cases

#### Features:

**Filtering System:**
- Search by: reference, plaintiff, defendant, authority, client
- Filter by Case Type (Civil, Criminal, Labor, Family, etc.)
- Filter by Authority (Courts, Tribunals, High Courts)
- Filter by Procedural Stage (Admission, Evidence, Closing arguments, Judgment)
- "Clear" button to reset filters
- Sorting: Most recent / Name A-Z
- Results counter

**File Process (Lawyers only):**
- Full form with validation
- Searchable combobox for process type
- Select Client and responsible Lawyer
- Fields: Plaintiff, Defendant, Authority, Reference, Subclass
- Upload multiple files
- Set initial procedural stage

**Process Detail:**
- Full case information
- Visual stage timeline with interactive bubbles
- Digital case file:
  - Case files table
  - Document search
  - Individual download
  - Pagination (10 per page)

**Request Information (Clients):**
- Button in process detail
- Pre-filled form
- Sent directly to the responsible lawyer

---

### 4. LEGAL FILES

**Available for**: All roles (with different permissions)

#### Tabs for Lawyers (5):
1. **Minutes** - Created documents (Published, Draft, Progress, Completed)
2. **Documents to Sign** - Status PendingSignatures
3. **Signed Documents** - Status FullySigned
4. **Client Documents (Completed)** - Completed by clients
5. **Client Documents (In Progress)** - In the completion process

#### Tabs for Clients (5):
1. **Folders** - Organized documents
2. **My Documents** - Assigned documents
3. **Use Document** - Fill in templates
4. **Documents to Sign** - Pending signatures
5. **Signed Documents** - Final archive

#### 10 Document Actions (Lawyers):
1. 👁️ **View/Edit** - Open in TinyMCE editor
2. 📋 **Duplicate** - Create a copy of the document
3. 👤 **Assign to Client** - Send to a client
4. ⚙️ **Configure Variables** - Define dynamic fields
5. 🏷️ **Manage Tags** - Organize with tags
6. 🗑️ **Delete** - Delete with confirmation
7. 📄 **Download PDF** - Export final version
8. 📁 **Move to Folder** - Organize hierarchically
9. ✍️ **Sign** - Add electronic signature
10. 👀 **Preview** - View without editing

#### Special Features:

**Electronic Signature** (NOT for Basic):
- Draw signature with mouse/touch
- Upload signature image
- Save signature for future use
- Full traceability: date, time, IP, method
- Multiple signers per document

**Global Letterhead** (NOT for Basic):
- Upload logo/header image
- Configure header and footer text
- Real-time preview
- Apply to all new documents

**Folder System**:
- Create custom folders
- Move documents between folders
- Grid or table view
- Search within folders

**Tag System** (Lawyers only):
- Create tags with colors
- Filter by tags
- Multiple tags per document
- Examples: Contracts, Powers of attorney, Lawsuits, Tutelas

**Dynamic Variables**:
- 6 field types: text, textarea, number, date, email, select
- Explanatory tooltips
- Real-time validation
- Configuration per variable

---

### 5. LEGAL REQUESTS

**Available for**: All roles (different views)

#### For Clients (Create Request):
- Form with type and discipline
- Detailed description (minimum 50 characters)
- Attach multiple files (PDF, DOC, DOCX, JPG, PNG)
- Auto-generated number: SOL-YYYY-NNN
- Statuses: Pending, In Review, Responded, Closed

#### For Lawyers (Requests Management):
- View all requests in the system
- Filter by status and date range
- Change request status
- Full conversation thread
- Reply with messages
- Delete requests
- Download attached files

#### Conversation Thread:
- Messages ordered chronologically
- Sender indicator (Client/Lawyer)
- Date and time per message
- Add additional files
- Full history

---

### 6. SCHEDULE APPOINTMENT (removed 2026-10-07)

The Calendly scheduler («Agendar Cita») was removed: it was not in use and its third-party script
loader blocked the production deploy. The route `/schedule_appointment`, the sidebar item and the
dashboard quick action no longer exist. See `docs/hotfixes/2026-10-07-remove-unused-third-party-loaders.md`
for the reason and how to bring it back.

---

### 7. ORGANIZATIONS

**Available for**: Client (read-only), Corporate Client (full management)

#### For Corporate Client:
**Create and Manage Organization:**
- Name and description
- Profile and cover images
- Manage team members
- Send invitations by email
- View pending invitations
- Create corporate requests
- Publish internal announcements
- Organization statistics

**Member Management:**
- Invite by email
- View active members
- Remove members
- Assign roles
- Invitation statuses: Pending, Accepted, Rejected, Expired

#### For Client:
- View organizations where they are a member
- Accept/reject invitations
- View posts
- View corporate requests
- View other members

---

### 8. G&M INTRANET

**Available for**: Lawyers only with is_gym_lawyer = true

#### Sections:

**Firm Profile:**
- Banner: Security, Trust, Peace of mind
- Cover image and logo
- Member count
- Pending invitations
- Creation date
- View org chart button

**File Report:**
- Full billing form:
  - Contract number
  - Start and end date of the period
  - Payment concept
  - Amount to charge
  - Attach: Activities report (PDF)
  - Attach: Invoice/Billing statement (PDF)
  - Attach: Additional attachments
  - Notes
- Field and date validation

**G&M Procedures:**
- Real-time search
- Match highlighting
- Links to external documents
- Categories: Administrative, Operational, Marketing, Commercial

**G&M Org Chart:**
- Modal with full image
- Firm hierarchy
- Roles and responsibilities

---

## Permissions Comparison Table

| Feature | Lawyer | Client | Corporate Client | Basic |
|--------------|--------|--------|-----------|-------|
| **Dashboard** | ✅ Full | ✅ Full | ✅ Full | ✅ Limited |
| **Directory** | ✅ | ❌ | ❌ | ❌ |
| **View Processes** | ✅ All | ✅ Own | ✅ Own | ✅ Own |
| **Create Processes** | ✅ | ❌ | ❌ | ❌ |
| **Request Process Info** | ❌ | ✅ | ✅ | ❌ |
| **Create Documents** | ✅ | ❌ | ❌ | ❌ |
| **Use Documents** | ✅ | ✅ | ✅ | ✅ |
| **Electronic Signature** | ✅ | ✅ | ✅ | ❌ |
| **Letterhead** | ✅ | ✅ | ✅ | ❌ |
| **Create Requests** | ❌ | ✅ | ✅ | ✅ |
| **Manage Requests** | ✅ | ❌ | ❌ | ❌ |
| **Schedule Appointment** | ❌ | ✅ | ✅ | ✅ |
| **View Organizations** | ❌ | ✅ | ✅ | ✅ |
| **Manage Organizations** | ❌ | ❌ | ✅ | ❌ |
| **G&M Intranet** | ✅ GYM only | ❌ | ❌ | ❌ |
| **Install PWA** | ✅ | ✅ | ✅ | ✅ |

---

## Technical Implementation

### Frontend Structure

#### Main Routes (`/router/index.js`)
```javascript
/dashboard - Dashboard
/directory_list - Directory (requiresLawyer)
/process_list - Processes List
/process_detail/:id - Process Detail
/process_form - File Process (requiresLawyer)
/dynamic_document_dashboard - Legal Files
/legal_requests - Requests/Management
/organizations_dashboard - Organizations
/intranet_g_y_m - Intranet (requiresLawyer + is_gym_lawyer)
/user_guide - User Guide
```

#### Key Components

**SlideBar** (`/components/layouts/SlideBar.vue`):
- Dynamic role-based navigation filtering
- Removes options based on role in `onMounted`
- Special logic for is_gym_lawyer

**Stores** (`/stores/`):
- `auth/user.js` - User and role management
- `auth/auth.js` - Authentication
- `user_guide.js` - User guide content

### Backend Structure

#### Main Models (`/backend/gym_app/models/`)

**User** (`user.py`):
- Roles: 'basic', 'client', 'corporate_client', 'lawyer'
- Field: is_gym_lawyer (Boolean)
- Fields: email, first_name, last_name, contact, birthday, identification

**Process** (`process.py`):
- Relationships: client, lawyer, case, stages, case_files
- Fields: authority, plaintiff, defendant, ref

**DynamicDocument** (`dynamic_document.py`):
- States: Published, Draft, Progress, Completed, PendingSignatures, FullySigned
- Relationships: created_by, assigned_to, tags
- Fields: title, content, variables

**LegalRequest** (`legal_request.py`):
- States: PENDING, IN_REVIEW, RESPONDED, CLOSED
- Auto-generated number: SOL-YYYY-NNN
- Relationships: user, request_type, discipline, files, responses

**Organization** (`organization.py`):
- Relationship: corporate_client (limit_choices_to 'corporate_client')
- Fields: title, description, profile_image, cover_image
- Methods: get_member_count, get_pending_invitations_count

### Guards and Permissions

**Router Guards** (`router/index.js`):
```javascript
requiresAuth: true - Requires authentication
requiresLawyer: true - Lawyers only
```

**SlideBar filtering**:
- Clients: Removes "File Process", "Directory", "G&M Intranet"
- Non-GYM lawyers: Removes "G&M Intranet"
- Lawyers: Removes "Organizations", "Schedule Appointment"

### User Guide

**Location**: `/user_guide`

**Components**:
- `UserGuideMain.vue` - Main view
- `GuideNavigation.vue` - Side navigation
- `ModuleGuide.vue` - Module content
- `SearchGuide.vue` - Search
- `ExampleModal.vue` - Step-by-step examples
- `RoleInfoCard.vue` - Role info
- `QuickLinksCard.vue` - Quick links

**Store** (`user_guide.js`):
- 8 complete modules
- 28 detailed sections
- 3 examples with modals
- Automatic role-based filtering
- Real-time search

**Features**:
- Integrated WhatsApp links
- Interactive examples with steps, tips, and common errors
- "Back" button in sections
- Fully responsive
- Real-time search with results

---

## System Statistics

### Documented Content
- **Modules**: 8 main modules
- **Sections**: 28 detailed sections
- **Features**: 200+ mapped features
- **Tabs**: 13 tabs explained
- **Actions**: 10 document actions
- **Roles**: 4 roles covered
- **Examples**: 3 complete examples

### Project Files
- **Views**: 11 main views
- **Components**: 100+ components
- **Stores**: 8+ Pinia stores
- **Backend Models**: 10+ Django models
- **Routes**: 15+ main routes

---

## Important Notes

### Role Restrictions
- **Basic**: No electronic signature, no letterhead, cannot request process info
- **Client/Corporate**: Read-only on processes, cannot create/edit
- **Lawyer**: No access to Organizations or Schedule Appointment
- **is_gym_lawyer**: Required to access G&M Intranet

### Important Flows
1. **File Process**: Lawyer creates → Client sees → Client can request info
2. **Documents**: Lawyer creates with variables → Assigns to client → Client completes → Lawyer reviews
3. **Requests**: Client creates → Lawyer manages → Conversation thread → Close
4. **Organizations**: Corporate creates → Invites members → Members accept → Corporate requests

---

**Consolidated Document**: Nov 21, 2025  
**Version**: 1.0.0  
**Status**: ✅ Complete and Updated
