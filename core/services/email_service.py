import smtplib
import ssl
import logging
from email.message import EmailMessage
from config.config import settings

logger = logging.getLogger("EMAIL_SERVICE")
logger.setLevel(logging.INFO)

class EmailService:
    @staticmethod
    def enviar(to_email: str, subject: str, html_content: str) -> dict:
        smtp_host = settings.SMTP_HOST
        smtp_port = settings.SMTP_PORT
        smtp_user = settings.SMTP_USER
        smtp_pass = settings.SMTP_PASS
        email_from = settings.EMAIL_FROM

        if not smtp_pass:
            logger.warning(f"⚠️ SIMULACIÓN DE CORREO (Falta SMTP_PASS) a {to_email} | Asunto: {subject}")
            return {"status": "simulated", "email": to_email}

        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = email_from
        msg['To'] = to_email
        msg.add_alternative(html_content, subtype='html')

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls(context=context)
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)

            logger.info(f"✅ [EMAIL_SERVICE] Email despachado exitosamente a {to_email}.")
            return {"status": "success", "email": to_email}
        except Exception as exc:
            logger.error(f"❌ [EMAIL_SERVICE] Fallo transitorio al enviar email a {to_email}: {exc}", exc_info=True)
            raise