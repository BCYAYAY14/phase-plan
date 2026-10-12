"""Worked examples from RFC 5545 section 3.8.5.3, date-only. The expected dates are the RFC's;
two UNTIL bounds are restated as dates because the RFC's carry times of day."""
import unittest
from datetime import date

from recur.expand import occurrences
from recur.rule import parse_rrule


def D(s):
    return date(int(s[:4]), int(s[4:6]), int(s[6:8]))


def run(rule, start, end=None, limit=None):
    return occurrences(parse_rrule(rule), D(start), end=D(end) if end else None, limit=limit)


def ds(*xs):
    return [D(x) for x in xs]


class Daily(unittest.TestCase):
    def test_daily_count(self):
        self.assertEqual(run("FREQ=DAILY;COUNT=10", "19970902"), [D(f"199709{d:02d}") for d in range(2, 12)])

    def test_every_10_days(self):
        self.assertEqual(run("FREQ=DAILY;INTERVAL=10;COUNT=5", "19970902"), ds("19970902", "19970912", "19970922", "19971002", "19971012"))

    def test_every_day_in_january_two_ways(self):
        want = [date(y, 1, d) for y in (1998, 1999, 2000) for d in range(1, 32)]
        self.assertEqual(run("FREQ=YEARLY;UNTIL=20000131T140000Z;BYMONTH=1;BYDAY=SU,MO,TU,WE,TH,FR,SA", "19980101"), want)
        self.assertEqual(run("FREQ=DAILY;UNTIL=20000131;BYMONTH=1", "19980101"), want)


class Weekly(unittest.TestCase):
    def test_weekly_count(self):
        self.assertEqual(run("FREQ=WEEKLY;COUNT=10", "19970902"),
                         ds("19970902", "19970909", "19970916", "19970923", "19970930", "19971007", "19971014", "19971021", "19971028", "19971104"))

    def test_tue_thu_for_five_weeks(self):
        want = ds("19970902", "19970904", "19970909", "19970911", "19970916", "19970918", "19970923", "19970925", "19970930", "19971002")
        self.assertEqual(run("FREQ=WEEKLY;UNTIL=19971006;WKST=SU;BYDAY=TU,TH", "19970902"), want)
        self.assertEqual(run("FREQ=WEEKLY;COUNT=10;WKST=SU;BYDAY=TU,TH", "19970902"), want)

    def test_every_other_week_mon_wed_fri(self):
        self.assertEqual(run("FREQ=WEEKLY;INTERVAL=2;UNTIL=19971223;WKST=SU;BYDAY=MO,WE,FR", "19970901"),
                         ds("19970901", "19970903", "19970905", "19970915", "19970917", "19970919", "19970929", "19971001", "19971003",
                            "19971013", "19971015", "19971017", "19971027", "19971029", "19971031", "19971110", "19971112", "19971114",
                            "19971124", "19971126", "19971128", "19971208", "19971210", "19971212", "19971222"))

    def test_until_time_part_is_ignored(self):
        # The RFC's examples carry times of day; dates here have none, so UNTIL's time is dropped.
        self.assertEqual(run("FREQ=WEEKLY;UNTIL=19971007T000000Z;BYDAY=TU", "19970930"), ds("19970930", "19971007"))

    def test_every_other_week_tue_thu(self):
        self.assertEqual(run("FREQ=WEEKLY;INTERVAL=2;COUNT=8;WKST=SU;BYDAY=TU,TH", "19970902"),
                         ds("19970902", "19970904", "19970916", "19970918", "19970930", "19971002", "19971014", "19971016"))

    def test_wkst_changes_the_result(self):
        self.assertEqual(run("FREQ=WEEKLY;INTERVAL=2;COUNT=4;BYDAY=TU,SU;WKST=MO", "19970805"), ds("19970805", "19970810", "19970819", "19970824"))
        self.assertEqual(run("FREQ=WEEKLY;INTERVAL=2;COUNT=4;BYDAY=TU,SU;WKST=SU", "19970805"), ds("19970805", "19970817", "19970819", "19970831"))


