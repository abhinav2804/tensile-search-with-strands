# User Status Widget

A lightweight, self-contained widget that displays authenticated user related backend state (login + provisioning of ES / MCP instances and index presence). It auto-hides after 10 seconds by default and does not disturb your existing layout.

## Files

- `user-status-config.js` – central configuration flags & display field definitions.
- `user-status-widget.js` – implementation (no external dependencies). Loads immediately once imported.

## Quick Integration (already done if you added scripts)

In your `index.html` (near the end of `<body>` or after auth logic):

```html
<script type="module" src="/static/js/user-status-config.js"></script>
<script type="module" src="/static/js/user-status-widget.js"></script>
```

(If you serve static with a different prefix adjust the paths.) The widget loads on page render and performs a single fetch by default.

## Expected Backend API

Endpoint: `GET /api/user/status` (editable via `USER_STATUS_API_URL`), returns JSON like:
```json
{
  "userId": "descope-user-id-123",
  "email": "amit.kumar@example.com",
  "login": true,
  "esInstance": "http://1.2.3.4:9200",
  "indexName": "products-index",
  "mcpInstance": "http://5.6.7.8:4000",
  "timestamp": "2025-09-18T12:34:56Z"
}
```

### Field Handling
- `login` (boolean) → green ✔ if true, red ✖ if false
- `esInstance` (string) → ✔ if non-empty else ✖
- `mcpInstance` (string) → ✔ if non-empty else ✖
- `indexName` (string) → prints name or ✖ if empty

Missing / null values are treated as not present (✖). If the API call fails entirely a fallback box appears with all ✖ and user label "Not authenticated".

## Configuration (edit `user-status-config.js`)
| Constant | Purpose | Default |
|----------|---------|---------|
| `USER_STATUS_API_URL` | Backend status endpoint | `'/api/user/status'` |
| `USER_STATUS_POLL_MS` | Poll interval (ms). 0 disables polling | `0` |
| `USER_STATUS_AUTO_HIDE_MS` | Auto-hide delay (ms). Set 0 to keep visible | `10000` |
| `USER_STATUS_ENABLE` | Master enable/disable | `true` |
| `USER_STATUS_DEBUG` | Verbose console logging | `false` |
| `ICONS` | Success / fail symbols | ✔ ✖ … |
| `DISPLAY_FIELDS` | Ordering + labels + type mapping | see file |

### Field Types
- `boolean` – truthy = ✔ / falsey = ✖
- `presence` – non-empty string = ✔ else ✖
- `string-or-cross` – show the string if present else ✖

## Theming / Styling
Inline styles keep it isolated. To override, add CSS rules targeting class names from `CLASSNAMES` in a global stylesheet:
```css
.user-status-widget { /* container overrides */ }
.user-status-widget .usw-row { /* each row */ }
```
Or add an extra stylesheet and remove some inline style lines if you prefer external styling.

## Accessibility
- `role="status"` + `aria-live="polite"` for screen readers.
- Close button is keyboard focusable, labelled.

## Auto-hide Behaviour
After a successful (or failed) fetch, a timer hides the widget in `USER_STATUS_AUTO_HIDE_MS`. Set to `0` if you want it always visible or implement manual closing only.

## Polling
Set `USER_STATUS_POLL_MS` to e.g. `5000` to refresh every 5 seconds (auto-hide still counts from the first display unless you modify logic). Adjust or move `scheduleHide()` inside `fetchStatus()` if you want the timer to reset each poll.

## Safe Failure
If fetch throws or JSON parse fails you still get a rendered widget, then it hides per configured timer.

## Changing Order / Labels
Edit `DISPLAY_FIELDS` array; order there = render order. Example add a new field:
```js
DISPLAY_FIELDS.push({ key: 'newMetric', label: 'New Metric', type: 'string-or-cross' });
```
Ensure the backend includes `newMetric`.

## Removing / Disabling
Set `USER_STATUS_ENABLE = false` to completely skip initialization (no network request, no DOM changes).

---
Feel free to extend with additional meta (e.g., last updated time) or integrate with your existing auth success callback if you want to defer showing until after Descope validation.
