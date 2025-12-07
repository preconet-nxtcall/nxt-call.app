
import logging
from flask import current_app

class NotificationService:
    @staticmethod
    def send_email(to_email, subject, html_content):
        """
        Sends an email using ZeptoMail HTTP API.
        """
        try:
            import requests
            
            api_token = current_app.config.get("ZEPTOMAIL_API_TOKEN")
            sender_email = current_app.config.get("ZEPTOMAIL_USER")
            
            if not api_token or not sender_email:
                logging.warning("Skipping Email: ZEPTOMAIL credentials not set.")
                return False

            url = "https://api.zeptomail.in/v1.1/email"
            
            payload = {
                "from": {
                    "address": sender_email
                },
                "to": [{
                    "email_address": {
                        "address": to_email,
                        "name": to_email.split('@')[0]
                    }
                }],
                "subject": subject,
                "htmlbody": html_content
            }
            
            headers = {
                "accept": "application/json",
                "content-type": "application/json",
                "authorization": api_token
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            
            if response.status_code == 200:
                logging.info(f"Email sent successfully to {to_email}")
                return True
            else:
                logging.error(f"Failed to send email to {to_email}: {response.status_code} - {response.text}")
                return False

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
        return NotificationService.send_email(email, subject, html_content)
