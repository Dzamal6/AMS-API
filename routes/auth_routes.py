from flask import Blueprint, request, jsonify
from authlib.integrations.base_client.errors import OAuthError
from flask.helpers import make_response
import jwt
from jwt import PyJWKClient
from config import GOOGLE_CLIENT_ID, limiter, user_session_serializer
from util_functions.functions import login_user
import logging
from services.sql_service import get_user

auth_bp = Blueprint('auth', __name__)

GOOGLE_JWK_URL = "https://www.googleapis.com/oauth2/v3/certs"

@auth_bp.route('/auth/google-login', methods=['POST'])
@limiter.limit('3/minute')
def google_login():
    token = request.json.get('token')
    if not token:
        return jsonify({'error': 'Missing token'}), 400

    try:
        jwks_client = PyJWKClient(GOOGLE_JWK_URL)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        decoded_token = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=GOOGLE_CLIENT_ID,
            issuer="https://accounts.google.com"
        )
        
        oauth_user_info = {
            "name": decoded_token.get("name"),
            "email": decoded_token.get("email"),
        }
        user_info = get_user(oauth_user_info['email'])
        if user_info is None:
            logging.warning(f'Attempted login of unregistered user: {oauth_user_info['email']}, {oauth_user_info['name']}')
            return jsonify({'error': 'User does not exist.'}), 400
        else:
            return login_user(user=user_info, remember=True)
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token has expired'}), 400
    except jwt.InvalidTokenError as e:
        return jsonify({'error': f'Invalid token: {str(e)}'}), 400
    except OAuthError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logging.error(msg=f'An error occurred while processing the token: {str(e)}')
        return jsonify({'error': f'An error occurred while processing the token.'}), 400
