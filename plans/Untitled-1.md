We need a sync button at the top of the app to sync quickly/easily

we have several layers of audits post refactor and post large implementations, as well as pre production and code hygiene audits done. We're trying to confirm these audits and brainstorm specs and create implementation plans to get our codebase to 100 clean and functional code. Use Opus level agents to explore and gather context. We are looking to use the brainstorming skill to create a spec for the audit in an attempt to get closer to production/beta. We will /tailor the spec and then use the writing plans skill on it. Please analyze the attached audit, then review codebase's layer that matches the audit and verify the errors that were found.  

New documentation system idea - 

Need to start documenting through github commits much more
 - standardize commit structure to tell a story
 - organize commits per our 8 layer structure
 - try to commit the phase if implementing a plan
 - create a phase map in a plan so when commit phases agents dont read the entire plan
 - 

  CLAUDE - 


  ❯ Do NOT stop iterating until the specs intent has been fully and completely captured. Do not forget that we do not want any god class screens, widgets, methods, helpers, over 300 lines. We want all UI screen API  endpoints to be easily exposed for the sync engine coordinators and orchestrators.This has been a major pain point and it has made it hard to verify our sync system. Confirm that all lint rules have been applied and are fixed and that no ignore rules or  other AI tricks have been applied to mitigate following the lint rules.

  Please add to or update your TODO list with these new requirements. 

  DO NOT STOP until you have finished and the specs intent has been fully captured.  


  › Yes let's install docker and figure out how to get the remote work accessible to you unless you've already figured it out                 
                                                                                                                                            

• Run these from an elevated PowerShell.
                                                                                                                                            
  Docker / Local Supabase                                                                                                                   
                                                                                                                                            
  Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -All -NoRestart                                      
  Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -All -NoRestart                                                 
                                                                                                                                            
  wsl --update                                                                                                                              
                                                                                                                                            
  winget install --id Docker.DockerDesktop --exact --accept-package-agreements --accept-source-agreements                                   
                                                                                                                                            
  Restart-Computer                                                                                                                          
                                                                                                                                            
  & "$Env:ProgramFiles\Docker\Docker\Docker Desktop.exe"

  Then verify:
  docker info
  supabase --version
  cd C:\Users\rseba\Projects\Field_Guide_App
  supabase status
  supabase start

  If docker version and supabase start work, I’ll be able to run the local Supabase stack, reset/apply migrations, and validate the DB side 
  of the beta work from this repo.

  Remote Supabase
  Remote access is already working from this shell. I already confirmed:

  supabase projects list

  and it returned your linked project Construction Inspector App with ref vsqvkxvvmnnhdajtgblj.

  If you want to re-link explicitly from admin PowerShell anyway:


  supabase login

  Once Docker is running, tell me the results of:


  and I’ll continue with local-stack validation plus the refactor work.

───────────────────────────────────────────────────────────────────────────

Testing notes - 

  - When deleting a project there is no-auto refresh, this needs to be fixed, make sure this doesn't happen in other areas of the app as well. 
  - It had alot of trouble syncing, took awhile, said it was complete but shows 2 pending and 12 conflicts in the sync dashboard. 
  - No way to clear the sync dashboard conflicts, this needs to be more intuitive since it is user facing
  - The integrity checks section is very misleading, not sure what it is even doing
  - No way to view the pending changes, again if this is user facing it needs to be more intuitive and transparent
  - I attempted a second sync and it cleared the 2 pending and now there are 15 conflicts? 
  - Synced again and now there are 20 conflicts
  


  - When editing the activities, when you click done, it doesn't show the data you've typed out, this must be fixed
  - When creating equipment in the create equipment popup there the equipment is listed and scrollable, this is fine but you can only see one piece of equipment at a time and its extremely unclear you can scroll. Needs to be fixed, the user would never know to scroll to find the equipment to delete/edit
  - When editing an entry by clicking continue todays entry in the dashboard, it says new entry. I know we use the new entry screen but can we make this a bit more honest / user friendly
  - If I submit the entry for the day I was working on and I click continue todays entry from the dashboard it starts a new entry. It should ask if you'd like to unsubmit as there is already an entry for this day
  - We need to have a way to intuitively make a report for a different date, I think the best way to do this is to allow the user to edit the date of a report in the new entry wizard
  - entries can be backdated by selecting a calendar day prior in the calendar screen, this is good. 
  - the calendar screen has an overflow error, this tells me that this hasn't been properly tokenized/scaffolded as the sizing should be adaptive. Our responsive scaffolding should've handled this I believe
  - There are no forms in the Forms screen in the Toolbox, when clicking the + icon it brings up a scroll box on the bottom of the screen that stays down and you can't do anything with it
  
   - One state-ownership rule per screen: detail screens render the live provider/model source, not stale screen-local copies after mutation.
  - One mutation contract: every create/update/delete must either update the canonical provider state or trigger a required reload path immediately.
  - One route-intent layer: actions like continue today, new entry, view submitted, edit draft should go through shared intent helpers, not screen-local ad hoc navigation.
  - One preload contract for screens/sheets: if a screen depends on builtin forms, contractor data, etc., it must load that before interactive controls enable.
  - One responsive content contract for dialogs/sheets: scrolling regions get explicit constraints and visible affordances, not “Flexible inside whatever dialog happens to host it”.
  - Contract tests for those behaviors: not just widget snapshots, but tests that assert “save updates visible state”, “delete removes item without manual refresh”, “continue today reopens today’s entry”, and “sheet never opens empty when action is enabled”.

  When loading into another project and on a different user/user role that another account is on, it shows their trash as mine, it just had 390 items in my  trash can on a different account
  The double screen view for the windows version of the dashboard just shows two of the same screen, this is pointless. Better to just keep this screen as one for now until we redesign it better