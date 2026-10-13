import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ProjectConfigurationTests(unittest.TestCase):
    def test_settings_are_conservative_and_vertical(self):
        settings = json.loads((ROOT / "config" / "settings.json").read_text(encoding="utf-8"))
        self.assertLessEqual(settings["render"]["width"], settings["render"]["height"])
        self.assertEqual(settings["render"]["width"] * 16, settings["render"]["height"] * 9)
        self.assertLessEqual(settings["video"]["fps"], 15)
        self.assertFalse(settings["publish"]["enabled"])
        self.assertTrue(settings["qa"]["enabled"])

    def test_scene_builder_is_a_real_blender_script(self):
        source = (ROOT / "scripts" / "blender_scene.py").read_text(encoding="utf-8")
        self.assertIn("bpy.ops.render.render(animation=True)", source)
        self.assertIn("primitive_uv_sphere_add", source)
        self.assertIn("bpy.ops.object.camera_add", source)

    def test_russian_story_and_character_options_exist(self):
        source = (ROOT / "scripts" / "generate.py").read_text(encoding="utf-8")
        scene = (ROOT / "scripts" / "blender_scene.py").read_text(encoding="utf-8")
        self.assertIn("Космос и дружба", source)
        self.assertIn("Piper", source)
        self.assertIn('"cat"', source)
        self.assertIn('character == "astronaut"', scene)
        self.assertIn('character == "dragon"', scene)


    def test_screenplay_validator_checks_multi_character_and_audio_timeline(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        from screenplay import validate_screenplay

        valid = {
            "title": "Слонёнок и друзья",
            "target_duration_seconds": 30,
            "cast": [
                {"id": "elephant", "name": "Топа", "description": "Слонёнок", "voice_profile": "warm"},
                {"id": "fox", "name": "Рыжик", "description": "Лисёнок", "voice_profile": "playful"},
            ],
            "scenes": [
                {
                    "id": "forest",
                    "duration_seconds": 30,
                    "location": "Лес",
                    "visual_action": "Друзья ищут колокольчик",
                    "camera": "Средний план",
                    "dialogue": [{"character_id": "elephant", "text": "Вы слышали звон?"}],
                    "sound_effects": [{"asset": "bell", "at_seconds": 7.5}],
                }
            ],
        }
        self.assertEqual(validate_screenplay(valid), [])
        valid["scenes"][0]["dialogue"][0]["character_id"] = "missing"
        valid["scenes"][0]["sound_effects"][0]["at_seconds"] = 35
        errors = validate_screenplay(valid)
        self.assertTrue(any("unknown character_id" in error for error in errors))
        self.assertTrue(any("within the scene duration" in error for error in errors))

    def test_no_paid_api_key_dependency(self):
        source = (ROOT / "scripts" / "generate.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("openai_api_key", source)
        self.assertNotIn("anthropic_api_key", source)


if __name__ == "__main__":
    unittest.main()
