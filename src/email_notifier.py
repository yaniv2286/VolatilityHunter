import smtplib
import os
import json
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from dotenv import load_dotenv

logger = logging.getLogger("VolatilityHunter")

class EmailNotifier:
    def __init__(self):
        load_dotenv()
        self.config = self._load_config()
        self.sender_email = os.environ.get('EMAIL_SENDER')
        self.sender_password = os.environ.get('EMAIL_PASSWORD')
        
        recipients = self.config.get('EMAIL_RECIPIENTS', [])
        if isinstance(recipients, str):
            self.recipient_email = [recipients]
        else:
            self.recipient_email = recipients

        # CRASH PROOF PARSING
        try:
            val = self.config.get('TIME_OFFSET', 0)
            # If corruption detected (string length > 5), force 0
            if isinstance(val, str) and len(val) > 5:
                self.time_offset = 0.0
            else:
                self.time_offset = float(val)
        except:
            self.time_offset = 0.0

    def _load_config(self):
        try:
            path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return json.load(f)
        except:
            return {}
        return {}

    def get_local_time(self):
        return datetime.utcnow() + timedelta(hours=self.time_offset)

    def send_email(self, subject, body):
        if not self.sender_email or not self.sender_password:
            logger.warning("⚠️ Credentials missing. Email not sent.")
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
            logger.error(f"❌ Email failed: {e}")

    def send_comprehensive_scan_results(self, scan_results, summary=None, portfolio_summary=None, executed_trades=None):
        try:
            summary = summary or {}
            portfolio_summary = portfolio_summary or {}
            
            try:
                total_val = float(portfolio_summary.get('total_value', 0))
                daily_pnl = float(portfolio_summary.get('daily_pnl', 0))
            except:
                total_val = 0.0
                daily_pnl = 0.0
            
            pnl_color = "green" if daily_pnl >= 0 else "red"
            
            html_body = f"""
            <html>
            <body>
                <h2>📊 VolatilityHunter Report</h2>
                <p><b>Date:</b> {self.get_local_time().strftime('%Y-%m-%d %H:%M')}</p>
                <h3>💰 Portfolio</h3>
                <ul>
                    <li>Value: <b></b></li>
                    <li>P&L: <b style="color:{pnl_color}"></b></li>
                </ul>
                <h3>📈 Signals</h3>
                <ul>
                    <li>Buy: {summary.get('buy_signals', 0)}</li>
                    <li>Sell: {summary.get('sell_signals', 0)}</li>
                </ul>
            </body>
            </html>
            """
            self.send_email("Daily Report", html_body)
            
        except Exception as e:
            logger.error(f"❌ Report generation failed: {e}")
