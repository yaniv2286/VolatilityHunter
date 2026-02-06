# Manual Windows Task Scheduler Setup Instructions
# Follow these steps to create the VolatilityHunter task manually

## STEP 1: Open Task Scheduler
1. Press Win + R, type "taskschd.msc" and press Enter
2. OR press Win, type "Task Scheduler" and open it

## STEP 2: Create New Task
1. In the right pane, click "Create Task..."
2. Name: "VolatilityHunter Daily Trading"
3. Description: "VolatilityHunter automated trading system - Daily execution at 12:30 AM"

## STEP 3: Set Triggers
1. Go to "Triggers" tab
2. Click "New..."
3. Settings:
   - Begin the task: "On a schedule"
   - Settings: "Daily"
   - Start time: "12:30:00 AM"
   - Enabled: ✓
4. Click OK

## STEP 4: Set Actions
1. Go to "Actions" tab
2. Click "New..."
3. Settings:
   - Action: "Start a program"
   - Program/script: "python"
   - Add arguments: "scheduler_updated.py --daily"
   - Start in: "D:\GitHub\VolatilityHunter"
4. Click OK

## STEP 5: Set Conditions
1. Go to "Conditions" tab
2. Settings:
   - Start the task only if the computer is on AC power: ✗ (uncheck)
   - Start the task only if the computer is on AC power: ✗ (uncheck)
   - Wake the computer to run this task: ✓ (check)

## STEP 6: Set Settings
1. Go to "Settings" tab
2. Settings:
   - Allow task to be run on demand: ✓
   - Run task as soon as possible after a scheduled start is missed: ✓
   - Stop the task if it runs longer than: "1 hour"
   - If the running task does not end when requested, force it to stop: ✓

## STEP 7: Set Environment Variables (Optional)
1. Go to "Actions" tab
2. Select your action and click "Edit..."
3. In "Start in", add: 
   "D:\GitHub\VolatilityHunter"
4. Click OK

## STEP 8: Save and Test
1. Click OK to save the task
2. Right-click the task and select "Run" to test
3. Check the history tab for results

## QUICK TEST COMMANDS:
# Test health check:
python scheduler_updated.py --health

# Test daily job:
python scheduler_updated.py --daily

# Test simulation:
python scheduler_updated.py --test
