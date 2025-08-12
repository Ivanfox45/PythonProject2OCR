import requests

oauth_token = "y0__xDcirSgqveAAhjB3RMg69yB-ROiJgcc6EUOSHCTjlfOBUBzXPo3Kw"

url = "https://iam.api.cloud.yandex.net/iam/v1/tokens"
headers = {"Content-Type": "application/json"}
data = {"yandexPassportOauthToken": oauth_token}

response = requests.post(url, headers=headers, json=data)
print(response.json())
# {'iamToken': 't1.9euelZqOlpqUzsvLncqPnZiUmc2Nze3rnpWak56XzsaWzZGJnpSMxorMzJPl8_cEO2E7-e8NLSh1_d3z90RpXjv57w0tKHX9zef1656Vmoqdx8vMns2OnYyJmpfKy4vO7_zF656Vmoqdx8vMns2OnYyJmpfKy4vO.ohCeytxtRHRJHNDl63No-kqf2bt-SrWuLuB6q6SZaK4OTIiMNtnSqJVKagsBRmJ0MiheUNs3ev50Vk8Y7ZPNCQ', 'expiresAt': '2025-07-29T04:16:59.559278450Z'}
#t1.9euelZrNl8iZlZmPmYyQjJ2KlJ2dzO3rnpWak56XzsaWzZGJnpSMxorMzJPl8_dCIV47-e9HRyFa_d3z9wJQWzv570dHIVr9zef1656Vmo2dncyPx53OyM6Tm5KNiZyK7_zF656Vmo2dncyPx53OyM6Tm5KNiZyK.dAp69zivkS2doHBa5Rl_XwgTjog9qOVjgsZB0jZOnjZl_4IJc9u8UrbGYyC3UYQOlJITL_BAjp7F6_eMaOBSCQ', 'expiresAt': '2025-07-29T18:50:37.616012856Z'}
#t1.9euelZqTzJGakJyeyMqbxpuSksaUlO3rnpWak56XzsaWzZGJnpSMxorMzJPl8_d2DBQ7-e8rC3Y2_d3z9zY7ETv57ysLdjb9zef1656VmseMkY7IjJjKk46Xk82RnsyY7_zF656VmseMkY7IjJjKk46Xk82RnsyY.O5n-qH-R-Ez7ayB4g_qroxa4_MCewIS9A0yw3TXsFnUiZA9qr3_BcaRIWYt8n98T3ThIAQC9mKzn9vI9lIGsCg