import datetime

import requests

from lms.models import OAuth2Token
from lms.services._helpers import CanvasAPIHelper


__all__ = ["CanvasAPIClient"]


class CanvasAPIClient:
    def __init__(self, _context, request):
        self._helper = CanvasAPIHelper(
            request.lti_user.oauth_consumer_key,
            request.find_service(name="ai_getter"),
            request.route_url,
        )
        self._lti_user = request.lti_user
        self._db = request.db

    def get_token(self, authorization_code):
        """
        Get an access token for the current LTI user.

        Posts to the Canvas API to get the access token and returns it.
        """
        access_token_request = self._helper.access_token_request(authorization_code)
        access_token_response = requests.Session().send(access_token_request)

        # TODO: Handle access token error responses.
        # These aren't documented in the Canvas docs as far as I can see.
        # They are documented in the OAuth 2 spec but I don't yet know if Canvas's
        # error responses follow this:
        # https://tools.ietf.org/html/rfc6749#section-5.2

        # TODO: Validate access_token_response.

        response_params = access_token_response.json()
        access_token = response_params["access_token"]
        refresh_token = response_params["refresh_token"]
        expires_in = response_params["expires_in"]

        return (access_token, refresh_token, expires_in)

    def save_token(self, access_token, refresh_token=None, expires_in=None):
        # Find the existing token in the DB.
        token = (
            self._db.query(OAuth2Token)
            .filter_by(
                consumer_key=self._lti_user.oauth_consumer_key,
                user_id=self._lti_user.user_id,
            )
            .one_or_none()
        )

        # If there's no existing token in the DB then create a new one.
        if token is None:
            token = OAuth2Token()
            self._db.add(token)

        # Either update the existing token, or set the attributes of the newly
        # created one.
        token.consumer_key = self._lti_user.oauth_consumer_key
        token.user_id = self._lti_user.user_id
        token.access_token = access_token
        token.refresh_token = refresh_token
        token.expires_in = expires_in
        token.received_at = datetime.datetime.utcnow()