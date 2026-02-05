"""
Email Notification Module
Sends trading signals via email
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
import os
from src.notifications import log_info, log_error, ensure_ascii
from src.log_collector import LogCollector
from src.trade_verifier import TradeVerifier

class EmailNotifier:
    """Handles email notifications for trading signals."""
    
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.sender_email = os.getenv('SENDER_EMAIL')
        self.sender_password = os.getenv('SENDER_PASSWORD')
        self.recipient_email = os.getenv('RECIPIENT_EMAIL')
        self.log_collector = LogCollector()
        self.trade_verifier = TradeVerifier()
        
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
            
            # Ensure ASCII-only output for Task Scheduler compatibility
            body = ensure_ascii(body)
            
            self._send_email(subject, body)
            log_info(f"Email sent successfully to {self.recipient_email}")
            return True
            
        except Exception as e:
            log_error(f"Failed to send email: {e}")
            return False
    
    def send_comprehensive_scan_results(self, scan_results, summary, portfolio_summary=None, executed_trades=None, attach_log_file=True):
        """
        Send comprehensive scan results with full logs and trade verification.
        
        Args:
            scan_results: Dictionary with BUY, SELL, HOLD signals
            summary: Summary statistics
            portfolio_summary: Portfolio performance metrics (optional)
            executed_trades: Dict with executed trades for verification
            attach_log_file: Whether to attach the full log file
        """
        if not self._validate_config():
            log_error("Email configuration incomplete. Skipping email notification.")
            return False
        
        try:
            # Record expected trades for verification
            timestamp = datetime.now().isoformat()
            self.trade_verifier.record_expected_trades(scan_results, timestamp)
            
            # Verify trades if executed trades provided
            verification_report = ""
            if executed_trades:
                verification_record = self.trade_verifier.verify_executed_trades(executed_trades, timestamp)
                verification_report = self.trade_verifier.get_verification_report()
            
            # Get system logs
            system_logs = self.log_collector.format_logs_for_email(hours=2, max_lines=150)
            error_summary = self.log_collector.get_error_summary(hours=2)
            performance_metrics = self.log_collector.get_performance_metrics(hours=2)
            
            # Update subject to include verification status
            missed_count = len(self.trade_verifier.get_missed_trades_summary(24)['missed_trades'])
            if portfolio_summary:
                return_pct = portfolio_summary['total_return_pct']
                subject = f"VolatilityHunter Scan - {summary['buy_signals']} BUY | Portfolio: {return_pct:+.2f}% | {missed_count} Missed"
            else:
                subject = f"VolatilityHunter Scan - {summary['buy_signals']} BUY | {missed_count} Missed Trades"
            
            body = self._format_comprehensive_email_body(
                scan_results, summary, portfolio_summary, 
                verification_report, system_logs, error_summary, performance_metrics
            )
            
            self._send_email(subject, body, attach_log_file=attach_log_file)
            log_info(f"Comprehensive email sent successfully to {self.recipient_email}")
            return True
            
        except Exception as e:
            log_error(f"Failed to send comprehensive email: {e}")
            return False
    
    def _validate_config(self):
        """Check if email configuration is complete."""
        return all([
            self.sender_email,
            self.sender_password,
            self.recipient_email
        ])
    
    def _format_comprehensive_email_body(self, scan_results, summary, portfolio_summary=None, 
                                    verification_report="", system_logs="", error_summary=None, performance_metrics=None):
        """Format comprehensive scan results with summary only - details in attached log."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        body = f"""
VolatilityHunter Daily Scan Summary
{'='*60}
Scan Date: {timestamp}
Total Stocks Scanned: {summary['total_stocks']}
"""
        
        # Add portfolio performance summary
        if portfolio_summary:
            total_value = portfolio_summary['total_value']
            total_return = portfolio_summary['total_return_pct']
            return_dollars = portfolio_summary['total_return_dollars']
            num_positions = portfolio_summary['num_positions']
            
            body += f"""
[PORTFOLIO] VIRTUAL PORTFOLIO
Total Value: ${total_value:,.2f}
Total Return: ${return_dollars:,.2f} ({total_return:+.2f}%)
Positions: {num_positions}/10
Cash: ${portfolio_summary['cash']:,.2f}
"""
        
        # Add performance metrics summary
        if performance_metrics:
            body += f"""
[SYSTEM] SYSTEM PERFORMANCE
Stocks Scanned: {performance_metrics['stocks_scanned']}
Data Updates: {performance_metrics['data_updated']}
Errors: {performance_metrics['errors']}
Warnings: {performance_metrics['warnings']}
"""
        
        # Add signal summary
        body += f"""
