from util_functions.functions import current_time_prague


def set_last_modified(mapper, connection, target):
    target.last_modified = current_time_prague()

def set_created(mapper, connection, target):
    if not target.created:
        target.created = current_time_prague()
    target.last_modified = current_time_prague()