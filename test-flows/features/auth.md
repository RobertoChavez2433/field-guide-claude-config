# Feature: auth

## Purpose
Authentication owns sign-in, registration, recovery, OTP/status routing, and account setup gates without using approved `base_data` for non-approved account states.

## Screens
- login: `lib/features/auth/presentation/screens/login_screen.dart`
- register: `lib/features/auth/presentation/screens/register_screen.dart`
- forgot-password: `lib/features/auth/presentation/screens/forgot_password_screen.dart`
- otp-verification: `lib/features/auth/presentation/screens/otp_verification_screen.dart`
- update-password: `lib/features/auth/presentation/screens/update_password_screen.dart`
- pending-approval: `lib/features/auth/presentation/screens/pending_approval_screen.dart`
- account-status: `lib/features/auth/presentation/screens/account_status_screen.dart`

## Preconditions catalog
- `otp_required_profile`: seeds a profile that must complete OTP.
- `pending_profile`: seeds a pending member profile.
- `rejected_profile`: seeds a rejected member profile.

## Sub-flows
```yaml
- name: forward_happy
  requires: [otp_required_profile]
  appliesTo: { roles: [admin, engineer, officeTechnician, inspector], devices: [s21, s10] }
  steps:
    - find: login_screen
    - tap: login_sign_up_button
    - find: register_screen
  assertions: [ { current_route: /register } ]
- name: backward_traversal
  requires: [otp_required_profile]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps:
    - navigate: /login
    - tap: forgot_password_link
    - find: forgot_password_screen
    - back: true
  assertions: [ { current_route: /login } ]
- name: back_at_root
  requires: [pending_profile]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps:
    - navigate: /login
    - find: login_screen
    - back: true
- name: deep_link_entry
  requires: [otp_required_profile]
  appliesTo: { roles: [admin, inspector], devices: [s21, s10] }
  steps:
    - navigate: /verify-otp
    - find: otp_verification_screen
  assertions: [ { current_route: /verify-otp } ]
- name: orientation_change
  requires: [rejected_profile]
  appliesTo: { roles: [inspector], devices: [s21, s10] }
  steps:
    - navigate: /account-status
    - find: account_status_screen
```

## Retired flow IDs
- T01
- T02
- T03
- T04
- M01
- M02
