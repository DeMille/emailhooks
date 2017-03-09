import random
import string

from ..models import GoogleUser


class GoogleBackend:
    def authenticate(self, google_user):
        if google_user is None:
            return None

        try:
            return GoogleUser.objects.get(user_id=google_user.user_id())
        except GoogleUser.DoesNotExist:
            chars = string.ascii_uppercase + string.digits
            key = ''.join(random.choice(chars) for x in range(20))

            user = GoogleUser.objects.create(
                user_id=google_user.user_id(),
                email=google_user.email(),
                key=key,
            )

            user.save()
            return user

    def get_user(self, user):
        try:
            return GoogleUser.objects.get(id=user)
        except GoogleUser.DoesNotExist:
            return None
