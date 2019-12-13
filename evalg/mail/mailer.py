"""Methods for creating and sending mails from jinja2 templates."""
import email.mime.multipart
import email.mime.text
import email.utils
import smtplib

from flask import current_app
from jinja2 import Environment, PackageLoader
from sentry_sdk import capture_exception


def load_template(template_name):
    """Load all jinja2 email templates."""
    return Environment(
            loader=PackageLoader('evalg.mail',
                                 'templates')).get_template(template_name)


def send_mail(template_name, subject, **kwargs):
    """Send a jinja2 template email."""
    config = current_app.config
    to_addr = kwargs.get('to_addr')

    if not config.get('MAIL_ENABLE'):
        current_app.info('No mail sent. Mail not enabled. '
                         'To: %s', to_addr)
        return

    smtp_server = config.get('MAIL_SMTP_SERVER')
    smtp_port = config.get('MAIL_SMTP_PORT')

    msg = email.mime.multipart.MIMEMultipart()
    msg['From'] = config.get('MAIL_FROM_ADDR')
    msg['To'] = to_addr
    msg['Subject'] = subject
    msg['Date'] = email.utils.formatdate(localtime=True)
    msg['Message-ID'] = email.utils.make_msgid()

    if config.get('MAIL_REPLY_TO_ADDR'):
        msg['Reply-To'] = config.get('MAIL_REPLY_TO_ADDR')

    text = load_template(template_name).render(**kwargs)
    msg.attach(email.mime.text.MIMEText(text))

    with smtplib.SMTP(host=smtp_server, port=smtp_port) as smtp:
        smtp.ehlo()
        try:
            smtp.starttls()
        except smtplib.SMTPNotSupportedError as e:
            current_app.logger.warning('Smtp server does not support tls %s',
                                       smtp_server)
            capture_exception(e)
        try:
            smtp.send_message(msg, 'noreply@uio.no', to_addr)
        except smtplib.SMTPRecipientsRefused as e:
            current_app.logger.error('SMTP error. Could not send email to '
                                     'the address: %s', to_addr)
            capture_exception(e)

        except smtplib.SMTPSenderRefused as e:
            current_app.logger.error('SMTP error. From address not allowed '
                                     'by server. %s', to_addr)
            capture_exception(e)
