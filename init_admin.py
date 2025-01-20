from models import User
from extensions import db, bcrypt

def init_admin(app):
    """Initialize the primary admin user if it doesn't exist."""
    with app.app_context():
        # Check if primary admin exists
        admin = User.query.filter_by(is_primary_admin=True).first()
        if not admin:
            # Create primary admin
            hashed_password = bcrypt.generate_password_hash('admin123').decode('utf-8')
            admin = User(
                email='admin@example.com',
                password=hashed_password,
                role='admin',
                is_primary_admin=True
            )
            db.session.add(admin)
            try:
                db.session.commit()
                print('Primary admin created successfully')
            except Exception as e:
                db.session.rollback()
                print(f'Error creating primary admin: {str(e)}')

if __name__ == '__main__':
    from app import create_app
    app = create_app()
    init_admin(app) 