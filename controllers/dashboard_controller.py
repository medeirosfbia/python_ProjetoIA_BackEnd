from flask import jsonify

from services.auth_service import authenticated_user_id
from services.dashboard_service import build_dashboard


def my_dashboard_controller():
    return jsonify(build_dashboard(authenticated_user_id())), 200
