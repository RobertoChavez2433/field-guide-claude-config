# Improvements

Non-blocking UX/polish items. Lower priority than defects — address during feature work or dedicated polish sprints.

## Active

### [UX] 2026-02-28: Remove Certification Number from profile setup
**Feature**: auth (profile setup)
**Screen**: Set Up Profile / "Tell us about yourself"
**Issue**: Certification Number field is asked too early in the onboarding flow. Not needed at this stage — users shouldn't have to dig up their cert number just to create an account.
**Fix**: Remove the field from `ProfileSetupScreen`. It can be added later in Settings > Profile or when generating a PDF report that requires it.
**Ref**: `lib/features/auth/presentation/screens/profile_setup_screen.dart`

### [UX] 2026-02-28: Phone number needs auto-formatting
**Feature**: auth (profile setup)
**Screen**: Set Up Profile / "Tell us about yourself"
**Issue**: Phone number field accepts raw digits with no formatting. Should auto-format as user types (e.g., `(269) 865-1676` for US numbers).
**Fix**: Add an input formatter that applies `(XXX) XXX-XXXX` mask on input. Consider using a package like `mask_text_input_formatter` or a custom `TextInputFormatter`.
**Ref**: `lib/features/auth/presentation/screens/profile_setup_screen.dart`

<!-- Add improvements above this line -->
