from app import create_app, db
from models import User
from extensions import bcrypt

def check_and_fix_admin():
    app = create_app()
    with app.app_context():
        # Check if admin exists
        admin = User.query.filter_by(email='admin@admin.com').first()
        
        if admin:
            print("Admin user exists!")
            # Update admin password
            admin.password = bcrypt.generate_password_hash('admin123').decode('utf-8')
            admin.role = 'admin'
            admin.is_primary_admin = True
            db.session.commit()
            print("Admin password has been reset to: admin123")
        else:
            print("Admin user does not exist, creating...")
            # Create new admin
            new_admin = User(
                email='admin@admin.com',
                password=bcrypt.generate_password_hash('admin123').decode('utf-8'),
                role='admin',
                is_primary_admin=True
            )
            db.session.add(new_admin)
            db.session.commit()
            print("New admin user created!")
        
        print("\nAdmin credentials:")
        print("Email: admin@admin.com")
        print("Password: admin123")

if __name__ == '__main__':
    check_and_fix_admin() 