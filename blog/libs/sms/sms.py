import json
from random import randint
from ronglian_sms_sdk import SmsSDK

accId = "8aaf07087ca221d8017cc4c3acb306cb"
accToken = "6020cadda6294977a7439bbef95adc51"
appId = "8aaf07087ca221d8017cc4c3adf606d2"


class SmsCode:
    # def __init__(self, mobile):
        # self.tid = "1"
        # self.mobile = str(mobile)
        # self.datas = (str(randint(0, 9999)), "5")

    def send_message(self, tid, mobile, datas):
        sdk = SmsSDK(accId, accToken, appId)
        resp = sdk.sendMessage(tid, mobile, datas)

        message = json.loads(resp)
        if message.get("statusCode") == "000000":
            return 0   # 发送成功
        return -1  # 发送失败


# if __name__ == '__main__':
#     sms_code = SmsCode(13229546760)
#     sms_code.send_message()
