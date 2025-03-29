import json


class Patcher():
    """
    Merges patches and applies them to data chunks
    """

    def __init__(self, parser):
        self.parser = parser

    def get_media_patch(self, title_id):
        patch = {
            "title_id": title_id,
            "data": [
                {
                    "file": "default.xbe",
                    "operations": [
                        {
                            "original_data": "E8CAFDFFFF85C07D",
                            "patched_data": "E8CAFDFFFF85C0EB"
                        }
                    ]
                }
            ]
        }
        return patch

    def parse_patches(self, patches, title_id):
        """
        Merges the input patches to have only one address-based patch
        for each file, discarding patches made for other title_ids.
        """
        res = {}
        for patch in patches:
            p_title_id = patch["title_id"].lower()
            if p_title_id != title_id and p_title_id is not None:
                continue
            if p_title_id is None:
                print("Warning: title_id not specified for the current patch")
            if self.parser.verbose:
                print("applying patch: " + json.dumps(patch, indent=4))
            for subpatch in patch["data"]:
                f = subpatch["file"]
                op = subpatch["operations"]
                if f not in res:
                    res[f] = []
                new_operations = self.preprocess_patch(f, op)
                print("applying patch: " + json.dumps(new_operations,
                                                      indent=4))
                res[f].extend(new_operations)
        return res

    def preprocess_patch(self, file, operations):
        """
        Outputs the data addresses for the input patch operations.
        If the input patch only has the original data, it finds the address.
        """
        res = []
        prev_data = None
        count = 0
        for operation in operations:
            if "address" in operation and "patched_data" in operation:
                res.append(operation)
            elif "original_data" in operation and "patched_data" in operation:
                og_data = operation["original_data"]
                if og_data == prev_data:
                    count += 1
                else:
                    count = 0
                address = self.get_data_address(file, og_data, count)
                if address >= 0:
                    new_operation = {
                        "address": address,
                        "patched_data": operation["patched_data"]
                    }
                    res.append(new_operation)
                else:
                    print("Failed to apply patch: " + json.dumps(operation,
                                                                 indent=4))
                prev_data = operation["original_data"]
            else:
                print("Cannot apply patch: " + json.dumps(operation, indent=4))
        return res

    def apply_patch(self, patch, data, start):
        """
        Applies a patch to the specified data chunk.
        Supports partial overlap between the patch and the chunk.
        """
        data_chunk = list(data)
        for operation in patch:
            pdata = bytes.fromhex(operation["patched_data"])
            plen = len(pdata)
            addr = operation["address"]
            for i in range(plen):
                j = addr + i - start
                if j >= 0 and j < len(data_chunk):
                    data_chunk[j] = pdata[i]
        return bytes(data_chunk)

    def get_data_address(self, file, data_str, count):
        """
        Finds the data addrses of the specified data (input as hex string)
        in the specified file. The file is read in 1 MiB chunks.
        """
        # TODO: find all required addresses in one run instead of N runs
        filesize = self.parser.toc["FILE:" + file]["size"]
        chunk_size = 1024*1024
        cur_chunk_addr = 0
        data = bytes.fromhex(data_str)
        addr = -1
        while addr < 0 and cur_chunk_addr < filesize:
            chunk = self.parser.get_file_data(file, cur_chunk_addr, chunk_size)
            addr = chunk.find(data)
            if addr >= 0:
                addr += cur_chunk_addr
            if addr >= 0 and count > 0:
                # resume searching from the current address
                cur_chunk_addr = addr + len(data)
                addr = -1
                count -= 1
            else:
                # go to the next chunk, but make it overlap
                # to cover cases where the data would be across two chunks
                cur_chunk_addr += chunk_size - len(data)
        return addr
