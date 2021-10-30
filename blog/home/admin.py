from django.contrib import admin
from home.models import *


# Register your models here.
@admin.register(ArticleCategory)
class ArticleCategoryManager(admin.ModelAdmin):
    list_display = [
        "title",
        "created"
    ]