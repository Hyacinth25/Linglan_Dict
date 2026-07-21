import os
import shutil
import sys
from pathlib import Path


def _translation_data_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class _SingleSentenceSentencizer:
    def split_sentences(self, text):
        return [text]


class SentenceTranslationService:
    def __init__(
        self,
        from_code="en",
        to_code="zh",
        project_dir=None,
        offline_dir_name="offline_assets",
        packages_subdir="argos_packages",
        stanza_subdir="stanza_resources",
    ):
        self.from_code = from_code
        self.to_code = to_code
        self.project_dir = os.path.abspath(
            project_dir or _translation_data_dir()
        )

        self.offline_root = os.path.join(self.project_dir, offline_dir_name)
        self.offline_packages_dir = os.path.join(self.offline_root, packages_subdir)
        self.offline_stanza_dir = os.path.join(self.offline_root, stanza_subdir)

        # Writable runtime mirror used when offline assets are read-only.
        self.runtime_root = os.path.join(self.project_dir, "offline_runtime")
        self.runtime_packages_dir = os.path.join(self.runtime_root, packages_subdir)
        self.runtime_stanza_dir = os.path.join(self.runtime_root, stanza_subdir)

        self._translator = None
        self._init_error = None
        self._init_attempted = False
        self._paths_configured = False

    def _matches_code(self, code, target):
        code = (code or "").lower()
        target = (target or "").lower()
        return code == target or code.startswith(target + "_")

    def _dir_allows_temp_create_delete(self, folder):
        folder_path = Path(folder)
        folder_path.mkdir(parents=True, exist_ok=True)
        probe = folder_path / "__write_delete_probe__.tmp"
        try:
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            return True
        except Exception:
            return False

    def _copy_tree(self, src, dst):
        src_path = Path(src)
        if not src_path.exists():
            return
        dst_path = Path(dst)
        dst_path.mkdir(parents=True, exist_ok=True)
        for item in src_path.iterdir():
            target = dst_path / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
            else:
                shutil.copy2(item, target)

    def _prepare_runtime_assets(self):
        source_packages = Path(self.offline_packages_dir)
        if not source_packages.exists():
            raise RuntimeError(f"??????????: {source_packages}")

        if self._dir_allows_temp_create_delete(self.offline_packages_dir):
            packages_dir = Path(self.offline_packages_dir)
            stanza_dir = Path(self.offline_stanza_dir) if Path(self.offline_stanza_dir).exists() else None
            return packages_dir, stanza_dir

        self._copy_tree(self.offline_packages_dir, self.runtime_packages_dir)
        if Path(self.offline_stanza_dir).exists():
            self._copy_tree(self.offline_stanza_dir, self.runtime_stanza_dir)
            stanza_dir = Path(self.runtime_stanza_dir)
        else:
            stanza_dir = None
        return Path(self.runtime_packages_dir), stanza_dir

    def _configure_argos_paths(self, argos_settings):
        if self._paths_configured:
            return

        packages_dir, stanza_dir = self._prepare_runtime_assets()

        runtime_root = packages_dir.parent
        cache_dir = runtime_root / "cache"
        downloads_dir = cache_dir / "downloads"
        config_dir = runtime_root / "config"
        minisbd_cache_dir = runtime_root / "minisbd"

        for folder in (runtime_root, packages_dir, cache_dir, downloads_dir, config_dir, minisbd_cache_dir):
            folder.mkdir(parents=True, exist_ok=True)

        argos_settings.data_dir = runtime_root
        argos_settings.package_data_dir = packages_dir
        argos_settings.legacy_package_data_dir = packages_dir
        argos_settings.package_dirs = [packages_dir]
        argos_settings.cache_dir = cache_dir
        argos_settings.downloads_dir = downloads_dir
        argos_settings.config_dir = config_dir
        argos_settings.local_package_index = runtime_root / "index.json"

        # Keep minisbd cache local if this module is imported.
        try:
            import minisbd.models as minisbd_models

            minisbd_models.cache_dir = str(minisbd_cache_dir)
        except Exception:
            pass
        try:
            import argostranslate.sbd as argos_sbd

            argos_sbd.minisbd_models.cache_dir = str(minisbd_cache_dir)
        except Exception:
            pass

        # Avoid stanza network requests in offline mode.
        if hasattr(argos_settings, "ChunkType") and hasattr(argos_settings, "chunk_type"):
            argos_settings.chunk_type = argos_settings.ChunkType.MINISBD

        if stanza_dir and stanza_dir.exists():
            os.environ["STANZA_RESOURCES_DIR"] = str(stanza_dir)

        self._paths_configured = True

    def _find_translation(self, installed_languages):
        from_lang = None
        for lang in installed_languages:
            if self._matches_code(getattr(lang, "code", ""), self.from_code):
                from_lang = lang
                break
        if not from_lang:
            return None

        for lang in installed_languages:
            if not self._matches_code(getattr(lang, "code", ""), self.to_code):
                continue
            try:
                translation = from_lang.get_translation(lang)
            except Exception:
                translation = None
            if translation:
                return translation
        return None

    def _force_single_sentence_mode(self, translation):
        if not translation:
            return translation
        try:
            underlying = getattr(translation, "underlying", None)
            if underlying is not None and hasattr(underlying, "sentencizer"):
                underlying.sentencizer = _SingleSentenceSentencizer()
            elif hasattr(translation, "sentencizer"):
                translation.sentencizer = _SingleSentenceSentencizer()
        except Exception:
            pass
        return translation

    def _translation_usable(self, translation):
        if not translation:
            return False
        try:
            translation.translate("hello")
            return True
        except Exception:
            return False

    def _init_translator(self):
        if self._translator:
            return self._translator
        if self._init_attempted and self._init_error:
            raise RuntimeError(self._init_error)

        self._init_attempted = True
        try:
            import argostranslate.settings as argos_settings

            self._configure_argos_paths(argos_settings)

            import argostranslate.translate as argos_translate
        except Exception as e:
            self._init_error = f"Argos ?????: {e}"
            raise RuntimeError(self._init_error) from e

        installed = argos_translate.get_installed_languages()
        translation = self._find_translation(installed)
        translation = self._force_single_sentence_mode(translation)
        if self._translation_usable(translation):
            self._translator = translation
            return self._translator

        self._init_error = (
            "???????????? offline_assets/argos_packages ????? en->zh ???"
            f"????: {self.offline_packages_dir}"
        )
        raise RuntimeError(self._init_error)

    def preload(self):
        self._init_translator()
        return True

    def translate_sentence(self, text):
        source = (text or "").strip()
        if not source:
            return ""

        translator = self._init_translator()
        try:
            return translator.translate(source)
        except Exception as e:
            raise RuntimeError(f"??????: {e}") from e
