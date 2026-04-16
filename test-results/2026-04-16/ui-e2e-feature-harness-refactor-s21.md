# UI E2E Feature Harness Refactor - Device Smoke

Date: 2026-04-16
Sessions: real authenticated sessions, no `MOCK_AUTH`

## Build

- Samsung S21, ADB `RFCNC0Y975L`: `pwsh -File tools/start-driver.ps1 -Platform android -DeviceId RFCNC0Y975L -Timeout 180 -DriverPort 4948`
- S10-class tablet, ADB `R52X90378YB`: `pwsh -File tools/start-driver.ps1 -Platform android -DeviceId R52X90378YB -Timeout 180 -DriverPort 4949`

Result: driver APK rebuilt, installed, and reported ready on both devices.

## Seed

`POST /driver/seed`

Preconditions:
- `base_data`
- `project_draft`
- `location_a`
- `contractor_a`
- `entry_draft`
- `pay_app_draft`

Result:

```json
{
  "seeded": [
    "base_data",
    "project_draft",
    "location_a",
    "contractor_a",
    "entry_draft",
    "pay_app_draft"
  ]
}
```

## Endpoint Smoke

Each row used `POST /driver/navigate`, `GET /driver/current-route`, and
`GET /driver/find?key=<sentinel>`.

| Route | Sentinel | S21 | S10-class tablet |
| --- | --- | --- | --- |
| `/projects` | `project_list_screen` | visible | visible |
| `/toolbox` | `toolbox_home_screen` | visible | visible |
| `/calculator` | `calculator_screen` | visible | visible |
| `/todos` | `todos_screen` | visible | visible |
| `/gallery` | `gallery_screen` | visible | visible |
| `/sync/dashboard` | `sync_dashboard_screen` | visible | visible |
| `/quantities` | `quantities_screen` | visible | visible |
| `/settings` | `settings_screen` | visible | visible |
| `/analytics/harness-project-001` | `project_analytics_screen` | visible | visible |
