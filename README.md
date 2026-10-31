# Third Person Camera (HD2 Style) for HELLDIVERS

Play **HELLDIVERS (Dive Harder Edition)** with the over-the-shoulder camera of **HELLDIVERS 2**.

**[⬇ Download v2.1](https://github.com/yukiorsrs/third-person-camera-helldivers/releases/latest)**

![Shoulder camera](screenshots/01_shoulder_camera_desert.jpg)

## What it does

The top-down view is replaced by an over-the-shoulder camera with free aim on mouse and controller, a first person view for aiming, pings for your squad, and the world was adjusted so it looks right from the ground: a real sky, your Super Destroyer above you and a few cinematic moments.

- Shoulder camera with free mouse look and a center crosshair
- First person while aiming, with real scopes for the Liberator, Justice, Stalwart, Marksman rifle and Railgun
- Ping: an eye on a spot, a red scope with the enemy's name on an enemy (uses the game's own map marker)
- Esc > THIRD PERSON CONTROLS: a separate set of buttons for third person, PRESS / HOLD / DOUBLE TAP for the main actions
- Co-op: shows when a player with or without the mod joins
- Aim (right mouse) brings the camera to your shoulder and zooms in
- The camera doesn't clip through rocks and walls
- Cameras for the mech, APC, bike, turrets and seats
- Your upper body follows your aim and bullets go where you point
- Grenades and stratagems land where you aim
- Smoother HD2-style dive
- A sky in the colour of each map's own fog, for every biome and time of day, plus a starry night sky
- One-colour fog, and trees, rocks and buildings keep their full detail further away
- Your Super Destroyer in the sky, with hellpods and orbital strikes coming from it
- Hellpod descent camera and extraction camera
- Camera shake on explosions and a taller stratagem beam
- HUD labels only show when you look at them
- The ship lobby uses the shoulder camera too
- Full controller support with the HELLDIVERS 2 button layout, every button can be changed
- In-game settings menu: sensitivity, FOV, camera distance / shoulder / height, controller buttons, compass
- HELLDIVERS 2 style compass that shows the map markers with their distance
- Orbital strikes come from your Super Destroyer: shells fly down from it and beams (Orbital Strike laser, Railcannon) reach up to it
- Eagle strikes: the plane flies over the strike for as long as it lasts and the bombs fall from it
- Works together with other mods that replace the game's main script file (like "Saber unlock")

## Controls

Every key and button can be changed in **Esc > THIRD PERSON CONTROLS**.

| | Keyboard / mouse | Controller (HD2 layout) |
|---|---|---|
| Camera | Mouse | Right stick |
| Aim | Right mouse | LT |
| First person (while aiming) | Mouse wheel | R3 |
| Fire | Left mouse | RT |
| Ping | Z | B |
| Grenade / stratagems | game keys | RB / LB |
| Reload, interact | game keys | X |
| Dive / switch weapon | game keys | A / Y |
| Camera settings | F9 | |
| Camera on / off | F8 | |

Strikes keep the game's own damage: only what you see changes (the Railcannon lock-on range and the Orbital Strike laser speed are the only gameplay changes to strikes).

## Screenshots

| | |
|---|---|
| ![Dive](screenshots/02_dive_desert.jpg) | ![Night sky](screenshots/03_night_sky_mech.jpg) |
| ![Ship window](screenshots/04_ship_window.jpg) | ![Ship lobby](screenshots/05_ship_lobby.jpg) |

![Ship lobby](screenshots/06_ship_lobby_wide.jpg)

## Changelog

**v2.1**
- THIRD PERSON CONTROLS now looks and works like the game's own key binding screen
- Controller: the binding screen no longer loops back to the Third Person Controls page
- Ping works every time; pings and enemy names stay on their spot in the world
- Fixed a crash when going back to the ship
- Warning when a player with an older (or newer) version of the mod joins

