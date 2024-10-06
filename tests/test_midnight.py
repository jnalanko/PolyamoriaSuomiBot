import unittest
import datetime

from midnight import contains_midnight_phrase, get_prize


class ContainsMidnightPhrase(unittest.TestCase):
    def test_valid_english(self):
        self.assertTrue(contains_midnight_phrase("Happy midnight! 🥳"))

    def test_valid_finnish(self):
        self.assertTrue(contains_midnight_phrase("Hyvää keskiyötä! 🥳"))

    def test_valid_keksiyo(self):
        self.assertTrue(contains_midnight_phrase("Hyvää keksiyötä 🍪"))

    def test_valid_kettuyo(self):
        self.assertTrue(contains_midnight_phrase("Hyvää kettuyötä 🦊"))

    def test_valid_all_caps(self):
        self.assertTrue(contains_midnight_phrase("HYVÄÄ KESKIYÖTÄ"))

    def test_valid_all_lower_case(self):
        self.assertTrue(contains_midnight_phrase("hyvää keskiyötä"))

    def test_invalid_keymash(self):
        self.assertFalse(contains_midnight_phrase("sdfakasjdhflaskjhflskajh"))

    def test_invalid_pleksiyo(self):
        self.assertFalse(contains_midnight_phrase("Hyvää pleksiyötä!"))

class GetPrize(unittest.TestCase):
    def test_trophy(self):
        self.assertEqual(get_prize("Hyvää keskiyötä", datetime.date(year=2023, month=1, day=2)), '🏆')

    def test_crown(self):
        self.assertEqual(get_prize("Hyvää keskiyötä", datetime.date(year=2023, month=1, day=1)), '👑')

    def test_cookie(self):
        self.assertEqual(get_prize("Hyvää keksiyötä", datetime.date(year=2023, month=1, day=2)), '🍪')

    def test_fox(self):
        self.assertEqual(get_prize("Hyvää kettuyötä", datetime.date(year=2023, month=1, day=2)), '🦊')

    def test_cookie_and_new_year(self):
        self.assertEqual(get_prize("Hyvää keksiyötä", datetime.date(year=2023, month=1, day=1)), '👑')


if __name__ == '__main__':
    unittest.main()