[SIGNALS] SIGNALS SUMMARY
[BUY] BUY Signals:  {summary['buy_signals']}
[SELL] SELL Signals: {summary['sell_signals']}
[HOLD] HOLD Signals: {summary['hold_signals']}
[ERROR] Errors:       {summary['errors']}
"""
        
        # Add top 3 buy signals (brief)
        if scan_results['BUY']:
            buy_signals = sorted(scan_results['BUY'], key=lambda x: x.get('quality_score', 0), reverse=True)
            top_3 = buy_signals[:3]
            
            body += f"\n[TOP] TOP 3 BUY SIGNALS\n"
            body += "-"*40 + "\n"
            
            for i, signal in enumerate(top_3, 1):
                ticker = signal['ticker']
                indicators = signal.get('indicators', {})
                price = indicators.get('price', 0)
                quality = signal.get('quality_score', 0)
                
                body += f"{i}. {ticker}: ${price:.2f} | Quality: {quality:.2f}\n"
        
        # Add sell signals count only
        if scan_results['SELL']:
            body += f"\n[SELL] SELL SIGNALS: {len(scan_results['SELL'])} stocks\n"
        
        # Add verification summary
        if verification_report:
            missed_count = len(self.trade_verifier.get_missed_trades_summary(24)['missed_trades'])
            body += f"\n[VERIFICATION] TRADE VERIFICATION: {missed_count} missed trades\n"
        
        # Add error summary count only
        if error_summary and (error_summary['error_count'] > 0 or error_summary['warning_count'] > 0):
            body += f"\n[ISSUES] ISSUES: {error_summary['error_count']} errors, {error_summary['warning_count']} warnings\n"
        
        # Add note about attached log
        body += f"""
[REPORT] DETAILED REPORT
Complete scan results, all signal details, system logs, and trade verification 
are included in the attached log file: volatility_hunter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log

[EMAIL] EMAIL CONFIGURATION
SMTP: {self.smtp_server}:{self.smtp_port}
Recipient: {self.recipient_email}

{'='*60}
VolatilityHunter - Automated Trading Signal Scanner
Report generated: {timestamp}
"""
        
        # Ensure ASCII-only output for Task Scheduler compatibility
        return ensure_ascii(body)
    
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
[PORTFOLIO] VIRTUAL PORTFOLIO
{'='*60}
Total Value: ${total_value:,.2f}
Total Return: ${return_dollars:,.2f} ({total_return:+.2f}%)
Positions: {num_positions}/10
Cash Available: ${portfolio_summary['cash']:,.2f}

"""
        
        body += f"""
[SUMMARY] SUMMARY
{'='*60}
[BUY] BUY Signals:  {summary['buy_signals']}
[SELL] SELL Signals: {summary['sell_signals']}
[HOLD] HOLD Signals: {summary['hold_signals']}
[ERROR] Errors:       {summary['errors']}

"""
        
        # BUY Signals - Show Top 10 Elite
        if scan_results['BUY']:
            # Sort by quality_score (CAGR) descending
            buy_signals = sorted(scan_results['BUY'], key=lambda x: x.get('quality_score', 0), reverse=True)
            
            total_buys = len(buy_signals)
            top_10 = buy_signals[:10]
            remaining = total_buys - 10
            
            body += f"\n[TOP] TOP 10 ELITE BUYS (from {total_buys} total)\n"
            body += "="*60 + "\n"
            
            for i, signal in enumerate(top_10, 1):
                ticker = signal['ticker']
                indicators = signal.get('indicators', {})
                price = indicators.get('price', 0)
                cagr = indicators.get('cagr', 0)
                stoch_k = indicators.get('stochastic_k', 0)
                quality = signal.get('quality_score', 0)
                
                body += f"\n#{i}. {ticker}: ${price:.2f}\n"
                body += f"    [CAGR] CAGR: {cagr:.2f}% | Stoch K: {stoch_k:.2f}\n"
                body += f"    Quality Score: {quality:.2f}\n"
            
            if remaining > 0:
                body += f"\n\n[CANDIDATES] Other Candidates: +{remaining} additional buy signals\n"
                body += "   (Lower quality scores - review if needed)\n"
        
        # SELL Signals
        if scan_results['SELL']:
            body += f"\n\n[SELL] SELL SIGNALS ({len(scan_results['SELL'])} stocks)\n"
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
    
    def _send_email(self, subject, body, attach_log_file=False):
        """Send email via SMTP with optional log file attachment."""
        msg = MIMEMultipart()
        msg['From'] = self.sender_email
        msg['To'] = self.recipient_email
        msg['Subject'] = subject
        
        # Attach the body
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach log file if requested
        if attach_log_file and os.path.exists(self.log_collector.log_file):
            try:
                with open(self.log_collector.log_file, 'rb') as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                
                encoders.encode_base64(part)
                
                # Create filename with timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"volatility_hunter_{timestamp}.log"
                
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {filename}'
                )
                
                msg.attach(part)
                log_info(f"Attached log file: {filename}")
                
            except Exception as e:
                log_error(f"Failed to attach log file: {e}")
        
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
