import re
import os
from os import listdir, path
from shutil import copyfile
import py7zr
import argparse

WORKDIR='/roms'

def good_file_sort(file_info):
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


def ia_file_sort(file_info):
    score = 0
    if 'USA' in file_info['langs']:
        score += 10000
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
    parser.add_argument('--ia', help="use internet archive formatting",
                        action='store_true')

    return parser.parse_args()

lang_re = re.compile('\s*\((.*?)\)\s*')
meta_re = re.compile('\s*\[(.*?)\]\s*')
name_re = re.compile('^(.*?)\s*[\(\.\[]')
sev_zip_re = re.compile('\.7z$')
reg_zip_re = re.compile('\.zip$')


def parse_ia_rom(z_file):
    metas = lang_re.findall(z_file)
    langs = re.split('\s*,\s*', metas.pop(0))
    name = name_re.findall(z_file)[0]
    version = None
    for meta in metas:
        match = re.findall('Rev (\w+)', meta)
        if match:
            version = match[0]
            if re.match('[a-zA-Z]', version):
                version = ord(version) - 92
            else:
                version = int(version)
            metas.remove(meta)

    return name, langs, metas, version


def parse_good_rom(z_file):
    langs = lang_re.findall(z_file)
    metas = meta_re.findall(z_file)
    name = name_re.findall(z_file)[0]
    version = None
    for lang in langs:
        match = re.findall('V(\d+(?:\.\d+))', lang)
        if match:
            version = float(match[0])
            langs.remove(lang)

    return name, langs, metas, version


def filter_good_rom(name, langs, metas):
    is_not_hack = len(list(filter(lambda x: re.search('Hack', x), langs))) == 0
    is_not_proto = (len(list(filter(lambda x: re.search('Prototype', x), langs))) == 0 and
                   not 'Sample' in langs and not 'Beta' in langs and not 'Prototype' in langs)
    is_not_pd = not 'PD' in langs and not 'AD' in langs and not 'MP' in langs
    is_likely_good = '!' in metas or len(metas) == 0
    is_us_game = 'U' in langs or 'UE' in langs
    is_not_new = len(list(filter(lambda x: re.search('20\d+', x), langs))) == 0

    return is_us_game and is_likely_good and is_not_hack and is_not_proto and is_not_pd and is_not_new


def filter_ia_rom(name, langs, metas):
    is_not_hack = len(list(filter(lambda x: re.search('Hack', x), metas))) == 0
    is_not_proto = (len(list(filter(lambda x: re.search('Proto', x), metas))) == 0 and
                   not 'Sample' in metas and not 'Beta' in metas and not 'Prototype' in metas and
                   not 'Virtual Console' in metas and not 'Demo' in metas and not 'Unl' in metas)
    is_not_pd = not 'PD' in metas and not 'AD' in metas and not 'MP' in metas
    is_not_video = not re.match('^Game Boy Advance Video', name)
    is_us_game = 'USA' in langs or 'World' in langs

    return is_us_game and is_not_hack and is_not_proto and is_not_pd and is_not_video


def read_src_dir(src_dir, is_ia):

    games = {}

    zip_re = sev_zip_re
    filter_rom = filter_good_rom
    parse_rom = parse_good_rom

    if is_ia:
        zip_re = reg_zip_re
        filter_rom = filter_ia_rom
        parse_rom = parse_ia_rom

    for f in listdir(src_dir):
        filename = path.join(WORKDIR, src_dir, f)
        if not path.isfile(filename) or not zip_re.search(filename):
            continue

        print("Inspecting " + filename)
        z_files = []
        if is_ia:
            z_files = [path.basename(filename)]
        else:
            with py7zr.SevenZipFile(filename, 'r') as archive:
                z_files = archive.getnames()

        for z_file in z_files:
            name, langs, metas, version = parse_rom(z_file)

            if filter_rom(name, langs, metas):
                uniq_name = filename
                if is_ia:
                    uniq_name = name
                if not uniq_name in games:
                    games[uniq_name] = []
                games[uniq_name].append({
                    'parent_filename': filename,
                    'filename': z_file,
                    'langs': langs,
                    'metas': metas,
                    'version': version
                })

    return games


def rezip(games, dest_dir, dry_run, debug, is_ia):
    file_sort = good_file_sort
    if is_ia:
        file_sort = ia_file_sort

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
        if is_ia:
            dest_filename = path.join(WORKDIR, dest_dir, filename)
        
        if os.path.exists(dest_filename):
            continue

        print("Creating " + dest_filename)
        if dry_run:
            continue

        if is_ia:
            copyfile(parent_filename, dest_filename)
        else:
            with py7zr.SevenZipFile(parent_filename, 'r') as archive:
                archive.extract(path='/tmp', targets=filename)

            with py7zr.SevenZipFile(dest_filename, 'w') as z:
                z.write(tmp_filename)
            os.remove(tmp_filename)

args = parse_args()
games = read_src_dir(args.src_dir, args.ia)
rezip(games, args.dest_dir, args.dry_run, args.debug, args.ia)
