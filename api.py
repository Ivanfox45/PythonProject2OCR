import requests

oauth_token = "y0__xDcirSgqveAAhjB3RMg69yB-ROiJgcc6EUOSHCTjlfOBUBzXPo3Kw"

url = "https://iam.api.cloud.yandex.net/iam/v1/tokens"
headers = {"Content-Type": "application/json"}
data = {"yandexPassportOauthToken": oauth_token}

response = requests.post(url, headers=headers, json=data)
print(response.json())

t1.9euelZqJmsaJzcqUjJPPmpSJlsaPku3rnpWak56XzsaWzZGJnpSMxorMzJPl8_cIMBM7-e8XdxJ0_N3z90heEDv57xd3EnT8zef1656VmovGjY6Jy8aMnJPLipmRjY7M7_zF656VmovGjY6Jy8aMnJPLipmRjY7M.a8jVKjlRefHpJ2alODrhcvWAnWtWhT4sirNOsG5MeMgYl6SiWca_hzFU7EUeGhLLlaOR6rCc7WIBywoPpK8sDw
