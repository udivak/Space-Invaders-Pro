"""Explicit media loading. Importing this module performs no I/O."""
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pygame

from space_invaders import paths
from space_invaders.settings import WIDTH, HEIGHT

IMAGE_FILES = {
    "enemy_red": "enemy - red.png",
    "enemy_green": "enemy - green.png",
    "enemy_blue": "enemy - blue.png",
    "player": "player.png",
    "player2": "player2.png",
    "boss_grey": "boss_grey.png",
    "player_laser": "player_laser.png",
    "player2_laser": "player2_laser.png",
    "boss_laser": "boss_laser_purple.png",
    "enemy_laser_blue": "enemy_laser_blue.png",
    "enemy_laser_red": "enemy_laser_red.png",
    "enemy_laser_green": "enemy_laser_green.png",
    "background": "background-black.png",
    "pack_hp": "healthpack.jpeg",
    "pack_triple_laser": "laserpack.png",
    "pack_shield": "shieldpack.png",
}
SOUND_FILES = {"laser": "laser-shot.mp3", "boss_explosion": "boss-explosion.mp3"}
BASE_VOLUMES = {"laser": 0.06, "boss_explosion": 1.0}
MUSIC_FILE = "trance-loop.mp3"
DEFAULT_MUSIC_VOLUME = 0.055


class AssetError(RuntimeError):
    pass


@dataclass
class AssetBundle:
    images: dict
    sounds: dict = field(default_factory=dict)
    music_path: Path = None
    effects_volume: float = 1.0

    @property
    def audio_enabled(self):
        return bool(self.sounds) or self.music_path is not None

    def play(self, name):
        sound = self.sounds.get(name)
        if sound is not None:
            sound.play()

    def set_effects_volume(self, volume):
        self.effects_volume = volume
        for name, sound in self.sounds.items():
            sound.set_volume(BASE_VOLUMES.get(name, 1.0) * volume)

    def start_music(self, volume):
        if self.music_path is None:
            return
        try:
            pygame.mixer.music.load(str(self.music_path))
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(-1)
        except pygame.error:
            self.music_path = None

    def set_music_volume(self, volume):
        if self.music_path is not None and pygame.mixer.get_init():
            pygame.mixer.music.set_volume(volume)

    def pause_music(self):
        if self.music_path is not None and pygame.mixer.get_init():
            pygame.mixer.music.pause()

    def resume_music(self):
        if self.music_path is not None and pygame.mixer.get_init():
            pygame.mixer.music.unpause()

    def stop_music(self):
        if self.music_path is not None and pygame.mixer.get_init():
            pygame.mixer.music.stop()


def _report(message):
    print(f"space_invaders: {message}", file=sys.stderr)


def load_assets(resource_root=None, audio_enabled=True):
    """Load images (required) and sounds (optional). Call after pygame.display is initialized."""
    root = Path(resource_root) if resource_root is not None else paths.resource_root()
    images = {}
    for key, filename in IMAGE_FILES.items():
        path = root / "assets" / filename
        if not path.is_file():
            raise AssetError(f"Required image is missing: {path}")
        try:
            images[key] = pygame.image.load(str(path))
        except pygame.error as error:
            raise AssetError(f"Cannot load required image {path}: {error}") from error
    images["background"] = pygame.transform.scale(images["background"], (WIDTH, HEIGHT))
    sounds = {}
    music_path = None
    if audio_enabled:
        missing = []
        for key, filename in SOUND_FILES.items():
            path = root / "sounds" / filename
            try:
                sounds[key] = pygame.mixer.Sound(str(path))
                sounds[key].set_volume(BASE_VOLUMES[key])
            except (pygame.error, FileNotFoundError):
                missing.append(str(path))
        music = root / "sounds" / MUSIC_FILE
        if music.is_file():
            music_path = music
        else:
            missing.append(str(music))
        if missing:
            _report("audio files unavailable, continuing without them: " + ", ".join(missing))
    return AssetBundle(images=images, sounds=sounds, music_path=music_path)


def init_audio():
    """Try to start the mixer. Returns False (reported once) when no device is available."""
    try:
        pygame.mixer.init()
        return True
    except pygame.error as error:
        _report(f"audio disabled: {error}")
        return False
