from mock import patch
import os
import unittest

import app

from tests.test_data import PEOPLE, RELATIONSHIPS


class AppTest(unittest.TestCase):

    @patch('app.app.current_request')
    def setUp(self, mock_request_method):
        self.longMessage = True  # Print complete error message
        os.environ['GRAPH_DB'] = 'ws://localhost:8182/gremlin'
        app.clear_graph()
        for person in PEOPLE:
            mock_request_method.json_body = person
            app.new_person()
        for relationship in RELATIONSHIPS:
            mock_request_method.json_body = relationship
            app.upsert_relationship()

    @patch('app.app.current_request')
    def test_GetKnownAssociates(self, mock_request_method):
        mock_request_method.query_params = {}
        associates = app.get_known_associates(1)
        self.assertEqual(len(associates['known_associates']), 8)


if __name__ == '__main__':
    unittest.main()
