from extensions import db
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app

class BaseService:
    def __init__(self):
        self.db = db

    def commit(self):
        try:
            self.db.session.commit()
        except SQLAlchemyError as e:
            self.db.session.rollback()
            current_app.logger.error(f'Database error: {str(e)}')
            raise

    def add(self, obj):
        try:
            self.db.session.add(obj)
        except SQLAlchemyError as e:
            current_app.logger.error(f'Error adding object: {str(e)}')
            raise

    def delete(self, obj):
        try:
            self.db.session.delete(obj)
        except SQLAlchemyError as e:
            current_app.logger.error(f'Error deleting object: {str(e)}')
            raise 