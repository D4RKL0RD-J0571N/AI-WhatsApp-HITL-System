# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2026-01-17

### Added
- **Conversation Management**:
  - Right-click Context Menus for Sidebar (Pin, Archive) and Messages (Copy, Delete, Edit).
  - Backend API endpoints for Pin/Unpin and Archive/Unarchive.
  - Database schema migration (v3) adding `is_archived` and `is_pinned` columns.
- **AI Metadata & HITL**:
  - Frontend display for AI Intent, Confidence Score, and Reasoning.
  - "AI is thinking..." visual indicator during generation.
  - Backend logic to analyze and store metadata for every AI response.
- **UI Improvements**:
  - Optimistic UI updates for instant "Approve/Reject" feedback.
  - Trash icon on hover for message deletion.
  - Timestamp formatting and sender differentiation.
  - Fully functional Dark/Light mode toggle.

### Changed
- Refactored `ChatDashboard.tsx` to include `InfoPanel` and `Sidebar` components.
- Updated database schema (v2) to include `confidence` and `metadata_json` in messages.
- Moved `Sidebar` logic to its own component with auto-refresh polling.

### Fixed
- Fixed bug where new messages were overwriting old ones due to missing ID broadcast.
- Fixed stale state issues where "Approve" button wouldn't update UI until refresh.
- Resolved TypeScript errors and syntax issues in Sidebar and Dashboard components.

---

## [0.2.0] - Prior to 2026-01-17

### Added
- **Visual Identity**:
  - Implemented Glassmorphism design system with Tailwind CSS.
  - Added Dark/Light mode theme engine using CSS variables and React state.
- **AI Core**:
  - Integrated Local LLM support via OpenAI-compatible endpoint (LM Studio).
  - Implemented System Prompts and basic conversation memory.
- **Operator Dashboard**:
  - Created the first iteration of the ChatDashboard with message bubbles and input field.
  - Side-panel for client listing (initial static data).

### Changed
- Migrated from vanilla CSS to localized component-based styles.

## [0.1.0] - Project Inception

### Added
- **Infrastructure**:
  - Core FastAPI server setup with Uvicorn.
  - SQLite database integration with SQLAlchemy ORM.
  - Initial database schema: `Client`, `Conversation`, `Message`.
- **Real-time Engine**:
  - WebSocket Manager for broadcasting messages to multiple frontend instances.
- **WhatsApp Webhook Simulation**:
  - Endpoint for receiving/simulating external messages from WhatsApp.
- **Frontend Skeleton**:
  - Vite + React + TypeScript boilerplate.
  - Basic routing and workspace structure.
