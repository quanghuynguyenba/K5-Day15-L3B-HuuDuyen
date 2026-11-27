import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from server import app


class ServiceAPITests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        poi_patch = patch('server.get_poi', side_effect=lambda poi_id: {'id':poi_id} if poi_id == 'hn_001' else None)
        poi_patch.start()
        self.addCleanup(poi_patch.stop)

    def test_language_and_unknown_poi(self):
        self.assertEqual(self.client.post('/api/narrate', json={'poi_id':'hn_001','lang':'fr'}).status_code, 422)
        self.assertEqual(self.client.post('/api/narrate', json={'poi_id':'missing','lang':'vi'}).status_code, 404)

    def test_placeholder_is_not_presented_as_real_audio(self):
        with patch('agent.tools.load_prepared_audio', return_value=None), patch('agent.tools.get_poi_context', return_value='SAMPLE — replace with Wikipedia content.'):
            response = self.client.post('/api/narrate', json={'poi_id':'hn_001','lang':'ko'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['mock'])
        self.assertIsNone(response.json()['audio_url'])
        self.assertEqual(response.json()['source'], 'placeholder')

    def test_prepared_audio_has_provenance_and_versioned_url(self):
        prepared = {'text':'Reviewed script','audio_path':'/audio/hn_001_ko.mp3','audio_version':'abc123',
                    'source':'prepared','mock':False,'tts_status':'cached','tts_provider':'edge-tts'}
        with patch('server.narrate', return_value=prepared):
            result = self.client.post('/api/narrate', json={'poi_id':'hn_001','lang':'ko'}).json()
        self.assertEqual(result['audio_url'], '/audio/hn_001_ko.mp3?v=abc123')
        self.assertNotIn('audio_path', result)
        self.assertFalse(result['mock'])

    def test_internal_failure_is_actionable_without_leaking_exception(self):
        with patch('server.narrate', side_effect=RuntimeError('private details')):
            result = self.client.post('/api/narrate', json={'poi_id':'hn_001','lang':'vi'})
        self.assertEqual(result.status_code, 503)
        self.assertNotIn('private details', result.text)

    def test_weather_unavailable_stays_null(self):
        with patch('server.get_weather', return_value={'temp_max':None,'is_rainy':None,'status':'unavailable','mock':False}):
            result = self.client.get('/api/weather?date=2026-11-28').json()
        self.assertIsNone(result['temp_max'])
        self.assertIsNone(result['is_rainy'])


if __name__ == '__main__':
    unittest.main()
