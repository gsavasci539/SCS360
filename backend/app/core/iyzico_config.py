import iyzipay

class IyzicoConfig:
    API_KEY = "sandbox-eXxqr3a5QTwdvoOSYwYU7zR0ZogDzTv3"
    SECRET_KEY = "sandbox-FAXBFu4J7YRfpI3UD4QfTZ8DrlLIRqW1"
    BASE_URL = "sandbox-api.iyzipay.com"

    @staticmethod
    def get_options():
        return {
            'api_key': IyzicoConfig.API_KEY,
            'secret_key': IyzicoConfig.SECRET_KEY,
            'base_url': IyzicoConfig.BASE_URL
        }
