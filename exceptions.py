from requests.exceptions import RequestException


class PostDeletedException(RequestException):
    """Post has been deleted"""


class AccountBannedException(RequestException):
    """Account has been banned in this sub"""


class PageCountNotMatchException(Exception):
    """Page count on sub site not matching actual number of pages"""

    def __init__(self, page_count: int) -> None:
        self.page_count = page_count
