
import smtplib
import ssl
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app

class NotificationService:
    @staticmethod
    def send_email(to_email, subject, html_content):
        """
        Sends an email using ZeptoMail SMTP.
        """
        try:
            user = current_app.config.get("ZEPTOMAIL_USER")
            password = current_app.config.get("ZEPTOMAIL_PASSWORD")
            host = "smtp.zeptomail.in"
            port = 465 # SSL
            
            # Since ZeptoMail user is the verified email, used that as From
            sender_email = user if user else "noreply@brandmo.in"

            if not user or not password:
                logging.warning("Skipping Email: ZEPTOMAIL credentials not set.")
                return False

            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = "Call Manager <" + sender_email + ">"
            message["To"] = to_email

            part = MIMEText(html_content, "html")
            message.attach(part)

            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, context=context) as server:
                server.login(user, password)
                server.sendmail(sender_email, to_email, message.as_string())
            
            logging.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logging.error(f"Failed to send email to {to_email}: {e}")
            return False

    @staticmethod
    def send_welcome_notification(name, username, password, expiry_date, email, phone=None):
        """
        Orchestrates sending Welcome Email using the specific HTML template.
        'phone' argument is kept for compatibility but ignored.
        """
        if not email:
            return

        # Format Expiry Date: 05 Dec 2025
        expiry_str = "N/A"
        if expiry_date:
            if hasattr(expiry_date, 'strftime'):
                expiry_str = expiry_date.strftime("%d %b %Y")
            else:
                expiry_str = str(expiry_date)

        # ---------------------------------------------------------
        # EMAIL CONTENT (TEMPLATE)
        # ---------------------------------------------------------
        subject = "Welcome to Call Manager"
        
        # Using the exact template provided
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8" />
  <title>Welcome to Call Manager</title>
  <style>
    body {{ font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px; }}
    .container {{ max-width: 600px; background: white; padding: 25px; border-radius: 10px;
                 box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
    h2 {{ color: #1a73e8; }}
    .details {{ background: #f1f1f1; padding: 15px; border-radius: 8px; margin-top: 15px; }}
    .footer {{ margin-top: 20px; font-size: 13px; color: #777; }}
  </style>
</head>
<body>

  <div class="container">
    <h2>Welcome to Call Manager!</h2>

    <p>Hello <strong>{name}</strong>,</p>

    <p>Your account has been successfully created.</p>

    <div class="details">
      <p><strong>Login Details:</strong></p>
      <p>Username: {username}</p>
      <p>Password: {password}</p>
      <p>Account Expiry Date: {expiry_str}</p>
    </div>

    <p>Please log in and change your password immediately for security.</p>

    <p>Thank you,<br/>The Call Manager Team</p>

    <div class="footer">
      This is an automated email. Please do not reply.
    </div>
  </div>

</body>
</html>
"""

        # ---------------------------------------------------------
        # SEND
        # ---------------------------------------------------------
        NotificationService.send_email(email, subject, html_content)
