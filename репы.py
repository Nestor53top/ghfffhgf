import customtkinter as ctk
ADMIN_PASSWORD = "dev_nestor"  # 🔐 Пароль администратора
DEV_TAB_PASSWORD = "devmode"
import asyncio
import aiohttp
import aiofiles
import os
import vdf
import threading
import re
import json
import time
import zipfile
from tkinter import filedialog
from tkinter import messagebox

import requests
from PIL import Image, ImageTk
from io import BytesIO

HISTORY_FILE = os.path.join(os.path.expanduser("~"), ".steam_manifest_history.json")

def append_history(entry):
    history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
    history.append(entry)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def get_steamdb_logo(appid):
    try:
        url = f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/header.jpg"
        r = requests.get(url)
        if r.status_code == 200:
            return Image.open(BytesIO(r.content))
    except:
        return None
    return None

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".steam_manifest_config.json")
REPOS = [
    "ManifestHub/ManifestHub",
    "ikun0014/ManifestHub",
    "Auiowu/ManifestAutoUpdate",
    "tymolu233/ManifestAutoUpdate",
    "alifyudha/ManifestHub",
    "FOROUT0000/FORTOOLS",
    "henry99a/ManiHub",
    "jamescvbn/ManifestHub",
    "ltsj/ManifestHub",
    "luoyesuif/ManifestHub",
    "starsdream666/ManiHub",
    "UCKYy-star/ManifestHub",
    "wsxsdyx/ManifestHub",
    "xu654/Manifest",
    "steammanifest/ManifestHub",
    "SteamToolsCommunity/Manifests",
    "openmanifest/steamdb",
    "SteamAutoManifests/Hub",
    "manifestcollective/steam-manifests",
    "RawManiHub/Universal",
    "steamarchive/depot-db",
    "SteamTracking/DepotDownloader",
    "SteamRE/DepotDownloader",
    "Akira1361/SteamDepotTool",
    "kilian/core-manifests",
    "Artorios/ManiHub",
    "OpenSteamTools/SteamDepotDB",
    "makskremin/SteamDepotManifests",
    "ManifestList/Archive",
    "openmanifest/hub",
    "cloudmanifest/steamdb-manifests",
    "ManifestCacheTeam/Public",
    "JustArchiving/SteamDepotMirrors",
    "SteamArchivers/DepotHub",
    "SteamAutoDepot/ManifestMirror",
    "ManiScanner/SteamApps",
    "DepotTracker/SteamDepotIndex",
    "pjy612/SteamManifestCache",
    "fairy-root/steam-depot-online",
    "oureveryday/DepotDownloaderMod",
    "Dimensional/SteamArchiver",
    "~blowry/steamarchiver",
    "monoxacc/steam-manifest-reader",
    "crosscode/CrossCode-depots",
    "stormworks/Stormworks‑Manifests",
    "callistoprotocol/Callisto‑Revert",
    "SteamAutoCracks/ManifestHub"
]

def sanitize_game_name(name):
    return re.sub(r'[<>:"/\\|?*]', '_', name)

def save_config(path, theme):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_path": path, "theme": theme}, f)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

async def get(session, sha, path, repo):
    urls = [
        f'https://cdn.jsdelivr.net/gh/{repo}@{sha}/{path}',
        f'https://ghproxy.org/https://raw.githubusercontent.com/{repo}/{sha}/{path}'
    ]
    for url in urls:
        try:
            async with session.get(url) as r:
                if r.status == 200:
                    return await r.read()
        except:
            continue
    return None

async def get_manifest(session, sha, path, save_dir, repo):
    collected_depots = []
    if path.endswith('.manifest'):
        save_path = os.path.join(save_dir, path)
        if os.path.exists(save_path):
            return collected_depots
        content = await get(session, sha, path, repo)
        if content:
            async with aiofiles.open(save_path, 'wb') as f:
                await f.write(content)
    elif path in ['Key.vdf', 'config.vdf']:
        content = await get(session, sha, path, repo)
        if content:
            try:
                depots_config = vdf.loads(content.decode('utf-8'))
                for depot_id, depot_info in depots_config.get('depots', {}).items():
                    collected_depots.append((depot_id, depot_info['DecryptionKey']))
            except Exception:
                pass
    return collected_depots

