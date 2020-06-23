# -*- coding: utf-8 -*-

# author:           seongcheol jeon
# email:            saelly55@gmail.com
# create date:      2020.02.17 03:11:54
# modified date:    
# description:      

import logging


class LogHandler(logging.Handler):
    def __init__(self, out_stream=None):
        super(LogHandler, self).__init__()
        # log text msg format
        self.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] : %(message)s'))
        logging.getLogger().addHandler(self)
        # logging level
        logging.getLogger().setLevel(logging.DEBUG)
        self.__out_stream = out_stream

    def emit(self, record):
        msg = self.format(record)
        self.__out_stream.append(msg)

    @staticmethod
    def log_msg(method=None, msg=''):
        if method is None:
            return
        if method.__name__ == 'info':
            new_msg = '<font color=#dddddd>{msg}</font>'.format(msg=msg)
        elif method.__name__ == 'debug':
            new_msg = '<font color=#23bcde>{msg}</font>'.format(msg=msg)
        elif method.__name__ == 'warning':
            new_msg = '<font color=#cc9900>{msg}</font>'.format(msg=msg)
        elif method.__name__ == 'error':
            new_msg = '<font color=#e32474>{msg}</font>'.format(msg=msg)
        elif method.__name__ == 'critical':
            new_msg = '<font color=#ff0000>{msg}</font>'.format(msg=msg)
        else:
            raise TypeError('[log method] unknown type')
        method(new_msg)


if __name__ == '__main__':
    pass
