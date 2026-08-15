import json
from unittest.mock import patch

from django.test import TestCase


class GeneratedAppViewTests(TestCase):
    @patch('main.views.generate_processing_node')
    def test_make_app_renders_generated_html_from_gemini_response(self, mock_generate_processing_node):
        mock_generate_processing_node.return_value = json.dumps({
            'inputs': [
                {'type': 'String', 'count': '1', 'name': 'userText'},
                {'type': 'ImageData', 'count': '1', 'name': 'userImage'},
            ],
            'outputs': [
                {'type': 'String', 'count': '1', 'name': 'resultText'},
                {'type': 'ImageData', 'count': '1', 'name': 'resultImage'},
            ],
            'code_snippet': 'resultText = userText.toUpperCase(); resultImage = userImage;'
        })

        response = self.client.post('/makeApp/', {'user_prompt': 'Create a text app'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')

        html = response.content.decode('utf-8')
        self.assertIn('Generated App', html)
        self.assertIn('userText', html)
        self.assertIn('userImage', html)
        self.assertIn('resultText', html)
        self.assertIn('resultImage', html)
        self.assertIn('toUpperCase', html)

    @patch('main.views.generate_processing_node')
    def test_make_app_supports_star_count_as_array_input_and_output(self, mock_generate_processing_node):
        mock_generate_processing_node.return_value = json.dumps({
            'inputs': [
                {'type': 'String', 'count': '*', 'name': 'tags'},
            ],
            'outputs': [
                {'type': 'String', 'count': '*', 'name': 'cleanTags'},
            ],
            'code_snippet': 'cleanTags = tags.map(tag => tag.trim()).filter(Boolean);'
        })

        response = self.client.post('/makeApp/', {'user_prompt': 'Normalize tags'})

        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf-8')
        self.assertIn('data-repeat-name="tags"', html)
        self.assertIn('Add another tags', html)
        self.assertIn('cleanTags', html)
        self.assertIn('tags.map', html)
