
import smtplib
import ssl
import requests
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
            sender_email = "noreply@brandmo.in"
            user = current_app.config.get("ZEPTOMAIL_USER")
            password = current_app.config.get("ZEPTOMAIL_PASSWORD")
            host = "smtp.zeptomail.in"
            port = 465

            if not user or not password:
                logging.warning("Skipping Email: ZEPTOMAIL credentials not set.")
                return False

            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = sender_email
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
    def send_sms(phone, message_text):
        """
        Sends SMS using the configured provider API.
        Assumes a generic GET/POST structure. 
        """
        try:
            api_url = current_app.config.get("SMS_API_URL")
            api_key = current_app.config.get("SMS_API_KEY")

            if not api_url or not api_key:
                logging.warning("Skipping SMS: SMS_API_URL or SMS_API_KEY not set.")
                return False

            # Placeholder logic - User needs to verify parameter names
            # Common pattern: ?apikey=KEY&mobile=PHONE&message=TEXT
            # Or JSON body
            
            # Implementation assuming GET request generic structure often used by Indian SMS providers
            # We try to accommodate common params or expect user to adjust.
            # Using query params for safety as it's common.
            
            params = {
                "apikey": api_key,
                "mobile": phone,
                "message": message_text,
                "sender": "BRANDMO" # Placeholder sender ID, user might need to change
            }
            
            # If the URL already has some params, requests handles it well.
            resp = requests.get(api_url, params=params, timeout=10)
            
            if resp.status_code >= 200 and resp.status_code < 300:
                logging.info(f"SMS sent successfully to {phone}")
                return True
            else:
                logging.error(f"SMS failed: {resp.status_code} - {resp.text}")
                return False

        except Exception as e:
            logging.error(f"Failed to send SMS to {phone}: {e}")
            return False

    @staticmethod
    def send_welcome_notification(name, username, password, expiry_date, phone, email):
        """
        Orchestrates sending Welcome Email and SMS.
        """
        # Ensure expiry_date is a string
        if hasattr(expiry_date, 'strftime'):
            expiry_str = expiry_date.strftime("%d %b %Y")
        else:
            expiry_str = str(expiry_date)

        # ---------------------------------------------------------
        # 1. EMAIL CONTENT
        # ---------------------------------------------------------
        subject = "Welcome to BrandMo - Your Account Details"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
                <h2 style="color: #0066cc;">Welcome to BrandMo!</h2>
                <p>Hello <strong>{name}</strong>,</p>
                <p>Your account has been successfully created. Here are your login credentials:</p>
                
                <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>Username:</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #eee;">{username}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>Password:</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #eee;">{password}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>Account Expiry:</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #eee;">{expiry_str}</td>
                    </tr>
                </table>

                <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin-top: 20px;">
                    <p style="margin: 0; font-size: 14px; color: #666;">
                        <strong>Important:</strong> For security reasons, please change your password immediately after your first login.
                    </p>
                </div>

                <p style="margin-top: 30px;">Best Regards,<br>Team BrandMo</p>
            </div>
        </body>
        </html>
        """

        # ---------------------------------------------------------
        # 2. SMS CONTENT
        # ---------------------------------------------------------
        # Keep it short/professional
        sms_text = (
            f"Welcome to BrandMo! "
            f"Hello {name}, your account is created. "
            f"User: {username} "
            f"Pass: {password} "
            f"Expiry: {expiry_str} "
            f"Pls change pass after login."
        )

        # ---------------------------------------------------------
        # 3. SEND
        # ---------------------------------------------------------
        # Send Email
        if email:
            NotificationService.send_email(email, subject, html_content)
        
        # Send SMS (if phone provided)
        if phone:
            NotificationService.send_sms(phone, sms_text)
