from time import strftime

class Logger:
    """
    Class for Logging purposes
    """

    @staticmethod
    def log(msg):
        prefix = strftime("%b %d %H:%M:%S")+": "
        print prefix + msg
