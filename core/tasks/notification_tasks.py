import logging
from core.tasks.celery_config import app
from core.tasks.base_task import DLQTask
from core.services.email_service import EmailService

logger = logging.getLogger("TASKS_NOTIFICATIONS")

@app.task(name="core.tasks.notification_tasks.send_otp_email_task", base=DLQTask, bind=True, max_retries=3)
def send_otp_email_task(self, email: str, otp_code: str):
    logger.info(f"📧 [WORKER] Iniciando envío (OTP) para: {email}")
    try:
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eaeaea; border-radius: 10px;">
            <h2 style="color: #4F46E5;">Verificación de Seguridad</h2>
            <p>Hola,</p>
            <p>Has solicitado acceso o realizado una acción crítica. Tu código de verificación es:</p>
            <div style="background-color: #f3f4f6; padding: 15px; text-align: center; font-size: 24px; font-weight: bold; letter-spacing: 5px; border-radius: 5px; margin: 20px 0;">
                {otp_code}
            </div>
            <p style="font-size: 12px; color: #6b7280;">Este código expirará en 15 minutos. Si no fuiste tú, ignora este correo.</p>
        </div>
        """
        return EmailService.enviar(to_email=email, subject="Tu Código de Verificación - Conciliador ERP", html_content=html_content)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=15 * (2 ** self.request.retries))

@app.task(name="core.tasks.notification_tasks.send_magic_link_email_task", base=DLQTask, bind=True, max_retries=3)
def send_magic_link_email_task(self, email: str, magic_link_url: str, empresa_nombre: str):
    logger.info(f"📧 [WORKER] Iniciando envío (Magic Link) para: {email}")
    try:
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eaeaea; border-radius: 10px;">
            <h2 style="color: #4F46E5;">Invitación al Equipo</h2>
            <p>Hola,</p>
            <p>Has sido invitado a colaborar en la empresa <strong>{empresa_nombre}</strong> dentro de Conciliador ERP.</p>
            <p>Haz clic en el siguiente botón para aceptar la invitación y configurar tu acceso. Este enlace es de un solo uso y expirará en 48 horas.</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{magic_link_url}" style="background-color: #4F46E5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">Aceptar Invitación</a>
            </div>
            <p style="font-size: 12px; color: #6b7280;">Si tienes problemas con el botón, copia y pega este enlace en tu navegador:<br><br>{magic_link_url}</p>
        </div>
        """
        return EmailService.enviar(to_email=email, subject=f"Invitación a colaborar en {empresa_nombre} - Conciliador ERP", html_content=html_content)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=15 * (2 ** self.request.retries))

@app.task(name="core.tasks.notification_tasks.send_welcome_email_task", base=DLQTask, bind=True, max_retries=3)
def send_welcome_email_task(self, email: str, empresa_nombre: str):
    logger.info(f"📧 [WORKER] Iniciando envío de Bienvenida para: {email}")
    try:
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eaeaea; border-radius: 10px;">
            <h2 style="color: #4F46E5;">¡Bienvenido a Conciliador ERP!</h2>
            <p>Hola,</p>
            <p>Tu espacio de trabajo para <strong>{empresa_nombre}</strong> ha sido creado exitosamente.</p>
            <p>Ya puedes ingresar al sistema y comenzar a sincronizar tus cuentas y comprobantes.</p>
        </div>
        """
        return EmailService.enviar(to_email=email, subject=f"¡Bienvenido a {empresa_nombre}!", html_content=html_content)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=15 * (2 ** self.request.retries))