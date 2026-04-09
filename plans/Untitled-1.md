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
Please turn these testing notes into a comprehensive spec. I'm going to go to bed for the night and I'd like you to create a TODO out of all of these items and keep iterating until all of them are completed. 

Testing notes - 

  - When deleting a project there is no-auto refresh, this needs to be fixed, make sure this doesn't happen in other areas of the app as well. 
  - When editing the activities, when you click done, it doesn't show the data you've typed out, this must be fixed
  - When creating equipment in the create equipment popup there the equipment is listed and scrollable, this is fine but you can only see one piece of equipment at a time and its extremely unclear you can scroll. Needs to be fixed, the user would never know to scroll to find the equipment to delete/edit
  - When editing an entry by clicking continue todays entry in the dashboard, it says new entry. I know we use the new entry screen but can we make this a bit more honest / user friendly
  - If I submit the entry for the day I was working on and I click continue todays entry from the dashboard it starts a new entry. It should ask if you'd like to unsubmit as there is already an entry for this day
  - We need to have a way to intuitively make a report for a different date, I think the best way to do this is to allow the user to edit the date of a report in the new entry wizard
  - entries can be backdated by selecting a calendar day prior in the calendar screen, this is good. 
  - the calendar screen has an overflow error, this tells me that this hasn't been properly tokenized/scaffolded as the sizing should be adaptive. Our responsive scaffolding should've handled this I believe
  - There are no forms in the Forms screen in the Toolbox, when clicking the + icon it brings up a scroll box on the bottom of the screen that stays down and you can't do anything with it
  - When loading into another project and on a different user/user role that another account is on, it shows their trash as mine, it just had 390 items in my  trash can on a different account
  - The double screen view for the windows version of the dashboard just shows two of the same screen, this is pointless. Better to just keep this screen as one for now until we redesign it better
  
 Forms -  
  - The station selection in the quick test section doesn't display a + sign, we display stations as xx+xx so we need to have a + 
  - The items of work are wrong, there is a table on the 0582B at on the second page of the pdf that displays the different items of work, we want the actual item names in the app and then the exported item of work is the item corresponding item code, we need to have a way to display the Density Requirements 
  -  when its the 'original' test we just want want it to be numbered chronologically, this should go in descending order per test, except when recheck has been checked, we display a recheck number subsequent to the original until the inspector gets a passing test, and then we continue back with the chronological numbering
  - It blocks me from exporting a 0582B without required fields, it shouldn't do this, we can always edit the form after its exported as well. forms aren't to be flattened on export
  - We only need to display to .0 accuracy on the 0582B. We are currently displaying as .00, this needs to be fixed.
  - After saving the 0582B it doesn't display in the 'saved responses' section of the 0582B tab in the forms gallery
  - When bringing the app to foreground after you've hit the home button the app loads in very slow, and also doesn't seem to assume state ownership because when i hit the back key it closes the app, this essentially locks the app until its killed and even then restarts to the same screen, so locks the user out of the app. When the app is completely closed and not just backgrounded you should be brought to the projects selection page if auth isn't needed. This is very important to get right, I'm thinking this could possibly be because we don't have proper nested screen routes but I'm not sure, this happens app wide too
  - Export didn't work, brought up multiple bottom screens, didn't let me select a file path for export, The other options are fine but need to be able to export to a dated folder. Should also prompt to ask if I'd like to attach this to a form or export as is
  







  - One state-ownership rule per screen: detail screens render the live provider/model source, not stale screen-local copies after mutation.
  - One mutation contract: every create/update/delete must either update the canonical provider state or trigger a required reload path immediately.
  - One route-intent layer: actions like continue today, new entry, view submitted, edit draft should go through shared intent helpers, not screen-local ad hoc navigation.
  - One preload contract for screens/sheets: if a screen depends on builtin forms, contractor data, etc., it must load that before interactive controls enable.
  - One responsive content contract for dialogs/sheets: scrolling regions get explicit constraints and visible affordances, not “Flexible inside whatever dialog happens to host it”.
  - Contract tests for those behaviors: not just widget snapshots, but tests that assert “save updates visible state”, “delete removes item without manual refresh”, “continue today reopens today’s entry”, and “sheet never opens empty when action is enabled”.