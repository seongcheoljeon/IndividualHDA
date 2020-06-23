# -*- coding: utf-8 -*-

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.03.18 15:28:25
# modified date:    
# description:      

import os
import sys
import shlex
from imp import reload
from subprocess import Popen, PIPE

import pathlib2

import public

reload(public)


class FFmpegAPI(object):
    def __init__(self):
        pass

    @staticmethod
    def make_image_seq_to_video(
            ffmpeg_dirpath=None, image_seq='/home/scii/test.%04d.jpg', output='/home/scii/out.mp4',
            sf=None, num_frame=None, fps=25, meta_data=None):
        assert isinstance(ffmpeg_dirpath, pathlib2.Path)
        assert isinstance(image_seq, pathlib2.Path)
        assert isinstance(output, pathlib2.Path)
        is_watermark = False
        ffmpeg_bin_dirpath = ffmpeg_dirpath / public.Name.bin_dirname
        if not ffmpeg_bin_dirpath.exists():
            return None
        ffmpeg_bin = ffmpeg_bin_dirpath / public.Name.FFmpeg.ffmpeg_bin_filename
        if meta_data is None:
            meta_str = ''
        else:
            meta_str = ' -metadata author="{author}" -metadata title="{title}" -metadata year="{year}" ' \
                       '-metadata description="{desc}" -metadata copyright="{copyr}" '.format(
                        author=meta_data['author'], title=meta_data['title'], year=meta_data['year'],
                        desc=meta_data['description'], copyr='Copyright (c) 2020 SeongcheolJeon')
        if is_watermark:
            cmd = '''
            {ff_binpath} -start_number {sf} -y -f image2 -i {img_seqpath} -i {watermark_imgpath} 
            -filter_complex "[1]format=bgra,colorchannelmixer=aa=0.5,scale=iw*0.5:-1[wm];[0][wm]overlay=10:10" 
            {metadata} -async 1 -r {fps} -vframes {nframe} {out}
            '''.format(
                ff_binpath=ffmpeg_bin.as_posix(), sf=sf, img_seqpath=image_seq.as_posix(),
                watermark_imgpath=public.Paths.icons_hda_default_filepath.as_posix(),
                fps=fps, nframe=num_frame, out=output.as_posix(), metadata=meta_str)
        else:
            cmd = '''
            {ff_binpath} -start_number {sf} -y -f image2 -i {img_seqpath}
            {metadata} -async 1 -r {fps} -vframes {nframe} {out}
            '''.format(
                ff_binpath=ffmpeg_bin.as_posix(), sf=sf, img_seqpath=image_seq.as_posix(),
                watermark_imgpath=public.Paths.icons_hda_default_filepath.as_posix(),
                fps=fps, nframe=num_frame, out=output.as_posix(), metadata=meta_str)
        result = Popen(shlex.split(cmd), stdout=PIPE, stderr=PIPE)
        out, err = result.communicate()
        out = out.decode('utf8')
        exitcode = result.returncode
        if exitcode != 0:
            print('{0}, {1}, {2}'.format(exitcode, out.decode('utf8'), err.decode('utf8')))
        return exitcode

    @staticmethod
    def play_video(ffmpeg_dirpath=None, video_filepath=None):
        assert isinstance(ffmpeg_dirpath, pathlib2.Path)
        assert isinstance(video_filepath, pathlib2.Path)
        ffmpeg_bin_dirpath = ffmpeg_dirpath / public.Name.bin_dirname
        if not ffmpeg_bin_dirpath.exists():
            return None
        if not video_filepath.exists():
            return None
        ffmpeg_play = ffmpeg_bin_dirpath / public.Name.FFmpeg.ffmpeg_play_filename
        cmd = '''{ff_playpath} -probesize 40'''.format(ff_playpath=ffmpeg_play.as_posix())
        # 띄어쓰기가 존재하는 파일이름의 경우 shlex로 가공하면, 제대로 안된다. 그래서 아래처럼 바꿈...
        cmd_lst = shlex.split(cmd) + [video_filepath.as_posix()]
        result = Popen(cmd_lst, stdout=PIPE, stderr=PIPE)
        out, err = result.communicate()
        out = out.decode('utf8')
        exitcode = result.returncode
        if exitcode != 0:
            sys.stderr.write(exitcode, out.decode('utf8'), err.decode('utf8'))
        return exitcode

    # 비디오 정보를 json 형식 반환
    @staticmethod
    def video_info(ffmpeg_dirpath=None, video_filepath=None):
        if ffmpeg_dirpath is None:
            return None
        assert isinstance(ffmpeg_dirpath, pathlib2.Path)
        assert isinstance(video_filepath, pathlib2.Path)
        ffmpeg_bin_dirpath = ffmpeg_dirpath / public.Name.bin_dirname
        if not ffmpeg_bin_dirpath.exists():
            return None
        # 한글로 된 파일인 경우, pathlib2.Path.exists() 함수가 안되어서 os 모듈을 이용함... python3에서는 이 문제 해결된듯..
        if not os.path.exists(video_filepath.as_posix()):
            return None
        ffmpeg_probe = ffmpeg_bin_dirpath / public.Name.FFmpeg.ffmpeg_probe_filename
        cmd = '''
        {ff_probepath} -loglevel quiet -print_format json -show_format -show_streams
        '''.format(ff_probepath=ffmpeg_probe.as_posix())
        # 띄어쓰기가 존재하는 파일이름의 경우 shlex로 가공하면, 제대로 안된다. 그래서 아래처럼 바꿈...
        cmd_lst = shlex.split(cmd) + [video_filepath.as_posix()]
        result = Popen(cmd_lst, stdout=PIPE, stderr=PIPE)
        out, err = result.communicate()
        out = out.decode('utf8')
        exitcode = result.returncode
        if exitcode != 0:
            sys.stderr.write(exitcode, out, err.decode('utf8'))
            return None
        return eval(out)


if __name__ == '__main__':
    pass
