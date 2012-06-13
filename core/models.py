from django.db import models

class GoogleProfile(models.Model):
    google_user_id = models.CharField()
    nickname = models.CharField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    security_key = models.CharField()

    def is_authenticated(self):
        return True

    def get_and_delete_messages(self):
        return " "

class emailHooks(models.Model):
    google_user_id = models.CharField()
    recipient = models.CharField()
    script_url = models.EmailField()

class emailPostRequest(models.Model):
    status_code = models.CharField()
    returned_response = models.CharField()
    sender = models.CharField()
    subject = models.CharField()
    google_date = models.CharField()
    created = models.DateTimeField(auto_now = True)
    # to identify which one ;
    google_user_id = models.CharField()
    recipient = models.CharField()
    script_url = models.EmailField()
