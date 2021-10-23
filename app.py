from flask import Flask, jsonify, make_response, request
from werkzeug.security import generate_password_hash,check_password_hash
from flask_cors import CORS, cross_origin
from flask_sqlalchemy import SQLAlchemy
from functools import wraps

from config.database import *
from config.config import *
from models import *

import uuid
import jwt
import datetime

app = Flask(__name__)

app.config['SECRET_KEY'] = RANDOM_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

db.init_app(app)

def token_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            bearer = request.headers['Authorization']
            token = bearer.split()[1]

        if not token:
            return jsonify({'message': 'token is missing'})
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = Users.query.filter_by(public_id=data['public_id']).first()
        except:
            return jsonify({'message': 'token is invalid'})
        
        return f(current_user, *args, **kwargs)
    
    return decorator


@app.route('/register', methods=['POST'])
def signup_user():
    data = request.get_json()
    hashed_pw = generate_password_hash(data['password'], method='sha256')

    new_user = Users(public_id=str(uuid.uuid4()), name=data['name'], password=hashed_pw, admin=False)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'user succesfully added'})


@app.route('/login', methods=['POST'])
def login_user():
    auth = request.authorization
    if not auth or not auth.username or not auth.password:
        return make_response('Not recognized', 401, {'Authentication': '"login required"'})

    user = Users.query.filter_by(name=auth.username).first()
    if check_password_hash(user.password, auth.password):
        token = jwt.encode({'public_id': user.public_id, 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=10)}, 
            app.config['SECRET_KEY'], "HS256")

        return jsonify({'token': token})

    return make_response('Failed to verify', 401, {'Authentication': '"login required"'})


@app.route('/users', methods=['GET'])
def get_all_users():
    users = Users.query.all()
    result = []
    for user in users:
        user_data = {}
        user_data['public_id'] = user.public_id
        user_data['name'] = user.name
        user_data['password'] = user.password
        user_data['admin'] = user.admin

        result.append(user_data)
    
    return jsonify({'users': result})


@app.route('/book', methods=['POST'])
@token_required
def create_book(current_user):
    data = request.get_json()
    new_books = Books(name=data['name'], author=data['author'], publisher=data['publisher'], 
        book_prize=data['book_prize'], user_id=current_user.id)
    db.session.add(new_books)
    db.commit()
    return jsonify({'message': 'book succesfully added'})


@app.route('/books', methods=['GET'])
@token_required
def get_books(current_user):
    books = Books.query.filter_by(user_id=current_user.id).all()
    book_list = []

    for book in books:
        book_data = {}
        book_data['id'] = book.id
        book_data['name'] = book.name
        book_data['author'] = book.author
        book_data['publisher'] = book.publisher
        book_data['book_prize'] = book.book_prize
        book_list.append(book_data)

    return jsonify({'list': book_list})


@app.route('/books/<book_id>', methods=['DELETE'])
@token_required
def delete_book(current_user, book_id):
    book = Books.query.filter_by(id=book_id, user_id=current_user.id).first()
    if not book:
        return jsonify({'messahe': 'book does not exist'})

    db.session.delete(book)
    db.session.commit()
    return jsonify({'message': 'book succesfully deleted'})


with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5000)