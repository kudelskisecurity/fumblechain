class Address:
    """Represents an IPv4 address."""

    def __init__(self, address):
        # address is a tuple (ip, port)
        self.address = address

    @staticmethod
    def parse(string):
        '''static function to parse ip,port from string'''
        ip = ''
        if ':' not in string:
            port = int(string)
        else:
            fields = string.split(':')
            ip = fields[0]
            port = int(fields[1])
        if not ip:
            ip = '127.0.0.1'
        return (ip, port)
