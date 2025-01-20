from flask import jsonify
from werkzeug.http import HTTP_STATUS_CODES

class APIError(Exception):
    """Bazowa klasa dla błędów API"""
    def __init__(self, message, status_code=400, payload=None):
        super().__init__()
        self.message = message
        self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        rv['status'] = self.status_code
        rv['error'] = HTTP_STATUS_CODES.get(self.status_code, 'Unknown error')
        return rv

class ValidationError(APIError):
    """Błąd walidacji danych"""
    def __init__(self, message):
        super().__init__(message, status_code=422)

class NotFoundError(APIError):
    """Błąd - zasób nie znaleziony"""
    def __init__(self, message):
        super().__init__(message, status_code=404)

class AuthenticationError(APIError):
    """Błąd uwierzytelniania"""
    def __init__(self, message):
        super().__init__(message, status_code=401)

class AuthorizationError(APIError):
    """Błąd autoryzacji"""
    def __init__(self, message):
        super().__init__(message, status_code=403)

class DatabaseError(APIError):
    """Błąd bazy danych"""
    def __init__(self, message):
        super().__init__(message, status_code=500)

class ConfigurationError(APIError):
    """Błąd konfiguracji"""
    def __init__(self, message):
        super().__init__(message, status_code=500)

def init_error_handlers(app):
    """Inicjalizacja obsługi błędów dla aplikacji"""
    
    @app.errorhandler(APIError)
    def handle_api_error(error):
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response

    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({
            'status': 404,
            'error': 'Not Found',
            'message': 'Żądany zasób nie został znaleziony'
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'status': 500,
            'error': 'Internal Server Error',
            'message': 'Wystąpił wewnętrzny błąd serwera'
        }), 500

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            'status': 405,
            'error': 'Method Not Allowed',
            'message': 'Metoda nie jest dozwolona dla tego zasobu'
        }), 405

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'status': 400,
            'error': 'Bad Request',
            'message': 'Nieprawidłowe żądanie'
        }), 400 