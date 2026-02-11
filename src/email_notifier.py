import smtplib
import os
import json
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
from dotenv import load_dotenv

logger = logging.getLogger("VolatilityHunter")

class EmailNotifier:
    def __init__(self):
        load_dotenv()
        self.config = self._load_config()
        self.sender_email = os.environ.get('EMAIL_SENDER')
        self.sender_password = os.environ.get('EMAIL_PASSWORD')
        
        # Safe Recipient Loading
        recipients = self.config.get('EMAIL_RECIPIENTS', [])
        if isinstance(recipients, str):
            self.recipient_email = [recipients]
        else:
            self.recipient_email = recipients

        # BULLETPROOF TIME OFFSET PARSING
        try:
            raw = self.config.get('TIME_OFFSET', 0)
            if isinstance(raw, str) and (len(raw) > 5 or "Volatility" in raw):
                self.time_offset = 0.0
            elif isinstance(raw, list):
                self.time_offset = float(raw[0])
            else:
                self.time_offset = float(raw)
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

    def get_daily_log_file(self) -> str:
        """Get the daily log file path"""
        today = datetime.now().strftime('%Y-%m-%d')
        return f"logs/VH_{today}.log"
    
    def send_email(self, subject: str, body: str, attachment_path: str = None) -> bool:
        """Send email with optional file attachment"""
        if not self.sender_email or not self.sender_password:
            logger.warning("⚠️ Credentials missing. Email not sent.")
            return False

        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = ", ".join(self.recipient_email)
            msg['Subject'] = f"[VolatilityHunter] {subject}"
            
            # Attach HTML body
            msg.attach(MIMEText(body, 'html'))
            
            # Add attachment if provided
            if attachment_path and os.path.exists(attachment_path):
                try:
                    # CRITICAL FIX: Flush logs to ensure everything is written to disk before emailing
                    import logging
                    for handler in logging.getLogger().handlers:
                        handler.flush()
                    
                    with open(attachment_path, 'rb') as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())
                    
                    encoders.encode_base64(part)
                    
                    filename = os.path.basename(attachment_path)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {filename}'
                    )
                    
                    msg.attach(part)
                    logger.info(f"Attached file: {filename}")
                    
                except Exception as attach_error:
                    logger.warning(f"Failed to attach file {attachment_path}: {attach_error}")
                    # Continue without attachment - email still useful
            
            # Send email
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.sendmail(self.sender_email, self.recipient_email, msg.as_string())
            server.quit()
            
            logger.info("✅ Email sent successfully.")
            return True
            
        except Exception as e:
            logger.error(f"❌ Email failed: {e}")
            return False

    # THE FIX: Added 'attach_log_file' argument to handle the call from main.py
    def send_comprehensive_scan_results(self, scan_results, summary=None, portfolio_summary=None, executed_trades=None, attach_log_file=False):
        try:
            summary = summary or {}
            portfolio_summary = portfolio_summary or {}
            executed_trades = executed_trades or {}
            
            # Extract detailed trade log
            detailed_trade_log = executed_trades.get('detailed_trade_log', [])
            
            try:
                total_val = float(portfolio_summary.get('total_value', 0))
                daily_pnl = float(portfolio_summary.get('daily_pnl', 0))
                total_return_dollars = float(portfolio_summary.get('total_return_dollars', 0))
                total_return_pct = float(portfolio_summary.get('total_return_pct', 0))
                cash = float(portfolio_summary.get('cash', 0))
                num_positions = int(portfolio_summary.get('num_positions', 0))
            except:
                total_val = 0.0
                daily_pnl = 0.0
                total_return_dollars = 0.0
                total_return_pct = 0.0
                cash = 0.0
                num_positions = 0
            
            pnl_color = "green" if daily_pnl >= 0 else "red"
            return_color = "green" if total_return_dollars >= 0 else "red"
            
            # Build HTML sections
            html_body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .header {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                    .section {{ margin-bottom: 25px; }}
                    .metric {{ display: inline-block; margin: 10px 20px 10px 0; }}
                    .metric-label {{ font-weight: bold; color: #666; }}
                    .metric-value {{ font-size: 18px; font-weight: bold; }}
                    table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; font-weight: bold; }}
                    .buy {{ color: #28a745; font-weight: bold; }}
                    .sell {{ color: #dc3545; font-weight: bold; }}
                    .positive {{ color: #28a745; }}
                    .negative {{ color: #dc3545; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h2>VolatilityHunter Daily Report</h2>
                    <p><b>Date:</b> {self.get_local_time().strftime('%Y-%m-%d %H:%M')}</p>
                    <p><b>Mode:</b> {portfolio_summary.get('execution_mode', 'PAPER').upper()}</p>
                </div>
                
                <div class="section">
                    <h3>Executive Summary</h3>
                    <div class="metric">
                        <div class="metric-label">Portfolio Value</div>
                        <div class="metric-value">${total_val:,.2f}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Total Return</div>
                        <div class="metric-value" style="color: {return_color}">${total_return_dollars:,.2f} ({total_return_pct:+.2f}%)</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Available Cash</div>
                        <div class="metric-value">${cash:,.2f}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Positions</div>
                        <div class="metric-value">{num_positions}/10</div>
                    </div>
                </div>
                
                <div class="section">
                    <h3>Market Activity</h3>
                    <div class="metric">
                        <div class="metric-label">Buy Signals</div>
                        <div class="metric-value">{summary.get('buy_signals', 0)}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Sell Signals</div>
                        <div class="metric-value">{summary.get('sell_signals', 0)}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Hold Signals</div>
                        <div class="metric-value">{summary.get('hold_signals', 0)}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Trades Executed</div>
                        <div class="metric-value">{len(detailed_trade_log)}</div>
                    </div>
                </div>
            """
            
            # Section 2: Today's Activity Table
            html_body += """
                <div class="section">
                    <h3>Today's Trading Activity</h3>
            """
            
            if detailed_trade_log:
                html_body += """
                    <table>
                        <tr>
                            <th>Time</th>
                            <th>Ticker</th>
                            <th>Action</th>
                            <th>Price</th>
                            <th>Shares</th>
                            <th>Value</th>
                            <th>Rationale</th>
                        </tr>
                """
                
                for trade in detailed_trade_log:
                    action_class = "buy" if trade['action'] == 'BUY' else "sell"
                    html_body += f"""
                        <tr>
                            <td>{trade['time']}</td>
                            <td>{trade['ticker']}</td>
                            <td class="{action_class}">{trade['action']}</td>
                            <td>${trade['price']:.2f}</td>
                            <td>{trade['shares']:.2f}</td>
                            <td>${trade['value']:.2f}</td>
                            <td>{trade['reason']}</td>
                        </tr>
                    """
                
                html_body += "</table>"
            else:
                html_body += "<p><i>No trading activity today.</i></p>"
            
            # Section 3: Current Portfolio Table
            html_body += """
                </div>
                <div class="section">
                    <h3>Current Portfolio Holdings</h3>
            """
            
            positions_detail = portfolio_summary.get('positions_detail', [])
            if positions_detail:
                html_body += """
                    <table>
                        <tr>
                            <th>Ticker</th>
                            <th>Shares</th>
                            <th>Cost Basis</th>
                            <th>Current Price</th>
                            <th>Market Value</th>
                            <th>Gain/Loss</th>
                            <th>Gain/Loss %</th>
                        </tr>
                """
                
                for pos in positions_detail:
                    pl_color = "positive" if pos['unrealized_pl'] >= 0 else "negative"
                    html_body += f"""
                        <tr>
                            <td>{pos['ticker']}</td>
                            <td>{pos['shares']:.2f}</td>
                            <td>${pos['entry_price']:.2f}</td>
                            <td>${pos['current_price']:.2f}</td>
                            <td>${pos['value']:.2f}</td>
                            <td class="{pl_color}">${pos['unrealized_pl']:+,.2f}</td>
                            <td class="{pl_color}">{pos['unrealized_pl_pct']:+.2f}%</td>
                        </tr>
                    """
                
                html_body += "</table>"
            else:
                html_body += "<p><i>No positions currently held.</i></p>"
            
            html_body += """
                </div>
            </body>
            </html>
            """
            
            # Determine attachment path
            attachment_path = None
            if attach_log_file:
                attachment_path = self.get_daily_log_file()
            
            return self.send_email("Daily Report", html_body, attachment_path)
            
        except Exception as e:
            logger.error(f"❌ Report generation failed: {e}")
            return False
