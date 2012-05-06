from nose.tools import raises

import primitives

## test primitive

def test_point():
    p = primitives.Point(1,1)
    assert 1 < p.modulo() < 4
    p2 = p * 4
    assert 5 < p2.modulo() < 6, p2.modulo()

def test_point2():
    p = primitives.Point(1,1)
    p = p.normalized()
    assert 0.99999 < p.modulo() < 1.00001, p.modulo()

def test_point_prod():
    p = primitives.Point(1,1)
    o = p.orthogonal()
    pr = p * o
    assert pr == 0, pr


def test_point_looks_like_a_tuple():
    p = primitives.Point(1,3)
    assert p[0] == 1
    assert p[1] == 3
    assert len(p) == 2

@raises(IndexError)
def test_point_looks_like_a_tuple2():
    p = primitives.Point(1,3)
    x = p[2]

