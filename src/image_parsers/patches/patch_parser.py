import json
import pathlib


class PatchParser:
    """
    Parses patch files in find-replace or address-data formats.
    """

    def parse_patch(self, file):
        ext = pathlib.Path(file).suffix.lower()
        if ext == ".json":
            return self.parse_json(file)
        elif ext == ".ips":
            return self.parse_ips(file)
        elif ext == ".jmp":
            return self.parse_jmp(file)
        else:
            return None

    def parse_json(self, file):
        try:
            with open(file, 'r') as f:
                patch = json.load(f)
            # Validation
            if "data" not in patch:
                return None
            for entry in patch["data"]:
                if "operations" not in entry:
                    return None
                for elem in entry["operations"]:
                    valid_patch = "patched_data" in elem
                    valid_info = "original_data" in elem or "address" in elem
                    valid = valid_patch and valid_info
                    if not valid:
                        return None
                if "file" not in patch:
                    patch["file"] = "default.xbe"
            name = file[:-5]
            if "title_id" not in patch:
                patch["title_id"] = None
            if "name" not in patch:
                patch["name"] = name
            if "author" not in patch:
                patch["author"] = None
            return patch
        except Exception as e:
            print(e)
            return None

    def parse_ips(self, file):
        res = []
        with open(file, 'rb') as f:
            header = f.read(5)
            if header != b'PATCH':
                return None
            address = f.read(3)
            while address != b'EOF':
                int_address = int.from_bytes(address, "big")
                length = int.from_bytes(f.read(2), "big")
                if length == 0:
                    run_length = int.from_bytes(f.read(2), "big")
                    byte = f.read(1)
                    payload = byte * run_length
                else:
                    payload = f.read(length)
                payload = payload.hex().upper()
                res.append({"address": int_address, "patched_data": payload})
                address = f.read(3)
        name=file[:-4]
        return {
            "name": name,
            "title_id": None,
            "author": None,
            "data": [{"file": "default.xbe", "operations": res}]
        }

    def parse_jmp(self, file):
        try:
            with open(file, 'r') as f:
                header = f.readline().rstrip()
                if header != "#Jay's Magic Patcher (www.jayxbox.com)":
                    return None
                system = f.readline().rstrip()
                if system != "system=Xbox":
                    return None
                game_title = f.readline().rstrip().split("=")[1]
                region = f.readline().rstrip().split("=")[1]
                version = f.readline().rstrip().split("=")[1]
                author = f.readline().rstrip().split("=")[1]
                notes = f.readline().rstrip().split("=")[1]

                clean = ".xbe" not in notes
                operations = []
                line = f.readline().rstrip()
                line_find = None
                line_replace = None
                while line:
                    if line[0] != "#":
                        if line_find is None:
                            line_find = line
                        elif line_replace is None:
                            line_replace = line
                            operations.append({
                                "original_data": line_find,
                                "patched_data": line_replace
                            })
                            line_find = None
                            line_replace = None
                    else:
                        clean = clean and ".xbe" not in line
                    line = f.readline().rstrip()

                title_id = version.split(" ")[0].lower()
                patched_file = "default.xbe" if clean else None
                patch_name = pathlib.Path(file).suffix.lower()
                data = [{"file": patched_file, "operations": operations}]

                return {
                    "name": file[:-4],
                    "title_id": title_id,
                    "author": author,
                    "data": data
                }
        except Exception as e:
            print(str(e))
            return None
