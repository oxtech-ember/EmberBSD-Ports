#!/usr/bin/env python3
"""Exercise the installed binding and the common libfdt library."""
import unittest
import libfdt


class DeviceTreeTests(unittest.TestCase):
    def test_create_and_read_property(self):
        tree = libfdt.Fdt.create_empty_tree(1024)
        node = tree.add_subnode(0, 'device')
        tree.setprop_str(node, 'compatible', 'emberbsd,test')
        self.assertEqual(tree.getprop(node, 'compatible').as_str(), 'emberbsd,test')
        self.assertEqual(tree.path_offset('/device'), node)
        prop = tree.get_property_by_offset(tree.first_property_offset(node))
        self.assertEqual(prop.name, 'compatible')
        self.assertEqual(prop.as_str(), 'emberbsd,test')
        next_node, depth = tree.next_node(0, 0)
        self.assertEqual((next_node, depth), (node, 1))

    def test_missing_property_is_reported(self):
        tree = libfdt.Fdt.create_empty_tree(1024)
        with self.assertRaises(libfdt.FdtException):
            tree.getprop(0, 'missing')

    def test_invalid_tree_is_rejected(self):
        with self.assertRaises(libfdt.FdtException):
            libfdt.Fdt(b'invalid')


if __name__ == '__main__':
    unittest.main()
