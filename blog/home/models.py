from django.db import models
from django.utils import timezone


# Create your models here.
class ArticleCategory(models.Model):
    title = models.CharField(max_length=100, blank=True)
    created = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.title

    class Meta:
        db_table = "tb_category"
        verbose_name = "文章类别管理"
        verbose_name_plural = verbose_name
