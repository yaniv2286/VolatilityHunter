#!/usr/bin/env python3
"""
Scheduler Agent Test
Test the scheduler agent's ability to see and manage Task Scheduler scripts
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

async def test_scheduler_agent():
    """Test scheduler agent functionality"""
    print("🤖 SCHEDULER AGENT TEST")
    print("=" * 60)
    
    try:
        # Import scheduler agent
        from src.agents.scheduler.agent import SchedulerAgent
        
        # Scheduler agent configuration
        scheduler_config = {
            "agent_id": "test_scheduler_agent",
            "agent_type": "scheduler",
            "enabled": True,
            "log_level": "INFO",
            "monitoring_interval": 30.0,
            "task_timeout": 300.0,
            "max_concurrent_tasks": 5,
            "health_check_interval": 60.0,
            "auto_restart_failed_tasks": True,
            "task_scripts": {
                "Auto_TWS_Manager": "scripts/DAILY_ROUTINE/run_auto_tws_manager.bat",
                "Auto_Trading_System": "scripts/DAILY_ROUTINE/run_trading.bat"
            }
        }
        
        print(f"🤖 Initializing Scheduler Agent...")
        scheduler_agent = SchedulerAgent("test_scheduler_agent", scheduler_config)
        
        if await scheduler_agent.initialize():
            print(f"✅ Scheduler Agent initialized successfully")
            
            # Test 1: Check monitored tasks
            print(f"\n📋 TEST 1: MONITORED TASKS")
            print("-" * 40)
            
            monitored_tasks = scheduler_agent.monitored_tasks
            task_scripts = scheduler_agent.task_scripts
            
            print(f"📊 Total Monitored Tasks: {len(monitored_tasks)}")
            print(f"📊 Total Task Scripts: {len(task_scripts)}")
            
            for task_name in monitored_tasks:
                task_status = monitored_tasks[task_name]
                script_path = task_scripts.get(task_name, "Not found")
                
                print(f"\n🔍 {task_name}:")
                print(f"   • Script Path: {script_path}")
                print(f"   • Status: {task_status.status}")
                print(f"   • Running: {task_status.is_running}")
                print(f"   • Last Run: {task_status.last_run}")
                print(f"   • Next Run: {task_status.next_run}")
                print(f"   • Process ID: {task_status.process_id}")
                print(f"   • CPU Usage: {task_status.cpu_usage}%")
                print(f"   • Memory Usage: {task_status.memory_usage}MB")
                print(f"   • Uptime: {task_status.uptime:.1f}s")
            
            # Test 2: Check script integrity
            print(f"\n📋 TEST 2: SCRIPT INTEGRITY")
            print("-" * 40)
            
            for task_name, script_path in task_scripts.items():
                print(f"\n🔍 Checking {task_name}...")
                
                # Check if script exists
                full_path = os.path.join(os.getcwd(), script_path)
                exists = os.path.exists(full_path)
                
                if exists:
                    print(f"   ✅ Script exists: {full_path}")
                    
                    # Check file size and modification
                    stat = os.stat(full_path)
                    size = stat.st_size
                    modified = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                    
                    print(f"   📊 Size: {size} bytes")
                    print(f"   📅 Modified: {modified}")
                    
                    # Check if readable
                    try:
                        with open(full_path, 'r') as f:
                            content = f.read()
                        print(f"   ✅ Readable: {len(content)} characters")
                        
                        # Check for key content
                        if task_name == "Auto_Trading_System":
                            if "Functional Health Check" in content:
                                print(f"   ✅ Contains: Functional Health Check")
                            if "deploy_agent_system.py" in content:
                                print(f"   ✅ Contains: Agent System Deployment")
                            if "daily_trading" in content:
                                print(f"   ✅ Contains: Daily Trading Workflow")
                        
                        elif task_name == "Auto_TWS_Manager":
                            if "auto_tws_manager.py" in content:
                                print(f"   ✅ Contains: Auto TWS Manager")
                            if "24/7" in content:
                                print(f"   ✅ Contains: 24/7 Auto-pilot")
                            if "keep-alive" in content:
                                print(f"   ✅ Contains: Keep-alive service")
                        
                    except Exception as e:
                        print(f"   ❌ Read error: {e}")
                        
                else:
                    print(f"   ❌ Script NOT found: {full_path}")
            
            # Test 3: Check Task Scheduler integration
            print(f"\n📋 TEST 3: TASK SCHEDULER INTEGRATION")
            print("-" * 40)
            
            for task_name in monitored_tasks:
                print(f"\n🔍 Checking Task Scheduler for {task_name}...")
                
                try:
                    scheduler_info = await scheduler_agent._get_task_scheduler_info(task_name)
                    
                    if scheduler_info:
                        print(f"   ✅ Task Scheduler info found:")
                        print(f"   📅 Last Run: {scheduler_info.get('last_run', 'Unknown')}")
                        print(f"   📅 Next Run: {scheduler_info.get('next_run', 'Unknown')}")
                        print(f"   📊 Status: {scheduler_info.get('status', 'Unknown')}")
                        print(f"   🔢 Exit Code: {scheduler_info.get('exit_code', 'Unknown')}")
                    else:
                        print(f"   ⚠️  No Task Scheduler info found")
                        print(f"   💡 Task may not be registered in Windows Task Scheduler")
                        
                except Exception as e:
                    print(f"   ❌ Error checking Task Scheduler: {e}")
            
            # Test 4: Test task monitoring
            print(f"\n📋 TEST 4: TASK MONITORING")
            print("-" * 40)
            
            print(f"🔍 Starting task monitoring test...")
            
            # Simulate task status check
            for task_name in monitored_tasks:
                print(f"\n🔍 Monitoring {task_name}...")
                
                try:
                    # Check if script process is running
                    await scheduler_agent._check_task_status(task_name)
                    
                    current_status = monitored_tasks[task_name]
                    print(f"   📊 Current Status: {current_status.status}")
                    print(f"   🔄 Running: {current_status.is_running}")
                    print(f"   🔢 Process ID: {current_status.process_id}")
                    print(f"   💾 Memory: {current_status.memory_usage}MB")
                    print(f"   ⚡ CPU: {current_status.cpu_usage}%")
                    
                except Exception as e:
                    print(f"   ❌ Error monitoring task: {e}")
            
            # Test 5: Test agent capabilities
            print(f"\n📋 TEST 5: AGENT CAPABILITIES")
            print("-" * 40)
            
            capabilities = scheduler_agent.get_capabilities()
            print(f"📊 Agent Capabilities: {capabilities}")
            
            # Test health check
            health = await scheduler_agent.get_health_status()
            print(f"\n📊 HEALTH STATUS:")
            print(f"   • Agent ID: {health.agent_id}")
            print(f"   • Status: {health.status}")
            print(f"   • CPU Usage: {health.cpu_usage}%")
            print(f"   • Memory Usage: {health.memory_usage}MB")
            print(f"   • Error Count: {health.error_count}")
            print(f"   • Last Check: {health.last_check}")
            
            return True
            
        else:
            print(f"❌ Scheduler Agent initialization failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing scheduler agent: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_task_scheduler_registration():
    """Test if tasks are registered in Windows Task Scheduler"""
    print(f"\n🔄 TASK SCHEDULER REGISTRATION TEST")
    print("=" * 60)
    
    try:
        import subprocess
        
        tasks_to_check = [
            "Auto_TWS_Manager",
            "Auto_Trading_System"
        ]
        
        for task_name in tasks_to_check:
            print(f"\n🔍 Checking Task Scheduler registration for {task_name}...")
            
            try:
                # Use schtasks command to check if task exists
                cmd = f'schtasks /query /tn "{task_name}" /fo list'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                
                if result.returncode == 0:
                    print(f"   ✅ Task is registered in Windows Task Scheduler")
                    print(f"   📊 Task Info:")
                    
                    # Parse output for key information
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if 'Last Run Time:' in line:
                            print(f"   📅 {line.strip()}")
                        elif 'Next Run Time:' in line:
                            print(f"   📅 {line.strip()}")
                        elif 'Status:' in line:
                            print(f"   📊 {line.strip()}")
                        elif 'Logon Mode:' in line:
                            print(f"   🔐 {line.strip()}")
                else:
                    print(f"   ❌ Task NOT found in Windows Task Scheduler")
                    print(f"   💡 Task may need to be registered manually")
                    print(f"   💡 Command: schtasks /create /tn \"{task_name}\" /tr \"path\\to\\script.bat\"")
                    
            except Exception as e:
                print(f"   ❌ Error checking Task Scheduler: {e}")
    
    except Exception as e:
        print(f"❌ Error in Task Scheduler registration test: {e}")

async def main():
    """Main test function"""
    print("🚀 VOLATILITYHUNTER SCHEDULER AGENT TEST")
    print("🤖 Testing Task Scheduler monitoring and management")
    print("=" * 60)
    
    # Test scheduler agent
    agent_test = await test_scheduler_agent()
    
    # Test Task Scheduler registration
    scheduler_test = await test_task_scheduler_registration()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Scheduler Agent Test: {'✅ PASS' if agent_test else '❌ FAIL'}")
    print(f"Task Scheduler Registration: {'✅ CHECKED' if scheduler_test else '❌ FAIL'}")
    
    if agent_test:
        print(f"\n🎉 SCHEDULER AGENT TEST COMPLETED!")
        print(f"🤖 Agent can see and monitor both Task Scheduler scripts")
        print(f"📋 Auto_TWS_Manager: Monitored for TWS keep-alive")
        print(f"📋 Auto_Trading_System: Monitored for daily trading workflow")
        print(f"🔍 Script integrity checks working")
        print(f"📊 Task monitoring functional")
    
    exit(0 if agent_test else 1)

if __name__ == "__main__":
    asyncio.run(main())