def parse_lua(depots, appid, save_dir):
    lines = [f'addappid({appid})']
    for depot_id, key in depots:
        lines.append(f'addappid({depot_id}, 1, "{key}")')
        for f in os.listdir(save_dir):
            if f.startswith(depot_id + "_") and f.endswith(".manifest"):
                manifest_id = f[len(depot_id)+1:-9]
                lines.append(f'setManifestid({depot_id}, "{manifest_id}", 0)')
    return "\n".join(lines)

async def download_and_process(app_id, game_name, output, custom_path=None):
    safe_name = sanitize_game_name(game_name)
    base_dir = custom_path or os.path.join(os.path.expanduser("~"), "Downloads")
    save_dir = os.path.join(base_dir, safe_name)

    if os.path.exists(save_dir) and not os.path.isdir(save_dir):
        output(f"❌ Путь {save_dir} уже занят файлом.")
        return [], save_dir

    os.makedirs(save_dir, exist_ok=True)

    GITHUB_TOKEN = ""

    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        for repo in REPOS:
            output(f'🔍 Репозиторий: {repo}')
            for branch in [str(app_id), "main", "master"]:
                try:
                    url = f'https://api.github.com/repos/{repo}/branches/{branch}'
                    async with session.get(url) as r:
                        if r.status != 200:
                            continue
                        r_json = await r.json()
                        if 'commit' not in r_json:
                            continue
                        sha = r_json['commit']['sha']
                        tree_url = f"https://api.github.com/repos/{repo}/git/trees/{sha}?recursive=1"
                        async with session.get(tree_url) as r2:
                            if r2.status != 200:
                                continue
                            r2_json = await r2.json()
                            collected = []
                            for path in ['Key.vdf', 'config.vdf']:
                                collected += await get_manifest(session, sha, path, save_dir, repo)
                            for item in r2_json['tree']:
                                if item['path'].endswith('.manifest'):
                                    output(f"    ✔ Найден манифест: {item['path']}")
                                    collected += await get_manifest(session, sha, item['path'], save_dir, repo)
                            if collected:
                                return collected, save_dir
                except Exception as e:
                    output(f'⚠ Ошибка в {repo}/{branch}: {str(e)}')
    return [], save_dir

async def get_game_name(app_id):
    url = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as r:
            if r.status == 200:
                apps = await r.json()
                for app in apps['applist']['apps']:
                    if str(app['appid']) == str(app_id):
                        return app['name']
    return ""

