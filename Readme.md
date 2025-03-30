This is a Python 3 implementation of an HTTP server that acts as a wrapper between Xbox images on the filesystem and [xemu](https://github.com/xemu-project/xemu).

Its purposes are:
- Loading images not in standard XISO format (e.g. Redump-style images and unpacked files)
- Applying patches (e.g. widescreen patches) on the fly, without modifying any files

Command line arguments:
- `--dvd_path PATH_TO_FILE`: starts the server in the directory of the file and launches xemu passing the corresponding URL as `dvd_path`
- `--xemu_path PATH_TO_EXE`: specifies the path to the xemu executable (required if `--dvd_path` is used)
- `--patches PATH1 PATH2 PATH3 ...`: applies the specified patches (see below for the supported formats, note that they won't be applied if the title_id (if present) does not match the current image), make sure you're using unmodified XBEs to avoid issues
- `--apply_media_patch`: applies a media patch on the default.xbe file (it is done automatically for Redump-style images)
- `--port PORT`: the port to use for the server (default is 8000)
- `--verbose`: enables verbose output (outputs the files included in the range for each request among other things)

For all arguments make sure to use full paths to avoid issues.

Examples of usage (on Windows):
- `python src/server.py --dvd_path "D:\Folder\Example\default.xbe" --xemu_path "D:\xemu\xemu.exe"`
- `python src/server.py --dvd_path "D:\Folder\example.iso" --xemu_path "D:\xemu\xemu.exe" --patches "D:\Folder\patch1.ips" "D:\Folder\patch2.jmp"`

To use this you need a build of xemu with support for loading files via URLs, you can get one from [this fork](https://github.com/wilkovatch/xemu/tree/fix/aio-win32). (see [the workflow on the latest commit](https://github.com/wilkovatch/xemu/actions/runs/14146282702) for the builds, note that you have to be logged into GitHub to download them, if they expired fork it and it should build again)

Supported formats for images:
- Standard XISO
- Redump-style XISO
- Unpacked files (use the path of the default.xbe file like in the above example)
- (Experimental, slow) Zipped files (e.g. the default.xbe and the other files in a single .zip file)

Supported formats for patches:
- JSON (see the `get_media_patch` method in `src/image_parsers/patches/patcher.py` for an example, note that an address (integer, field `address`) can be provided instead of the original data)
- IPS
- JMP (used in patches from [this repository](https://github.com/JayYardley/Xbox-Magic-Patches-by-Jay))
