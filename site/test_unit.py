import unittest
import queryparser

class TestParser(unittest.TestCase):
    # todo: disallow queries which will take a long time.

    def parse_in(self, sql):
        i = sql.find(' IN (') + 5
        n = sql[i:].find(')') + i
        return sql[i:n].split(',')


    def test_gender_F(self):
        want = ['0.7', '0.8', '0.9', '1.0']

        sql, args = queryparser.parse_query('foo gender:F')
        self.assertEqual(args, ['foo'])

        in_array = self.parse_in(sql)
        self.assertEqual(in_array, want)


    def test_gender_M(self):
        want = ['0.0', '0.1', '0.2', '0.3']

        sql, args = queryparser.parse_query('bar gender:M')
        self.assertEqual(args, ['bar'])

        in_array = self.parse_in(sql)
        self.assertEqual(in_array, want)


    def test_case_insensitive_M(self):
        s1, a1 = queryparser.parse_query('bar gender:M')
        s2, a2 = queryparser.parse_query('bar gender:m')
        self.assertEqual(s1, s2)
        self.assertEqual(a1, a2)

    def test_case_insensitive_F(self):
        s1, a1 = queryparser.parse_query('foo gender:F')
        s2, a2 = queryparser.parse_query('foo gender:f')
        self.assertEqual(s1, s2)
        self.assertEqual(a1, a2)



if __name__ == '__main__':
    unittest.main()
