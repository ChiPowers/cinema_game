import string
import secrets


def generate_secret_key(n=32):
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return "".join(secrets.choice(alphabet) for i in range(n))
