from services.sql_service import get_user

def oauth_sign_in(email: str):
    """
    Checks if the email of a OAuth authenticated user is found in the database.
    
    Parameters: 
        email (str): The email of the OAuth authenticated user.
        
    Returns:
        dict[str, any]: Dictionary with the authenticated user's information or None if the
        user's email wasn't found in the database.
    """
    user = get_user(credential=email)
    if not user:
        return None
    user_info = {
        'Username': user['Username'],
        'Email': user['Email'],
        'Id': user['Id'],
        'Roles': user['Roles'],
        'Assistants':  user['Assistants'],
        'Created': user['Created'],
        'LastModified': user['LastModified'],
    }
    return user_info