We need a sync button at the top of the app to sync quickly/easily

we have several layers of audits post refactor and post large implementations, as well as pre production and code hygiene audits done. We're trying to confirm these audits and brainstorm specs and create implementation plans to get our codebase to 100 clean and functional code. Use Opus level agents to explore and gather context. We are looking to use the brainstorming skill to create a spec for the audit in an attempt to get closer to production/beta. We will /tailor the spec and then use the writing plans skill on it. Please analyze the attached audit, then review codebase's layer that matches the audit and verify the errors that were found.  

New documentation system idea - 

Need to start documenting through github commits much more
 - standardize commit structure to tell a story
 - organize commits per our 8 layer structure
 - try to commit the phase if implementing a plan
 - create a phase map in a plan so when commit phases agents dont read the entire plan
 - 

• Use this next session:
                                                                                                                                    
  Resume sync delete verification on branch `sync-engine-refactor` in `C:\Users\rseba\Projects\Field_Guide_App`.                    
                                                                                                                                    
  Before doing anything else:                                                                                                       
  1. Read `.codex/AGENTS.md`                                                                                                        
  2. Read `.codex/Context Summary.md`                                                                                               
  3. Read `.codex/PLAN.md`                                                                                                          
  4. Read `.codex/CLAUDE_CONTEXT_BRIDGE.md`                                                                                         
  5. Read `.codex/plans/2026-04-06-payapp-sync-bulletproof-todo.md`                                                                 
  6. Read `.codex/plans/2026-04-06-delete-propagation-hardening-plan.md`                                                            
  7. Read `.claude/autoload/_state.md`                                                                                              
  8. Read `.claude/state/PROJECT-STATE.json`                                                                                        
  9. Read `.claude/state/feature-sync.json`                                                                                         
  10. Read `.claude/test-results/2026-04-06_193351_codex_sync-delete-live/report.md`                                                
  11. Read `.claude/test-results/2026-04-06_193351_codex_sync-delete-live/checkpoint.json`                                          
                                                                                                                                    
  Current branch state:                                                                                                             
  - branch: `sync-engine-refactor`                                                                                                  
  - head: `604c3fed` (merge of OCR branch back into sync branch)                                                                    
  - sync delete hardening commits already on branch:                                                                                
    - `15597815` Add delete propagation verification checkpoint                                                                     
    - `7af1da6a` Cascade entry deletes from the UI layer                                                                            
    - `12ad7b43` Retain deleted parent scope for child tombstones                                                                   
    - `41616481` Extend project delete graph to assignment parity                                                                   
  - OCR branch was merged back successfully and verified                                                                            
                                                                                                                                    
  What was proven live already on S21 + Windows:                                                                                    
  - Entry delete now converges correctly:                                                                                           
    - sender tombstones entry + photo + document                                                                                    
    - sender queue drains                                                                                                           
    - Supabase rows tombstoned                                                                                                      
    - storage prefixes emptied                                                                                                      
    - Windows receiver converges with deleted child rows                                                                            
  - Project delete now converges much better:                                                                                       
    - remote RPC tombstones full subtree including `project_assignments`                                                            
    - local project delete graph was fixed so sender and Windows now both tombstone `project_assignments`                           
  - The main architecture conclusion:                                                                                               
    - we need split delete orchestration, not a bigger monolithic `SoftDeleteService`                                               
    - lock shared delete graph + lock materialized pull scope to prevent graph drift and scope drift                                

  Most important remaining delete-verification work:
  1. Verify project-delete storage cleanup explicitly
  2. Verify deleted entry absence in UI on both devices
  3. Verify deleted project absence in UI on both devices
  4. Deduplicate `/driver/delete-propagation` project snapshot output
  5. Continue remaining file-backed delete lanes and revocation/restore/hard-delete lanes

  Known artifact/run context:
  - live run dir: `.claude/test-results/2026-04-06_193351_codex_sync-delete-live`
  - run tag: `t138i`
  - deleted project used in proof: `d2bb6a5d-010f-4e9b-adcb-9188ea442391`
  - deleted entry used in proof: `1a31fc0c-33ef-4f99-8c07-60ebc9825c4e`
  - photo id: `7c25e358-351b-42b7-9de2-a04c9659b0be`
  - document id: `88c32836-4c19-4297-b36e-255ecd0e0b8d`

  Operational rules for this resume:
  - sync is the top priority
  - use S21 (`RFCNC0Y975L`) and Windows only for live sync verification
  - do not pivot into broad UI refactor work
  - fix sync defects immediately
  - file non-sync defects to GitHub issues
  - keep updating the checklist/report/checkpoint artifacts as you go

  Then continue the delete verification from the current proof state.






















  CLAUDE - 


  ❯ Do NOT stop iterating until the specs intent has been fully and completely captured. Do not forget that we do not want any god class screens, widgets, methods, helpers, over 300 lines. We want all UI screen API  endpoints to be easily exposed for the sync engine coordinators and orchestrators.This has been a major pain point and it has made it hard to verify our sync system. Confirm that all lint rules have been applied and are fixed and that no ignore rules or  other AI tricks have been applied to mitigate following the lint rules.

  Please add to or update your TODO list with these new requirements. 

  DO NOT STOP until you have finished and the specs intent has been fully captured.  

