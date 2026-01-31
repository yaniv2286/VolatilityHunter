"""
Email Notification Module
Sends trading signals via email
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
from src.notifications import log_info, log_error

class EmailNotifier:
    """Handles email notifications for trading signals."""
    
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.sender_email = os.getenv('SENDER_EMAIL')
        self.sender_password = os.getenv('SENDER_PASSWORD')
        self.recipient_email = os.getenv('RECIPIENT_EMAIL')
        
    def send_scan_results(self, scan_results, summary, portfolio_summary=None):
        """
        Send scan results via email.
        
        Args:
            scan_results: Dictionary with BUY, SELL, HOLD signals
            summary: Summary statistics
            portfolio_summary: Portfolio performance metrics (optional)
        """
        if not self._validate_config():
            log_error("Email configuration incomplete. Skipping email notification.")
            return False
        
        try:
            # Update subject to include portfolio performance
            if portfolio_summary:
                return_pct = portfolio_summary['total_return_pct']
                subject = f"VolatilityHunter Daily Scan - {summary['buy_signals']} BUY Signals | Portfolio: {return_pct:+.2f}%"
            else:
                subject = f"VolatilityHunter Daily Scan - {summary['buy_signals']} BUY Signals"
            
            body = self._format_email_body(scan_results, summary, portfolio_summary)
            
            self._send_email(subject, body)
            log_info(f"Email sent successfully to {self.recipient_email}")
            return True
            
        except Exception as e:
            log_error(f"Failed to send email: {e}")
            return False
    
    def _validate_config(self):
        """Check if email configuration is complete."""
        return all([
            self.sender_email,
            self.sender_password,
            self.recipient_email
        ])
    
    def _format_email_body(self, scan_results, summary, portfolio_summary=None):
        """Format scan results into email body."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        body = f"""
VolatilityHunter Daily Scan Results
{'='*60}
Scan Date: {timestamp}
Total Stocks Scanned: {summary['total_stocks']}
"""
        
        # Add portfolio performance header
        if portfolio_summary:
            total_value = portfolio_summary['total_value']
            total_return = portfolio_summary['total_return_pct']
            return_dollars = portfolio_summary['total_return_dollars']
            num_positions = portfolio_summary['num_positions']
            
            body += f"""
💰 VIRTUAL PORTFOLIO
{'='*60}
Total Value: ${total_value:,.2f}
Total Return: ${return_dollars:,.2f} ({total_return:+.2f}%)
Positions: {num_positions}/10
Cash Available: ${portfolio_summary['cash']:,.2f}

"""
        
        body += f"""
SUMMARY
{'='*60}
🟢 BUY Signals:  {summary['buy_signals']}
🔴 SELL Signals: {summary['sell_signals']}
⚪ HOLD Signals: {summary['hold_signals']}
❌ Errors:       {summary['errors']}

"""
        
        # BUY Signals - Show Top 10 Elite
        if scan_results['BUY']:
            # Sort by quality_score (CAGR) descending
            buy_signals = sorted(scan_results['BUY'], key=lambda x: x.get('quality_score', 0), reverse=True)
            
            total_buys = len(buy_signals)
            top_10 = buy_signals[:10]
            remaining = total_buys - 10
            
            body += f"\n🏆 TOP 10 ELITE BUYS (from {total_buys} total)\n"
            body += "="*60 + "\n"
            
            for i, signal in enumerate(top_10, 1):
                ticker = signal['ticker']
                indicators = signal.get('indicators', {})
                price = indicators.get('price', 0)
                cagr = indicators.get('cagr', 0)
                stoch_k = indicators.get('stochastic_k', 0)
                quality = signal.get('quality_score', 0)
                
                body += f"\n#{i}. {ticker}: ${price:.2f}\n"
                body += f"    📈 CAGR: {cagr:.2f}% | Stoch K: {stoch_k:.2f}\n"
                body += f"    Quality Score: {quality:.2f}\n"
            
            if remaining > 0:
                body += f"\n\n📋 Other Candidates: +{remaining} additional buy signals\n"
                body += "   (Lower quality scores - review if needed)\n"
        
        # SELL Signals
        if scan_results['SELL']:
            body += f"\n\n🔴 SELL SIGNALS ({len(scan_results['SELL'])} stocks)\n"
            body += "="*60 + "\n"
            for signal in scan_results['SELL']:
                ticker = signal['ticker']
                indicators = signal.get('indicators', {})
                price = indicators.get('price', 0)
                
                body += f"\n{ticker}: ${price:.2f}\n"
                body += f"  Reason: {signal.get('reason', 'N/A')}\n"
        
        # Footer
        body += f"\n\n{'='*60}\n"
        body += "VolatilityHunter - Automated Trading Signal Scanner\n"
        body += f"Powered by Yahoo Finance | {summary['total_stocks']} stocks monitored\n"
        
        return body
    
    def _send_email(self, subject, body):
        """Send email via SMTP."""
        msg = MIMEMultipart()
        msg['From'] = self.sender_email
        msg['To'] = self.recipient_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.send_message(msg)
    
    def send_test_email(self):
        """Send a test email to verify configuration."""
        try:
            subject = "VolatilityHunter - Test Email"
            body = f"""
This is a test email from VolatilityHunter.

Configuration:
- SMTP Server: {self.smtp_server}:{self.smtp_port}
- Sender: {self.sender_email}
- Recipient: {self.recipient_email}

If you received this email, your email notifications are configured correctly!

Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            self._send_email(subject, body)
            log_info("Test email sent successfully!")
            return True
        except Exception as e:
            log_error(f"Test email failed: {e}")
            return False
