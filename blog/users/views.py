# import os
# import sys
# sys.path.insert(0, os.path.join(os.getcwd(), "libs"))

from django.shortcuts import render
from django.views import View
from django.http import HttpResponseBadRequest, HttpResponse
from django.http.response import JsonResponse
from utils.response_code import RETCODE
from django_redis import get_redis_connection
from libs.captcha import captcha
from random import randint
from libs.sms.sms import SmsCode
import logging

logger = logging.getLogger("django")


# Create your views here.
class RegisterView(View):

    def get(self, request):
        return render(request, "register.html")


class ImageCodeView(View):

    def get(self, request):
        # 1.接收前端的uuid
        # 2.判断uuid是否获取到
        # 3.通过调用captcha来生成图片验证码
        # 4.将uuid保存到redis中
        # 5。返回图片二进制

        uuid = request.GET.get("uuid")
        if uuid is None:
            return HttpResponseBadRequest("没有传入uuid")

        text, image = captcha.captcha.generate_captcha()
        redis_connection = get_redis_connection("default")
        redis_connection.setex("img:%s" % uuid, 300, text)
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

        if not all([mobile, image_code, uuid]):
            return JsonResponse({
                "code": RETCODE.NECESSARYPARAMERR,
                "errmsg": "缺少必要的参数",
            })
        redis_connection = get_redis_connection("default")
        redis_image_code = redis_connection.get("img:%s" % uuid)

        if redis_image_code is None:
            return JsonResponse({
                "code": RETCODE.IMAGECODEERR,
                "errmsg": "图片验证码已经过期",
            })

        try:
            redis_connection.delete("img:%s" % uuid)
        except Exception as e:
            logger.error(e)

        if redis_image_code.decode().lower() != image_code.lower():
            return JsonResponse({
                "code": RETCODE.IMAGECODEERR,
                "errmsg": "图片验证码错误",
            })

        sms_code = "%06d" % randint(0, 999999)
        logger.info(sms_code)

        redis_connection.setex("sms:%s" % mobile, 300, sms_code)

        SmsCode().send_message(1, mobile, [sms_code, "5"])
        return JsonResponse({
            "code": RETCODE.OK,
            "errmsg": "短信验证码发送成功",
        })
