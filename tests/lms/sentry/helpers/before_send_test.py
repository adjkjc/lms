import logging
from unittest import mock

import pytest

from lms.sentry.helpers.before_send import before_send
from lms.sentry.helpers import filters


@pytest.mark.usefixtures("Event", "filters")
class TestBeforeSend(object):
    def test_it_creates_an_Event(self, Event):
        before_send(mock.sentinel.event_dict, mock.sentinel.hint_dict)

        Event.assert_called_once_with(mock.sentinel.event_dict, mock.sentinel.hint_dict)

    def test_it_calls_all_the_filters(self, Event, filters):
        before_send(mock.sentinel.event_dict, mock.sentinel.hint_dict)

        # If you've added a new filter function you should add it to this list.
        filters = [filters.filter_canvas_api_access_token_error]

        for filter in filters:
            filter.assert_called_once_with(Event.return_value)

    def test_it_filters_out_the_event_if_a_filter_returns_false(self, filters):
        filters.filter_canvas_api_access_token_error.return_value = False

        result = before_send(mock.sentinel.event_dict, mock.sentinel.hint_dict)

        assert result is None

    def test_it_logs_when_it_filters_out_an_event(self, caplog, filters):
        caplog.set_level(logging.INFO)
        filters.filter_canvas_api_access_token_error.return_value = False

        before_send(mock.sentinel.event_dict, mock.sentinel.hint_dict)

        assert caplog.record_tuples == [
            (
                "lms.sentry.helpers.before_send",
                logging.INFO,
                "Filtering out Sentry event: sentinel.hint_dict",
            )
        ]

    def test_it_lets_through_the_event_if_all_filters_return_true(self):
        filters.filter_canvas_api_access_token_error.return_value = True

        result = before_send(mock.sentinel.event_dict, mock.sentinel.hint_dict)

        assert result == mock.sentinel.event_dict

    @pytest.fixture
    def Event(self, patch):
        return patch("lms.sentry.helpers.before_send.Event")

    @pytest.fixture
    def filters(self, patch):
        return patch("lms.sentry.helpers.before_send.filters")
