from django.shortcuts import render, redirect, reverse
from django.views import View
from django.http import HttpResponseBadRequest, HttpResponse
from django.http.response import JsonResponse
from utils.response_code import RETCODE
from django_redis import get_redis_connection
from django.db import DataError
from libs.captcha import captcha
from random import randint
from libs.sms.sms import SmsCode
from .models import UserProfile
import logging
import re

logger = logging.getLogger("django")


# Create your views here.
class RegisterView(View):

    def get(self, request):
        return render(request, "register.html")

    def post(self, request):
        """
        1.接收数据
        2.验证数据
            2.1 参数是否齐全
            2.2 手机号格式是否在正确
            2.3 密码是否符合格式
            2.4 密码和确认密码是否一致
            2.5 短信验证码是否和redis中的一致
        3.保存注册信息
        4.返回响应，跳转指定页面
        """
        # 1.接收数据
        mobile = request.POST.get("mobile")
        passwd = request.POST.get("password")
        passwd2 = request.POST.get("password2")
        sms_code = request.POST.get("sms_code")

        if not all([mobile, passwd, passwd2, sms_code]):
            return HttpResponseBadRequest("缺少必要的参数")

        if not re.match(r"^1[3-9]\d{9}$", mobile):
            return HttpResponseBadRequest("手机号不符合规则")

        if not re.match(r"^[0-9a-zA-Z]{8,20}$", passwd):
            return HttpResponseBadRequest("请输入8到20为密码，密码为数字和字母")

        if passwd != passwd2:
            return HttpResponseBadRequest("两次密码不一致")

        redis_connection = get_redis_connection()
        redis_sms_code = redis_connection.get("sms:%s"%mobile)

        if redis_sms_code is None:
            return HttpResponseBadRequest("短信验证码已过期")

        if sms_code != redis_sms_code.decode():
            return HttpResponseBadRequest("短信验证码不一致")

        try:
            user = UserProfile.objects.create(
                username=mobile,
                mobile=mobile,
                password=passwd,
            )
        except DataError as e:
            logger.error(e)
            return HttpResponseBadRequest("注册失败")
        # return HttpResponse("注册成功，重定向到首页")
        return redirect(reverse("home:index"))

class ImageCodeView(View):

    def get(self, request):
        # 1.接收前端的uuid
        uuid = request.GET.get("uuid")

        # 2.判断uuid是否获取到
        if uuid is None:
            return HttpResponseBadRequest("没有传入uuid")

        # 3.通过调用captcha来生成图片验证码
        text, image = captcha.captcha.generate_captcha()

        # 4.将uuid保存到redis中
        redis_connection = get_redis_connection("default")
        redis_connection.setex("img:%s" % uuid, 300, text)

        # 5。返回图片二进制
        return HttpResponse(image, content_type="image/jpeg")


class SmsCodeView(View):

    def get(self, request):
        """
        1.接收参数
        2.参数的验证
            2.1检验参数是否完整
            2.2图片验证码的验证
                链接redis，获取redis中图片验证码的值
                判断图片验证码是否存在
                如果图片验证码未过期，之后删除图片验证码
                对比图片验证码
        3.生成短信验证码
        4.将短信验证码保存到redis中
        5.发送短信
        6.返回响应
        """
        # 1.接收参数
        mobile = request.GET.get("mobile")
        image_code = request.GET.get("image_code")
        uuid = request.GET.get("uuid")

        # 2.参数的验证
        # 检验参数是否完整
        if not all([mobile, image_code, uuid]):
            return JsonResponse({
                "code": RETCODE.NECESSARYPARAMERR,
                "errmsg": "缺少必要的参数",
            })
        # 链接redis，获取redis中图片验证码的值
        redis_connection = get_redis_connection("default")
        redis_image_code = redis_connection.get("img:%s" % uuid)

        # 判断图片验证码是否存在
        if redis_image_code is None:
            return JsonResponse({
                "code": RETCODE.IMAGECODEERR,
                "errmsg": "图片验证码已经过期",
            })

        # 如果图片验证码未过期，之后删除图片验证码
        try:
            redis_connection.delete("img:%s" % uuid)
        except Exception as e:
            logger.error(e)

        # 对比图片验证码
        if redis_image_code.decode().lower() != image_code.lower():
            return JsonResponse({
                "code": RETCODE.IMAGECODEERR,
                "errmsg": "图片验证码错误",
            })

        # 3.生成短信验证码
        sms_code = "%06d" % randint(0, 999999)
        logger.info(sms_code)

        # 4.将短信验证码保存到redis中
        redis_connection.setex("sms:%s" % mobile, 300, sms_code)

        #  5.发送短信
        SmsCode().send_message(1, mobile, [sms_code, "5"])
        # 6.返回响应
        return JsonResponse({
            "code": RETCODE.OK,
            "errmsg": "短信验证码发送成功",
        })
