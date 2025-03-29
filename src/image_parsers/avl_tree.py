"""
AVL Tree implementation with support for byte range search
for nodes with a "size" parameter
"""

class AVLTree:
    """
    An AVL tree with support for byte range search.
    The entries are expected to be dictionaries with:
    - offset (int or string, it's the node value)
    - size (int, for byte range search, only when the offset is int)
    - data (dictionary or string)
    """

    class Node:
        def __init__(self, value, size, data):
            self.value = value
            self.size = size
            self.data = data
            self.left = None
            self.right = None
            self.height = 1

        def update_height(self):
            self.height = 1 + max(self.get_height(self.left),
                                  self.get_height(self.right))

        def get_height(self, node):
            return 0 if node is None else node.height

        def get_balance_factor(self):
            return self.get_height(self.left) - self.get_height(self.right)

    def __init__(self, entries):
        self.root = None
        self.populate(entries)

    def populate(self, entries):
        for f in entries:
            value = entries[f]["offset"]
            size = entries[f]["size"]
            data = entries[f]["data"] if "data" in entries[f] else f
            self.root = self.insert_node(self.root, value, size, data)

    def to_list(self):
        """
        Traverses the tree in preorder and returns the nodes in a list
        """
        res = []
        self.traverse_tree(self.root, res)
        return res

    def traverse_tree(self, node, res):
        res.append(node)
        if node.left:
            self.traverse_tree(node.left, res)
        if node.right:
            self.traverse_tree(node.right, res)

    def get_nodes_in_range(self, start, end):
        """
        Retrieves the nodes within a byte range (delimited by start and end),
        plus start and end padding entries if needed, with the byte range and
        padding for each node.
        """
        res = []
        self.search_nodes_in_range(self.root, start, end, res)

        # padding for the first file
        if len(res) > 0:
            res[0]["start_padding"] = max(0, res[0]["offset"] - start)

        # calculate paddings
        for i in range(len(res) - 1):
            e0 = res[i]
            e1 = res[i + 1]
            padding = e1["offset"] - (e0["offset"] + e0["size"])
            max_padding_needed = end - (e0["offset"] + e0["size"])
            padding_needed = min(padding, max_padding_needed)
            res[i]["end_padding"] = padding_needed

        # padding for the last file
        if len(res) > 0:
            end_padding = max(0, end - (res[-1]["offset"] + res[-1]["size"]))
            res[-1]["end_padding"] = end_padding

        # empty area, padding only
        if len(res) == 0:
            res.append({
                'file': 'PAD:PAD',
                'start': start,
                'end': end,
                'size': end - start,
                'end_padding': 0,
                'start_padding': 0
            })

        return res

    def search_nodes_in_range(self, node, start, end, res):
        s = start
        e = end

        if node is None:
            return

        if s <= node.value + node.size and node.value <= e:
            self.search_nodes_in_range(node.left, s, e, res)

            res.append({
                "file": node.data,
                "start": max(0, s - node.value),
                "end": min(node.size, e - node.value),
                "size": node.size,
                "offset": node.value,
                "start_padding": 0,
                "end_padding": 0
            })

            self.search_nodes_in_range(node.right, s, e, res)

        elif node.value + node.size < s:
            self.search_nodes_in_range(node.right, s, e, res)

        elif node.value > e:
            self.search_nodes_in_range(node.left, s, e, res)

    def insert_node(self, root, value, size, data):
        # insert the node
        if root is None:
            return self.Node(value, size, data)
        elif value < root.value:
            root.left = self.insert_node(root.left, value, size, data)
        else:
            root.right = self.insert_node(root.right, value, size, data)
        root.update_height()

        # balance the tree
        bf = root.get_balance_factor()
        if bf > 1:
            if value < root.left.value:
                return self.rotate_right(root)
            else:
                root.left = self.rotate_left(root.left)
                return self.rotate_right(root)

        if bf < -1:
            if value > root.right.value:
                return self.rotate_left(root)
            else:
                root.right = self.rotate_right(root.right)
                return self.rotate_left(root)

        return root

    def rotate_left(self, x):
        z = x.right
        t23 = z.left
        z.left = x
        x.right = t23
        x.update_height()
        z.update_height()
        return z

    def rotate_right(self, x):
        z = x.left
        t23 = z.right
        z.right = x
        x.left = t23
        x.update_height()
        z.update_height()
        return z
