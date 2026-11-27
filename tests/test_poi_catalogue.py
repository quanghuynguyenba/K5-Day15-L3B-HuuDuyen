import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from server import app, _poi_view
from rag.search import load_pois, is_schedulable


class PoiCatalogueTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_catalogue_includes_incomplete_places_without_mutating_data(self):
        original = {'id':'test','name':{'vi':'Test'},'price_vnd':None,'open':None,'close':None}
        result = _poi_view(original)
        self.assertFalse(result['schedulable'])
        self.assertEqual(result['missing_fields'], ['price','opening_hours'])
        self.assertNotIn('missing_fields',original)

    def test_api_exposes_actual_catalogue_and_completeness(self):
        rows = self.client.get('/api/pois').json()
        self.assertEqual(len(rows),len(load_pois()))
        self.assertGreater(len(rows),0)
        self.assertEqual(sum(p['schedulable'] for p in rows),sum(is_schedulable(p) for p in load_pois()))
        for poi in rows:
            self.assertEqual(poi['data_source'],'repo-pois')

    def test_chat_plan_uses_catalogue_ids_and_known_prices(self):
        with patch('agent.llm.USE_MOCK', True), patch('routing.optimizer.travel_minutes', return_value=15), patch('routing.optimizer.directions',return_value=[]):
            response = self.client.post('/api/chat',json={'session_id':'catalogue-regression','message':'2 người, 1 triệu, bảo tàng trong nhà','date':'2026-11-28'})
        self.assertEqual(response.status_code,200)
        plan = response.json()['plan']
        pois = {p['id']:p for p in load_pois()}
        self.assertGreater(len(plan['stops']),0)
        for stop in plan['stops']:
            self.assertIn(stop['poi_id'],pois)
            self.assertTrue(is_schedulable(pois[stop['poi_id']]))
            self.assertTrue(pois[stop['poi_id']]['indoor'])
            self.assertEqual(stop['cost'],pois[stop['poi_id']]['price_vnd']*2)
            self.assertEqual(stop['description_vi'],pois[stop['poi_id']]['description_vi'])
        self.assertEqual(plan['total_cost'],sum(stop['cost'] for stop in plan['stops']))
        self.assertLessEqual(plan['total_cost'],1000000)


if __name__ == '__main__':
    unittest.main()
