# Manual-Only Flows (M01-M13)

> These flows require capabilities the HTTP driver cannot provide. Run manually on device.

| ID | Flow | Why Manual | Verify | Notes |
|----|------|-----------|--------|-------|
| M01 | Register New Account | Requires OTP email verification | Check user_profiles in Supabase | Full: register → OTP → profile-setup → company-setup |
| M02 | Forgot Password → Reset | Requires OTP email delivery | Login with new password | Full: forgot-password → OTP → update-password |
| M03 | Import Pay Items from PDF | Requires FilePicker + OCR pipeline | Check bid_items count in project | Full: project edit → pay items → PDF import → preview → import |
| M04 | Import M&P from PDF | Requires FilePicker | Check bid_items enrichment | Full: project edit → pay items → M&P import → preview → apply |
| M05 | Capture Photo (Camera) | Requires camera hardware | Check photos table | Full: entry → photos → camera → name dialog → save |
| M07 | Download Remote Project | Requires remote-only project | Check synced_projects locally | Full: company tab → tap remote → download → verify |
| M08 | Deactivate/Reactivate Member | Requires second active member | Check user_profiles status | Admin: member sheet → deactivate → reactivate |
| M09 | Submit Form (Section-by-Section) | 0582B uses proctor/test section sends, no global submit | Check form_responses status | Was T37 — no single submit button to automate |
| M10 | Approve Join Request | Requires pending join request from second account | Check user_profiles approval | Was T56 — no pending requests exist for automation |
| M11 | Reject Join Request | Requires pending join request from second account | Check company_join_requests rejection | Was T57 — no pending requests exist for automation |
| M12 | Use Quantity Calculator from Entry | Calculator not launchable from entry report screen | Check entry_quantities count | Was T21 — calculator not wired from entry context |
| M13 | Add Personnel Type from Entry | Personnel types management not reachable from entry | Check personnel_types count | Was T67 — PersonnelTypesScreen exists but no tile/route to it |
