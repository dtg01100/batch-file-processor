"""
Tests for plugin section registry lifecycle and contracts.
"""

import unittest

from interface.plugins.section_registry import (
    ConfigSectionBase,
    PluginSection,
    SectionRegistry,
)


class _BaseTestSection(ConfigSectionBase):
    @classmethod
    def get_section_id(cls) -> str:
        return cls.section_id

    @classmethod
    def get_section_title(cls) -> str:
        return cls.title

    @classmethod
    def get_section_description(cls) -> str:
        return cls.description

    @classmethod
    def get_schema(cls):
        return None

    @classmethod
    def get_priority(cls) -> int:
        return cls.priority


class HighPrioritySection(_BaseTestSection):
    section_id = "high_priority"
    title = "High"
    description = "High priority section"
    priority = 10


class LowPrioritySection(_BaseTestSection):
    section_id = "low_priority"
    title = "Low"
    description = "Low priority section"
    priority = 200


class PluginASection(_BaseTestSection):
    section_id = "plugin_a_section"
    title = "Plugin A"
    description = "Plugin A section"
    priority = 50


class PluginASecondSection(_BaseTestSection):
    section_id = "plugin_a_second_section"
    title = "Plugin A Second"
    description = "Plugin A second section"
    priority = 60


class PluginBSection(_BaseTestSection):
    section_id = "plugin_b_section"
    title = "Plugin B"
    description = "Plugin B section"
    priority = 70


class TestSectionRegistry(unittest.TestCase):
    def setUp(self):
        SectionRegistry.clear()

    def tearDown(self):
        SectionRegistry.clear()

    def test_register_get_and_count(self):
        SectionRegistry.register_section(HighPrioritySection)

        self.assertEqual(SectionRegistry.get_section_count(), 1)
        self.assertIs(SectionRegistry.get_section("high_priority"), HighPrioritySection)

    def test_duplicate_register_raises_value_error(self):
        SectionRegistry.register_section(HighPrioritySection)

        with self.assertRaises(ValueError):
            SectionRegistry.register_section(HighPrioritySection)

    def test_get_all_sections_sorted_by_priority(self):
        SectionRegistry.register_section(LowPrioritySection)
        SectionRegistry.register_section(HighPrioritySection)

        sections = SectionRegistry.get_all_sections()
        section_ids = [section.get_section_id() for section in sections]

        self.assertEqual(section_ids, ["high_priority", "low_priority"])

    def test_unregister_removes_section_and_renderer(self):
        SectionRegistry.register_section(HighPrioritySection)
        SectionRegistry.register_renderer("high_priority", lambda: "renderer")

        SectionRegistry.unregister_section("high_priority")

        self.assertIsNone(SectionRegistry.get_section("high_priority"))
        self.assertIsNone(SectionRegistry.get_renderer("high_priority"))
        self.assertEqual(SectionRegistry.get_section_count(), 0)

    def test_register_plugin_section_and_filter_after_unregister(self):
        SectionRegistry.register_plugin_section("plugin_a", PluginASection)
        SectionRegistry.register_plugin_section("plugin_a", PluginASecondSection)
        SectionRegistry.register_plugin_section("plugin_b", PluginBSection)

        plugin_a_sections_before = SectionRegistry.get_sections_by_plugin("plugin_a")
        self.assertEqual(
            [section.get_section_id() for section in plugin_a_sections_before],
            ["plugin_a_section", "plugin_a_second_section"],
        )

        SectionRegistry.unregister_section("plugin_a_section")

        plugin_a_sections_after = SectionRegistry.get_sections_by_plugin("plugin_a")
        self.assertEqual(
            [section.get_section_id() for section in plugin_a_sections_after],
            ["plugin_a_second_section"],
        )
        self.assertEqual(
            [section.get_section_id() for section in SectionRegistry.get_sections_by_plugin("plugin_b")],
            ["plugin_b_section"],
        )

    def test_clear_resets_state(self):
        SectionRegistry.register_section(HighPrioritySection)
        SectionRegistry.register_renderer("high_priority", lambda: "renderer")
        SectionRegistry.register_plugin_section("plugin_a", PluginASection)

        SectionRegistry.clear()

        self.assertEqual(SectionRegistry.get_section_count(), 0)
        self.assertEqual(SectionRegistry.get_all_sections(), [])
        self.assertEqual(SectionRegistry.get_sections_by_plugin("plugin_a"), [])
        self.assertIsNone(SectionRegistry.get_renderer("high_priority"))

    def test_plugin_section_get_plugin_id_raises_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            PluginSection.get_plugin_id()


if __name__ == "__main__":
    unittest.main()
