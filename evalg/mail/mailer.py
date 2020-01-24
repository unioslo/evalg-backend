"""Methods for creating and sending mails from jinja2 templates."""
import email.mime.multipart
import email.mime.text
import email.utils
import smtplib

from flask import current_app
from jinja2 import Environment, PackageLoader


def load_template(template_name):
    """Load all jinja2 email templates."""
    return Environment(
        loader=PackageLoader('evalg.mail',
                             'templates')).get_template(template_name)


def send_mail(
        template_name=None,
        html_template_name=None,
        to_addr=None,
        subject='',
        **kwargs):
    """
    Function for sending emails.

    Minimum one of the templates needs to be defined. If both are defined,
    the plain text will be added as the alternative.

    :param template_name: Filename for the plain text mail jinja2 template
    :param html_template_name: Filename for the html mail jinja2 template
    :param to_addr: To address
    :param subject: Mail subject
    :param kwargs: Parameters used to generate mail from jinja2 templates
    :return: None
    """
    config = current_app.config

    if not template_name or not html_template_name:
        current_app.logger.error('Could not send email, no template given')
        return

    if not to_addr:
        current_app.logger.error('Could not send email, not to_address '
                                 'given')
        return

    if not config.get('MAIL_ENABLE'):
        current_app.logger.info('No mail sent. Mail not enabled. '
                                'To: %s', to_addr)
        return

    smtp_server = config.get('MAIL_SMTP_SERVER')
    smtp_port = config.get('MAIL_SMTP_PORT')

    if template_name and html_template_name:
        msg = email.mime.multipart.MIMEMultipart('alternative')
    else:
        msg = email.mime.multipart.MIMEMultipart()
    msg['From'] = config.get('MAIL_FROM_ADDR')
    msg['To'] = to_addr
    msg['Subject'] = subject
    msg['Date'] = email.utils.formatdate(localtime=True)
    msg['Message-ID'] = email.utils.make_msgid()

    if config.get('MAIL_REPLY_TO_ADDR'):
        msg['Reply-To'] = config.get('MAIL_REPLY_TO_ADDR')

    if template_name:
        text = load_template(template_name).render(**kwargs)
        msg.attach(email.mime.text.MIMEText(text, 'plain'))

    if html_template_name:
        html = load_template(html_template_name).render(**kwargs)
        msg.attach(email.mime.text.MIMEText(html, 'html'))

    with smtplib.SMTP(host=smtp_server, port=smtp_port) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.send_message(msg)

