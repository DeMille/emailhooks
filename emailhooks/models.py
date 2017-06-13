import re
import json
from email.utils import getaddresses, parseaddr

from django.db import models

from google.appengine.api import mail, urlfetch


class GoogleUser(models.Model):
    user_id = models.CharField(unique=True)
    email = models.EmailField()
    key = models.CharField()
    last_login = models.DateTimeField(auto_now=True, null=True)

    def is_authenticated(self):
        return True


class EmailHook(models.Model):
    user_id = models.SlugField(max_length=100)
    recipient = models.SlugField(max_length=100, unique=True)
    destination = models.URLField()


class LogEntry(models.Model):
    user_id = models.CharField()
    recipient = models.CharField()
    destination = models.URLField()
    num_attachments = models.IntegerField()
    size = models.CharField()
    response = models.CharField(default='N/A')
    status_code = models.CharField(default='ERR')
    created = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created']


class Email():
    def __init__(self, body):
        # make email obj from body
        message = mail.InboundEmailMessage(body)

        # list of emails: ['blah@example.com', ...]
        self.to = [a[1] for a in getaddresses([message.to])]
        self.cc = [a[1] for a in getaddresses([getattr(message, 'cc', '')])]

        self.recipient = None

        # check hook recipient in message.to list first
        for addr in self.to:
            if (addr.split('@')[1] == 'emailhooks.xyz'):
                self.recipient = addr.split('@')[0]
                break

        # if not in message.to, parse hook recipient from forwarding
        # details following the patterns:
        # "for <_____ @emailhooks.xyz>" or "for _____ @emailhooks.xyz"
        if (self.recipient is None):
            match = re.search('for <?(\S+)@emailhooks\.xyz', body, re.IGNORECASE)
            self.recipient = match.group(1).lower() if match else None

        self.sender = parseaddr(message.sender)[1]
        self.subject = getattr(message, 'subject', '')
        self.date = message.date

        self.html_body = ''
        for _, body in message.bodies('text/html'):
            self.html_body = body.decode()

        self.plain_body = ''
        for _, plain in message.bodies('text/plain'):
            self.plain_body = plain.decode()

        # Attachments are a list of tuples: (filename, EncodedPayload)
        # EncodedPayloads are likely to be base64
        #
        # EncodedPayload:
        # https://cloud.google.com/appengine/docs/python/refdocs/google.appengine.api.mail#google.appengine.api.mail.EncodedPayload
        #
        self.attachments = []

        for attachment in getattr(message, 'attachments', []):
            encoding = attachment[1].encoding
            payload = attachment[1].payload

            if (not encoding or encoding.lower() != 'base64'):
                payload = attachment[1].decode().encode('base64')

            self.attachments.append({
                'filename': attachment[0],
                'payload': payload
            })

    def payload(self):
        return json.dumps({
            'sender': self.sender,
            'to': self.to,
            'cc': self.cc,
            'date': self.date,
            'subject': self.subject,
            'html_body': self.html_body,
            'plain_body': self.plain_body,
            'attachments': self.attachments
        })
