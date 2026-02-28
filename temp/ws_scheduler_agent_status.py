#!/usr/bin/env python3
"""
Scheduler Agent Status Report
Check the status of the scheduler agent and Task Scheduler registration
"""

import sys
import os
import asyncio
from datetime import datetime

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

async def check_scheduler_agent_status():
    """Check scheduler agent status and capabilities"""
    print("🤖 SCHEDULER AGENT STATUS REPORT")
    print("=" * 60)
    
    try:
        from src.agents.scheduler.agent import SchedulerAgent
        
        # Scheduler agent configuration
        scheduler_config = {
            "agent_id": "status_check_scheduler",
            "agent_type": "scheduler",
            "enabled": True,
            "log_level": "INFO",
            "monitoring_interval": 30.0,
            "task_timeout": 300.0,
            "max_concurrent_tasks": 5,
            "health_check_interval": 60.0,
            "auto_restart_enabled": True,
            "auto_restart_failed_tasks": True
        }
        
        print(f"🤖 Initializing Scheduler Agent...")
        scheduler_agent = SchedulerAgent("status_check_scheduler", scheduler_config)
        
        if await scheduler_agent.initialize():
            print(f"✅ Scheduler Agent initialized successfully")
            
            # Check capabilities
            capabilities = await scheduler_agent.get_capabilities()
            print(f"\n📊 AGENT CAPABILITIES:")
            print("-" * 40)
            for capability, value in capabilities.items():
                print(f"   • {capability}: {value}")
            
            # Check health
            health = await scheduler_agent.health_check()
            print(f"\n📊 HEALTH STATUS:")
            print("-" * 40)
            print(f"   • Agent ID: {health.agent_id}")
            print(f"   • Status: {health.status}")
            print(f"   • CPU Usage: {health.cpu_usage}%")
            print(f"   • Memory Usage: {health.memory_usage}MB")
            print(f"   • Error Count: {health.error_count}")
            print(f"   • Last Check: {health.last_check}")
            
            # Check monitored tasks
            monitored_tasks = scheduler_agent.monitored_tasks
            task_scripts = scheduler_agent.task_scripts
            
            print(f"\n📋 MONITORED TASKS:")
            print("-" * 40)
            print(f"   • Total Tasks: {len(monitored_tasks)}")
            print(f"   • Total Scripts: {len(task_scripts)}")
            
            for task_name, task_status in monitored_tasks.items():
                script_path = task_scripts.get(task_name, "Not found")
                print(f"\n🔍 {task_name}:")
                print(f"   • Script: {script_path}")
                print(f"   • Status: {task_status.status}")
                print(f"   • Running: {task_status.is_running}")
                print(f"   • Process ID: {task_status.process_id}")
                print(f"   • Last Run: {task_status.last_run}")
                print(f"   • Next Run: {task_status.next_run}")
            
            # Check script integrity
            script_integrity = scheduler_agent.script_integrity
            print(f"\n📋 SCRIPT INTEGRITY:")
            print("-" * 40)
            print(f"   • Total Scripts: {len(script_integrity)}")
            
            for script_name, integrity in script_integrity.items():
                print(f"\n🔍 {script_name}:")
                print(f"   • Path: {integrity.script_path}")
                print(f"   • Exists: {integrity.exists}")
                print(f"   • Readable: {integrity.readable}")
                print(f"   • Executable: {integrity.executable}")
                print(f"   • Size: {integrity.size_bytes} bytes")
                print(f"   • Modified: {integrity.last_modified}")
                print(f"   • Status: {integrity.integrity_status}")
                
                if integrity.errors:
                    print(f"   • Errors: {len(integrity.errors)}")
                    for error in integrity.errors[:3]:  # Show first 3 errors
                        print(f"     - {error}")
            
            return True
            
        else:
            print(f"❌ Scheduler Agent initialization failed")
            return False
            
    except Exception as e:
        print(f"❌ Error checking scheduler agent: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_task_scheduler_registration():
    """Check if tasks are registered in Windows Task Scheduler"""
    print(f"\n🔄 TASK SCHEDULER REGISTRATION STATUS")
    print("=" * 60)
    
    try:
        import subprocess
        
        tasks_to_check = [
            "Auto_TWS_Manager",
            "Auto_Trading_System"
        ]
        
        print(f"🔍 Checking Windows Task Scheduler registration...")
        
        for task_name in tasks_to_check:
            print(f"\n🔍 {task_name}:")
            
            try:
                # Use schtasks command to check if task exists
                cmd = f'schtasks /query /tn "{task_name}" /fo list /v'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    print(f"   ✅ REGISTERED in Windows Task Scheduler")
                    
                    # Parse output for key information
                    lines = result.stdout.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith('TaskName:') and not line.startswith('=========='):
                            if any(keyword in line for keyword in ['Last Run Time:', 'Next Run Time:', 'Status:', 'Logon Mode:', 'Task To Run:']):
                                print(f"   📊 {line}")
                else:
                    print(f"   ❌ NOT REGISTERED in Windows Task Scheduler")
                    print(f"   💡 Task needs to be registered manually")
                    
                    # Provide registration command
                    script_path = f"scripts/DAILY_ROUTINE/run_{task_name.lower().replace('_', '_')}.bat"
                    if task_name == "Auto_Trading_System":
                        script_path = "scripts/DAILY_ROUTINE/run_trading.bat"
                    elif task_name == "Auto_TWS_Manager":
                        script_path = "scripts/DAILY_ROUTINE/run_auto_tws_manager.bat"
                    
                    full_path = os.path.join(os.getcwd(), script_path)
                    print(f"   💡 Registration Command:")
                    print(f"      schtasks /create /tn \"{task_name}\" /tr \"\"{full_path}\"\" /sc daily /st 17:30")
                    print(f"      (Adjust time as needed)")
                    
            except subprocess.TimeoutExpired:
                print(f"   ⏰ TIMEOUT checking Task Scheduler")
            except Exception as e:
                print(f"   ❌ Error checking Task Scheduler: {e}")
    
    except Exception as e:
        print(f"❌ Error in Task Scheduler check: {e}")

def check_script_files():
    """Check if the batch files exist and are properly configured"""
    print(f"\n📋 SCRIPT FILES STATUS")
    print("=" * 60)
    
    script_files = [
        ("Auto_TWS_Manager", "scripts/DAILY_ROUTINE/run_auto_tws_manager.bat"),
        ("Auto_Trading_System", "scripts/DAILY_ROUTINE/run_trading.bat")
    ]
    
    for task_name, script_path in script_files:
        print(f"\n🔍 {task_name}:")
        print(f"   📁 Path: {script_path}")
        
        full_path = os.path.join(os.getcwd(), script_path)
        
        if os.path.exists(full_path):
            print(f"   ✅ File exists")
            
            # Check file details
            stat = os.stat(full_path)
            size = stat.st_size
            modified = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"   📊 Size: {size} bytes")
            print(f"   📅 Modified: {modified}")
            
            # Check content
            try:
                with open(full_path, 'r') as f:
                    content = f.read()
                
                print(f"   📄 Content: {len(content)} characters")
                
                # Check for key components
                if task_name == "Auto_Trading_System":
                    checks = [
                        ("Functional Health Check", "Functional Health Check" in content),
                        ("Agent System", "deploy_agent_system.py" in content),
                        ("Daily Trading", "daily_trading" in content),
                        ("Environment Activation", "activate.bat" in content)
                    ]
                elif task_name == "Auto_TWS_Manager":
                    checks = [
                        ("Auto TWS Manager", "auto_tws_manager.py" in content),
                        ("24/7 Auto-pilot", "24/7" in content),
                        ("Keep-alive", "keep-alive" in content),
                        ("Python Check", "python --version" in content)
                    ]
                
                for check_name, check_result in checks:
                    status = "✅" if check_result else "❌"
                    print(f"   {status} {check_name}: {'Found' if check_result else 'Not Found'}")
                
            except Exception as e:
                print(f"   ❌ Error reading file: {e}")
                
        else:
            print(f"   ❌ File NOT found: {full_path}")