**v2.0**
- First person while aiming (mouse wheel / R3), with real scopes for scoped weapons
- Ping (Z / B): an eye on a spot, a red scope with the enemy's name on an enemy
- Esc > THIRD PERSON CONTROLS: a separate set of buttons for third person (keyboard and controller, in the game's own key binding screen), PRESS / HOLD / DOUBLE TAP, camera keys
- Co-op: banner when a player with or without the mod joins; "Stay near squad" turns on for everyone when someone has no mod
- Shot spread smaller while aiming, smaller still in first person
- HELLDIVERS 2 hellpod descent, jump pack camera, smoother camera at any frame rate
- Railcannon locks on to the biggest enemy near the beacon, the Orbital Strike laser chases faster, both beams come from the Super Destroyer
- Fire from napalm, flamethrowers and incendiary grenades burns on the ground
- Settings menu with tabs, Performance mode
- Fixes: black sky on big maps, escort NPCs pulled out of the map, controllers whose right stick did nothing, close-range shots

**v1.5**
- Settings menu (F9, or L3 + R3 on a controller): sensitivity, FOV, camera distance, shoulder side and height, camera on / off key (F8), reset to default
- Controller support with the HELLDIVERS 2 layout, every button can be changed in the menu; Y goes to the next weapon
- HELLDIVERS 2 style compass with the map markers
- Orbital strikes come from the Super Destroyer, the Orbital Strike laser and the Railcannon beam reach up to it
- Eagle strikes: the plane stays over the strike and the bombs fall from it
- The Super Destroyer and the plane are no longer hidden by the fog
- Smoother mouse look on fast turns, the character is no longer cut when aiming close, crosshair centred on ultrawide screens
- Co-op: the camera follows only you, and an option keeps you near squadmates who don't have the mod
- Compatible with mods that replace the main script file (installer: install them first; manual zip: any order)

**v1.2**
- Fixes for the camera and the dive

**v1.1**
- The sky now takes the colour of the map's own fog (read from the game's original settings), so sky and haze match
- The fog has a single colour (no more whitish second fog towards the sun)
- Trees, rocks and buildings keep their high-detail models further away, and ambient occlusion is on during play
- The tutorial gets the same sky, fog and ship as the other maps

## Install

1. Download the zip from [Releases](https://github.com/yukiorsrs/third-person-camera-helldivers/releases/latest) and extract it.
2. Open the `ThirdPersonCamera_Installer` folder, run `ThirdPersonCamera_Installer.exe` and click **Install**.
3. Play.

No installer? Download `ThirdPersonCamera_v2.1_manual.zip` from the same release and copy its `contents` folder into your HELLDIVERS folder, replacing the 3 files. To remove it, verify the game files on Steam.

The installer finds the game in any Steam library and closes it if it's open. It only changes your own game files and keeps a backup of every original in `Helldivers\contents\hd2cam_backup`. Run it again and click **Uninstall** to remove the mod. Verifying the game files on Steam also works.

If the game gets an update, uninstall and install again. The installer won't touch files it doesn't recognize.

## About this repository

This is the source code of the installer:

- `installer.py` is the whole installer (GUI, game detection, patching, backup and uninstall).
- `data/lua/*.bin` are the mod's compiled scripts, which replace scripts in the game's script bundles.
- `data/sky/*.dds` are the sky textures. The installer adds every sky to the mission_start bundle, using the dome model from the player's own menu bundle. The night sky and the fog-colour skies are generated by `installer.py` at install time.
- `data/originals.json` lists the game files the mod touches with their SHA-256 (and a fingerprint of every script in the script bundles). The installer refuses to patch anything it does not recognize, but keeps the changes of other mods that only replaced other scripts.

It has no network access, no registry writes and does not touch any file outside the game's `contents` folder. A few antivirus engines flag PyInstaller executables; that is a known false positive.

### Build

Requirements: Windows, Python 3.12, PyInstaller 6.22.3.

```
python -m pip install pyinstaller==6.22.3
python -m PyInstaller --noconfirm --onedir --windowed --noupx --name ThirdPersonCamera_Installer --version-file version_info.txt --add-data "data;data" installer.py
```

The installer is created in `dist/ThirdPersonCamera_Installer/`. You can also run it without building: `python installer.py`, or `python installer.py --install` / `--uninstall` for silent mode.

## Credits

Made by yukiorsrs with help from AI (Claude, by Anthropic). Arrowhead Game Studios for HELLDIVERS.
