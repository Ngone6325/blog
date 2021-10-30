from django.shortcuts import render, redirect, reverse
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.http import HttpResponseBadRequest, HttpResponse
from django.http.response import JsonResponse
from utils.response_code import RETCODE
from django_redis import get_redis_connection
from django.db import DataError
from libs.captcha import captcha
from random import randint
from libs.sms.sms import SmsCode
from users.models import User
from home.models import ArticleCategory, Article
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
        password = request.POST.get("password")
        password2 = request.POST.get("password2")
        sms_code = request.POST.get("sms_code")

        if not all([mobile, password, password2, sms_code]):
            return HttpResponseBadRequest("缺少必要的参数")

        if not re.match(r"^1[3-9]\d{9}$", mobile):
            return HttpResponseBadRequest("手机号不符合规则")

        if not re.match(r"^[0-9a-zA-Z]{8,20}$", password):
            return HttpResponseBadRequest("请输入8到20为密码，密码为数字和字母")

        if password != password2:
            return HttpResponseBadRequest("两次密码不一致")

        redis_connection = get_redis_connection()
        redis_sms_code = redis_connection.get("sms:%s" % mobile)

        if redis_sms_code is None:
            return HttpResponseBadRequest("短信验证码已过期")

        if sms_code != redis_sms_code.decode():
            return HttpResponseBadRequest("短信验证码不一致")

        try:
            user = User.objects.create_user(
                username=mobile,
                mobile=mobile,
                password=password,
            )
        except DataError as e:
            logger.error(e)
            return HttpResponseBadRequest("注册失败")

        # 状态保持
        login(request, user)

        response = redirect(reverse("home:index"))
        response.set_cookie("is_login", True)
        response.set_cookie("username", user.username, max_age=7 * 24 * 3600)

        # return HttpResponse("注册成功，重定向到首页")
        return response


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


class LoginView(View):

    def get(self, request):
        return render(request, "login.html")

    def post(self, request):
        """
        1.接收参数
        2.参数的验证
            2.1验证手机号是否符合规则
            2.2验证密码是否符合规则
        3.用户认证登录
        4.状态的保持
        5.根据用户是否记住登录状态来进行判断
        6.为了首页显示我们需要设置一些cookie信息
        7.返回响应
        """
        # 1.接收参数
        mobile = request.POST.get("mobile")
        password = request.POST.get("password")
        remember = request.POST.get("remember")

        # 判断参数是否齐全
        if not all([mobile, password]):
            return HttpResponseBadRequest('缺少必传参数')

        # 2.参数的验证
        if not re.match(r"1[3-9]\d{9}$", mobile):
            return HttpResponseBadRequest("手机号不符合规则")
        if not re.match(r"^[0-9a-zA-Z]{8,20}$", password):
            return HttpResponseBadRequest("密码不符合规则")
        # 3.用户认证登录
        user = authenticate(mobile=mobile, password=password)

        if user is None:
            return HttpResponseBadRequest("用户名或密码错误")
        # 4.状态的保持
        login(request, user)

        # 5.根据用户是否记住登录状态来进行判断
        # 6.为了首页显示我们需要设置一些cookie信息
        # 根据next参数来进行页面地跳转
        next_page = request.GET.get("next")
        if next_page:
            response = redirect(next_page)
        else:
            response = redirect(reverse("home:index"))
        if remember != "on":
            request.session.set_expiry(0)
            response.set_cookie("is_login", True)
            response.set_cookie("username", user.username, max_age=14 * 24 * 3600)
        else:
            # None，过期时间默认为两周
            request.session.set_expiry(None)
            response.set_cookie("is_login", True, max_age=14 * 24 * 3600)
            response.set_cookie("username", user.username, max_age=14 * 24 * 3600)

        # 7.返回响应
        return response


class LogoutView(View):
    """
    1.清除session
    2.删除部分cookie数据
    3.跳转到首页
    """

    def get(self, request):
        # 1.清除session
        logout(request)
        # 2.删除部分cookie数据
        response = redirect(reverse("home:index"))
        response.delete_cookie("is_login")
        # 3.跳转到首页
        return response


