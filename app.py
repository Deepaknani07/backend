import re
import secrets
from datetime import datetime, timedelta

from flask import Flask, request, jsonify, session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from models import db, Admin, Opportunity, PasswordResetToken


app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
CORS(app, supports_credentials=True)

with app.app_context():
    db.create_all()


def is_valid_email(email: str) -> bool:
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email))


def logged_in_admin_id():
    """Return the session user_id or None."""
    return session.get('user_id')


def opportunity_to_dict(opp: Opportunity) -> dict:
    return {
        'id': opp.id,
        'name': opp.name,
        'category': opp.category,
        'duration': opp.duration,
        'start_date': opp.start_date,
        'description': opp.description,
        'skills': opp.skills,
        'future_opportunities': opp.future_opportunities,
        'max_applicants': opp.max_applicants,
        'created_at': opp.created_at.isoformat() if opp.created_at else None,
    }


VALID_CATEGORIES = {
    'Technology', 'Business', 'Design',
    'Marketing', 'Data Science', 'Other'
}


# Health check 
@app.route('/')
def home():
    return jsonify({'message': 'Backend running'}), 200



#  TASK 1 — Auth


# US-1.1  Sign Up
@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json(silent=True) or {}

    full_name = (data.get('full_name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    confirm_password = data.get('confirm_password') or ''

    # --- Validate all fields present ---
    if not full_name or not email or not password or not confirm_password:
        return jsonify({'error': 'All fields are required.'}), 400

    # --- Email format ---
    if not is_valid_email(email):
        return jsonify({'error': 'Invalid email format.'}), 400

    # --- Password length ---
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters.'}), 400

    # --- Passwords match ---
    if password != confirm_password:
        return jsonify({'error': 'Passwords do not match.'}), 400

    # --- Duplicate email ---
    if Admin.query.filter_by(email=email).first():
        return jsonify({'error': 'An account with this email already exists.'}), 409

    admin = Admin(
        full_name=full_name,
        email=email,
        password=generate_password_hash(password),
    )
    db.session.add(admin)
    db.session.commit()

    return jsonify({'message': 'Account created successfully. Please log in.'}), 201


# US-1.2  Login
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}

    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    remember_me = bool(data.get('remember_me', False))

    if not email or not password:
        return jsonify({'error': 'Invalid email or password.'}), 401

    admin = Admin.query.filter_by(email=email).first()

    if not admin or not check_password_hash(admin.password, password):
        return jsonify({'error': 'Invalid email or password.'}), 401

    # Store user in session
    session.permanent = remember_me
    if remember_me:
        # Keep session alive for 30 days
        app.permanent_session_lifetime = timedelta(days=30)
    else:
        # Session ends when browser closes
        app.permanent_session_lifetime = timedelta(hours=0)

    session['user_id'] = admin.id
    session['full_name'] = admin.full_name

    return jsonify({
        'message': 'Login successful.',
        'admin': {'id': admin.id, 'full_name': admin.full_name, 'email': admin.email},
    }), 200


# Logout
@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out successfully.'}), 200


# US-1.3  Forgot Password
@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()

    # Always return the same message to protect privacy
    GENERIC_MSG = 'If this email is registered you will receive a reset link.'

    if not email or not is_valid_email(email):
        # Still return 200 so we don't reveal anything
        return jsonify({'message': GENERIC_MSG}), 200

    admin = Admin.query.filter_by(email=email).first()

    if admin:
        # Invalidate any existing unused tokens for this admin
        PasswordResetToken.query.filter_by(admin_id=admin.id, used=False).delete()

        token = secrets.token_urlsafe(48)
        expires_at = datetime.utcnow() + timedelta(hours=1)

        reset_token = PasswordResetToken(
            admin_id=admin.id,
            token=token,
            expires_at=expires_at,
        )
        db.session.add(reset_token)
        db.session.commit()

        # In production, send an email. For now, log internally.
        reset_link = f'http://localhost:5000/reset-password?token={token}'
        print(f'[RESET LINK] {reset_link}')  # Internal log only

    return jsonify({'message': GENERIC_MSG}), 200


# US-1.3  Reset Password (consume the token)
@app.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json(silent=True) or {}
    token_value = (data.get('token') or '').strip()
    new_password = data.get('new_password') or ''
    confirm_password = data.get('confirm_password') or ''

    if not token_value:
        return jsonify({'error': 'Reset token is required.'}), 400

    record = PasswordResetToken.query.filter_by(token=token_value, used=False).first()

    if not record:
        return jsonify({'error': 'Invalid or already used reset link.'}), 400

    if datetime.utcnow() > record.expires_at:
        return jsonify({'error': 'This reset link has expired. Please request a new one.'}), 400

    if len(new_password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters.'}), 400

    if new_password != confirm_password:
        return jsonify({'error': 'Passwords do not match.'}), 400

    admin = Admin.query.get(record.admin_id)
    admin.password = generate_password_hash(new_password)
    record.used = True
    db.session.commit()

    return jsonify({'message': 'Password reset successful. Please log in.'}), 200


# ══════════════════════════════════════════════════════════════════════════════
#  TASK 2 — Opportunity Management
# ══════════════════════════════════════════════════════════════════════════════

# US-2.1  View all opportunities for logged-in admin
@app.route('/opportunities', methods=['GET'])
def get_opportunities():
    admin_id = logged_in_admin_id()
    if not admin_id:
        return jsonify({'error': 'Unauthorized. Please log in.'}), 401

    opps = (
        Opportunity.query
        .filter_by(admin_id=admin_id)
        .order_by(Opportunity.created_at.desc())
        .all()
    )

    return jsonify([opportunity_to_dict(o) for o in opps]), 200


# US-2.2  Create a new opportunity
@app.route('/opportunities', methods=['POST'])
def create_opportunity():
    admin_id = logged_in_admin_id()
    if not admin_id:
        return jsonify({'error': 'Unauthorized. Please log in.'}), 401

    data = request.get_json(silent=True) or {}

    # Required fields
    name = (data.get('name') or '').strip()
    category = (data.get('category') or '').strip()
    duration = (data.get('duration') or '').strip()
    start_date = (data.get('start_date') or '').strip()
    description = (data.get('description') or '').strip()
    skills = (data.get('skills') or '').strip()
    future_opportunities = (data.get('future_opportunities') or '').strip()

    # Optional
    max_applicants = data.get('max_applicants')

    # Validate required fields
    missing = []
    if not name:                missing.append('Opportunity Name')
    if not category:            missing.append('Category')
    if not duration:            missing.append('Duration')
    if not start_date:          missing.append('Start Date')
    if not description:         missing.append('Description')
    if not skills:              missing.append('Skills to Gain')
    if not future_opportunities: missing.append('Future Opportunities')

    if missing:
        return jsonify({'error': f"Required fields missing: {', '.join(missing)}."}), 400

    # Validate category
    if category not in VALID_CATEGORIES:
        return jsonify({'error': f"Invalid category. Choose from: {', '.join(VALID_CATEGORIES)}."}), 400

    # Validate max_applicants if provided
    if max_applicants is not None:
        try:
            max_applicants = int(max_applicants)
            if max_applicants < 1:
                raise ValueError
        except (ValueError, TypeError):
            return jsonify({'error': 'Max applicants must be a positive integer.'}), 400

    opp = Opportunity(
        admin_id=admin_id,
        name=name,
        category=category,
        duration=duration,
        start_date=start_date,
        description=description,
        skills=skills,
        future_opportunities=future_opportunities,
        max_applicants=max_applicants,
    )
    db.session.add(opp)
    db.session.commit()

    return jsonify({'message': 'Opportunity created.', 'opportunity': opportunity_to_dict(opp)}), 201


# US-2.4  View single opportunity details
@app.route('/opportunities/<int:opp_id>', methods=['GET'])
def get_opportunity(opp_id):
    admin_id = logged_in_admin_id()
    if not admin_id:
        return jsonify({'error': 'Unauthorized. Please log in.'}), 401

    opp = Opportunity.query.get(opp_id)

    if not opp:
        return jsonify({'error': 'Opportunity not found.'}), 404

    # Ownership check
    if opp.admin_id != admin_id:
        return jsonify({'error': 'Forbidden. You do not have access to this opportunity.'}), 403

    return jsonify(opportunity_to_dict(opp)), 200


# US-2.5  Edit an opportunity
@app.route('/opportunities/<int:opp_id>', methods=['PUT'])
def update_opportunity(opp_id):
    admin_id = logged_in_admin_id()
    if not admin_id:
        return jsonify({'error': 'Unauthorized. Please log in.'}), 401

    opp = Opportunity.query.get(opp_id)

    if not opp:
        return jsonify({'error': 'Opportunity not found.'}), 404

    # Ownership check
    if opp.admin_id != admin_id:
        return jsonify({'error': 'Forbidden. You can only edit your own opportunities.'}), 403

    data = request.get_json(silent=True) or {}

    name = (data.get('name') or '').strip()
    category = (data.get('category') or '').strip()
    duration = (data.get('duration') or '').strip()
    start_date = (data.get('start_date') or '').strip()
    description = (data.get('description') or '').strip()
    skills = (data.get('skills') or '').strip()
    future_opportunities = (data.get('future_opportunities') or '').strip()
    max_applicants = data.get('max_applicants')

    # Validate required fields
    missing = []
    if not name:                missing.append('Opportunity Name')
    if not category:            missing.append('Category')
    if not duration:            missing.append('Duration')
    if not start_date:          missing.append('Start Date')
    if not description:         missing.append('Description')
    if not skills:              missing.append('Skills to Gain')
    if not future_opportunities: missing.append('Future Opportunities')

    if missing:
        return jsonify({'error': f"Required fields missing: {', '.join(missing)}."}), 400

    if category not in VALID_CATEGORIES:
        return jsonify({'error': f"Invalid category. Choose from: {', '.join(VALID_CATEGORIES)}."}), 400

    if max_applicants is not None and max_applicants != '':
        try:
            max_applicants = int(max_applicants)
            if max_applicants < 1:
                raise ValueError
        except (ValueError, TypeError):
            return jsonify({'error': 'Max applicants must be a positive integer.'}), 400
    else:
        max_applicants = None

    # Apply updates
    opp.name = name
    opp.category = category
    opp.duration = duration
    opp.start_date = start_date
    opp.description = description
    opp.skills = skills
    opp.future_opportunities = future_opportunities
    opp.max_applicants = max_applicants

    db.session.commit()

    return jsonify({'message': 'Opportunity updated.', 'opportunity': opportunity_to_dict(opp)}), 200


# US-2.6  Delete an opportunity
@app.route('/opportunities/<int:opp_id>', methods=['DELETE'])
def delete_opportunity(opp_id):
    admin_id = logged_in_admin_id()
    if not admin_id:
        return jsonify({'error': 'Unauthorized. Please log in.'}), 401

    opp = Opportunity.query.get(opp_id)

    if not opp:
        return jsonify({'error': 'Opportunity not found.'}), 404

    # Ownership check — only creator can delete
    if opp.admin_id != admin_id:
        return jsonify({'error': 'Forbidden. You can only delete your own opportunities.'}), 403

    db.session.delete(opp)
    db.session.commit()

    return jsonify({'message': 'Opportunity deleted successfully.'}), 200


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True)