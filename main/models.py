from django.db import models
from django.contrib.auth.models import User


class History(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='history')
	prompt = models.TextField()
	gemini_output = models.JSONField()
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ('-created_at',)
