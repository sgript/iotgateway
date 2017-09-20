#;policy

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pymysql
import sys
sys.path.append("..")

import policy_database

class Alert:
    def __init__(self, database):
        email_config = database.get_email_config()

        self.MY_ADDRESS = email_config[0][1]
        self.PASSWORD = email_config[0][2]
        self.database_emails = database.get_admin_emails()

        self.s = smtplib.SMTP(host = email_config[0][3], port = email_config[0][4])
        self.s.starttls()
        self.s.login(self.MY_ADDRESS, self.PASSWORD)

        self.emails = ["s94ahmad@gmail.com", "ahmads18@cardiff.ac.uk"]


    def to_administrators(self, function, uuid, channel):
        for email in self.database_emails:
            msg = MIMEMultipart()
            message = "The canary function {} was ran by {} on channel at {}!".format(function, uuid, channel)

            msg['From'] = self.MY_ADDRESS
            msg['To'] = email[1]
            msg['Subject'] = "This is TEST"

            msg.attach(MIMEText(message, 'plain'))

            self.s.send_message(msg)
            del msg

        self.s.quit()

    def email_config(self):
        pass

if __name__ == '__main__':

    pd = policy_database.PolicyDatabase('ephesus.cs.cf.ac.uk', 'c1312433', 'berlin', 'c1312433')
    alert = Alert(pd)
    alert.to_administrators('myFunc', 'someUUID', 'someChannel')
