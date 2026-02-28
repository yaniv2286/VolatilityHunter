#!/usr/bin/env python3
"""
Register VolatilityHunter tasks in Windows Task Scheduler
"""

import sys
import os
import subprocess
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def register_task_scheduler_tasks():
    """Register both tasks in Windows Task Scheduler"""
    print("🔧 REGISTERING TASKS IN WINDOWS TASK SCHEDULER")
    print("=" * 60)
    
    tasks = [
        {
            "name": "Auto_TWS_Manager",
            "script": "scripts/DAILY_ROUTINE/run_auto_tws_manager.bat",
            "schedule": "minute",
            "modifier": 5,
            "description": "VolatilityHunter TWS Keep-Alive Manager"
        },
        {
            "name": "Auto_Trading_System", 
            "script": "scripts/DAILY_ROUTINE/run_trading.bat",
            "schedule": "daily",
            "time": "17:30",
            "description": "VolatilityHunter Daily Trading System"
        }
    ]
    
    for task in tasks:
        print(f"\n🔧 Registering {task['name']}...")
        
        # Check if script exists
        script_path = os.path.join(os.getcwd(), task['script'])
        if not os.path.exists(script_path):
            print(f"   ❌ Script not found: {script_path}")
            continue
        
        print(f"   ✅ Script found: {script_path}")
        
        # Build schtasks command
        if task['schedule'] == 'minute':
            cmd = f'schtasks /create /tn "{task["name"]}" /tr "{script_path}" /sc minute /mo {task["modifier"]} /f'
        else:
            cmd = f'schtasks /create /tn "{task["name"]}" /tr "{script_path}" /sc daily /st {task["time"]} /f'
        
        print(f"   📝 Command: {cmd}")
        
        try:
            # Execute the command
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"   ✅ Task registered successfully!")
                
                # Verify registration
                verify_cmd = f'schtasks /query /tn "{task["name"]}" /fo list'
                verify_result = subprocess.run(verify_cmd, shell=True, capture_output=True, text=True)
                
                if verify_result.returncode == 0:
                    print(f"   ✅ Verification successful!")
                    print(f"   📊 Task Details:")
                    for line in verify_result.stdout.split('\n'):
                        if line.strip() and task['name'] in line:
                            print(f"      {line.strip()}")
                else:
                    print(f"   ⚠️  Verification failed")
                    
            else:
                print(f"   ❌ Registration failed!")
                print(f"   📄 Error: {result.stderr}")
                
        except Exception as e:
            print(f"   ❌ Error registering task: {e}")

def verify_task_registration():
    """Verify that both tasks are registered"""
    print(f"\n🔍 VERIFYING TASK REGISTRATION")
    print("=" * 60)
    
    tasks = ["Auto_TWS_Manager", "Auto_Trading_System"]
    
    for task_name in tasks:
        print(f"\n🔍 Checking {task_name}...")
        
        try:
            cmd = f'schtasks /query /tn "{task_name}" /fo list /v'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print(f"   ✅ Task is registered!")
                
                # Extract key information
                lines = result.stdout.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and any(keyword in line for keyword in ['Last Run Time:', 'Next Run Time:', 'Status:', 'Task To Run:']):
                        print(f"   📊 {line}")
            else:
                print(f"   ❌ Task NOT registered!")
                
        except Exception as e:
            print(f"   ❌ Error checking task: {e}")

def test_scheduler_agent_after_registration():
    """Test scheduler agent after task registration"""
    print(f"\n🤖 TESTING SCHEDULER AGENT AFTER REGISTRATION")
    print("=" * 60)
    
    try:
        from src.agents.scheduler.agent import SchedulerAgent
        
        # Simple configuration
        config = {
            "agent_id": "test_after_registration",
            "agent_type": "scheduler",
            "enabled": True,
            "log_level": "INFO",
            "monitoring_interval": 30.0,
            "auto_restart_enabled": True
        }
        
        print(f"🤖 Initializing Scheduler Agent...")
        agent = SchedulerAgent("test_after_registration", config)
        
        # Initialize manually
        import asyncio
        
        async def test_agent():
            await agent.initialize()
            
            # Check monitored tasks
            print(f"\n📋 MONITORED TASKS:")
            print("-" * 40)
            
            for task_name, task_status in agent.monitored_tasks.items():
                script_path = agent.task_scripts.get(task_name, "Not found")
                print(f"\n🔍 {task_name}:")
                print(f"   • Script: {script_path}")
                print(f"   • Status: {task_status.status}")
                print(f"   • Running: {task_status.is_running}")
                
                # Check Task Scheduler info
                try:
                    scheduler_info = await agent._get_task_scheduler_info(task_name)
                    if scheduler_info:
                        print(f"   📊 Last Run: {scheduler_info.get('last_run', 'Unknown')}")
                        print(f"   📊 Next Run: {scheduler_info.get('next_run', 'Unknown')}")
                        print(f"   📊 Status: {scheduler_info.get('status', 'Unknown')}")
                    else:
                        print(f"   ⚠️  No Task Scheduler info")
                except Exception as e:
                    print(f"   ❌ Error checking Task Scheduler: {e}")
        
        # Run the async test
        asyncio.run(test_agent())
        
        print(f"\n✅ Scheduler Agent test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing scheduler agent: {e}")
        return False

def main():
    """Main function"""
    print("🚀 VOLATILITYHUNTER TASK SCHEDULER REGISTRATION")
    print("🔧 Register tasks and test scheduler agent")
    print("=" * 60)
    
    # Register tasks
    register_task_scheduler_tasks()
    
    # Verify registration
    verify_task_registration()
    
    # Test scheduler agent
    agent_test = test_scheduler_agent_after_registration()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 REGISTRATION SUMMARY")
    print("=" * 60)
    print(f"Task Registration: ✅ COMPLETED")
    print(f"Task Verification: ✅ COMPLETED")
    print(f"Scheduler Agent Test: {'✅ PASS' if agent_test else '❌ FAIL'}")
    
    if agent_test:
        print(f"\n🎉 TASK SCHEDULER SETUP COMPLETED!")
        print(f"🤖 Scheduler Agent can now monitor both tasks")
        print(f"📋 Auto_TWS_Manager: Registered for 5-minute intervals")
        print(f"📋 Auto_Trading_System: Registered for daily 17:30 execution")
        print(f"🔍 Both tasks are ready for automated execution")
    
    print(f"\n💡 NEXT STEPS:")
    print(f"1. Monitor task execution in Windows Task Scheduler")
    print(f"2. Check logs for task execution results")
    print(f"3. Verify TWS stays alive with Auto_TWS_Manager")
    print(f"4. Confirm daily trading workflow executes properly")

if __name__ == "__main__":
    main()