class ForgetPasswdView(View):
    def get(self, request):
        return render(request, "forget_password.html")

    def post(self, request):
        """
        1.接收数据
        2.验证数据
            2.1判断参数是否齐全
            2.2判断手机号是否符合规则
            2.3判断密码是否符合规则
            2.4判断密码和确认密码是否一致
            2.5短信验证码是否正确
        3.根据手机号进行用户信息的查询
        4.如果用户存在，则进行密码修改
        5.不存在则添加用户
        6.进行页面跳转，跳转到登录页面
        7.返回响应
        """
        # 1.接收数据
        mobile = request.POST.get("mobile")
        password = request.POST.get("password")
        password2 = request.POST.get("password2")
        sms_code = request.POST.get("sms_code")
        # 2.验证数据
        # 2.1判断参数是否齐全
        if not all([mobile, password, password2, sms_code]):
            return HttpResponseBadRequest('缺少必传参数')
        # 2.2判断手机号是否符合规则
        if not re.match(r"1[3-9]\d{9}$", mobile):
            return HttpResponseBadRequest("手机号不符合规则")
        # 2.3判断密码是否符合规则
        if not re.match(r"^[0-9a-zA-Z]{8,20}$", password):
            return HttpResponseBadRequest("密码不符合规则")
        # 2.4判断密码和确认密码是否一致
        if password != password2:
            return HttpResponseBadRequest("两次密码不一致")
        # 2.65短信验证码是否正确
        redis_connection = get_redis_connection()
        redis_sms_code = redis_connection.get("sms:%s" % mobile)

        if redis_sms_code is None:
            return HttpResponseBadRequest("短信验证码已过期")

        if sms_code != redis_sms_code.decode():
            return HttpResponseBadRequest("短信验证码不一致")

        # 3.根据手机号进行用户信息的查询
        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            # 5.不存在则添加用户
            try:
                User.objects.create_user(
                    username=mobile,
                    mobile=mobile,
                    password=password
                )
            except Exception as e:
                logger.error(e)
                return HttpResponseBadRequest("修改失败，请稍后再试")
        else:
            # 4.如果用户存在，则进行密码修改
            user.set_password(password)
            user.save()

        # 6.进行页面跳转，跳转到登录页面
        response = redirect(reverse("users:login"))
        # 7.返回响应
        return response


# 如果用户没登陆，则会默认跳转到accounts/login/?next=xxx
class UserCenterView(LoginRequiredMixin, View):

    def get(self, request):
        user = request.user
        context = {
            "username": user.username,
            "mobile": user.mobile,
            "avatar": user.avatar.url if user.avatar else None,
            "user_desc": user.user_desc,
        }
        return render(request, "center.html", context=context)

    def post(self, request):
        # 接收数据
        user = request.user
        username = request.POST.get("username", user.username)
        avatar = request.FILES.get("avatar")
        user_desc = request.POST.get("desc", user.user_desc)

        # 修改数据库数据
        try:
            user.username = username
            user.user_desc = user_desc
            if avatar:
                user.avatar = avatar
            user.save()
        except Exception as e:
            logger.error(e)
            return HttpResponseBadRequest("更新失败，请稍后再试")

        # 返回响应，刷新页面
        response = redirect(reverse("users:center"))
        # 更新cookie信息
        response.set_cookie("username", user.username, max_age=30 * 24 * 3600)
        return response


class WriteBlogView(LoginRequiredMixin, View):

    def get(self, request):
        # 获取博客分类信息
        categories = ArticleCategory.objects.all()

        context = {
            'categories': categories
        }
        return render(request, 'write_blog.html', context=context)

    def post(self, request):
        user = request.user
        avatar = request.FILES.get("avatar")
        title = request.POST.get("title")
        category_id = request.POST.get("category")
        tags = request.POST.get("tags")
        summary = request.POST.get("summary")
        content = request.POST.get("content")

        if not all([avatar, title, category_id, tags, summary, content]):
            return HttpResponseBadRequest('参数不全')

        try:
            article_category = ArticleCategory.objects.get(id=category_id)
        except Exception as e:
            logger.error(e)
            return HttpResponseBadRequest("没有此分类信息")

        try:
            article = Article.objects.create(
                author=user,
                avatar=avatar,
                category=article_category,
                tags=tags,
                title=title,
                summary=summary,
                content=content
            )
        except Exception as e:
            logger.error(e)
            return HttpResponseBadRequest('发布失败，请稍后再试')

        response = redirect(reverse('home:index'))
        return response
