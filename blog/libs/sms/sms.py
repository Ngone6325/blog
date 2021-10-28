import json
from ronglian_sms_sdk import SmsSDK


class SmsCode:
    __accId = "8aaf07087ca221d8017cc4c3acb306cb"
    __accToken = "6020cadda6294977a7439bbef95adc51"
    __appId = "8aaf07087ca221d8017cc4c3adf606d2"

    def send_message(self, tid, mobile, datas):
        sdk = SmsSDK(self.__accId, self.__accToken, self.__appId)
        resp = sdk.sendMessage(tid, mobile, datas)

        message = json.loads(resp)
        if message.get("statusCode") == "000000":
            return 0   # 发送成功
        return -1  # 发送失败

