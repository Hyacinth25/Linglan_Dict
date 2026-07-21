import json
import socket
import urllib.error
import urllib.request


class LLMService:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.api_key = api_key

    def call_chat(self, prompt, model="gpt-4o-mini", temperature=0.7, timeout=12):
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            message = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"API请求失败：{message or e.reason}")
        except urllib.error.URLError:
            raise RuntimeError("网络或API无法连通")
        except socket.timeout:
            raise RuntimeError("网络请求超时")
        choices = result.get("choices") or []
        if not choices:
            raise RuntimeError("LLM返回为空")
        content = choices[0].get("message", {}).get("content", "").strip()
        if not content:
            raise RuntimeError("LLM故事内容为空")
        return content
