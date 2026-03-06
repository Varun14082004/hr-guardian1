import smtplib
from email.mime.text import MIMEText
from config import SENDER_EMAIL, APP_PASSWORD

def send_email(to_email, subject, message):
    """
    Sends an email using the credentials from the config file.
    """
    if not SENDER_EMAIL or SENDER_EMAIL == "your_email_here@gmail.com":
        print("---")
        print("EMAIL NOT SENT: Please configure your email credentials in config.py")
        print("---")
        return False

    try:
        msg = MIMEText(message)
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.send_message(msg)
        
        print(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"---")
        print(f"FAILED TO SEND EMAIL: {e}")
        print("---")
        return False
