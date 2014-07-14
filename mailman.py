# coding=utf-8
import smtplib
import logging
from email.mime.text import MIMEText
from utils.credentials_sample import gmail_username, gmail_password, my_name, mail_template

handler = logging.FileHandler("run.log", "a", encoding="UTF-8")
formatter = logging.Formatter("%(levelname)s:%(message)s")
handler.setFormatter(formatter)
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.INFO)

hostname = "smtp.gmail.com"


def email_sender(r_dict):
    try:
        name = u''
        if r_dict['contact_name'] is not None and len(r_dict['contact_name'].split(' ')) == 2 and '.' not in \
                r_dict['contact_name'].split(' ')[1] and len(r_dict['contact_name'].split(' ')[1]) > 2:
            name = u' {0}'.format(r_dict['contact_name'].split(' ')[1])
        link = u'in {0}.'.format(r_dict['link'])
        if r_dict['type'].startswith('WG'):
            link = 'advertised here: {0}'.format(r_dict['link'])
        msg = MIMEText(mail_template.format(name, link, my_name), 'plain', 'utf-8')

        msg["Subject"] = "Renting your room"
        msg["From"] = gmail_username
        msg["To"] = r_dict['email']

        s = smtplib.SMTP_SSL(hostname)
        s.login(gmail_username, gmail_password)
        s.sendmail(gmail_username, [r_dict['email']], msg.as_string())
        s.quit()
    except Exception, e:
        print('Email to {0} failed because of {1}'.format(r_dict.get('email', ''), repr(e)))