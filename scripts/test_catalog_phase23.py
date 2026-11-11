import unittest
from technophere_catalog import choose_detail_refresh

A='https://game.technophere.com/monst/char/177/'
B='https://game.technophere.com/monst/char/9531/'
C='https://game.technophere.com/monst/char/9548/'

def row(url, no, **kw):
    return dict(id=str(no), name='sample', attribute='光', source=url, **kw)

class Phase23Tests(unittest.TestCase):
    def test_picks_verified_with_missing_stats_first(self):
        rows={'177':row(A,177,hp=1,attack=1,speed=1),
              '9532':row(B,9532,abilities=['a']),
              '9549':row(C,9549,hp=3,attack=4,speed=5,abilities=['x'])}
        self.assertEqual(choose_detail_refresh(rows,{A,B,C},{},10),[B])

    def test_blank_abilities_is_review_candidate(self):
        rows={'177':row(A,177,hp=1,attack=2,speed=3,abilities=[])}
        self.assertEqual(choose_detail_refresh(rows,{A},{},2),[A])

    def test_no_repeat_until_cooldown(self):
        rows={'177':row(A,177)}
        self.assertEqual(choose_detail_refresh(rows,{A},{A:61},60),[])
        self.assertEqual(choose_detail_refresh(rows,{A},{A:61},61),[A])

    def test_excludes_unverified_even_with_gaps(self):
        self.assertEqual(choose_detail_refresh({'177':row(A,177)},set(),{},1),[])

    def test_empty_and_limit(self):
        self.assertEqual(choose_detail_refresh({},set(),{},1),[])
        self.assertEqual(choose_detail_refresh({'177':row(A,177)},{A},{},1,0),[])

    def test_deterministic_tie_break(self):
        rows={'177':row(A,177),'9532':row(B,9532)}
        self.assertEqual(choose_detail_refresh(rows,{A,B},{},1,2),[A,B])

    def test_complete_core_not_refetched(self):
        rows={'177':row(A,177,hp=0,attack=0,speed=0,abilities=['a'])}
        self.assertEqual(choose_detail_refresh(rows,{A},{},1),[])

if __name__=='__main__':unittest.main()
