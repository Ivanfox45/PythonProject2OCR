# python
import os
import sys
import json
import requests

IAM_URL = "https://iam.api.cloud.yandex.net/iam/v1/tokens"

def mask_secret(s: str, keep: int = 4) -> str:
    if not s:
        return ""
    if len(s) <= keep * 2:
        return "*" * len(s)
    return f"{s[:keep]}...{s[-keep:]}"

def get_oauth_token() -> str:
    # 1) из переменной окружения
    env_token = os.getenv("YANDEX_OAUTH_TOKEN")
    if env_token:
        return env_token.strip()
    # 2) запросить у пользователя скрытым вводом
    try:
        import getpass
        return getpass.getpass("Введите Yandex OAuth токен: ").strip()
    except Exception:
        return input("Введите Yandex OAuth токен: ").strip()

def fetch_iam_token(oauth_token: str, timeout: int = 30) -> dict:
    headers = {"Content-Type": "application/json"}
    data = {"yandexPassportOauthToken": oauth_token}
    try:
        resp = requests.post(IAM_URL, headers=headers, json=data, timeout=timeout)
    except requests.RequestException as e:
        return {"error": {"message": f"Network error: {e}"}}

    # Пытаемся разобрать JSON, даже если статус не 200
    try:
        payload = resp.json()
    except ValueError:
        payload = {"error": {"message": f"Non-JSON response, status={resp.status_code}", "raw": resp.text[:500]}}

    if resp.status_code != 200:
        # Добавим статус и тело в ошибку
        if "error" not in payload:
            payload = {"error": {}}
        payload["error"]["status"] = resp.status_code
        payload["error"]["message"] = payload["error"].get("message") or f"HTTP {resp.status_code}"
    return payload

def main() -> None:
    oauth_token = get_oauth_token()
    if not oauth_token:
        print("OAuth токен не указан.", file=sys.stderr)
        sys.exit(1)

    print(f"Запрашиваю IAM токен по OAuth ({mask_secret(oauth_token)}) ...")
    result = fetch_iam_token(oauth_token)

    if "iamToken" in result:
        iam = result["iamToken"]
        exp = result.get("expiresAt", "<unknown>")
        print("Успех. Получен IAM токен.")
        print(f"expiresAt: {exp}")
        # Не печатаем токен полностью
        print(f"iamToken(masked): {mask_secret(iam)}")
        # Если нужно — выведите в пайп без логов:
        # print(iam, end="")  # но будьте осторожны: это секрет
    else:
        # Печатаем ошибку в читабельном виде
        err = result.get("error") or result
        print("Не удалось получить IAM токен.", file=sys.stderr)
        print(json.dumps(err, ensure_ascii=False, indent=2), file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()
