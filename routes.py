from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
from extensions import db
from models import User, Event, Registration

bp = Blueprint('main', __name__)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('main.login'))
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated

@bp.route('/')
def index():
    events = Event.query.all()
    return render_template('index.html', events=events)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='Username already exists')
        user = User(username=username, email=email, password=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('main.login'))
    return render_template('register.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('main.index'))
        return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.index'))

@bp.route('/events')
def events():
    search = request.args.get('search', '')
    if search:
        events = Event.query.filter(Event.title.ilike(f'%{search}%')).all()
    else:
        events = Event.query.all()
    return render_template('events.html', events=events)

@bp.route('/event/<int:event_id>')
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    is_registered = False
    if 'user_id' in session:
        is_registered = Registration.query.filter_by(user_id=session['user_id'], event_id=event_id).first() is not None
    return render_template('event_detail.html', event=event, is_registered=is_registered)

@bp.route('/register_event/<int:event_id>', methods=['POST'])
@login_required
def register_event(event_id):
    event = Event.query.get_or_404(event_id)
    user_id = session['user_id']
    if event.available_seats() <= 0:
        return jsonify({'success': False, 'message': 'No seats available'}), 400
    existing = Registration.query.filter_by(user_id=user_id, event_id=event_id).first()
    if existing:
        return jsonify({'success': False, 'message': 'Already registered'}), 400
    registration = Registration(user_id=user_id, event_id=event_id)
    db.session.add(registration)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Registration successful'})

@bp.route('/cancel_registration/<int:event_id>', methods=['POST'])
@login_required
def cancel_registration(event_id):
    registration = Registration.query.filter_by(user_id=session['user_id'], event_id=event_id).first_or_404()
    db.session.delete(registration)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Registration cancelled'})

@bp.route('/create_event', methods=['GET', 'POST'])
@login_required
def create_event():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        date = datetime.strptime(request.form.get('date'), '%Y-%m-%dT%H:%M')
        location = request.form.get('location')
        capacity = int(request.form.get('capacity'))
        event = Event(title=title, description=description, date=date, location=location, capacity=capacity, organizer_id=session['user_id'])
        db.session.add(event)
        db.session.commit()
        return redirect(url_for('main.index'))
    return render_template('create_event.html')

@bp.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    total_users = User.query.count()
    total_events = Event.query.count()
    total_registrations = Registration.query.count()
    events = Event.query.all()
    return render_template('admin_dashboard.html', total_users=total_users, total_events=total_events, total_registrations=total_registrations, events=events)
