import re
import os
from os import listdir, path
import py7zr
import argparse

WORKDIR='/roms'

def file_sort(file_info):
    score = 0
    if 'U' in file_info['langs']:
        score += 10000
    if '!' in file_info['metas']:
        score += 1000
    if len(file_info['metas']) == 0:
        score += 100
    if file_info['version']:
        score += file_info['version']
    return score

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--src_dir', help="source directory of 7z roms",
                        action='store', required=True)
    parser.add_argument('--dest_dir', help="destination directory of 7z roms",
                        action='store', required=True)
    parser.add_argument('--dry_run', help="don't write files",
                        action='store_true')
    parser.add_argument('--debug', help="print all matched filenames",
                        action='store_true')

    return parser.parse_args()

def read_src_dir(src_dir):

    games = {}
    lang_re = re.compile('\s*\((.*?)\)\s*')
    meta_re = re.compile('\s*\[(.*?)\]\s*')
    name_re = re.compile('^(.*?)\s*[\(\.\[]')
    zip_re = re.compile('\.7z$')

    for f in listdir(src_dir):
        filename = path.join(WORKDIR, src_dir, f)
        if not path.isfile(filename) or not zip_re.search(filename):
            continue

        print("Inspecting " + filename)
        z_files = []
        with py7zr.SevenZipFile(filename, 'r') as archive:
            z_files = archive.getnames()

        for z_file in z_files:
            langs = lang_re.findall(z_file)
            metas = meta_re.findall(z_file)
            name = name_re.findall(z_file)[0]
            version = None
            for lang in langs:
                match = re.findall('V(\d+(?:\.\d+))', lang)
                if match:
                    version = float(match[0])
                    langs.remove(lang)
            is_not_hack = len(list(filter(lambda x: re.search('Hack', x), langs))) == 0
            is_not_proto = (len(list(filter(lambda x: re.search('Prototype', x), langs))) == 0 and
                           not 'Sample' in langs and not 'Beta' in langs and not 'Prototype' in langs)
            is_not_pd = not 'PD' in langs and not 'AD' in langs and not 'MP' in langs
            is_likely_good = '!' in metas or len(metas) == 0
            is_us_game = 'U' in langs or 'UE' in langs
            is_not_new = len(list(filter(lambda x: re.search('20\d+', x), langs))) == 0
            if is_us_game and is_likely_good and is_not_hack and is_not_proto and is_not_pd and is_not_new:
                if not filename in games:
                    games[filename] = []
                games[filename].append({
                    'parent_filename': filename,
                    'filename': z_file,
                    'langs': langs,
                    'metas': metas,
                    'version': version
                })

    return games

def rezip(games, dest_dir, dry_run, debug):
    for name, file_infos in games.items():
        file_infos.sort(key=file_sort, reverse=True)
        if debug:
            print("")
            for file_info in file_infos:
                filename = path.basename(file_info['filename'])
                print(filename)

        filename = path.basename(file_infos[0]['filename'])
        parent_filename = file_infos[0]['parent_filename']
        filename_7z = re.sub('\.\w+$', '.7z', filename)

        tmp_filename = path.join('/tmp/', filename)
        dest_filename = path.join(WORKDIR, dest_dir, filename_7z)
        
        if os.path.exists(dest_filename):
            continue

        print("Creating " + filename_7z)
        if not dry_run:
            with py7zr.SevenZipFile(parent_filename, 'r') as archive:
                archive.extract(path='/tmp', targets=filename)

            with py7zr.SevenZipFile(dest_filename, 'w') as z:
                z.write(tmp_filename)
            os.remove(tmp_filename)

args = parse_args()
games = read_src_dir(args.src_dir)
rezip(games, args.dest_dir, args.dry_run, args.debug)
