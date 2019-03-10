"""Fix tracking of migrated files.

Attempted to copy over svg files with name of old sub_dir to the new, but easier just to manually arrange.

"""

import json
import logging

from make import SiteCompiler

# Debugging options
preview = False

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, filename='fix_file_reorganization.log', filemode='w')

logger.debug('With preview = {}, parsing dir: {}'.format(preview, SiteCompiler.DIR_DIST_IMGS))


def count_glob(pth, pattern):
    """Return the number of glob matches."""
    return len([str(match) for match in pth.glob(pattern)])


# Find all created files
matches = {}
for fn in SiteCompiler.DIR_DIST_IMGS.glob('*.*'):
    key = '-'.join(fn.name.split('-')[1:]).replace(fn.suffix, '')
    if key not in matches:
        matches[key] = []
    matches[key].append(fn.name)

# Filter for multiple matches
rem_keys = []
for key, fns in matches.items():
    if len(fns) > 1:
        logger.debug('{}\n\tIssue with key: {} / {}'.format('-' * 80, key, fns))
        mapping = {
            'img': {'source': None, 'sink': None},
            'svg': {'source': None, 'sink': None},
        }
        for fn in fns:
            # Remove leading 'placeholder' from name
            sub_dir = fn.split('-')[0]
            if fn.endswith('svg'):
                img_type = 'svg'
                sub_dir = sub_dir.split('_')[1]
            else:
                img_type = 'img'
            # If the file exists, then it is a 'sink' and needs to be overwritten by the source file
            src_pth = SiteCompiler.DIR_SRC / sub_dir
            direction = 'sink' if count_glob(src_pth, '{}.json'.format(key)) == 1 else 'source'
            logger.debug('Checking ({}): {} for: {}'.format(direction, src_pth, fn))
            mapping[img_type][direction] = SiteCompiler.DIR_DIST_IMGS / fn

        # Replace sink items with the source
        for flow in mapping.values():
            noSink = flow['sink'] is None
            noSource = flow['source'] is None
            if not(noSink or noSource):
                logger.debug('Delete: {}\n\tAnd replace with: {}'.format(flow['sink'], flow['source']))
                # TODO: this didn't really work...
                # if not preview:
                #     flow['sink'].unlink()
                #     flow['source'].rename(flow['sink'])
            elif (noSink and noSource) or noSource:
                pass
            else:
                logger.debug('{}\n\tError in flow: {}'.format('=' * 80, flow))

    else:
        rem_keys.append(key)

# Cleanup object for logging
for key in rem_keys:
    matches.pop(key, None)
logger.debug(json.dumps(matches, indent=4, separators=(',', ': '), sort_keys=True))
