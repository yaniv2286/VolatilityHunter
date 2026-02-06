"""
Email Notification Module
Sends trading signals via email
"""

import smtplib
import os
import json
import logging
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from dotenv import load_dotenv

logger = logging.getLogger("VolatilityHunter")

class EmailNotifier:
    def __init__(self):
        from dotenv import load_dotenv
        load_dotenv()  # Ensure env vars are loaded
        
        self.config = self._load_config()
        self.sender_email = os.environ.get('SENDER_EMAIL')  # Fixed: Use SENDER_EMAIL
        self.sender_password = os.environ.get('SENDER_PASSWORD')  # Fixed: Use SENDER_PASSWORD
        
        # safely handle recipients
        recipients = self.config.get('EMAIL_RECIPIENTS', [os.environ.get('RECIPIENT_EMAIL')])
        if isinstance(recipients, str):
            self.recipient_email = [recipients]
        else:
            self.recipient_email = recipients

        # --- ROBUST TIME OFFSET PARSING ---
        # The config file might be corrupted with log text.
        # We wrap this in a try/except to default to 0.0 if anything goes wrong.
        try:
            raw_offset = self.config.get('TIME_OFFSET', 0)
            
            # Handle list inputs (e.g. [3])
            if isinstance(raw_offset, list):
                raw_offset = raw_offset[0]
            
            # Clean string
            if isinstance(raw_offset, str):
                # Remove any non-numeric characters except . and -
                import re
                cleaned = re.sub(r'[^\d\.-]', '', raw_offset)
                self.time_offset = float(cleaned) if cleaned else 0.0
            else:
                self.time_offset = float(raw_offset)
                
        except (ValueError, TypeError, AttributeError):
            # If anything goes wrong, default to 0.0
            logger.warning("⚠️ TIME_OFFSET config corrupted, defaulting to 0.0")
            self.time_offset = 0.0

    def _load_config(self):
        """Loads config with fallback."""
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def get_local_time(self):
        """Returns time with the corrected offset."""
        return datetime.utcnow() + timedelta(hours=self.time_offset)

    def send_email(self, subject, body):
        """Standard sender with error catching."""
        if not self.sender_email or not self.sender_password:
            logger.warning("⚠️ Email credentials missing. Skipping email.")
            return

        msg = MIMEMultipart()
        msg['From'] = self.sender_email
        msg['To'] = ", ".join(self.recipient_email)
        msg['Subject'] = f"[VolatilityHunter] {subject}"
        msg.attach(MIMEText(body, 'html'))

        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.sendmail(self.sender_email, self.recipient_email, msg.as_string())
            server.quit()
            logger.info("✅ Email sent successfully.")
        except Exception as e:
            logger.error(f"❌ Failed to send email: {e}")
            # Do NOT crash the app, just log the error
            pass

    def send_comprehensive_scan_results(self, scan_results, summary=None, portfolio_summary=None, executed_trades=None):
        """Formats the daily report."""
        try:
            # Safe defaults if data is missing
            summary = summary or {'buy_signals': 0, 'sell_signals': 0, 'hold_signals': 0}
            portfolio_summary = portfolio_summary or {'total_value': 0, 'daily_pnl': 0}
            
            # Format numbers safely
            total_val = float(portfolio_summary.get('total_value', 0))
            daily_pnl = float(portfolio_summary.get('daily_pnl', 0))
            
            pnl_color = "green" if daily_pnl >= 0 else "red"
            
            html_body = f"""
            <html>
            <body>
                <h2>📊 VolatilityHunter Daily Scan</h2>
                <p><b>Date:</b> {self.get_local_time().strftime('%Y-%m-%d %H:%M')}</p>
                
                <h3>💰 Portfolio Snapshot</h3>
                <ul>
                    <li>Total Value: <b>${total_val:,.2f}</b></li>
                    <li>Daily P&L: <b style="color:{pnl_color}">${daily_pnl:,.2f}</b></li>
                </ul>

                <h3>📡 Scan Results</h3>
                <ul>
                    <li>🟢 BUY Signals: {summary.get('buy_signals')}</li>
                    <li>🔴 SELL Signals: {summary.get('sell_signals')}</li>
                    <li>⚪ HOLD Signals: {summary.get('hold_signals')}</li>
                </ul>
                
                <p><i>System: Version 2.0 (Automated)</i></p>
            </body>
            </html>
            """
            self.send_email(f"Daily Report ({self.get_local_time().strftime('%Y-%m-%d')})", html_body)
            
        except Exception as e:
            logger.error(f"❌ Error constructing email report: {e}")
            import traceback
            logger.error(traceback.format_exc())
