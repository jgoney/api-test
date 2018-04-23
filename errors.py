from flask import jsonify

class ApiError(Exception):
    status_code = 500
    message = "An error has occurred"

    def __init__(self, message, status_code=None):
        super().__init__()

        self.message = message
        if status_code is not None:
            self.status_code = status_code

    def to_dict(self):
        return {'message': self.message}

class InvalidArgumentError(ApiError):

    def __init__(self, value, arg):
        super().__init__('"{}" is not a valid argument for parameter "{}"'.format(value, arg), status_code=500)


class MissingRequireArgumentError(ApiError):

    def __init__(self, arg, url):
        super().__init__('argument "{}" is required for endpoint "{}"'.format(arg, url), status_code=500)


class ObjectNotFoundError(ApiError):

    def __init__(self, oid):
        super().__init__('song_id "{}" not found'.format(oid), status_code=404)

