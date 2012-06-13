from core.models import GoogleProfile
import string
import random

class GoogleBackend:
    def authenticate(self, request, google_user):
        try:
            prof = GoogleProfile.objects.get(google_user_id=google_user.user_id())
            return prof
        except GoogleProfile.DoesNotExist:
            
            security_key = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(15))

            newprofile = GoogleProfile.objects.create(
                google_user_id = google_user.user_id(),
                nickname = google_user.nickname(),
                email = google_user.email(),
                security_key = security_key)
            newprofile.save()

            return newprofile


    def get_user(self, google_user_id):
        try:
            return GoogleProfile.objects.get(pk=google_user_id)
        except GoogleProfile.DoesNotExist:
            return None
