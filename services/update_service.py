import json
import re
import urllib.error
import urllib.request


class UpdateService:
    def __init__(self, github_repo, current_version, timeout=8):
        self.github_repo = (github_repo or "").strip()
        self.current_version = (current_version or "").strip()
        self.timeout = timeout

    def latest_release_url(self):
        if not self.github_repo:
            return ""
        return f"https://github.com/{self.github_repo}/releases/latest"

    def fetch_latest_release(self):
        if not self.github_repo:
            raise RuntimeError("尚未配置 GitHub 仓库地址")
        api_url = f"https://api.github.com/repos/{self.github_repo}/releases/latest"
        request = urllib.request.Request(
            api_url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "LinglanDict-Updater",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise RuntimeError("GitHub 还没有可用的 Release") from exc
            raise RuntimeError(f"GitHub 返回错误：{exc.code}") from exc
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            raise RuntimeError(f"无法连接 GitHub：{reason}") from exc

        tag_name = str(payload.get("tag_name") or "").strip()
        latest_version = self.normalize_version(tag_name)
        release_url = str(payload.get("html_url") or self.latest_release_url()).strip()
        body = str(payload.get("body") or "").strip()
        assets = payload.get("assets") if isinstance(payload.get("assets"), list) else []
        asset_url = self._pick_download_asset(assets)

        return {
            "tag_name": tag_name,
            "version": latest_version,
            "release_url": release_url,
            "body": body,
            "asset_url": asset_url,
            "has_update": self.is_newer(latest_version, self.current_version),
        }

    @staticmethod
    def normalize_version(version):
        text = (version or "").strip()
        if text.lower().startswith("v"):
            text = text[1:]
        return text

    @classmethod
    def is_newer(cls, latest_version, current_version):
        latest_key = cls._version_key(latest_version)
        current_key = cls._version_key(current_version)
        return latest_key > current_key

    @staticmethod
    def _version_key(version):
        text = UpdateService.normalize_version(version)
        match = re.match(r"^(\d+(?:\.\d+){0,3})", text)
        if not match:
            return (0, 0, 0, 0)
        parts = [int(part) for part in match.group(1).split(".")]
        while len(parts) < 4:
            parts.append(0)
        return tuple(parts[:4])

    @staticmethod
    def _pick_download_asset(assets):
        candidates = []
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            name = str(asset.get("name") or "").lower()
            url = str(asset.get("browser_download_url") or "").strip()
            if not url:
                continue
            score = 0
            if name.endswith(".zip"):
                score += 3
            if "windows" in name or "win" in name:
                score += 2
            if "x64" in name or "amd64" in name:
                score += 1
            candidates.append((score, url))
        if not candidates:
            return ""
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]
