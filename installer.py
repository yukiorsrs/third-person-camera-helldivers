"""Third Person Camera (HD2 Style) for HELLDIVERS: installer.

Patches the player's own game files (nothing from the game is shipped): the script bundle gets the mod scripts,
the render config gets the gbuffer clear fix, and the bundles that carry the skydome get the HD2-style skies.
Every original file is copied to contents/hd2cam_backup before it is touched; Uninstall copies them back."""
import os, sys, json, struct, zlib, hashlib, shutil, threading, traceback
import tkinter as tk
from tkinter import filedialog, messagebox

APP_ID = "394510"
VERSION = "1.1"


def resource(*p):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *p)


# ---------------------------------------------------------------- bundle format (Bitsquid/Stingray 2015)
def murmur64a(data, seed=0):
    m = 0xc6a4a7935bd1e995
    r = 47
    M = (1 << 64) - 1
    h = (seed ^ (len(data) * m)) & M
    n = len(data) // 8
    for i in range(n):
        k = struct.unpack_from("<Q", data, i * 8)[0]
        k = (k * m) & M
        k ^= k >> r
        k = (k * m) & M
        h ^= k
        h = (h * m) & M
    t = data[n * 8:]
    if t:
        v = 0
        for i, b in enumerate(t):
            v |= b << (8 * i)
        h ^= v
        h = (h * m) & M
    h ^= h >> r
    h = (h * m) & M
    h ^= h >> r
    return h


def unpack_bundle(raw):
    ver, usize = struct.unpack_from("<IQ", raw, 0)
    pos, out = 12, bytearray()
    while pos + 4 <= len(raw) and len(out) < usize:
        (c,) = struct.unpack_from("<I", raw, pos)
        pos += 4
        ch = raw[pos:pos + c]
        pos += c
        try:
            out += zlib.decompress(ch)
        except zlib.error:
            out += ch
    return bytes(out[:usize])


def pack_bundle(buf, level=6):
    usize = len(buf)
    padded = buf + b"\0" * ((-usize) % 65536)
    out = bytearray(struct.pack("<IQ", 0xF0000004, usize))
    for i in range(0, len(padded), 65536):
        c = zlib.compress(padded[i:i + 65536], level)
        if len(c) >= 65536:
            c = padded[i:i + 65536]  # incompressible: stored raw, exactly 64 KB, like the game's own bundles
        out += struct.pack("<I", len(c)) + c
    return bytes(out)


def read_entries(buf):
    n = struct.unpack_from("<I", buf, 0)[0]
    head = buf[4:260]
    p = 260 + 16 * n
    ents = []
    for _ in range(n):
        ext, name = struct.unpack_from("<QQ", buf, p)
        p += 16
        nv, unk = struct.unpack_from("<II", buf, p)
        p += 8
        vs = [list(struct.unpack_from("<III", buf, p + 12 * i)) for i in range(nv)]
        p += 12 * nv
        datas = []
        for v in vs:
            datas.append(buf[p:p + v[1]])
            p += v[1]
        ents.append([ext, name, unk, vs, datas])
    if p != len(buf):
        raise ValueError("unexpected bundle layout")
    return head, ents


def write_entries(head, ents):
    out = bytearray(struct.pack("<I", len(ents)) + head)
    for e in ents:
        out += struct.pack("<QQ", e[0], e[1])
    for ext, name, unk, vs, datas in ents:
        out += struct.pack("<QQII", ext, name, len(vs), unk)
        for v, d in zip(vs, datas):
            out += struct.pack("<III", v[0], len(d), v[2])
        for d in datas:
            out += d
    return bytes(out)


LUA = murmur64a(b"lua")
UNIT = murmur64a(b"unit")
MAT = murmur64a(b"material")
TEX = murmur64a(b"texture")
RC = murmur64a(b"render_config")
RC_NAME = murmur64a(b"core/rendering/renderer")
SKY = murmur64a(b"core/editor_slave/units/skydome/skydome")
SKYTEX = 0x6953ca830b6f36f5


