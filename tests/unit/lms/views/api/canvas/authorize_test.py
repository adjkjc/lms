from unittest import mock
from urllib.parse import parse_qs, urlparse

import pytest
from pyramid.httpexceptions import HTTPInternalServerError

from lms.services import CanvasAPIServerError
from lms.views.api.canvas.authorize import CanvasAPIAuthorizeViews


class TestAuthorize:
    def test_it_redirects_to_the_right_Canvas_endpoint(self, ai_getter, views):
        response = views.authorize()

        assert response.status_code == 302
        ai_getter.lms_url.assert_called_once_with()
        assert response.location.startswith(
            f"{ai_getter.lms_url.return_value}/login/oauth2/auth"
        )

    def test_it_includes_the_client_id_in_a_query_param(self, ai_getter, views):
        response = views.authorize()

        query_params = parse_qs(urlparse(response.location).query)

        ai_getter.developer_key.assert_called_once_with()
        assert query_params["client_id"] == [str(ai_getter.developer_key.return_value)]

    def test_it_includes_the_response_type_in_a_query_param(self, views):
        response = views.authorize()

        query_params = parse_qs(urlparse(response.location).query)

        assert query_params["response_type"] == ["code"]

    def test_it_includes_the_redirect_uri_in_a_query_param(self, views):
        response = views.authorize()

        query_params = parse_qs(urlparse(response.location).query)

        assert query_params["redirect_uri"] == [
            "http://example.com/canvas_oauth_callback"
        ]

    def test_it_includes_the_scopes_in_a_query_param(self, views):
        response = views.authorize()

        query_params = parse_qs(urlparse(response.location).query)

        assert query_params["scope"] == [
            "url:GET|/api/v1/courses/:course_id/files "
            "url:GET|/api/v1/files/:id/public_url "
            "url:GET|/api/v1/courses/:id "
            "url:GET|/api/v1/courses/:course_id/sections "
            "url:GET|/api/v1/courses/:course_id/users/:id"
        ]

    @pytest.mark.usefixtures("sections_disabled")
    def test_it_doesnt_request_sections_scopes_if_sections_is_disabled(self, views):
        response = views.authorize()

        query_params = parse_qs(urlparse(response.location).query)
        assert query_params["scope"] == [
            "url:GET|/api/v1/courses/:course_id/files url:GET|/api/v1/files/:id/public_url"
        ]

    def test_it_includes_the_state_in_a_query_param(
        self,
        pyramid_request,
        CanvasOAuthCallbackSchema,
        canvas_oauth_callback_schema,
        views,
    ):
        response = views.authorize()

        query_params = parse_qs(urlparse(response.location).query)

        CanvasOAuthCallbackSchema.assert_called_once_with(pyramid_request)
        canvas_oauth_callback_schema.state_param.assert_called_once_with()
        assert query_params["state"] == [
            canvas_oauth_callback_schema.state_param.return_value
        ]


class TestOAuth2Redirect:
    def test_it_gets_an_access_token_from_canvas(self, canvas_api_client, views):
        views.oauth2_redirect()

        canvas_api_client.get_token.assert_called_once_with("test_authorization_code")

    def test_it_500s_if_get_token_raises(self, canvas_api_client, views):
        canvas_api_client.get_token.side_effect = CanvasAPIServerError()

        with pytest.raises(HTTPInternalServerError):
            views.oauth2_redirect()

    @pytest.fixture
    def pyramid_request(self, pyramid_request):
        pyramid_request.parsed_params = {"code": "test_authorization_code"}
        return pyramid_request


class TestOAuth2RedirectError:
    def test_it_passes_authorize_url_to_the_template(
        self, BearerTokenSchema, bearer_token_schema, pyramid_request, views
    ):
        template_variables = views.oauth2_redirect_error()

        BearerTokenSchema.assert_called_once_with(pyramid_request)
        bearer_token_schema.authorization_param.assert_called_once_with(
            pyramid_request.lti_user
        )
        assert (
            template_variables["authorize_url"]
            == "http://example.com/api/canvas/authorize?authorization=TEST_AUTHORIZATION_PARAM"
        )

    def test_it_doesnt_pass_authorize_url_if_theres_no_authorized_user(
        self, pyramid_request, views
    ):
        pyramid_request.lti_user = None

        template_variables = views.oauth2_redirect_error()

        assert "authorize_url" not in template_variables

    @pytest.mark.parametrize(
        "params,invalid_scope",
        [
            ({"error": "invalid_scope"}, True),
            ({"error": "unknown_error"}, False),
            ({"foo": "bar"}, False),
        ],
    )
    def test_it_tells_the_template_whether_to_show_the_missing_scopes_error_message(
        self, pyramid_request, params, invalid_scope, views
    ):
        pyramid_request.params.clear()
        pyramid_request.params.update(params)

        template_variables = views.oauth2_redirect_error()

        assert template_variables["invalid_scope"] == invalid_scope

    @pytest.mark.parametrize(
        "params,expected_details",
        [
            (
                {"error_description": mock.sentinel.error_description},
                mock.sentinel.error_description,
            ),
            ({"foo": "bar"}, None),
        ],
    )
    def test_it_passes_error_descriptions_from_Canvas_to_the_template(
        self, pyramid_request, params, expected_details, views
    ):
        pyramid_request.params.clear()
        pyramid_request.params.update(params)

        template_variables = views.oauth2_redirect_error()

        assert template_variables["details"] == expected_details

    def test_it_passes_our_required_API_scopes_to_the_template(self, views):
        template_variables = views.oauth2_redirect_error()

        assert template_variables["scopes"] == (
            "url:GET|/api/v1/courses/:course_id/files",
            "url:GET|/api/v1/files/:id/public_url",
            "url:GET|/api/v1/courses/:id",
            "url:GET|/api/v1/courses/:course_id/sections",
            "url:GET|/api/v1/courses/:course_id/users/:id",
        )


@pytest.fixture
def views(pyramid_request):
    return CanvasAPIAuthorizeViews(pyramid_request)


@pytest.fixture(autouse=True)
def BearerTokenSchema(patch):
    return patch("lms.views.api.canvas.authorize.BearerTokenSchema")


@pytest.fixture
def bearer_token_schema(BearerTokenSchema):
    schema = BearerTokenSchema.return_value
    schema.authorization_param.return_value = "TEST_AUTHORIZATION_PARAM"
    return schema


@pytest.fixture(autouse=True)
def CanvasOAuthCallbackSchema(patch):
    return patch("lms.views.api.canvas.authorize.CanvasOAuthCallbackSchema")


@pytest.fixture
def canvas_oauth_callback_schema(CanvasOAuthCallbackSchema):
    schema = CanvasOAuthCallbackSchema.return_value
    schema.state_param.return_value = "test_state"
    return schema


@pytest.fixture
def sections_disabled(ai_getter):
    ai_getter.canvas_sections_enabled.return_value = False


pytestmark = pytest.mark.usefixtures("ai_getter", "canvas_api_client")