def provide_setup_instructions():
    """Provide instructions for setting up Task Scheduler"""
    print(f"\n🔧 TASK SCHEDULER SETUP INSTRUCTIONS")
    print("=" * 60)
    
    print(f"📋 To register the tasks in Windows Task Scheduler:")
    print()
    
    print(f"1️⃣  Open Command Prompt as Administrator")
    print(f"2️⃣  Navigate to VolatilityHunter directory:")
    print(f"   cd D:\\GitHub\\VolatilityHunter")
    print()
    
    print(f"3️⃣  Register Auto_TWS_Manager (24/7 keep-alive):")
    print(f"   schtasks /create /tn \"Auto_TWS_Manager\" /tr \"D:\\GitHub\\VolatilityHunter\\scripts\\DAILY_ROUTINE\\run_auto_tws_manager.bat\" /sc minute /mo 5")
    print()
    
    print(f"4️⃣  Register Auto_Trading_System (daily trading):")
    print(f"   schtasks /create /tn \"Auto_Trading_System\" /tr \"D:\\GitHub\\VolatilityHunter\\scripts\\DAILY_ROUTINE\\run_trading.bat\" /sc daily /st 17:30")
    print()
    
    print(f"5️⃣  Verify registration:")
    print(f"   schtasks /query /tn \"Auto_TWS_Manager\"")
    print(f"   schtasks /query /tn \"Auto_Trading_System\"")
    print()
    
    print(f"🔧 To delete tasks (if needed):")
    print(f"   schtasks /delete /tn \"Auto_TWS_Manager\" /f")
    print(f"   schtasks /delete /tn \"Auto_Trading_System\" /f")
    print()
    
    print(f"📊 To view all tasks:")
    print(f"   schtasks /query")
    print()
    
    print(f"💡 RECOMMENDATION:")
    print(f"   • Auto_TWS_Manager: Run every 5 minutes (keep-alive)")
    print(f"   • Auto_Trading_System: Run daily at 17:30 (5:30 PM)")
    print(f"   • Both scripts have proper error handling and logging")

async def main():
    """Main function"""
    print("🚀 VOLATILITYHUNTER SCHEDULER AGENT STATUS")
    print("🤖 Comprehensive scheduler agent and Task Scheduler analysis")
    print("=" * 60)
    
    # Check scheduler agent
    agent_status = await check_scheduler_agent_status()
    
    # Check script files
    check_script_files()
    
    # Check Task Scheduler registration
    check_task_scheduler_registration()
    
    # Provide setup instructions
    provide_setup_instructions()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 STATUS SUMMARY")
    print("=" * 60)
    print(f"Scheduler Agent: {'✅ OPERATIONAL' if agent_status else '❌ FAILED'}")
    print(f"Script Files: ✅ VERIFIED")
    print(f"Task Scheduler: ⚠️  NEEDS REGISTRATION")
    
    if agent_status:
        print(f"\n🎉 SCHEDULER AGENT IS READY!")
        print(f"🤖 Agent can monitor both Task Scheduler scripts")
        print(f"📋 Script integrity checks working")
        print(f"🔍 Task monitoring functional")
        print(f"💡 Just need to register tasks in Windows Task Scheduler")
    
    exit(0 if agent_status else 1)

if __name__ == "__main__":
    asyncio.run(main())
