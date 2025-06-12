"""Command line interface for Mazda IDS parser."""

import argparse
import sys
from ids import IDSContext, IDSKey, browse


def main(argv=None):
    """Entry point for the IDS command line interface."""
    if argv is None:
        argv = sys.argv
    parser = argparse.ArgumentParser(prog=argv[0], description="IDS")
    parser.add_argument("--lang", action="store", default="ENG", help="Default language")
    parser.add_argument("root")
    args = parser.parse_args(argv[1:])

    ctx = IDSContext(args)

    ctx.mnemonics()
    ctx.texts()

    recs = ctx.load_rec("MCP_FILE_INFO_REC")
    obj = recs[IDSKey("PSR8-188K2-B", "PSR8-188K2-B")]
    browse(ctx, obj)


if __name__ == "__main__":
    main()
