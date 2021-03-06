from django.db import models
from django.contrib.auth.models import AbstractUser


# Create your models here.
class User(AbstractUser):
    mobile = models.CharField("手机号", max_length=11, unique=True, blank=False)
    avatar = models.ImageField("头像", upload_to="avatar/%Y%m%d/", blank=True)
    user_desc = models.TextField("个人描述", max_length=500, blank=True)

    # 修改认证的字段
    USERNAME_FIELD = 'mobile'

    # 创建超级管理员的需要必须输入的字段
    REQUIRED_FIELDS = ['username', 'email']

    def __str__(self):
        return self.mobile

    class Meta:
        db_table = "tb_users"
        verbose_name = "用户信息"
        verbose_name_plural = verbose_name
