/**
 * User Status Widget Configuration
 * ---------------------------------
 * Adjust these constants to match your backend environment and desired behaviour.
 *
 * EXPECTED API (dummy example):
 *   GET /api/user/status  (replace with USER_STATUS_API_URL)
 *   Response JSON shape:
 *   {
 *     "userId": "descope-user-id-or-email",
 *     "email": "amit.kumar@example.com",       // optional (fallback to userId)
 *     "login": true,                            // whether auth validated on backend
 *     "esInstance": "http://1.2.3.4:9200",     // string or null/'' if not created
 *     "indexName": "products-index",           // string or null if none
 *     "mcpInstance": "http://5.6.7.8:4000",    // string or null
 *     "timestamp": "2025-09-18T12:34:56Z"      // optional informational
 *   }
 *
 * If request fails or JSON missing keys we degrade gracefully and still show a box (with crosses).
 */

export const USER_STATUS_API_URL = '/api/user/status'; // <-- Replace with your real endpoint
export const USER_STATUS_POLL_MS = 0;                   // 0 disables polling (only fetch once on load)
export const USER_STATUS_AUTO_HIDE_MS = 10000;          // Auto-hide after 10s
export const USER_STATUS_ENABLE = true;                 // Master toggle
export const USER_STATUS_DEBUG = false;                 // Extra console logging when true
export const SHOW_WIDGET_LOGS = true;                   // High-level lifecycle checkpoints (overrides USER_STATUS_DEBUG for critical logs)

/**
 * Icon characters (can swap to emojis or SVG). Keep short for layout stability.
 */
export const ICONS = {
  success: '✔',
  fail: '✖',
  loading: '…'
};

/**
 * Styling hooks (class names) so you can override in existing CSS if needed.
 */
export const CLASSNAMES = {
  container: 'user-status-widget',
  row: 'usw-row',
  label: 'usw-label',
  value: 'usw-value',
  fadeOut: 'usw-fade-out',
  closing: 'usw-closing'
};

/**
 * Map internal fields to display labels & accessors for flexible ordering.
 */
export const DISPLAY_FIELDS = [
  {
    key: 'login',
    label: 'Login successful',
    type: 'boolean'
  },
  {
    key: 'esInstance',
    label: 'Hosted the ES',
    type: 'presence' // treat non-empty string as success
  },
  {
    key: 'mcpInstance',
    label: 'Hosted the MCP',
    type: 'presence'
  },
  {
    key: 'indexName',
    label: 'Index name',
    type: 'string-or-cross'
  }
];
