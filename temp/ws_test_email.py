#!/usr/bin/env python3
"""
Email Test Script - Test VolatilityHunter email functionality
"""

import sys
import os
import asyncio
from datetime import datetime

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

async def test_email_functionality():
    """Test email sending functionality"""
    print("📧 TESTING EMAIL FUNCTIONALITY")
    print("=" * 50)
    
    try:
        # Import notification agent
        from src.agents.notification.agent import NotificationAgent
        
        # Email configuration
        email_config = {
            "agent_id": "test_email_agent",
            "agent_type": "notification",
            "enabled": True,
            "log_level": "INFO",
            "retry_attempts": 3,
            "timeout": 30.0,
            "max_concurrent_tasks": 3,
            "health_check_interval": 60.0,
            "email_enabled": True,
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "email_sender": "lugassy.ai@gmail.com",
            "email_recipients": ["lugassy.ai@gmail.com"],  # Use real email instead of test@example.com
            "alert_thresholds": {"error_rate": 0.1, "response_time": 5.0, "memory_usage": 0.8}
        }
        
        print(f"📧 Email Configuration:")
        print(f"   • Sender: {email_config['email_sender']}")
        print(f"   • Recipients: {email_config['email_recipients']}")
        print(f"   • SMTP Server: {email_config['smtp_server']}:{email_config['smtp_port']}")
        print(f"   • Email Enabled: {email_config['email_enabled']}")
        
        # Initialize notification agent
        print(f"\n🤖 Initializing Notification Agent...")
        notification_agent = NotificationAgent("test_email_agent", email_config)
        
        if await notification_agent.initialize():
            print(f"✅ Notification Agent initialized successfully")
            
            # Test email sending
            print(f"\n📧 Sending test email...")
            test_subject = f"VolatilityHunter Email Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            test_body = """
This is a test email from VolatilityHunter system.

Test Details:
- Timestamp: {timestamp}
- System: VolatilityHunter Trading System
- Purpose: Email functionality verification
- Status: TEST

If you receive this email, the email system is working correctly!
            """.format(timestamp=datetime.now().isoformat())
            
            # Send test email
            email_result = await notification_agent.send_email(
                recipients=email_config['email_recipients'],
                subject=test_subject,
                body=test_body
            )
            
            if email_result.get('success', False):
                print(f"✅ Email sent successfully!")
                print(f"   • Method: {email_result.get('method', 'Unknown')}")
                print(f"   • Message: {email_result.get('message', 'Email sent')}")
            else:
                print(f"❌ Email failed to send")
                print(f"   • Error: {email_result.get('error', 'Unknown error')}")
                if 'file' in email_result:
                    print(f"   • Fallback file: {email_result['file']}")
            
            # Test email verification
            print(f"\n🔍 Verifying email delivery...")
            delivery_verified = await notification_agent.verify_email_delivery(email_result)
            
            if delivery_verified:
                print(f"✅ Email delivery verified")
            else:
                print(f"⚠️  Email delivery could not be verified")
            
            # Cleanup
            await notification_agent.stop()
            
        else:
            print(f"❌ Notification Agent initialization failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing email functionality: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print(f"\n🎉 Email test completed!")
    return True

def test_email_credentials():
    """Test email credentials directly"""
    print("🔐 TESTING EMAIL CREDENTIALS")
    print("=" * 50)
    
    try:
        import smtplib
        from email.mime.text import MIMEText
        
        # Load credentials from environment
        email_sender = os.getenv('EMAIL_SENDER', 'lugassy.ai@gmail.com')
        email_password = os.getenv('EMAIL_PASSWORD', '')
        
        print(f"📧 Email Credentials:")
        print(f"   • Sender: {email_sender}")
        print(f"   • Password: {'*' * len(email_password) if email_password else 'NOT SET'}")
        
        if not email_password:
            print(f"❌ Email password not found in environment variables")
            return False
        
        # Create test message
        msg = MIMEText(f"Direct SMTP test from VolatilityHunter\nTimestamp: {datetime.now().isoformat()}")
        msg['Subject'] = f"VolatilityHunter SMTP Test - {datetime.now().strftime('%H:%M:%S')}"
        msg['From'] = email_sender
        msg['To'] = email_sender  # Send to self for testing
        
        print(f"\n📧 Testing direct SMTP connection...")
        
        # Connect to Gmail SMTP
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_sender, email_password)
        
        print(f"✅ SMTP connection successful")
        print(f"✅ Authentication successful")
        
        # Send test email
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Test email sent successfully to {email_sender}")
        return True
        
    except Exception as e:
        print(f"❌ SMTP test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 VOLATILITYHUNTER EMAIL SYSTEM TEST")
    print("=" * 60)
    
    # Test 1: Direct SMTP credentials
    print("\n" + "=" * 60)
    smtp_success = test_email_credentials()
    
    # Test 2: Full notification agent
    print("\n" + "=" * 60)
    notification_success = asyncio.run(test_email_functionality())
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 EMAIL TEST SUMMARY")
    print("=" * 60)
    print(f"SMTP Test: {'✅ PASS' if smtp_success else '❌ FAIL'}")
    print(f"Notification Agent Test: {'✅ PASS' if notification_success else '❌ FAIL'}")
    
    if smtp_success and notification_success:
        print(f"\n🎉 ALL EMAIL TESTS PASSED!")
        print(f"📧 Email system is fully functional")
    else:
        print(f"\n⚠️  SOME EMAIL TESTS FAILED")
        print(f"🔧 Check email configuration and credentials")
    
    exit(0 if (smtp_success and notification_success) else 1)
