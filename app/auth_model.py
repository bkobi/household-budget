from flask_login import UserMixin


class User(UserMixin):
    def __init__(self, id: int, username: str):
        self.id       = id
        self.username = username
