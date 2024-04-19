from cinema.cinegraph.node_types import ProfessionalNode, PersonNode, WorkNode

from django.test import TestCase


class TestNodeTypes(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_professional_node(self):
        n0 = ProfessionalNode(42, False)
        s0 = ProfessionalNode("42", False)
        n1 = ProfessionalNode(42, False)
        n2 = ProfessionalNode(41, False)
        n3 = ProfessionalNode(42, True)

        self.assertEqual(n0, n1)
        self.assertEqual(hash(n0), hash(n1))

        self.assertNotEqual(n0, n2)
        self.assertNotEqual(hash(n0), hash(n2))

        self.assertNotEqual(n0, n3)
        self.assertNotEqual(hash(n0), hash(n3))

        self.assertNotEqual(n0, s0)
        self.assertNotEqual(hash(n0), hash(s0))

    def test_person_node(self):
        n0 = ProfessionalNode(42, True)
        n1 = PersonNode(42)

        self.assertTrue(n1.is_person)
        self.assertEqual(n0, n1)
        self.assertEqual(hash(n0), hash(n1))

    def test_movie_node(self):
        n0 = ProfessionalNode(42, False)
        n1 = WorkNode(42)

        self.assertFalse(n1.is_person)
        self.assertEqual(n0, n1)
        self.assertEqual(hash(n0), hash(n1))

    def test_node_to_string(self):
        n0 = ProfessionalNode(0, False)
        n1 = ProfessionalNode(1, True)

        self.assertEqual("<work 0>", str(n0))
        self.assertEqual("<person 1>", str(n1))

    def test_node_repr(self):
        n0 = ProfessionalNode(0, False)
        n1 = ProfessionalNode(1, True)
        w = WorkNode(2)
        p = PersonNode(3)

        self.assertEqual("ProfessionalNode(0, False)", repr(n0))
        self.assertEqual("ProfessionalNode(1, True)", repr(n1))
        self.assertEqual("WorkNode(2)", repr(w))
        self.assertEqual("PersonNode(3)", repr(p))

        s0 = ProfessionalNode("0", False)
        sw = WorkNode("2")
        sp = PersonNode("3")
        self.assertEqual("ProfessionalNode('0', False)", repr(s0))
        self.assertEqual("WorkNode('2')", repr(sw))
        self.assertEqual("PersonNode('3')", repr(sp))