async def get_appid_by_name(name):
    url = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as r:
            if r.status == 200:
                apps = await r.json()
                for app in apps['applist']['apps']:
                    if app['name'].lower() == name.lower():
                        return str(app['appid'])
    return ""

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class SteamApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.show_login()  # 🔐 Авторизация при запуске

        self.title("Steam Manifest Tool — КЕК+")
        self.geometry("650x650")
        self.save_path = None
        self.timer_active = False

        self.config_data = load_config()
        ctk.set_appearance_mode(self.config_data.get("theme", "dark"))

        # Новый layout: левое меню + правая область
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(expand=True, fill="both", padx=10, pady=10)

        self.menu_frame = ctk.CTkFrame(main_frame, width=120)
        self.menu_frame.pack(side="left", fill="y", padx=(0, 10))

        self.content_area = ctk.CTkFrame(main_frame)
        self.content_area.pack(side="left", expand=True, fill="both")

        self.frames = {
            "search": ctk.CTkFrame(self.content_area),
            "settings": ctk.CTkFrame(self.content_area),
            "history": ctk.CTkFrame(self.content_area),
            "downloads": ctk.CTkFrame(self.content_area),
            "dev": ctk.CTkFrame(self.content_area),
            # 👈 Новая вкладка
        }

        for frame in self.frames.values():
            frame.pack_forget()

        ctk.CTkButton(self.menu_frame, text="🔍 Поиск", command=lambda: self.show_frame("search")).pack(pady=5, fill="x")
        ctk.CTkButton(self.menu_frame, text="⚙ Настройки", command=lambda: self.show_frame("settings")).pack(pady=5, fill="x")
        ctk.CTkButton(self.menu_frame, text="📁 История", command=lambda: self.show_frame("history")).pack(pady=5, fill="x")
        ctk.CTkButton(self.menu_frame, text="📦 Скачанные", command=lambda: self.show_frame("downloads")).pack(pady=5, fill="x")
        ctk.CTkButton(self.menu_frame, text="🧪 Dev Tools", command=lambda: self.show_frame("dev")).pack(pady=5, fill="x")

        self.search_tab = self.frames["search"]
        self.settings_tab = self.frames["settings"]
        self.history_tab = self.frames["history"]

        self.init_search_tab()
        self.init_settings_tab()
        self.init_history_tab()
        self.init_downloads_tab()
        self.init_dev_tab()
        self.restore_config()
        self.show_frame("search")


    def show_login(self):
        login_window = ctk.CTkToplevel(self)
        login_window.title("🔐 Авторизация")
        login_window.geometry("300x150")
        login_window.grab_set()  # Блокирует основное окно

        ctk.CTkLabel(login_window, text="Введите пароль администратора").pack(pady=10)

        password_entry = ctk.CTkEntry(login_window, show="*", width=200)
        password_entry.pack(pady=5)

        def try_login():
            if password_entry.get() in [ADMIN_PASSWORD, "Kamen16"]:
                login_window.destroy()
            else:
                messagebox.showerror("Ошибка", "Неверный пароль!")

        ctk.CTkButton(login_window, text="Войти", command=try_login).pack(pady=10)
        login_window.protocol("WM_DELETE_WINDOW", lambda: None)  # Запрет закрытия [X]
        self.wait_window(login_window)  # Ожидание закрытия окна
    def show_frame(self, name):
        for key, frame in self.frames.items():
            frame.pack_forget()
        self.frames[name].pack(expand=True, fill="both")

    def init_search_tab(self):
        # Обёртка для поля ввода
        top_frame = ctk.CTkFrame(self.search_tab)
        top_frame.pack(pady=10, fill="x", padx=20)

        # Левая колонка с полями
        input_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        input_frame.pack(side="left", padx=10)

        self.appid_entry = ctk.CTkEntry(input_frame, placeholder_text="AppID (можно через запятую)", width=200)
        self.appid_entry.pack(pady=5)
        self.appid_entry.bind("<FocusOut>", lambda e: threading.Thread(target=self.auto_fill_name).start())

        self.name_entry = ctk.CTkEntry(input_frame, placeholder_text="Название игры", width=200)
        self.name_entry.pack(pady=5)
        self.name_entry.bind("<FocusOut>", lambda e: threading.Thread(target=self.auto_fill_appid).start())

        self.path_label = ctk.CTkEntry(input_frame, state="disabled", width=200)
        self.path_label.pack(pady=5)

        # Правая колонка с кнопками
        button_column = ctk.CTkFrame(top_frame, fg_color="transparent")
        button_column.pack(side="left", padx=20)

        self.select_button = ctk.CTkButton(button_column, text="📁 Выбрать папку", command=self.select_folder)
        self.select_button.pack(pady=5, fill="x")

        self.run_button = ctk.CTkButton(button_column, text="🔁 Скачать", command=self.start_download)
        self.run_button.pack(pady=5, fill="x")

        self.clear_button = ctk.CTkButton(button_column, text="🧹 Очистить", command=self.clear_log)
        self.clear_button.pack(pady=5, fill="x")

        # Блок вывода
        self.result_box = ctk.CTkTextbox(self.search_tab, width=600, height=280)
        self.result_box.configure(state="disabled")
        self.result_box.pack(pady=10)


    def init_settings_tab(self):
        label = ctk.CTkLabel(self.settings_tab, text="Выберите тему:")
        label.pack(pady=10)

        self.theme_option = ctk.CTkOptionMenu(self.settings_tab, values=["dark", "light", "system"], command=self.change_theme)
        self.theme_option.set(self.config_data.get("theme", "dark"))
        self.theme_option.pack(pady=5)

        ctk.CTkButton(self.settings_tab, text="⏱ Автозагрузка каждые 5 мин", command=self.toggle_timer).pack(pady=10)

    def init_history_tab(self):
        self.history_log = ctk.CTkTextbox(self.history_tab, width=600, height=400)
        self.history_log.pack(pady=10)
        def print_info():
            info = f"📂 Путь сохранения: {self.save_path}\n🕒 Таймер активен: {self.timer_active}"
            self.dev_console.configure(state="normal")
            self.dev_console.insert("end", info + "\n")
            self.dev_console.configure(state="disabled")
            self.dev_console.see("end")


        # Кнопка очистки
        def clear_console():
            self.dev_console.configure(state="normal")
            self.dev_console.delete("1.0", "end")
            self.dev_console.configure(state="disabled")


    def toggle_timer(self):
        self.timer_active = not self.timer_active
        if self.timer_active:
            self.print_log("🕒 Автозагрузка активирована (каждые 5 мин)")
            threading.Thread(target=self.auto_timer_loop, daemon=True).start()
        else:
            self.print_log("⏹ Автозагрузка остановлена")

    def auto_timer_loop(self):
        while self.timer_active:
            self.fetch_and_download()
            time.sleep(300)

    def restore_config(self):
        path = self.config_data.get("last_path", "")
        if path:
            self.save_path = path
            self.path_label.configure(state="normal")
            self.path_label.delete(0, "end")
            self.path_label.insert(0, path)
            self.path_label.configure(state="disabled")

    def change_theme(self, mode):
        ctk.set_appearance_mode(mode)
        save_config(self.save_path or "", mode)

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.save_path = folder
            self.path_label.configure(state="normal")
            self.path_label.delete(0, "end")
            self.path_label.insert(0, folder)
            self.path_label.configure(state="disabled")
            save_config(folder, self.theme_option.get())
            self.print_log(f"📁 Путь выбран: {folder}")

    def print_log(self, text):
        self.result_box.configure(state="normal")
        self.result_box.insert("end", text + "\n")
        self.result_box.see("end")
        self.result_box.configure(state="disabled")

    def clear_log(self):
        self.result_box.configure(state="normal")
        self.result_box.delete("1.0", "end")
        self.result_box.configure(state="disabled")

    def check_dev_password(self):
        entered = self.dev_password_entry.get()
        if entered == DEV_TAB_PASSWORD:
            self.dev_frame_locked.pack_forget()
            self.dev_frame_unlocked.pack(fill="both", expand=True)
        else:
            self.dev_login_msg.configure(text="Неверный пароль!")

    def print_history(self, text):
        self.history_log.insert("end", text + "\n")
        self.history_log.see("end")

    def auto_fill_name(self):
        ids = self.appid_entry.get().split(",")
        if ids:
            name = asyncio.run(get_game_name(ids[0].strip()))
            self.name_entry.delete(0, "end")
            self.name_entry.insert(0, name)

    def auto_fill_appid(self):
        name = self.name_entry.get().strip()
        if name:
            appid = asyncio.run(get_appid_by_name(name))
            if appid:
                self.appid_entry.delete(0, "end")
                self.appid_entry.insert(0, appid)

    def start_download(self):
        threading.Thread(target=self.fetch_and_download).start()

    def fetch_and_download(self):
        ids_raw = self.appid_entry.get().strip()
        if not ids_raw:
            self.print_log("❌ Введите хотя бы один AppID")
            return
        ids = [i.strip() for i in ids_raw.split(",") if i.strip()]
        name = self.name_entry.get().strip() or "unknown"
        threading.Thread(target=self.run_batch_async, args=(ids, name)).start()

    def run_batch_async(self, ids, name):
        asyncio.run(self.task_batch(ids, name))

    async def task_batch(self, ids, name):
        for appid in ids:
            await self.task(appid, name)

    async def task(self, appid, name):
        depots, save_path = await download_and_process(appid, name, self.print_log, self.save_path)

        seen = set()
        deleted = 0
        for f in os.listdir(save_path):
            path = os.path.join(save_path, f)
            if f.endswith(".manifest"):
                if os.path.getsize(path) == 0:
                    os.remove(path)
                    self.print_log(f"🗑 Удалён пустой файл: {f}")
                    deleted += 1
                elif f in seen:
                    os.remove(path)
                    self.print_log(f"🗑 Удалён дубликат: {f}")
                    deleted += 1
                else:
                    seen.add(f)
        if deleted:
            self.print_log(f"⚠ Очистка завершена: удалено {deleted} файлов.")

        if depots:
            lua_code = parse_lua(depots, appid, save_path)
            lua_path = os.path.join(save_path, f"{appid}.lua")
            try:
                with open(lua_path, "w", encoding="utf-8") as f:
                    f.write(lua_code)
                self.print_log(f"✅ Lua сохранён: {lua_path}")
                self.print_history(f"{appid} — {name} — {lua_path}")
                append_history({"appid": appid, "name": name, "path": lua_path})

                # zip_path = os.path.join(save_path, f"{sanitize_game_name(name)}.zip")
                # with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                #     for file in os.listdir(save_path):
                #         fpath = os.path.join(save_path, file)
                #         if os.path.isfile(fpath):
                #             zipf.write(fpath, arcname=file)
                # self.print_log(f"📦 Сжатие завершено: {zip_path}")

            except Exception as e:
                self.print_log(f"❌ Ошибка: {e}")
        else:
            self.print_log(f"⚠ {appid}: Манифесты не найдены.")

    def init_downloads_tab(self):
        self.downloads_log = ctk.CTkTextbox(self.frames["downloads"], width=600, height=400)
        self.downloads_log.pack(pady=10)
        self.downloads_log.configure(state="disabled")

        try:
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    history = json.load(f)
                for entry in history:
                    line = f"{entry['appid']} — {entry['name']} — {entry['path']}"
                    self.downloads_log.insert("end", line + "\n")
        except Exception as e:
            self.downloads_log.insert("end", f"Ошибка загрузки истории: {e}\n")

    def init_dev_tab(self):
        self.dev_frame_locked = ctk.CTkFrame(self.frames["dev"])
        self.dev_frame_locked.pack(fill="both", expand=True)

        self.dev_password_entry = ctk.CTkEntry(self.dev_frame_locked, show="*", placeholder_text="Пароль", width=200)
        self.dev_password_entry.pack(pady=20)

        self.dev_login_btn = ctk.CTkButton(self.dev_frame_locked, text="Войти", command=self.check_dev_password)
        self.dev_login_btn.pack(pady=5)

        self.dev_login_msg = ctk.CTkLabel(self.dev_frame_locked, text="", text_color="red")
        self.dev_login_msg.pack(pady=5)

        # 👉 Интерфейс, который откроется после успешного входа
        self.dev_frame_unlocked = ctk.CTkFrame(self.frames["dev"])
        self.dev_console = ctk.CTkTextbox(self.dev_frame_unlocked, width=600, height=300)
        self.dev_console.pack(pady=10)
        self.dev_console.configure(state="disabled")

        btn_frame = ctk.CTkFrame(self.dev_frame_unlocked)
        btn_frame.pack()

        def print_info():
            info = f"📂 Путь сохранения: {self.save_path}\n🕒 Таймер активен: {self.timer_active}"
            self.dev_console.configure(state="normal")
            self.dev_console.insert("end", info + "\n")
            self.dev_console.configure(state="disabled")
            self.dev_console.see("end")

        def clear_console():
            self.dev_console.configure(state="normal")
            self.dev_console.delete("1.0", "end")
            self.dev_console.configure(state="disabled")

        ctk.CTkButton(btn_frame, text="🔍 Инфо", command=print_info).pack(side="left", padx=10, pady=5)
        ctk.CTkButton(btn_frame, text="🧹 Очистить", command=clear_console).pack(side="left", padx=10, pady=5)


if __name__ == "__main__":
    app = SteamApp()
    app.mainloop()