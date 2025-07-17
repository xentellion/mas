import json
import os
import requests
import subprocess
import uuid
from datetime import datetime
from dotenv import load_dotenv
from pydantic import BaseModel


load_dotenv()

TOKEN = os.getenv("TOKEN_GIGACHAT")
AUTH_PATH = "app/access_token.json"
CERT_PATH_DEFAULT = "app/ca-gigachat.pem"
CERT_CREATE_PATH = "app/gen_cert.sh"


class GigaChatAccessToken(BaseModel):
    access_token: str
    expires_at: int


class GigachatSession:
    def __init__(self):
        self.access_data = None
        self.cert = self.get_cerificate()

    def request(
        self,
        system_content,
        prompt,
        model="GigaChat-2",
        scope="GIGACHAT_API_PERS",
    ):
        self.check_access_token()

        url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
        request_uuid = uuid.uuid4()

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "RqUID": str(request_uuid),
            "Authorization": f"Bearer {self.access_data.access_token}",
        }

        payload = json.dumps(
            {
                "scope": scope,
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": system_content,
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                "stream": False,
                "update_interval": 0,
            }
        )
        try:
            response = requests.request(
                "POST",
                url,
                headers=headers,
                data=payload,
                verify=self.cert,
            )
        except requests.exceptions.SSLError as e:
            print(f"\033[1;31m {e}\033[0m")
            self.cert = self.create_certificate()
            response = requests.request(
                "POST",
                url,
                headers=headers,
                data=payload,
                verify=self.cert,
            )
            return response.json()["choices"]
        return response.json()["choices"]

    # certificates
    def get_cerificate(self):
        if os.path.isfile(CERT_PATH_DEFAULT):
            return CERT_PATH_DEFAULT
        self.create_certificate()

    def create_certificate(self):
        try:
            subprocess.run([CERT_CREATE_PATH], shell=True)
        except Exception as e:
            print(e)
            return None
        return CERT_PATH_DEFAULT

    # access token
    def get_access_token(self):
        if not os.path.isfile(AUTH_PATH):
            return None
        with open(AUTH_PATH, "r", encoding="utf-8") as f:
            try:
                data = GigaChatAccessToken(**json.load(f))
            except json.JSONDecodeError:
                print("Error decoding auth token file - loading a new one")
                return None
        if datetime.now() >= datetime.fromtimestamp(data.expires_at / 1e3):
            return None
        return data

    def create_access_token(self):
        request_uuid = uuid.uuid4()
        url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        payload = {"scope": "GIGACHAT_API_PERS"}

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": str(request_uuid),
            "Authorization": f"Basic {TOKEN}",
        }

        try:
            response = requests.request(
                "POST",
                url=url,
                headers=headers,
                data=payload,
                verify=self.cert,
            ).json()
        except requests.exceptions.RequestException as e:
            print("Authentication token request error")
            raise SystemExit(e)

        with open(AUTH_PATH, "w", encoding="utf-8") as f:
            json.dump(
                response,
                f,
                sort_keys=False,
                indent=4,
                ensure_ascii=False,
            )
        try:
            answer = GigaChatAccessToken(**response)
            return answer
        except Exception as e:
            print(f"\033[1;31m {e}\033[0m")
            return None

    def check_access_token(self):
        if self.access_data is None:
            a_t = self.get_access_token()
            if a_t is not None:
                self.access_data = a_t
            else:
                self.access_data = self.create_access_token()
        elif datetime.now() >= datetime.fromtimestamp(
            self.access_data.expires_at / 1e3
        ):
            self.access_data = self.create_access_token()
