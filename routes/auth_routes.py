from flask import Blueprint, request, jsonify
from authlib.integrations.base_client.errors import OAuthError
from flask.helpers import make_response
import jwt
from jwt import PyJWKClient
from config import GOOGLE_CLIENT_ID, limiter, user_session_serializer
from services.auth_service import oauth_sign_in

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
        user_info = oauth_sign_in(oauth_user_info['email'])
        if not user_info:
            return jsonify({'error': 'User does not exist.'}), 400
        else:
            serializer = user_session_serializer
            session_data = serializer.dumps(user_info)
            print('user session token set.')

            if isinstance(session_data, bytes):
                session_data = session_data.decode('utf-8')

            response = make_response(jsonify({'message': 'Login successful', 'user': user_info}), 200)
            response.set_cookie('user_session',
                                session_data,
                                httponly=True,
                                secure=True,
                                samesite='none',
                                max_age=1209600)
            return response
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token has expired'}), 400
    except jwt.InvalidTokenError as e:
        return jsonify({'error': f'Invalid token: {str(e)}'}), 400
    except OAuthError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'An error occurred while processing the token: {str(e)}'}), 400
