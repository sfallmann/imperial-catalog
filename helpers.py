import random, string
from flask import session


def logged_on():
    if 'email' in session:
        return True
    else:
        return False


def random_string():
    return ''.join(random.choice(string.ascii_uppercase + string.digits)
            for x in xrange(32))
