#!/usr/bin/env python3
"""
Test all 7 agents to verify they're working
"""

import sys
import os
import asyncio

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import testing.agents_tests.test_data_agent
import testing.agents_tests.test_strategy_agent
import testing.agents_tests.test_testing_agent
import testing.agents_tests.test_execution_agent
import testing.agents_tests.test_sync_agent
import testing.agents_tests.test_notification_agent
import testing.agents_tests.test_scheduler_agent

async def run_tests():
    print('Testing all 7 agents...')
    print('=' * 50)
    
    # Test Data Agent
    print('Testing Data Agent...')
    result1 = await testing.agents_tests.test_data_agent.main()
    print(f'Data Agent: {"PASS" if result1 else "FAIL"}')
    
    # Test Strategy Agent
    print('Testing Strategy Agent...')
    result2 = await testing.agents_tests.test_strategy_agent.main()
    print(f'Strategy Agent: {"PASS" if result2 else "FAIL"}')
    
    # Test Testing Agent
    print('Testing Testing Agent...')
    result3 = await testing.agents_tests.test_testing_agent.main()
    print(f'Testing Agent: {"PASS" if result3 else "FAIL"}')
    
    # Test Execution Agent
    print('Testing Execution Agent...')
    result4 = await testing.agents_tests.test_execution_agent.main()
    print(f'Execution Agent: {"PASS" if result4 else "FAIL"}')
    
    # Test Sync Agent
    print('Testing Sync Agent...')
    result5 = await testing.agents_tests.test_sync_agent.main()
    print(f'Sync Agent: {"PASS" if result5 else "FAIL"}')
    
    # Test Notification Agent
    print('Testing Notification Agent...')
    result6 = await testing.agents_tests.test_notification_agent.main()
    print(f'Notification Agent: {"PASS" if result6 else "FAIL"}')
    
    # Test Scheduler Agent
    print('Testing Scheduler Agent...')
    result7 = await testing.agents_tests.test_scheduler_agent.main()
    print(f'Scheduler Agent: {"PASS" if result7 else "FAIL"}')
    
    print('=' * 50)
    passed = sum([result1, result2, result3, result4, result5, result6, result7])
    print(f'Total: {passed}/7 agents passed ({passed/7*100:.1f}%)')
    
    if passed == 7:
        print('🎉 ALL AGENTS WORKING!')
    else:
        print(f'⚠️  {7-passed} agents failed')
    
    return passed == 7

if __name__ == "__main__":
    result = asyncio.run(run_tests())
    print(f'\nAll agents working: {result}')
    exit(0 if result else 1)
