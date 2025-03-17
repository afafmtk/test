import os
import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

class EmailSender:
    def __init__(self, sender_email, sender_password):
        
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587  # Port pour TLS

    def send_email(self, recipient_email, subject, body, attachment_path=None):
        
        msg = MIMEMultipart()
        msg['From'] = self.sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Ajouter une pièce jointe si un fichier est fourni
        if attachment_path:
            if os.path.exists(attachment_path):
                with open(attachment_path, 'rb') as file:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(file.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(attachment_path)}')
                    msg.attach(part)
            else:
                print(f"⚠️ Le fichier {attachment_path} n'existe pas. Email envoyé sans pièce jointe.")

        # Envoi de l’email via SMTP
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            print(f"✅ Email envoyé avec succès à {recipient_email} !")
        except Exception as e:
            print(f"❌ Erreur lors de l'envoi de l'email : {e}")


    def send_feedback_email(self, recipient_email, filepath):
        if os.path.exists(filepath):
            subject = f"Feedbacks de votre session {os.path.basename(filepath)}"
            body = "Veuillez trouver ci-joint le fichier contenant les feedbacks de votre session."
            self.send_email(recipient_email, subject, body, filepath)
        else:
            print("⚠️ Fichier feedback non trouvé, email non envoyé.")


    def send_error_email(self, recipient_email, error_message):
        subject = "🚨 Erreur dans LAW_GPT"
        body = f"Une erreur est survenue dans l'application :\n\n{error_message}"
        self.send_email(recipient_email, subject, body)

