import unittest

from midnight import contains_midnight_phrase


class ContainsMidnightPhrase(unittest.TestCase):
    def test_valid_english(self):
        self.assertTrue(contains_midnight_phrase("Happy midnight! 🥳"))

    def test_valid_finnish(self):
        self.assertTrue(contains_midnight_phrase("Hyvää keskiyötä! 🥳"))

    def test_valid_keksiyo(self):
        self.assertTrue(contains_midnight_phrase("Hyvää keksiyötä 🍪"))

    def test_valid_all_caps(self):
        self.assertTrue(contains_midnight_phrase("HYVÄÄ KESKIYÖTÄ"))

    def test_valid_all_lower_case(self):
        self.assertTrue(contains_midnight_phrase("hyvää keskiyötä"))

    def test_invalid_keymash(self):
        self.assertFalse(contains_midnight_phrase("sdfakasjdhflaskjhflskajh"))

    def test_invalid_pleksiyo(self):
        self.assertFalse(contains_midnight_phrase("Hyvää pleksiyötä!"))


if __name__ == '__main__':
    unittest.main()
