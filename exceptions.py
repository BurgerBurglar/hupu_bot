from requests.exceptions import RequestException


class PostsDeletedException(RequestException):
    """Post has been deleted"""


class AccountBannedException(RequestException):
    """Account has been banned in this sub"""