# ---------------------------------------------------------------- the three patches
def patch_lua(ents, lua_dir):
    """Replaces the mod scripts this bundle carries (the scripts are split over two bundles); returns their names."""
    repl = {int(f[:-4], 16): open(os.path.join(lua_dir, f), "rb").read() for f in os.listdir(lua_dir)}
    hit = set()
    for e in ents:
        if e[0] == LUA and e[1] in repl:
            e[4][0] = repl[e[1]]
            hit.add(e[1])
    return hit


def patch_render_config(ents):
    old = b"mask self_illumination light_accumulation\x00"
    new = b"albedo normal mask self_illumination light_accumulation\x00"
    ptr_off = 8420
    for e in ents:
        if e[0] == RC and e[1] == RC_NAME:
            out = []
            for d in e[4]:
                at = d.index(old)
                if struct.unpack_from("<I", d, ptr_off)[0] != at:
                    raise ValueError("render config layout differs")
                b = bytearray(d)
                while len(b) % 4:
                    b += b"\0"
                new_at = len(b)
                b += new
                while len(b) % 4:
                    b += b"\0"
                struct.pack_into("<I", b, ptr_off, new_at)
                out.append(bytes(b))
            e[4] = out
            return
    raise ValueError("render config not found")


def make_night_dds(template_path, out_path, size=2048):
    """Builds the night sky (black with one-texel stars, same seed and rules as skygen.py) instead of shipping
    a 21 MB file: the download stays small. Mipmaps are box-averaged, touching only the texels with stars."""
    import random
    rnd = random.Random(777)
    base = (0, 0, 1)
    stars = {}
    tints = ((255, 255, 255), (210, 222, 255), (255, 238, 215), (228, 232, 255))
    for _ in range(int(size * size * 0.0012)):
        x, y = rnd.randrange(size), rnd.randrange(size)
        bright = rnd.random() ** 4
        t = rnd.choice(tints)
        lvl = 55 + bright * 200
        old = stars.get((x, y), base)
        stars[(x, y)] = tuple(max(old[c], int(t[c] * lvl / 255)) for c in range(3))
    tpl = open(template_path, "rb").read()
    head = bytearray(tpl[:128])
    trail = tpl[128 + sum((256 >> i) ** 2 * 4 for i in range(9)):]
    mips = size.bit_length()
    struct.pack_into("<I", head, 12, size)
    struct.pack_into("<I", head, 16, size)
    struct.pack_into("<I", head, 20, size * 4)
    struct.pack_into("<I", head, 28, mips)
    bg = bytes((base[2], base[1], base[0], 255))
    with open(out_path, "wb") as f:
        f.write(head)
        level, s = stars, size
        for _ in range(mips):
            row = bytearray(bg * (s * s))
            for (x, y), c in level.items():
                i = (y * s + x) * 4
                row[i:i + 4] = bytes((c[2], c[1], c[0], 255))
            f.write(row)
            # next mip: average of 2x2 blocks; blocks without stars stay background
            acc = {}
            for (x, y), c in level.items():
                k = (x // 2, y // 2)
                a = acc.setdefault(k, [0, 0, 0, 0])
                a[0] += c[0]; a[1] += c[1]; a[2] += c[2]; a[3] += 1
            level = {k: tuple(int((a[c] + base[c] * (4 - a[3])) / 4) for c in range(3)) for k, a in acc.items()}
            s = max(1, s // 2)
        f.write(trail)


MENU_BUNDLE = "ec181385e7000cf1"
# fog-tint skies: one flat colour per (r, g, b) level with the brightest channel at full. The mod picks the one
# closest to the level's own fog colour and sets its intensity to the fog's brightness (same levels in patch.py)
TINT_LV = (0, 0.06, 0.18, 0.36, 0.62, 1)
TINTS = [f"t_{r}{g}{b}" for r in range(6) for g in range(6) for b in range(6) if max(r, g, b) == 5]
SKY_SETS = ["city", "desert", "forest", "lava", "snow", "night", "dusk"] + TINTS


def make_tint_dds(template_path, out_path, name, size=8):
    """Flat sky of one fog-tint colour (linear level stored as is), with its mipmaps."""
    lv = [round(TINT_LV[int(c)] * 255) for c in name[2:]]
    tpl = open(template_path, "rb").read()
    head = bytearray(tpl[:128])
    trail = tpl[128 + sum((256 >> i) ** 2 * 4 for i in range(9)):]
    mips = size.bit_length()
    struct.pack_into("<I", head, 12, size)
    struct.pack_into("<I", head, 16, size)
    struct.pack_into("<I", head, 20, size * 4)
    struct.pack_into("<I", head, 28, mips)
    px = bytes((lv[2], lv[1], lv[0], 255))
    with open(out_path, "wb") as f:
        f.write(head)
        for i in range(mips):
            f.write(px * (max(1, size >> i) ** 2))
        f.write(trail)


def add_mission_skies(ents, template_ents, sky_dir):
    """Adds every mod sky (mod/sky/<name>) to the mission_start bundle, which the mod loads in every mission.
    The dome unit, material and texture header are copied from the player's own menu bundle (not shipped)."""
    unit = mat = tex = None
    for e in template_ents:
        if e[0] == TEX and e[1] == SKYTEX:
            tex = e
        elif e[0] == UNIT and e[1] == SKY:
            unit = e
        elif e[0] == MAT and e[1] == SKY:
            mat = e
    if not (unit and mat and tex):
        raise ValueError("skydome not found in the menu bundle")
    sky8, tex8 = struct.pack("<Q", SKY), struct.pack("<Q", SKYTEX)
    for name in SKY_SETS:
        dds = open(os.path.join(sky_dir, name + ".dds"), "rb").read()
        u_name = murmur64a(f"mod/sky/{name}".encode())
        t_name = murmur64a(f"mod/sky/{name}_tex".encode())
        ents = [e for e in ents if e[1] not in (u_name, t_name)]
        ents += [
            [TEX, t_name, tex[2], [list(v) for v in tex[3]], [dds for _ in tex[4]]],
            [MAT, u_name, mat[2], [list(v) for v in mat[3]], [d.replace(tex8, struct.pack("<Q", t_name)) for d in mat[4]]],
            [UNIT, u_name, unit[2], [list(v) for v in unit[3]], [d.replace(sky8, struct.pack("<Q", u_name)) for d in unit[4]]],
        ]
    return ents


def patch_sky(ents, sky_dir, sets):
    """The shared skydome texture gets the HD2 sky, and for every name in `sets` a copy of the dome is added
    (mod/sky/<name>) with that sky's texture. Mission skies must live in the biome bundles themselves: the menu
    bundle's resources are not available in missions, and spawning a missing sky crashes the game."""
    hd2 = open(os.path.join(sky_dir, "hd2.dds"), "rb").read()
    unit = mat = tex = None
    for e in ents:
        if e[0] == TEX and e[1] == SKYTEX:
            e[4] = [hd2 for _ in e[4]]
            tex = e
        elif e[0] == UNIT and e[1] == SKY:
            unit = e
        elif e[0] == MAT and e[1] == SKY:
            mat = e
    if not (unit and mat and tex):
        raise ValueError("skydome not found")
    sky8, tex8 = struct.pack("<Q", SKY), struct.pack("<Q", SKYTEX)
    for biome in sets:
        mine = open(os.path.join(sky_dir, biome + ".dds"), "rb").read()
        u_name = murmur64a(f"mod/sky/{biome}".encode())
        t_name = murmur64a(f"mod/sky/{biome}_tex".encode())
        ents = [e for e in ents if e[1] not in (u_name, t_name)]
        ents += [
            [TEX, t_name, tex[2], [list(v) for v in tex[3]], [mine for _ in tex[4]]],
            [MAT, u_name, mat[2], [list(v) for v in mat[3]], [d.replace(tex8, struct.pack("<Q", t_name)) for d in mat[4]]],
            [UNIT, u_name, unit[2], [list(v) for v in unit[3]], [d.replace(sky8, struct.pack("<Q", u_name)) for d in unit[4]]],
        ]
    return ents


# ---------------------------------------------------------------- game folder
def is_game_dir(p):
    return bool(p) and os.path.exists(os.path.join(p, "contents", "9e13b2414b41b842"))


def find_game():
    """Steam's own records first (every library, the app manifest, the uninstall entry), then common folders on
    every drive."""
    libs = []
    uninst = None
    try:
        import winreg
        for hive, key, val in ((winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
                               (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
                               (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath")):
            try:
                libs.append(winreg.QueryValueEx(winreg.OpenKey(hive, key), val)[0].replace("/", "\\"))
            except OSError:
                pass
        for view in (0, winreg.KEY_WOW64_32KEY):
            try:
                k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                   r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Steam App " + APP_ID,
                                   0, winreg.KEY_READ | view)
                p = winreg.QueryValueEx(k, "InstallLocation")[0]
                if is_game_dir(p):
                    uninst = p
            except OSError:
                pass
    except ImportError:
        pass
    for steam in list(libs):
        vdf = os.path.join(steam, "steamapps", "libraryfolders.vdf")
        if os.path.exists(vdf):
            for line in open(vdf, encoding="utf-8", errors="ignore"):
                line = line.strip()
                if line.startswith('"path"'):
                    libs.append(line.split('"')[3].replace("\\\\", "\\"))
    for d in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        for sub in (r"Program Files (x86)\Steam", r"Program Files\Steam", "Steam", "SteamLibrary", r"Games\Steam",
                    r"Games\SteamLibrary", r"Jogos\Steam", r"Jogos\SteamLibrary"):
            libs.append(f"{d}:\\{sub}")
    # 1) the library whose app manifest says the game is installed there (what Steam actually launches)
    seen = []
    for lib in libs:
        if lib.lower() not in [s.lower() for s in seen] and os.path.isdir(lib):
            seen.append(lib)
    for lib in seen:
        acf = os.path.join(lib, "steamapps", f"appmanifest_{APP_ID}.acf")
        if os.path.exists(acf):
            for line in open(acf, encoding="utf-8", errors="ignore"):
                if line.strip().startswith('"installdir"'):
                    p = os.path.join(lib, "steamapps", "common", line.split('"')[3])
                    if is_game_dir(p):
                        return p
    # 2) Windows' uninstall entry, 3) a Helldivers folder in any known library / common Steam folder
    if uninst:
        return uninst
    for lib in seen:
        p = os.path.join(lib, "steamapps", "common", "Helldivers")
        if is_game_dir(p):
            return p
    return None


def close_game(log):
    """Closes HELLDIVERS if it is open (asks it to close first, then forces it). Returns when it is gone, or after
    a few seconds: a game process stuck while exiting does not lock the files."""
    import subprocess, time
    flags = 0x08000000

    def running():
        try:
            out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq helldivers.exe", "/FO", "CSV", "/NH"],
                                 capture_output=True, text=True, creationflags=flags).stdout
            return "helldivers.exe" in out.lower()
        except Exception:
            return False

    if not running():
        return
    log("Fechando o jogo / Closing the game...")
    subprocess.run(["taskkill", "/IM", "helldivers.exe"], capture_output=True, creationflags=flags)
    for _ in range(10):
        time.sleep(0.5)
        if not running():
            return
    subprocess.run(["taskkill", "/F", "/IM", "helldivers.exe"], capture_output=True, creationflags=flags)
    for _ in range(10):
        time.sleep(0.5)
        if not running():
            return
    time.sleep(1)


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def retry(fn, tries=20):
    """A game that was just closed can hold its files for a moment."""
    import time
    for i in range(tries):
        try:
            return fn()
        except PermissionError:
            if i == tries - 1:
                raise
            time.sleep(0.5)


def build_one(h, info, contents, backup, data_dir, sky_dir):
    """Worker process: returns (name, is_known_original, scripts_placed); writes contents/<name>.hd2cam_tmp."""
    bk = os.path.join(backup, h)
    src = bk if os.path.exists(bk) else os.path.join(contents, h)
    if not os.path.exists(src):
        return h, False, set()
    raw = open(src, "rb").read()
    if hashlib.sha256(raw).hexdigest() != info["sha256"]:
        return h, False, set()
    head, ents = read_entries(unpack_bundle(raw))
    found = set()
    if info["kind"] == "lua":
        found = patch_lua(ents, os.path.join(data_dir, "lua"))
    elif info["kind"] == "render_config":
        patch_render_config(ents)
    elif info["kind"] == "mission_sky":
        # the dome comes from the player's own (untouched) menu bundle, checked like every other file
        tpl = open(os.path.join(contents, MENU_BUNDLE), "rb").read()
        if hashlib.sha256(tpl).hexdigest() != info["template_sha256"]:
            return h, False, set()
        ents = add_mission_skies(ents, read_entries(unpack_bundle(tpl))[1], sky_dir)
    else:
        # each biome bundle: its daytime sky plus the night and dusk/dawn skies; other bundles: shared sky only
        sets = [info["biome"], "night", "dusk"] if info.get("biome") else []
        ents = patch_sky(ents, sky_dir, sets)
    open(os.path.join(contents, h + ".hd2cam_tmp"), "wb").write(pack_bundle(write_entries(head, ents), level=1))
    return h, True, found


# ---------------------------------------------------------------- install / uninstall
def install(game, log, progress):
    contents = os.path.join(game, "contents")
    backup = os.path.join(contents, "hd2cam_backup")
    os.makedirs(backup, exist_ok=True)
    orig = json.load(open(resource("data", "originals.json")))

    from concurrent.futures import ProcessPoolExecutor, as_completed
    workers = max(2, min(8, os.cpu_count() or 4))
    data_dir = resource("data")
    # the night sky is generated here (once) next to the shipped skies, in the mod's own backup folder
    sky_dir = os.path.join(backup, "sky")
    os.makedirs(sky_dir, exist_ok=True)
    for f in os.listdir(os.path.join(data_dir, "sky")):
        shutil.copyfile(os.path.join(data_dir, "sky", f), os.path.join(sky_dir, f))
    if not os.path.exists(os.path.join(sky_dir, "night.dds")):
        log("Gerando o ceu noturno / Building the night sky...")
        make_night_dds(os.path.join(sky_dir, "hd2.dds"), os.path.join(sky_dir, "night.dds"))
    for t in TINTS:
        make_tint_dds(os.path.join(sky_dir, "hd2.dds"), os.path.join(sky_dir, t + ".dds"), t)
    log(f"Instalando com {workers} nucleos / Installing on {workers} cores...")

    # 1) one read per file: check it is the known original, patch it and write the result next to it as a temp
    #    file. Nothing in the game folder is replaced until every file has passed.
    results = {}
    with ProcessPoolExecutor(workers) as ex:
        futs = [ex.submit(build_one, h, info, contents, backup, data_dir, sky_dir) for h, info in orig.items()]
        for n, f in enumerate(as_completed(futs)):
            h, ok, found = f.result()
            results[h] = (ok, found)
            progress((n + 1) / len(futs) * 0.95)
    bad = [h for h, (ok, _) in results.items() if not ok]
    if bad:
        for h in orig:
            tmp = os.path.join(contents, h + ".hd2cam_tmp")
            if os.path.exists(tmp):
                os.remove(tmp)
        raise RuntimeError("Arquivos do jogo diferentes do esperado (versao do jogo diferente ou outro mod instalado). "
                           "Verifique a integridade dos arquivos na Steam e tente de novo.\n"
                           f"Game files differ from the expected version ({len(bad)} files). "
                           "Verify the game files in Steam and try again.")
    placed = set()
    for _, found in results.values():
        placed |= found
    if len(placed) != len(os.listdir(os.path.join(data_dir, "lua"))):
        raise RuntimeError("Nem todos os scripts do mod foram encontrados / Not every mod script was found.")

    # 2) swap: original -> backup folder, patched temp -> game file (renames on the same disk: instant)
    for h in orig:
        bk = os.path.join(backup, h)
        if not os.path.exists(bk):
            retry(lambda: os.replace(os.path.join(contents, h), bk))
        retry(lambda: os.replace(os.path.join(contents, h + ".hd2cam_tmp"), os.path.join(contents, h)))
    log(f"  {len(orig)} arquivos / files")
    progress(1)
    open(os.path.join(backup, "installed.txt"), "w").write(VERSION)


def uninstall(game, log, progress):
    contents = os.path.join(game, "contents")
    backup = os.path.join(contents, "hd2cam_backup")
    if not os.path.isdir(backup):
        raise RuntimeError("O mod nao esta instalado / The mod is not installed.")
    files = [f for f in os.listdir(backup) if len(f) == 16]
    for i, f in enumerate(files):
        progress(i / max(1, len(files)))
        # a rename back into place: instant, the backup folder is removed afterwards anyway
        retry(lambda: os.replace(os.path.join(backup, f), os.path.join(contents, f)))
    log(f"  {len(files)} arquivos restaurados / files restored")
    shutil.rmtree(backup)
    progress(1)


# ---------------------------------------------------------------- window
class App:
    def __init__(self, root):
        self.root = root
        root.title(f"Third Person Camera {VERSION} - HELLDIVERS")
        root.geometry("620x450")
        tk.Label(root, text="THIRD PERSON CAMERA", font=("Segoe UI", 16, "bold")).pack(pady=(12, 0))
        tk.Label(root, text="HELLDIVERS 2 style  -  for HELLDIVERS", font=("Segoe UI", 10)).pack(pady=(0, 4))
        tk.Label(root, text="Pasta do jogo / Game folder:").pack()
        row = tk.Frame(root)
        row.pack(fill="x", padx=12)
        self.path = tk.StringVar(value=find_game() or "")
        tk.Entry(row, textvariable=self.path).pack(side="left", fill="x", expand=True)
        tk.Button(row, text="...", command=self.browse).pack(side="left", padx=4)
        btns = tk.Frame(root)
        btns.pack(pady=8)
        self.b_inst = tk.Button(btns, text="Instalar / Install", width=20, command=lambda: self.run(install, "Instalado! / Installed!"))
        self.b_inst.pack(side="left", padx=6)
        self.b_un = tk.Button(btns, text="Desinstalar / Uninstall", width=20, command=lambda: self.run(uninstall, "Desinstalado. / Uninstalled."))
        self.b_un.pack(side="left", padx=6)
        self.bar = tk.Canvas(root, height=14, bg="#222", highlightthickness=0)
        self.bar.pack(fill="x", padx=12)
        self.text = tk.Text(root, height=14, bg="#111", fg="#ddd")
        self.text.pack(fill="both", expand=True, padx=12, pady=8)

    def browse(self):
        d = filedialog.askdirectory(title="Pasta do Helldivers / Helldivers folder")
        if d:
            self.path.set(d)

    def log(self, msg):
        self.root.after(0, lambda: (self.text.insert("end", msg + "\n"), self.text.see("end")))

    def progress(self, f):
        def draw():
            self.bar.delete("all")
            self.bar.create_rectangle(0, 0, self.bar.winfo_width() * f, 14, fill="#f5c400", width=0)
        self.root.after(0, draw)

    def run(self, job, done_msg):
        game = self.path.get().strip()
        if not is_game_dir(game):
            game = find_game() or ""
            self.path.set(game)
        if not is_game_dir(game):
            messagebox.showerror("Erro / Error", "HELLDIVERS nao encontrado. Escolha a pasta do jogo em \"...\".\n"
                                                 "HELLDIVERS not found. Pick the game folder with \"...\".")
            return
        self.b_inst.config(state="disabled")
        self.b_un.config(state="disabled")

        def work():
            try:
                close_game(self.log)
                job(game, self.log, self.progress)
                self.root.after(0, lambda: messagebox.showinfo("OK", done_msg))
            except Exception as e:
                self.log(traceback.format_exc())
                msg = str(e)
                self.root.after(0, lambda: messagebox.showerror("Erro / Error", msg))
            finally:
                self.root.after(0, lambda: (self.b_inst.config(state="normal"), self.b_un.config(state="normal")))

        threading.Thread(target=work, daemon=True).start()


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()  # worker processes inside the PyInstaller exe
    # silent mode: HD2CamMod_Installer.exe --install | --uninstall  (writes hd2cam_install.log next to the exe)
    if len(sys.argv) > 1 and sys.argv[1] in ("--install", "--uninstall"):
        logp = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "hd2cam_install.log")
        with open(logp, "w", encoding="utf-8") as lf:
            def say(m):
                lf.write(m + "\n")
                lf.flush()
            try:
                g = find_game()
                if not g:
                    raise RuntimeError("HELLDIVERS not found")
                say("game: " + g)
                close_game(say)
                (install if sys.argv[1] == "--install" else uninstall)(g, say, lambda f: None)
                say("OK")
            except Exception:
                say(traceback.format_exc())
                sys.exit(1)
        sys.exit(0)
    root = tk.Tk()
    App(root)
    root.mainloop()
