from nose.tools import raises
from nose.tools import assert_almost_equal
import primitives

## test primitive

def test_point():
    p = primitives.Point(1,1)
    assert 1 < p.modulo < 4
    p2 = p * 4
    assert 5 < p2.modulo < 6, p2.modulo

def test_point2():
    p = primitives.Point(1,1)
    p = p.normalized()
    assert 0.99999 < p.modulo < 1.00001, p.modulo

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

def test_angle():

    correct = (
        (-1,-1,3.9269908169872414),
        (-1,0,4.7123889803846897),
        (-1,1,5.4977871437821380),
        (0,-1,3.1415926535897931),
        (0,0,0.0000000000000000),
        (0,1,0.0000000000000000),
        (1,-1,2.3561944901923448),
        (1,0,1.5707963267948966),
        (1,1,0.7853981633974484),
    )
    for x, y, val in correct:
        assert_almost_equal(primitives.Point(x,y).angle, val)


@raises(TypeError)
def test_vector_type_check_mul():
    primitives.GVector(1,1) * primitives.PVector(3,3)

@raises(TypeError)
def test_vector_type_check_add():
    primitives.GVector(1,1) + primitives.PVector(3,3)

def test_vector_type_check():
    primitives.GVector(1,1) + primitives.GVector(3,3)
    primitives.GVector(1,1) * primitives.GVector(3,3)







