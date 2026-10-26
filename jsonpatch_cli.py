# -*- coding: utf-8 -*-

""" The jsondiff and jsonpatch command line programs """

import sys
import os.path
import json
import jsonpatch
import tempfile
import argparse


jsondiff_parser = argparse.ArgumentParser(
    prog='jsondiff', description='Diff two JSON files')
jsondiff_parser.add_argument('FILE1', type=argparse.FileType('r', encoding='utf-8'))
jsondiff_parser.add_argument('FILE2', type=argparse.FileType('r', encoding='utf-8'))
jsondiff_parser.add_argument('--indent', type=int, default=None,
                             help='Indent output by n spaces')
jsondiff_parser.add_argument('-u', '--preserve-unicode', action='store_true',
                             help='Output Unicode character as-is without using Code Point')
jsondiff_parser.add_argument('-v', '--version', action='version',
                             version='%(prog)s ' + jsonpatch.__version__)


def jsondiff_main():
    try:
        diff_files()
    except KeyboardInterrupt:
        sys.exit(1)


def diff_files():
    """ Diffs two JSON files and prints a patch """
    args = jsondiff_parser.parse_args()
    doc1 = json.load(args.FILE1)
    doc2 = json.load(args.FILE2)
    patch = jsonpatch.make_patch(doc1, doc2)
    if patch.patch:
        print(json.dumps(patch.patch, indent=args.indent, ensure_ascii=not(args.preserve_unicode)))
        sys.exit(1)


jsonpatch_parser = argparse.ArgumentParser(
    prog='jsonpatch',
    description='Apply a JSON patch on a JSON file')
jsonpatch_parser.add_argument('ORIGINAL', type=argparse.FileType('r', encoding='utf-8'),
                              help='Original file')
jsonpatch_parser.add_argument('PATCH', type=argparse.FileType('r', encoding='utf-8'),
                              nargs='?', default=sys.stdin,
                              help='Patch file (read from stdin if omitted)')
jsonpatch_parser.add_argument('--indent', type=int, default=None,
                              help='Indent output by n spaces')
jsonpatch_parser.add_argument('-b', '--backup', action='store_true',
                              help='Back up ORIGINAL if modifying in-place')
jsonpatch_parser.add_argument('-i', '--in-place', action='store_true',
                              help='Modify ORIGINAL in-place instead of to stdout')
jsonpatch_parser.add_argument('-v', '--version', action='version',
                              version='%(prog)s ' + jsonpatch.__version__)
jsonpatch_parser.add_argument('-u', '--preserve-unicode', action='store_true',
                              help='Output Unicode character as-is without using Code Point')

def jsonpatch_main():
    try:
        patch_files()
    except KeyboardInterrupt:
        sys.exit(1)


def patch_files():
    """ Applies a JSON patch on a JSON file """
    args = jsonpatch_parser.parse_args()
    doc = json.load(args.ORIGINAL)
    patch = json.load(args.PATCH)
    result = jsonpatch.apply_patch(doc, patch)

    if args.in_place:
        # 2026-10-11: Release the input handle before replacing it on Windows.
        args.ORIGINAL.close()
        dirname = os.path.abspath(os.path.dirname(args.ORIGINAL.name))

        fd = None
        try:
            # Attempt to replace the file atomically.  We do this by
            # creating a temporary file in the same directory as the
            # original file so we can atomically move the new file over
            # the original later.  (This is done in the same directory
	    # because atomic renames do not work across mount points.)

            fd, pathname = tempfile.mkstemp(dir=dirname)
            fp = os.fdopen(fd, 'w', encoding='utf-8')
            atomic = True

        except OSError:
            # mkstemp may have succeeded before fdopen failed. Neither the
            # descriptor nor the temporary file belongs to the fallback.
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
                try:
                    os.unlink(pathname)
                except OSError:
                    pass
            # We failed to create the temporary file for an atomic
            # replace, so fall back to non-atomic mode by backing up
            # the original (if desired) and writing a new file.

            if args.backup:
                os.rename(args.ORIGINAL.name, args.ORIGINAL.name + '.orig')
            fp = open(args.ORIGINAL.name, 'w', encoding='utf-8')
            atomic = False

    else:
        # Since we're not replacing the original file in-place, write
        # the modified JSON to stdout instead.

        fp = sys.stdout

    # By this point we have some sort of file object we can write the 
    # modified JSON to.
    
    try:
        json.dump(result, fp, indent=args.indent, ensure_ascii=not(args.preserve_unicode))
        fp.write('\n')
        if args.in_place:
            fp.close()
    except BaseException:
        if args.in_place:
            # Cleanup must not replace the original output error.
            try:
                fp.close()
            except OSError:
                pass
            if atomic:
                try:
                    os.unlink(pathname)
                except OSError:
                    pass
        raise

    if args.in_place:
        if atomic:
            try:
                # Complete the atomic replace by linking the original
                # to a backup (if desired), fixing up the permissions
                # on the temporary file, and moving it into place.

                if args.backup:
                    os.link(args.ORIGINAL.name, args.ORIGINAL.name + '.orig')
                os.chmod(pathname, os.stat(args.ORIGINAL.name).st_mode)
                os.replace(pathname, args.ORIGINAL.name)

            except OSError:
                # Preserve the original if backup, permissions, or replacement
                # fails. replace() can overwrite an existing file on Windows
                # without unlinking it first.
                os.unlink(pathname)
                raise
