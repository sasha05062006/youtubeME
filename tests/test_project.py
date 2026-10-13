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

    def test_no_paid_api_key_dependency(self):
        source = (ROOT / "scripts" / "generate.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("openai_api_key", source)
        self.assertNotIn("anthropic_api_key", source)


if __name__ == "__main__":
    unittest.main()
