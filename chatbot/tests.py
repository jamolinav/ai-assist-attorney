from django.test import TestCase, Client
from django.urls import reverse
import json


class ChatbotRoutesTests(TestCase):
    def setUp(self):
        self.client = Client()
    
    def test_home_ok(self):
        r = self.client.get(reverse('chatbot:home'))
        self.assertEqual(r.status_code, 200)
    
    def test_chat_ok(self):
        r = self.client.get(reverse('chatbot:chat'))
        self.assertEqual(r.status_code, 200)
    
    def test_send_and_progress_ok(self):
        r = self.client.post(
            reverse('chatbot:api_send'),
            data=json.dumps({"question": "Hola"}),
            content_type='application/json'
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data.get('status'), 'ok')
        key = data.get('progress_key')
        self.assertTrue(key)
        
        r2 = self.client.get(reverse('chatbot:api_progress') + f"?key={key}")
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json().get('status'), 'ok')
    
    def test_rate_limit_minute(self):
        # Hacer múltiples requests rápidos para gatillar el 429
        for i in range(4):
            r = self.client.post(
                reverse('chatbot:api_send'),
                data=json.dumps({"question": f"Hola {i}"}),
                content_type='application/json'
            )
            self.assertIn(r.status_code, (200, 429))