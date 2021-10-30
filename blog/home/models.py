from django.db import models
from django.utils import timezone
from users.models import User


# Create your models here.
class ArticleCategory(models.Model):
    title = models.CharField("文章标题", max_length=100, blank=True)
    created = models.DateTimeField("创建时间", default=timezone.now)

    def __str__(self):
        return self.title

    class Meta:
        db_table = "tb_category"
        verbose_name = "类别管理"
        verbose_name_plural = verbose_name


class Article(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="作者")
    avatar = models.ImageField("封面图", upload_to="article/%Y%m%d/", blank=True)
    category = models.ForeignKey(
        ArticleCategory,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="article",
        verbose_name="文章类别"
    )
    tags = models.CharField(max_length=20, blank=True)
    title = models.CharField(max_length=100, blank=False, null=False)
    summary = models.CharField(max_length=200, blank=False, null=False)

    content = models.TextField()

    total_views = models.PositiveSmallIntegerField(default=0)
    comments_count = models.PositiveSmallIntegerField(default=0)
    created = models.DateTimeField(default=timezone.now)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ("-created",)
        db_table = "tb_article"
        verbose_name = "文章管理"
        verbose_name_plural = verbose_name
