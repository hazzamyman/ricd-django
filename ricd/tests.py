from django.test import TestCase
from ricd.models import Council

class CouncilModelTest(TestCase):
    def test_create_council(self):
        council = Council.objects.create(name="Test Council")
        self.assertEqual(str(council), "Test Council")
