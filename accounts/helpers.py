import random
from django.core.mail import send_mail
from django.conf import settings


def send_confirmation_email(email, code):
    send_mail(
        'Код подтверждения',
        f'Ваш код подтверждения: {code}',
        settings.DEFAULT_FROM_EMAIL,[email],fail_silently=False,)

def make_confirmation_code():
    return str(random.randint(100000, 999999))