class Monthly(unittest.TestCase):
    def test_first_friday(self):
        self.assertEqual(run("FREQ=MONTHLY;COUNT=10;BYDAY=1FR", "19970905"),
                         ds("19970905", "19971003", "19971107", "19971205", "19980102", "19980206", "19980306", "19980403", "19980501", "19980605"))

    def test_every_other_month_first_and_last_sunday(self):
        self.assertEqual(run("FREQ=MONTHLY;INTERVAL=2;COUNT=10;BYDAY=1SU,-1SU", "19970907"),
                         ds("19970907", "19970928", "19971102", "19971130", "19980104", "19980125", "19980301", "19980329", "19980503", "19980531"))

    def test_second_to_last_monday(self):
        self.assertEqual(run("FREQ=MONTHLY;COUNT=6;BYDAY=-2MO", "19970922"),
                         ds("19970922", "19971020", "19971117", "19971222", "19980119", "19980216"))

    def test_third_to_last_day(self):
        self.assertEqual(run("FREQ=MONTHLY;BYMONTHDAY=-3", "19970928", limit=6),
                         ds("19970928", "19971029", "19971128", "19971229", "19980129", "19980226"))

    def test_2nd_and_15th(self):
        self.assertEqual(run("FREQ=MONTHLY;COUNT=10;BYMONTHDAY=2,15", "19970902"),
                         ds("19970902", "19970915", "19971002", "19971015", "19971102", "19971115", "19971202", "19971215", "19980102", "19980115"))

    def test_first_and_last_day(self):
        self.assertEqual(run("FREQ=MONTHLY;COUNT=10;BYMONTHDAY=1,-1", "19970930"),
                         ds("19970930", "19971001", "19971031", "19971101", "19971130", "19971201", "19971231", "19980101", "19980131", "19980201"))

    def test_every_18_months_10th_to_15th(self):
        self.assertEqual(run("FREQ=MONTHLY;INTERVAL=18;COUNT=10;BYMONTHDAY=10,11,12,13,14,15", "19970910"),
                         ds("19970910", "19970911", "19970912", "19970913", "19970914", "19970915", "19990310", "19990311", "19990312", "19990313"))

    def test_every_tuesday_every_other_month(self):
        self.assertEqual(run("FREQ=MONTHLY;INTERVAL=2;BYDAY=TU", "19970902", end="19980331"),
                         ds("19970902", "19970909", "19970916", "19970923", "19970930", "19971104", "19971111", "19971118", "19971125",
                            "19980106", "19980113", "19980120", "19980127", "19980303", "19980310", "19980317", "19980324", "19980331"))

    def test_friday_the_13th(self):
        self.assertEqual(run("FREQ=MONTHLY;BYDAY=FR;BYMONTHDAY=13", "19970902", limit=5),
                         ds("19980213", "19980313", "19981113", "19990813", "20001013"))

    def test_saturday_after_first_sunday(self):
        self.assertEqual(run("FREQ=MONTHLY;BYDAY=SA;BYMONTHDAY=7,8,9,10,11,12,13", "19970913", limit=10),
                         ds("19970913", "19971011", "19971108", "19971213", "19980110", "19980207", "19980307", "19980411", "19980509", "19980613"))

    def test_third_tue_wed_or_thu(self):
        self.assertEqual(run("FREQ=MONTHLY;COUNT=3;BYDAY=TU,WE,TH;BYSETPOS=3", "19970904"), ds("19970904", "19971007", "19971106"))

    def test_second_to_last_weekday(self):
        self.assertEqual(run("FREQ=MONTHLY;BYDAY=MO,TU,WE,TH,FR;BYSETPOS=-2", "19970929", limit=7),
                         ds("19970929", "19971030", "19971127", "19971230", "19980129", "19980226", "19980330"))

    def test_invalid_dates_are_skipped(self):
        self.assertEqual(run("FREQ=MONTHLY;BYMONTHDAY=15,30;COUNT=5", "20070115"), ds("20070115", "20070130", "20070215", "20070315", "20070330"))


class Yearly(unittest.TestCase):
    def test_june_and_july(self):
        self.assertEqual(run("FREQ=YEARLY;COUNT=10;BYMONTH=6,7", "19970610"),
                         [date(y, m, 10) for y in range(1997, 2002) for m in (6, 7)])

    def test_every_other_year_jan_feb_mar(self):
        self.assertEqual(run("FREQ=YEARLY;INTERVAL=2;COUNT=10;BYMONTH=1,2,3", "19970310"),
                         ds("19970310", "19990110", "19990210", "19990310", "20010110", "20010210", "20010310", "20030110", "20030210", "20030310"))

    def test_every_third_year_by_yearday(self):
        self.assertEqual(run("FREQ=YEARLY;INTERVAL=3;COUNT=10;BYYEARDAY=1,100,200", "19970101"),
                         ds("19970101", "19970410", "19970719", "20000101", "20000409", "20000718", "20030101", "20030410", "20030719", "20060101"))

    def test_20th_monday_of_the_year(self):
        self.assertEqual(run("FREQ=YEARLY;BYDAY=20MO", "19970519", limit=3), ds("19970519", "19980518", "19990517"))

    def test_every_thursday_in_march(self):
        self.assertEqual(run("FREQ=YEARLY;BYMONTH=3;BYDAY=TH", "19970313", limit=11),
                         ds("19970313", "19970320", "19970327", "19980305", "19980312", "19980319", "19980326", "19990304", "19990311", "19990318", "19990325"))

    def test_thursdays_in_summer(self):
        got = run("FREQ=YEARLY;BYDAY=TH;BYMONTH=6,7,8", "19970605", end="19980831")
        self.assertEqual(got[:5], ds("19970605", "19970612", "19970619", "19970626", "19970703"))
        self.assertEqual(len(got), 13 + 13)
        self.assertEqual(got[13], D("19980604"))

    def test_us_election_day(self):
        self.assertEqual(run("FREQ=YEARLY;INTERVAL=4;BYMONTH=11;BYDAY=TU;BYMONTHDAY=2,3,4,5,6,7,8", "19961105", limit=3),
                         ds("19961105", "20001107", "20041102"))
