"""Regression tests for EcoVent metadata and protocol references."""

import json
import unittest

from ecovent_test_helpers import COMPONENT_PATH, Fan, PROTOCOL_REFERENCE_PATH


class ParseResponseTest(unittest.TestCase):
    def test_entity_platforms_do_not_branch_on_profile_names(self):
        for filename in (
            "binary_sensor.py",
            "number.py",
            "select.py",
            "sensor.py",
            "switch.py",
        ):
            source = (COMPONENT_PATH / filename).read_text()
            self.assertNotIn('profile_key == "extract_fan"', source)
            self.assertNotIn('profile_key != "extract_fan"', source)
            self.assertNotIn('profile_key == "breezy"', source)
            self.assertNotIn('profile_key != "breezy"', source)

    def test_entity_platforms_keep_model_names_out_of_capabilities(self):
        for filename in (
            "binary_sensor.py",
            "ecoventv2.py",
            "fan.py",
            "number.py",
            "sensor.py",
            "switch.py",
        ):
            source = (COMPONENT_PATH / filename).read_text()
            self.assertNotIn("smart_", source)
            self.assertNotIn("Smart Wi-Fi", source)
            self.assertNotIn("dual_fan_speed", source)

    def test_fan_preset_labels_and_icons_cover_all_profiles(self):
        strings = json.loads((COMPONENT_PATH / "strings.json").read_text())
        icons = json.loads((COMPONENT_PATH / "icons.json").read_text())

        labels = strings["entity"]["fan"]["vent"]["state_attributes"][
            "preset_mode"
        ]["state"]
        preset_icons = icons["entity"]["fan"]["vent"]["state_attributes"][
            "preset_mode"
        ]["state"]

        expected_modes = {
            mode
            for profile in Fan.device_profiles.values()
            for mode in profile.preset_modes
        }
        for mode in expected_modes:
            self.assertIn(mode, labels)
            self.assertIn(mode, preset_icons)

    def test_unit_type_metadata_selects_device_profiles(self):
        self.assertEqual(
            Fan.device_models[0x1A00].name,
            "VENTO inHome old / TwinFresh Atmo old",
        )
        atmo_old_names = {
            marketing.model for marketing in Fan.device_models[0x1A00].official_names
        }
        self.assertIn("VENTO inHome", atmo_old_names)
        self.assertIn("TwinFresh Atmo", atmo_old_names)
        self.assertEqual(Fan.device_models[0x1A00].profile_key, "vento")
        self.assertEqual(Fan.device_models[0x1A00].device_type, 26)
        self.assertEqual(Fan.device_models[0x1A00].parser_key, 0x1A00)
        self.assertEqual(
            Fan.device_models[0x0E00].name,
            "VENTS TwinFresh Style Wi-Fi",
        )
        style_names = {
            marketing.model for marketing in Fan.device_models[0x0E00].official_names
        }
        style_relabels = {
            marketing.model for marketing in Fan.device_models[0x0E00].relabels
        }
        style_candidates = {
            marketing.model for marketing in Fan.device_models[0x0E00].candidates
        }
        self.assertIn("Vents TwinFresh Style Wi-Fi", style_names)
        self.assertIn("OXXIFY.smart 50", style_relabels)
        self.assertIn("Oxxify.smart 30", style_candidates)
        breezy_160_names = {
            marketing.model for marketing in Fan.device_models[0x1100].official_names
        }
        self.assertIn("Vents Breezy 160-E", breezy_160_names)
        self.assertIn("Freshpoint 160-E Pro L055", breezy_160_names)
        self.assertEqual(Fan.device_models[0x1100].profile_key, "breezy")
        breezy_eco_names = {
            marketing.model for marketing in Fan.device_models[0x1400].official_names
        }
        self.assertIn("Freshpoint Eco 160-E L07", breezy_eco_names)
        self.assertEqual(Fan.device_models[0x1400].profile_key, "breezy")
        breezy_200_names = {
            marketing.model for marketing in Fan.device_models[0x1600].official_names
        }
        self.assertIn("Vents Breezy 200-E Smart", breezy_200_names)
        self.assertEqual(
            Fan.device_models[0x1800].name,
            "VENTS Breezy Eco 200 / Blauberg Freshpoint Eco 200",
        )
        self.assertEqual(
            Fan.device_models[0x1C00].name,
            "VENTO inHome 160 / TwinFresh Atmo 160",
        )
        atmo_160_names = {
            marketing.model for marketing in Fan.device_models[0x1C00].official_names
        }
        self.assertIn("TwinFresh Atmo 160", atmo_160_names)
        self.assertEqual(Fan.device_models[0x1C00].profile_key, "vento")
        self.assertEqual(
            Fan.device_models[0x1B00].name,
            "VENTO inHome 100 / TwinFresh Atmo 100",
        )
        atmo_100_names = {
            marketing.model for marketing in Fan.device_models[0x1B00].official_names
        }
        self.assertIn("VENTO inHome mini W", atmo_100_names)
        self.assertIn("TwinFresh Atmo 100", atmo_100_names)
        self.assertEqual(Fan.device_models[0x1B00].profile_key, "vento")
        self.assertEqual(Fan.device_models[0x0600].profile_key, "extract_fan")
        self.assertEqual(
            Fan.device_models[0x0600].name,
            "Blauberg Smart Wi-Fi / VENTS iFan Wi-Fi",
        )
        extract_names = {
            marketing.model for marketing in Fan.device_models[0x0600].official_names
        }
        self.assertIn("Vents iFan Move Wi-Fi", extract_names)
        self.assertEqual(
            Fan.device_models[0x0D00].name,
            "VENTS Arc Smart / Blauberg O2 Supreme",
        )
        arc_names = {
            marketing.model for marketing in Fan.device_models[0x0D00].official_names
        }
        self.assertIn("Vents Arc Smart white", arc_names)
        self.assertIn("Blauberg O2 Supreme", arc_names)
        self.assertEqual(Fan.device_models[0x0D00].device_type, 13)
        self.assertEqual(Fan.device_models[0x0D00].parser_key, 0x0D00)
        self.assertEqual(Fan.device_models[0x0D00].profile_key, "arc")

    def test_unit_type_metadata_keeps_relabels_and_candidates_separate(self):
        expert = Fan.device_models[0x0300]
        relabels = {marketing.model: marketing.evidence for marketing in expert.relabels}
        candidates = {
            marketing.model: marketing.evidence for marketing in expert.candidates
        }

        self.assertEqual(expert.manufacturer_group, "Blauberg Group / VENTS platform")
        self.assertEqual(relabels["SIKU RV 50 W Pro WiFi V2"], "official_listing")
        self.assertEqual(relabels["RL 50RVW"], "community_tested")
        self.assertEqual(relabels["Winzel Expert WiFi RW1-50 P"], "app_by_blauberg")
        self.assertEqual(candidates["Flexit Roomie One WiFi V2"], "candidate")
        self.assertEqual(candidates["NIBE DVC 10-50W"], "candidate")
        self.assertNotIn("Flexit Roomie One WiFi V2", expert.display_name)

    def test_unit_type_metadata_keeps_source_documents_with_models(self):
        self.assertIn(
            "https://blaubergventilatoren.net/download/vento-inhome-manual-14758.pdf",
            Fan.device_models[0x0300].source_documents,
        )
        self.assertIn(
            "https://ventilation-system.com/download/twinfresh-style-wi-fi-manual-19765.pdf",
            Fan.device_models[0x0E00].source_documents,
        )
        self.assertIn(
            "https://ventilation-system.com/download/twinfresh-style-wi-fi-mini-manual-19765.pdf",
            Fan.device_models[0x1C00].source_documents,
        )
        self.assertEqual(
            Fan.device_models[0x1400].source_documents,
            (
                "https://ventilation-system.com/download/breezy-eco-manual-21433.pdf",
                "https://blaubergventilatoren.net/download/freshpoint-manual-16999.pdf",
            ),
        )
        self.assertEqual(
            Fan.device_models[0x0600].source_documents,
            (
                "https://blaubergventilatoren.net/download/smart-wi-fi-manual-8533.pdf",
            ),
        )
        self.assertEqual(
            Fan.device_models[0x0200].name,
            "Blauberg Freshbox 100 WiFi / VENTS Micra 100 WiFi",
        )
        freshbox_names = {
            marketing.model for marketing in Fan.device_models[0x0200].official_names
        }
        self.assertIn("Freshbox E2-100 ERV WiFi", freshbox_names)
        self.assertIn("Vents Micra 100 E2 ERV WiFi", freshbox_names)
        self.assertEqual(Fan.device_models[0x0200].device_type, 2)
        self.assertEqual(Fan.device_models[0x0200].parser_key, 0x0200)
        self.assertEqual(Fan.device_models[0x0200].profile_key, "freshbox")
        self.assertEqual(
            Fan.device_models[0x0200].source_documents,
            (
                "https://blaubergventilatoren.net/download/freshbox-100-wifi-datasheet-7508.pdf",
                "https://ventilation-system.com/download/micra-100-wifi-manual-19886.pdf",
            ),
        )
        self.assertEqual(
            Fan.device_models[0x0D00].source_documents,
            (
                "https://ventilation-system.com/download/arc-smart-manual-21863.pdf",
                "https://blaubergventilatoren.net/download/o2-supreme-manual-15274.pdf",
            ),
        )

    def test_protocol_reference_documents_extract_fan_param_map(self):
        reference = PROTOCOL_REFERENCE_PATH.read_text()
        params = {
            **Fan.extract_fan_params,
            **Fan.extract_fan_write_params,
        }

        for param_id, (field, _values) in sorted(params.items()):
            with self.subTest(param_id=param_id, field=field):
                self.assertIn(f"| 0x{param_id:04X} | `{field}` |", reference)

    def test_protocol_reference_documents_breezy_feature_param_map(self):
        reference = PROTOCOL_REFERENCE_PATH.read_text()
        feature_param_ids = (
            0x0011,
            0x001A,
            0x001F,
            0x0020,
            0x0021,
            0x0022,
            0x0027,
            0x0068,
            0x007F,
            0x0081,
            0x0084,
            0x0129,
            0x0306,
            0x030B,
            0x0315,
            0x031F,
            0x0320,
            0x0400,
            0x0401,
            0x0402,
            0x0403,
            0x0404,
            0x0405,
            0x0406,
            0x0407,
            0x0408,
            0x0409,
        )

        for param_id in feature_param_ids:
            field = Fan.breezy_params[param_id][0]
            with self.subTest(param_id=param_id, field=field):
                self.assertIn(f"| 0x{param_id:04X} | `{field}` |", reference)

    def test_protocol_reference_documents_arc_param_map(self):
        reference = PROTOCOL_REFERENCE_PATH.read_text()

        for param_id, (field, _values) in sorted(Fan.arc_params.items()):
            with self.subTest(param_id=param_id, field=field):
                self.assertIn(f"| 0x{param_id:04X} | `{field}` |", reference)
